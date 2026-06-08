import collections
import re
import base64
import hashlib
import math
import time

from .keccak import keccak256


class EIP55ChecksumError(ValueError):
    """
    Raised by parse_ethereum_address when a mixed-case Ethereum input (with
    explicit 0x/0X prefix) fails the EIP-55 checksum — i.e., its case
    pattern disagrees with the canonical case derived from keccak256 of the
    lowercase body.

    Subclasses ValueError so existing handlers that catch ValueError keep
    working; specific callers can catch EIP55ChecksumError for targeted
    handling. See `this.i:3ip55rj1` and review F7 for rationale.
    """
    def __init__(self, address: str, position: int, expected: str, got: str):
        self.address = address
        self.position = position
        self.expected = expected
        self.got = got
        super().__init__(
            f"Ethereum address {address!r} fails EIP-55 checksum: "
            f"position {position} is {got!r}, canonical case is {expected!r}"
        )


# Alphabet metadata. Each parser declares the alphabet of the `core` it
# produces; the tokenizer reads `Parsed.alphabet` directly and dispatches
# without re-guessing from the type name. (See spec-improvement-notes.md
# discussion in the v3 errata commit; the v1/v2 substring guess broke for
# UUID and Ethereum, which carry hex content but non-"hex" type names.)
class Alphabet:
    __slots__ = ('name', 'chars', 'bits_per_char')

    def __init__(self, name, chars, bits_per_char):
        self.name = name
        self.chars = chars
        self.bits_per_char = bits_per_char

    def __repr__(self):
        return f"Alphabet({self.name!r})"

    def __eq__(self, other):
        return isinstance(other, Alphabet) and self.name == other.name

    def __hash__(self):
        return hash(self.name)


BASE58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
BASE32_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"
BASE32_ALPHABET_EITHER_CASE = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ234567"
BASE58_CHECK_LENGTH = 25  # Expected length of Base58Check encoded Bitcoin addresses
BASE64_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
HEX_ALPHABET = "0123456789ABCDEF"
# Bech32 alphabet per BIP-173: 32 chars, intentionally excludes 1/b/i/o
# to reduce visual ambiguity (and '1' doubles as the bech32 separator).
BECH32_ALPHABET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
BECH32_ALPHABET_EITHER_CASE = BECH32_ALPHABET + BECH32_ALPHABET.upper()
# Crockford base32: 32 chars, intentionally excludes I/L/O/U for visual
# disambiguation. Used by ULIDs. The ULID/Crockford spec additionally
# accepts I->1, L->1, O->0 as case-insensitive INPUT aliases; canonical
# OUTPUT form is upper-case from this alphabet.
CROCKFORD32_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
# Base36: digits then uppercase letters. Used by GLEIF LEI (ISO 17442).
# Case-insensitive (LEI normalizes to upper). 36 isn't a power of 2; for
# token-alignment purposes we treat it like BASE58 — 6 effective bits/char,
# 4 chars per 24-bit token (true entropy is ~5.17 bits/char).
BASE36_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
# Decimal: used only by snowflake IDs today. Not a power of 2; treated as
# 4 bits/char for token alignment (6 chars per 24-bit token, matching HEX).
# True entropy density is log2(10) ≈ 3.32 bits/char — the slight overshoot
# from 3.32 to 4 leaves a few low-order quant bits as zero-padding instead
# of entropy. See `this.i:sn0wfl4k` for the design rationale.
DECIMAL_ALPHABET = "0123456789"

# Named alphabet singletons. BASE32 is still deferred — types whose core
# uses base32 (Bitcoin Cash CashAddr, Stellar, IPFS CID v1) still
# declare BASE64 as a placeholder.
HEX       = Alphabet("hex",       HEX_ALPHABET,        4)
BASE58    = Alphabet("base58",    BASE58_ALPHABET,     6)  # ~5.86 bits true; treated as 6 for token alignment
BASE64    = Alphabet("base64",    BASE64_ALPHABET,     6)
# Both base32 (RFC 4648) and bech32 (BIP-173) are 5 bits/char with
# different character sets. At 5 bits/char, 24/5 doesn't divide evenly:
# we choose 4 chars/token (20 bits) and let the spec's bit-extension
# rule pad to 24, rather than 5 chars/token (25 bits) which would
# overshoot the 24-bit quant budget.
BASE32    = Alphabet("base32",    BASE32_ALPHABET,     5)
BECH32    = Alphabet("bech32",    BECH32_ALPHABET,     5)
CROCKFORD32 = Alphabet("crockford32", CROCKFORD32_ALPHABET, 5)
# base36 is used only by GLEIF LEI today. 6 bits/char for token alignment
# (mirrors BASE58); true entropy is ~5.17 bits/char.
BASE36    = Alphabet("base36",    BASE36_ALPHABET,     6)
# decimal is used only by snowflake IDs today. 4 bits/char for token
# alignment (mirrors HEX — 6 chars per 24-bit token); true entropy is
# ~3.32 bits/char.
DECIMAL   = Alphabet("decimal",   DECIMAL_ALPHABET,    4)
# BASE64URL is declared after BASE64URL_ALPHABET below.


# `prefix_semantic` marks a prefix as identity-bearing (it must bind the
# fingerprint) rather than a mere signal. See the "swap test" in docs/spec.md
# and `this.i:s3mpr3fx`. Defaults to False so every existing 5-arg
# Parsed(...) construction keeps the old signal-prefix behavior.
Parsed = collections.namedtuple(
    'Parsed',
    ['type', 'alphabet', 'prefix', 'core', 'suffix', 'prefix_semantic'],
    defaults=(False,),
)
# A tokenized chunk of entropy: its source text, its position, and the 24-bit
# quant derived from it. Defined here beside Parsed (its sibling output type)
# rather than mid-module next to tokenize() where it used to sit.
Token = collections.namedtuple('Token', ['text', 'index', 'quant'])

UUID_REGEX = re.compile(r'^\{?[0-9a-f]{8}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{12}\}?$', re.I)
DID_REGEX = re.compile(r'^(did:[a-z0-9]+:)((?:[a-zA-Z0-9_.-]|%[a-fA-F0-9]{2})+)((/[^?]*)?([?].*)?)$')
STELLAR_REGEX = re.compile(r'^(G|g)([' + BASE32_ALPHABET_EITHER_CASE + ']{55})$')
# Stellar muxed account (strkey 'M…'): version byte 0x60 (med25519) + 32-byte
# ed25519 key + 8-byte memo id + CRC16, base32-encoded to 69 chars total
# (1 prefix + 68 body). Distinct prefix and length from a 'G' account, same
# base32 alphabet. See `this.i:xtra4lph`.
STELLAR_MUXED_REGEX = re.compile(r'^(M|m)([' + BASE32_ALPHABET_EITHER_CASE + ']{68})$')
# Generic bech32 address: <hrp>1<data>, used by Cosmos-SDK chains (cosmos1,
# osmo1, juno1, …) and many others. Detection is made SOUND by validating
# the BIP-173 / BIP-350 checksum (see _bech32_checksum_const); the HRP names
# the chain in the label. Specific bech32 formats (bc1/tb1, ltc1, addr1…)
# have their own parsers that run first. HRP is lowercase letters in
# practice; data part (incl. 6-char checksum) is the bech32 charset.
BECH32_GENERIC_REGEX = re.compile(
    r'^([a-z]{1,83})1([' + BECH32_ALPHABET + ']{8,})$', re.I)
IPFS_CIDV0_REGEX = re.compile(r'^(Qm)([' + BASE58_ALPHABET + ']{44})$')
IPFS_CIDV1_REGEX = re.compile(r'^(b)([' + BASE32_ALPHABET_EITHER_CASE + ']{58,112})$')
EOS_REGEX = re.compile(r"(^[a-z1-5.]{1,11}[a-z1-5]$)|(^[a-z1-5.]{12}[a-j1-5]$)")
CARDANO_SHORT_BYRON_REGEX = re.compile(r'^(Ae2)([' + BASE58_ALPHABET + ']{50})([' + BASE58_ALPHABET + ']{6})$')
CARDANO_LONG_BYRON_REGEX = re.compile(r'^(DdzFF)([' + BASE58_ALPHABET + ']{65})([' + BASE58_ALPHABET + ']{6})$')
CARDANO_SHELLEY_REGEX = re.compile(r'^((?:addr|stake)(?:_test)?1)([' + BECH32_ALPHABET_EITHER_CASE + ']{50,100})([' + BECH32_ALPHABET_EITHER_CASE + ']{6})$')
BITCOIN_CASH_REGEX = re.compile(r'^((?:bitcoincash|bchtest):)?([pq][' + BECH32_ALPHABET_EITHER_CASE + ']{41})$', re.I)
LITECOIN_LEGACY_REGEX = re.compile(r'^(t?L)([' + BASE58_ALPHABET + ']{33})$')
LITECOIN_REGEX = re.compile(r'^(ltc1)([' + BECH32_ALPHABET_EITHER_CASE + ']{38,68})$', re.I)
ETHEREUM_REGEX = re.compile(r'^(0x)?([0-9a-f]{40})$', re.I)
RIPPLE_REGEX = re.compile(r'^(r)([' + BASE58_ALPHABET + ']{33})$')
BITCOIN_LEGACY_REGEX = re.compile(r'^([123mn])([' + BASE58_ALPHABET + ']{21,30})([' + BASE58_ALPHABET + ']{4})$')
BITCOIN_SEGWIT_REGEX = re.compile(r'^(bc1|tb1)([' + BECH32_ALPHABET_EITHER_CASE + ']{39,69})$', re.I)
# SSH public-key wire format (base64-decoded):
#   length(4 BE) + type_string + length + field1 [+ length + field2 + ...]
# Each known type has a base64 prefix that encodes structural overhead
# (length-prefixed type-string, plus constant subsequent fields). The
# prefix is extended to cover the leading bytes of the next length-prefix
# field too — those bytes are structural zeros that would otherwise render
# as identical `AAA…` cells on every key of the same type.
#
# Entry shape: (short_name, match_str, prefix_length).
#   * match_str is the prefix's leading constant portion used to identify
#     the key type.
#   * prefix_length is how many chars are consumed (≥ len(match_str)). When
#     greater, the extra chars are bytes whose values vary per key (e.g.
#     ssh-rsa's modulus-length) but are still structural — pulling them
#     into the prefix region keeps the cells starting on per-key entropy.
#
# Order matters: prefixes that are substrings of others would shadow them
# if checked first. Longer/more-specific prefixes come first.
SSH_KEY_TYPES = [
    # ecdsa: 52-char prefix = type-string-field + curve-name-field +
    # key-length-field (39 bytes total, cleanly aligns to 52 base64 chars).
    # Each curve has its own constant key-length encoding.
    ("ecdsa-nistp256", "AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAABB", 52),
    ("ecdsa-nistp384", "AAAAE2VjZHNhLXNoYTItbmlzdHAzODQAAAAIbmlzdHAzODQAAABh", 52),
    ("ecdsa-nistp521", "AAAAE2VjZHNhLXNoYTItbmlzdHA1MjEAAAAIbmlzdHA1MjEAAACF", 52),
    # rsa: 24-char structural match (type-string + exponent fields), then
    # consume 4 more chars covering 3 of 4 modulus-length bytes. The high
    # 2 bytes of modulus-length are always 0x00 for any realistic RSA
    # key; the 3rd byte is 0x00/0x01/0x02/0x04 depending on key size.
    # That 3rd byte varies per key size, so we can't include it in the
    # match string, but it's still structural data, not entropy.
    ("rsa",            "AAAAB3NzaC1yc2EAAAADAQAB", 28),
    # ed25519: 24-char prefix = type-string-field (15 bytes) + first 3 of
    # 4 key-length-field bytes (0x000000 of the always-32 length).
    ("ed25519",        "AAAAC3NzaC1lZDI1NTE5AAAA", 24),
    # dss: just the type-string field — p/q/g/y lengths and values are
    # variable, nothing more is structurally constant.
    ("dss",            "AAAAB3NzaC1kc3M",         15),
]
# Generic fallback: any AAAA-prefixed base64 blob.
# Anchored ^…$ as defense-in-depth (review F4): currently only reached as
# a fallback inside parse_ssh_key after SSH_LINE_REGEX (which IS anchored)
# fails, but a future refactor that calls SSH_KEY_REGEX on whole input
# directly would otherwise inherit a silent-truncation bug.
SSH_KEY_REGEX = re.compile(r'^(AAAA)([0-9A-Za-z+/]+={0,3})$')
# Full openssh-format line:  <type-string> <base64-payload> [<comment>]
# When present, the leading "<type-string> " is stripped before matching the
# payload, and a trailing " <comment>" is captured as the suffix.
SSH_LINE_REGEX = re.compile(
    r'^(?:(?:ssh-(?:ed25519|rsa|dss)|ecdsa-sha2-nistp(?:256|384|521))\s+)?'
    r'(AAAA[0-9A-Za-z+/]+={0,3})'
    r'(?:\s+(\S.*))?$'
)
HEX_REGEX = re.compile(r'^[a-fA-F0-9]+$')
BASE64URL_NO_PAD_REGEX = re.compile(r'^[A-Za-z0-9-_]+$') # used by CESR
BASE64URL_ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_'
BASE64URL = Alphabet("base64url", BASE64URL_ALPHABET, 6)

# ULID: 26 chars of Crockford base32 (case-insensitive). The Crockford
# spec accepts I, L (-> 1) and O (-> 0) as input aliases, so they appear
# in the regex character class even though the canonical alphabet
# excludes them. U is NOT an alias (excluded to dodge profanity) and
# remains forbidden — hence A-T and V-Z, skipping U.
ULID_REGEX = re.compile(r'^[0-9A-TV-Za-tv-z]{26}$')
LEI_REGEX = re.compile(r'^[0-9A-Z]{20}$', re.I)
# Snowflake: 17-20 ASCII decimal digits. We use [0-9] (NOT \d) so Unicode
# digits like Arabic-Indic ٠-٩ are rejected. Discord/Twitter/Mastodon IDs
# encode a 64-bit integer; 17-20 digits covers everything from the early
# years through near-future IDs. The length filter alone is insufficient
# to disambiguate from arbitrary long decimals — parse_snowflake adds a
# plausible-timestamp range check on the top 42 bits.
SNOWFLAKE_REGEX = re.compile(r'^[0-9]{17,20}$')

# SWHID (Software Heritage IDentifier) core form: swh:1:<type>:<40-hex>.
# <type> is one of snp/rel/rev/dir/cnt; a git commit is `rev` (revision).
# v1 hashes are git-style SHA-1 (40 hex, lowercase canonical). An optional
# trailing `;<qualifiers>` (origin/lines/etc.) is addressing context, not
# entropy, so it is split off into the suffix. Case-insensitive on input;
# scheme/type/hex are normalized to lowercase. See `this.i:g1tha5h0`.
SWHID_REGEX = re.compile(
    r'^(swh:1:(?:snp|rel|rev|dir|cnt):)([0-9a-f]{40})(?:;(.+))?$', re.I)
# gitoid (OmniBOR) form: gitoid:<object-type>:<hash-algo>:<hex>. The hex
# length must match the algorithm (sha1 -> 40, sha256 -> 64); a mismatch
# is rejected rather than silently re-tokenized. Case-insensitive on input.
GITOID_REGEX = re.compile(
    r'^(gitoid:(blob|tree|commit|tag):(sha1|sha256):)([0-9a-f]+)$', re.I)
_GITOID_ALGO_LEN = {"sha1": 40, "sha256": 64}
# Discord epoch: 2015-01-01T00:00:00.000Z = 1420070400000 ms since UNIX
# epoch. Twitter's snowflake epoch is earlier (2010-11-04T01:42:54.657Z)
# but we use Discord's epoch as the lower bound because (a) it is the
# more conservative filter — anything decoding to a pre-2015 timestamp
# under Discord's epoch is rejected even if it would be a valid Twitter
# ID, and (b) Twitter snowflakes from 2010-2014 are increasingly rare in
# entropy-comparison use cases. See `this.i:sn0wfl4k`.
DISCORD_EPOCH_MS = 1420070400000
# Future-acceptance window: 5 years past the current wall clock. Wide
# enough to absorb clock skew and "future" test snowflakes, narrow enough
# to keep false-positive rate on random 18-digit decimals around 3.6%.
_SNOWFLAKE_FUTURE_WINDOW_MS = 5 * 365 * 86400 * 1000


def _now_ms() -> int:
    """Current wall-clock time in unix milliseconds.

    Isolated as a one-line seam (rather than inlining `time.time()` at the
    call site) so the snowflake future-window tests can pin a deterministic
    reference clock and stop depending on the real wall clock — see
    tests/test_snowflake.py and the testability review (TST-F3).
    """
    return int(time.time() * 1000)

# Crockford input-alias translation table: I/L -> 1, O -> 0 (in either
# case). Applied during parse_ulid after the regex match, before
# upper-casing the rest of the string to canonical form.
_CROCKFORD_ALIASES = str.maketrans({
    'I': '1', 'i': '1',
    'L': '1', 'l': '1',
    'O': '0', 'o': '0',
})

MULTIHASH_HASH_FUNCS = {
    0x11: "sha1",
    0x12: "sha2-256",
    0x13: "sha2-512",
    0x14: "sha3-224",
    0x15: "sha3-256",
    0x16: "sha3-384",
    0x17: "sha3-512",
    0x18: "shake-128",
    0x19: "shake-256",
    0x1a: "keccak-224",
    0x1b: "keccak-256",
    0x1c: "keccak-384",
    0x1d: "keccak-512",
    0x22: "blake2b-8",
    0x23: "blake2b-16",
    0x24: "blake2b-24",
    0x25: "blake2b-32",
    0x26: "blake2b-40",
    0x27: "blake2b-48",
    0x28: "blake2b-56",
    0x29: "blake2b-64",
    0x2a: "blake2b-72",
    0x2b: "blake2b-80",
    0x2c: "blake2b-88",
    0x2d: "blake2b-96",
    0x2e: "blake2b-104",
    0x2f: "blake2b-112",
    0x30: "blake2b-120",
    0x31: "blake2b-128",
    0x32: "blake2b-136",
    0x33: "blake2b-144",
    0x34: "blake2b-152",
    0x35: "blake2b-160",
    0x36: "blake2b-168",
    0x37: "blake2b-176",
    0x38: "blake2b-184",
    0x39: "blake2b-192",
    0x3a: "blake2b-200",
    0x3b: "blake2b-208",
    0x3c: "blake2b-216",
    0x3d: "blake2b-224",
    0x3e: "blake2b-232",
    0x3f: "blake2b-240",
    0x40: "blake2b-248",
    0x41: "blake2b-256",
    0xb201: "dbl-sha2-256",
    0xb202: "murmur3-128",
    0xb203: "murmur3-32"
}

# Multicodec content-type codes (the subset that actually appears as a
# CID's content codec). The multicodec table is a registry, not a wire
# format; decoding these codes is label-only — it names what a CID wraps
# without changing the visualized entropy. See `this.i:mult1c0d`.
MULTICODEC_CONTENT = {
    0x00: "identity",
    0x51: "cbor",
    0x55: "raw",
    0x60: "rlp",
    0x70: "dag-pb",
    0x71: "dag-cbor",
    0x72: "libp2p-key",
    0x78: "git-raw",
    0x90: "eth-block",
    0x97: "eth-tx",
    0x0129: "dag-json",
    0x0202: "car",
}


def _read_uvarint(data, pos):
    """Read an unsigned LEB128 varint from `data` at `pos`.

    Returns (value, next_pos), or (None, pos) if the buffer ends mid-varint.
    """
    result = 0
    shift = 0
    while pos < len(data):
        b = data[pos]
        pos += 1
        result |= (b & 0x7F) << shift
        if not (b & 0x80):
            return result, pos
        shift += 7
    return None, pos


def _b32_nopad_decode(s: str) -> bytes:
    """RFC 4648 base32 decode of a lowercase, unpadded multibase body."""
    s = s.upper()
    return base64.b32decode(s + "=" * ((-len(s)) % 8))


def decode_multicodec(cid_bytes: bytes):
    """Decode the leading varints of a binary CIDv1 into a
    (content_codec_name, hash_name) pair, or None if the bytes do not
    describe a recognized version-1 codec/hash.

    This reads only the self-describing prefix bytes; it does not validate
    the digest. Defensive by construction — any malformed/unknown buffer
    yields None and the caller falls back to the plain CID label.
    """
    version, pos = _read_uvarint(cid_bytes, 0)
    if version != 1:
        return None
    codec, pos = _read_uvarint(cid_bytes, pos)
    hash_fn, pos = _read_uvarint(cid_bytes, pos)
    codec_name = MULTICODEC_CONTENT.get(codec)
    hash_name = MULTIHASH_HASH_FUNCS.get(hash_fn)
    if codec_name is None or hash_name is None:
        return None
    return codec_name, hash_name

def _parse_multihash(text):
    """
    See if we can parse text as a Multihash.
    If yes, return Parsed("multihash...", prefix (2 bytes), body, None).
    """
    if text and len(text) >= 3:
        hash_func = MULTIHASH_HASH_FUNCS.get(text[0])
        if hash_func:
            hash_length = int(text[1])
            if len(text) == hash_length + 2:
                # sha2-256 is the near-universal default, so it is elided;
                # any other hash function is shown (see this.i:lbldedup).
                label = "multihash" if hash_func == "sha2-256" else f"multihash {hash_func}"
                return Parsed(label, BASE64, text[0:2], text[2:], None)

def parse_hex_multihash(text) -> Parsed:
    """
    See if we can parse text as a hex-encoded Multihash.
    If yes, return Parsed("hex multihash...", prefix (2 bytes), body, None).
    """
    if text and len(text) >= 6:
        # bytes.fromhex requires even-length input; an odd-length all-hex
        # string would raise ValueError and abort the whole dispatch
        # chain before parse_hex (which DOES check parity) gets a turn.
        # See review F3 in reviews/adversarial-2026-05-27.md.
        if len(text) % 2: return None
        m = HEX_REGEX.match(text)
        if m:
            answer = _parse_multihash(bytes.fromhex(text))
            if answer:
                return Parsed(f"hex {answer.type}", HEX, bytes.hex(answer.prefix).lower(), bytes.hex(answer.core).lower(), None)
            
CESR_1_BYTE_CODES = [
    ("A", "Ed25519 seed", 44),
    ("B", "Ed25519 nt pubkey", 44),
    ("C", "X25519 pub enckey", 44),
    ("D", "Ed25519 pubkey", 44),
    ("E", "Blake3-256", 44),
    ("F", "Blake2b-256", 44),
    ("G", "Blake2s-256", 44),
    ("H", "SHA3-256", 44),
    ("I", "SHA2-256", 44),
    ("J", "secp256k1 seed", 44),
    ("K", "Ed448 seed", 76),
    ("L", "X448 pub enckey", 76),
    ("O", "X25519 priv deckey", 44),
    ("P", "X25519 124 cipher 44 seed", 124),
    ("Q", "secp256r1 seed", 44),
    # Blinding factor is lowercase `a` (44 chars). The capital `Z` is Tag11
    # (12 chars), NOT a blinding factor — earlier code mislabeled it, which
    # both failed to parse real `a...` blinding factors and would have
    # accepted bogus 44-char `Z...` strings. See `this.i:s3mpr3fx`.
    ("a", "blinding factor", 44),
    # FN-DSA (FIPS 206) post-quantum signature scheme. Seeds sit at the
    # 44-char sweet spot; public keys and signatures are large.
    ("c", "FN-DSA-512 seed", 44),
    ("d", "FN-DSA-1024 seed", 44),
    ("e", "FN-DSA-1024 sig", 1708),
    ("b", "FN-DSA-1024 pubkey", 2392),
]
CESR_1_BYTE_LENGTHS = set([x[2] for x in CESR_1_BYTE_CODES])

CESR_2_BYTE_CODES = [
    ("0A", "random 128-bit number", 24),
    ("0B", "Ed25519 sig", 88),
    ("0C", "secp256k1 sig", 88),
    ("0D", "Blake3-512", 88),
    ("0E", "Blake2b-512", 88),
    ("0F", "SHA3-512", 88),
    ("0G", "SHA2-512", 88),
    ("0I", "secp256r1 sig", 88),
]
CESR_2_BYTE_LENGTHS = set([x[2] for x in CESR_2_BYTE_CODES])

CESR_4_BYTE_CODES = [
    ("1AAA", "secp256k1 nt pubkey", 48),
    ("1AAB", "secp256k1 pub/enc key", 48),
    ("1AAC", "Ed448 nt pubkey", 80),
    ("1AAD", "Ed448 pubkey", 80),
    ("1AAE", "Ed448 sig", 156),
    ("1AAH", "X25519 100 cipher 24 salt", 100),
    ("1AAI", "secp256r1 nt pubkey", 48),
    ("1AAJ", "secp256r1 pub/enc key", 48),
    ("1AAR", "FN-DSA-512 sig", 892),
    ("1AAQ", "FN-DSA-512 pubkey", 1200),
]
CESR_4_BYTE_LENGTHS = set([x[2] for x in CESR_4_BYTE_CODES])

            
def parse_cesr(text) -> Parsed:
    """
    See if we can parse text as a CESR.
    If yes, return Parsed("CESR...", prefix, body, None).
    """
    items = None
    len_text = len(text)
    if text:
        code = text[0]
        if code == '0':
            if len_text in CESR_2_BYTE_LENGTHS:
                items = CESR_2_BYTE_CODES
        elif code == '1':
            if len_text in CESR_4_BYTE_LENGTHS:
                items = CESR_4_BYTE_CODES
        else:
            if len_text in CESR_1_BYTE_LENGTHS:
                items = CESR_1_BYTE_CODES
        if items:
            for item in items:
                if text.startswith(item[0]) and len_text == item[2]:
                    if BASE64URL_NO_PAD_REGEX.match(text):
                        # The derivation code is IDENTITY, not a stripped
                        # prefix: the same body under a different code is a
                        # different object (swap test). It is base64url like
                        # the body and sits contiguously at the front, so it
                        # stays IN the core — rendered in the cells AND bound
                        # by the fingerprint (which hashes the core text). The
                        # decoded type ("CESR Ed25519 pubkey") goes in the
                        # label; we do NOT split the code into `prefix`.
                        # See `this.i:s3mpr3fx` and `this.i:h4shtext`.
                        return Parsed(f"CESR {item[1]}", BASE64URL, None,
                                      text, None)

def parse_ssh_key(text) -> Parsed:
    """
    See if we can parse text as an SSH public key.

    Accepts either:
      * a bare base64 payload (`AAAA...`), optionally followed by a
        space-separated comment (e.g., `user@host`); or
      * the full openssh single-line form `<type> <base64> [<comment>]`
        — the leading `<type> ` token is stripped before matching.

    When the base64 prefix matches one of the known type-string encodings
    (ed25519, rsa, dss, ecdsa-nistp256/384/521), the parser returns that
    specific type-name in `type` and the type-string portion as `prefix`
    (so visualization can distinguish per-key entropy from structural
    overhead). For ssh-rsa the prefix also includes the small public
    exponent (`AAAADAQAB` for the universal value 65537), and for
    ecdsa-nistpXXX it includes the redundant curve-name field — both of
    these carry no per-key entropy.

    The trailing comment (if any) is matched so the line still parses, but
    it is a FREE annotation — not a checksum or derivation of the key, and
    freely variable while the key bytes are fixed — so it is DROPPED, not
    surfaced as a suffix. See `this.i:sufxbind`.

    Falls back to a generic `AAAA`-prefix match (legacy behavior) when no
    known type-string is recognized.
    """
    m = SSH_LINE_REGEX.match(text)
    if not m:
        m = SSH_KEY_REGEX.match(text)
        if m:
            return Parsed("SSH key", BASE64, m.group(1), m.group(2), None)
        return None
    payload = m.group(1)
    # group(2) is the trailing comment — a free annotation, dropped (see above).
    for short_name, match_str, prefix_length in SSH_KEY_TYPES:
        if payload.startswith(match_str) and len(payload) >= prefix_length:
            return Parsed(
                # entviz only ever parses SSH *public* keys, so "pubkey" is
                # a constant default and is elided (see this.i:lbldedup).
                f"SSH {short_name}",
                BASE64,
                payload[:prefix_length],
                payload[prefix_length:],
                None,
            )
    legacy = SSH_KEY_REGEX.match(payload)
    if legacy:
        return Parsed("SSH key", BASE64, legacy.group(1), legacy.group(2), None)
    return None

def parse_bitcoin_address(text) -> Parsed:
    """
    See if we can parse text as a Bitcoin address.
    If yes, return Parsed("bitcoin", prefix, body, None).
    """
    m = BITCOIN_LEGACY_REGEX.match(text)
    if m:
        return Parsed("BTC legacy", BASE58, m.group(1), m.group(2), m.group(3))
    m = BITCOIN_SEGWIT_REGEX.match(text)
    if m:
        # Bitcoin SegWit uses bech32 (BIP-173).
        return Parsed("BTC SegWit", BECH32, m.group(1).lower(), m.group(2).lower(), None)

def parse_ripple_address(text) -> Parsed:
    """
    See if we can parse text as a Ripple address.
    If yes, return Parsed("XRP", prefix, body, None).
    """
    m = RIPPLE_REGEX.match(text)
    if m:
        return Parsed("XRP", BASE58, m.group(1), m.group(2), None)

def to_EIP55_address(address: str) -> str:
    """
    Return the canonical EIP-55-cased form of a 40-hex Ethereum address
    (with leading "0x"). Uses Keccak-256 (the original Keccak, NOT NIST
    SHA3-256 — see entviz/keccak.py for why this distinction matters).

    Input may be 40 or 42 chars (with or without 0x prefix), any case.
    Output is the 0x-prefixed 42-char canonical form.
    """
    body = address.lower()
    if body.startswith('0x'):
        body = body[2:]
    digest_hex = keccak256(body.encode('ascii')).hex()
    return '0x' + ''.join(
        c if c.isdigit()
        else (c.upper() if int(digest_hex[i], 16) >= 8 else c.lower())
        for i, c in enumerate(body)
    )


def parse_ethereum_address(text) -> Parsed:
    """
    See if we can parse text as an Ethereum address. Recognition
    requires either:
      - an explicit "0x" / "0X" prefix on a 40-hex-char body, OR
      - EIP-55-style mixed case (at least one uppercase AND one
        lowercase hex letter) on a 40-hex-char body without prefix.

    A bare 40-char single-case hex string without prefix falls through
    to plain hex — "0x" is a generic hex prefix predating Ethereum,
    and a length-40 match alone is too weak a signal.

    For prefix-bearing mixed-case input, enforces lenient B1 EIP-55
    validation (see spec.md "Ethereum (EIP-55) case validation" and
    this.i:3ip55rj1):
      - all-lowercase body: accept ("checksum not asserted").
      - all-uppercase body: accept ("checksum not asserted").
      - mixed-case body matching canonical EIP-55: accept.
      - mixed-case body NOT matching canonical EIP-55: raise
        EIP55ChecksumError identifying the first mismatched position.
        (Crucially we raise rather than return None — silent fall-through
        to parse_hex would re-introduce the F7b silent-normalization bug.)

    In every accepted case, the parsed core is the lowercase 40-hex body.
    The visualization itself does NOT carry the EIP-55 case (which is the
    bug F7b documents: re-deriving canonical case on render meant a bad-
    checksum input rendered identically to a good one).
    """
    m = ETHEREUM_REGEX.match(text)
    if not m:
        return None
    has_prefix = bool(m.group(1))
    body = m.group(2)  # the 40-char hex body, original case

    # Classify case pattern.
    letters = [c for c in body if c.isalpha()]
    has_lower = any(c.islower() for c in letters)
    has_upper = any(c.isupper() for c in letters)
    is_mixed = has_lower and has_upper

    if not has_prefix:
        # Without an explicit 0x prefix we only promote to Ethereum if the
        # case pattern itself is a signal (mixed case). Single-case bodies
        # fall through to parse_hex. We do NOT validate the checksum in
        # this branch — there is no caller-asserted "this is an Ethereum
        # address" signal, and mistakenly rejecting a 40-char hex blob
        # because it happens to be 40 chars would be a foot-gun.
        if not is_mixed:
            return None
        # Mixed-case unprefixed input: still enforce EIP-55 (mixed case IS
        # the signal that the user means EIP-55).
        _validate_eip55(text, body)
    elif is_mixed:
        # Explicit 0x prefix AND mixed case → user is asserting EIP-55.
        _validate_eip55(text, body)
    # else: explicit prefix + single-case body → "checksum not asserted",
    # accepted unchanged per lenient B1.

    # Normalized core is lowercase in all accepted cases. The full 40-char
    # body is the core (no separable suffix — a prior implementation split
    # off the last 8 chars as a fake suffix, which silently dropped them
    # from tokenization and the fingerprint).
    return Parsed("ETH", HEX, "0x", body.lower(), None)


def _validate_eip55(original: str, body: str) -> None:
    """
    Raise EIP55ChecksumError if `body` (40 hex chars, mixed case) does NOT
    match the canonical EIP-55 case derived from keccak256(lower(body)).
    `original` is the user's full input (with prefix) — included in the
    error message so the user can fix the offending position.
    """
    lower_body = body.lower()
    digest_hex = keccak256(lower_body.encode('ascii')).hex()
    for i, c in enumerate(body):
        if not c.isalpha():
            continue
        canonical_upper = int(digest_hex[i], 16) >= 8
        expected = c.upper() if canonical_upper else c.lower()
        if c != expected:
            raise EIP55ChecksumError(
                address=original, position=i, expected=expected, got=c,
            )

def parse_litecoin_address(text) -> Parsed:
    """
    See if we can parse text as a Litecoin address.
    If yes, return Parsed("Litecoin...", prefix, body, None).
    """
    m = LITECOIN_LEGACY_REGEX.match(text)
    if m:
        return Parsed("LTC legacy", BASE58, m.group(1), m.group(2), None)
    m = LITECOIN_REGEX.match(text)
    if m:
        # Modern Litecoin "ltc1..." uses bech32.
        return Parsed("LTC", BECH32, m.group(1).lower(), m.group(2).lower(), None)

def parse_bitcoin_cash_address(text) -> Parsed:
    """
    See if we can parse text as a Bitcoin cash address.
    If yes, return Parsed("Bitcoin cash", prefix, body, None).
    """
    m = BITCOIN_CASH_REGEX.match(text)
    if m:
        # Bitcoin Cash uses CashAddr, which despite being commonly called
        # "base32" actually uses the bech32 alphabet (BIP-173 char set),
        # NOT RFC 4648 base32. Token alignment uses 5 bits/char either way.
        return Parsed("BCH", BECH32, m.group(1), m.group(2).lower(), None)

def parse_cardano_address(text) -> Parsed:
    """
    See if we can parse text as a Cardano address.
    If yes, return Parsed("Cardano...", prefix ("addr", "stake", etc.), body, checksum).
    """
    m = CARDANO_SHORT_BYRON_REGEX.match(text)
    if m:
        return Parsed("ADA Byron", BASE58, m.group(1), m.group(2), m.group(3))
    m = CARDANO_LONG_BYRON_REGEX.match(text)
    if m:
        return Parsed("ADA Byron", BASE58, m.group(1), m.group(2), m.group(3))
    m = CARDANO_SHELLEY_REGEX.match(text)
    if m:
        # Cardano Shelley uses bech32.
        return Parsed("ADA Shelley", BECH32, m.group(1), m.group(2).lower(), m.group(3).lower())

def parse_eos_address(text) -> Parsed:
    """
    See if we can parse text as an EOS address.
    If yes, return Parsed("EOS", None, body (address), None).
    """
    m = EOS_REGEX.match(text)
    if m:
        # F6 (adversarial-2026-06-02): don't let EOS claim a string that is
        # entirely hex-alphabet characters. parse_hex runs before this and
        # already wins for EVEN-length hex, but it returns None for ODD-length
        # hex, so an odd-length all-[a-f1-5] fragment like 'badcafe' would
        # otherwise be mislabeled EOS (and base64-tokenized) when the user
        # means a hex fragment. Real EOS names contain a char in [g-z] or '.'
        # (the EOS alphabet minus the hex overlap), so requiring at least one
        # such character cleanly separates the two without a length floor
        # (which would reject legitimately short EOS system names).
        if all(c in "0123456789abcdef" for c in m.group(0)):
            return None
        # EOS uses a constrained alphabet [a-z1-5.] (32 chars + dot, ~5 bits).
        # Treated as BASE64 alphabet for tokenization for now; a proper
        # narrow-alphabet treatment is a deferred follow-up.
        return Parsed("EOS", BASE64, None, m.group(0), None)

def parse_stellar_address(text) -> Parsed:
    """
    See if we can parse text as a Stellar address.
    If yes, return prefix (G), body (rest of address), and suffix (empty).
    """
    m = STELLAR_REGEX.match(text)
    if m:
        # Stellar uses base32 (RFC 4648).
        return Parsed("XLM", BASE32, m.group(1).upper(), m.group(2).upper(), None)
    m = STELLAR_MUXED_REGEX.match(text)
    if m:
        # Muxed account (M…): same base32 alphabet, longer body (key + memo id).
        return Parsed("XLM muxed", BASE32, m.group(1).upper(), m.group(2).upper(), None)
    
def parse_uuid(text) -> Parsed:
    """
    See if we can parse text as a UUID.
    If yes, return Parsed("UUID", prefix (None), body (lower-case UUID sans punct), suffix (None)).
    """
    m = UUID_REGEX.match(text)
    if m:
        body = m.group(0).lower().replace('-', '').replace('{', '').replace('}', '')
        # A UUID's normalized core is 32 hex characters. Declare HEX so
        # the tokenizer reads each char as 4 bits with the correct
        # alphabet, not as a base64-position lookup.
        return Parsed("UUID", HEX, None, body, None)

def parse_ulid(text) -> Parsed:
    """
    See if we can parse text as a ULID — 26 chars of Crockford base32
    (case-insensitive), per the ULID spec.

    Crockford accepts I, L (-> 1) and O (-> 0) as input aliases for
    visually-similar canonical chars; this parser normalizes them, then
    upper-cases the result to canonical Crockford form. U is NOT an
    alias and is rejected.

    Registered BEFORE parse_hex so that a 26-char string of pure
    [0-9A-F] (which is valid both as hex and as Crockford32) is
    recognized as a ULID, not as plain hex.
    """
    if text is None:
        return None
    m = ULID_REGEX.match(text)
    if not m:
        return None
    normalized = text.translate(_CROCKFORD_ALIASES).upper()
    return Parsed("ULID", CROCKFORD32, None, normalized, None)

def parse_snowflake(text) -> Parsed:
    """
    See if we can parse text as a Twitter/Discord/Mastodon-style snowflake
    ID — a 64-bit integer serialized as 17-20 ASCII decimal digits, with
    the top 42 bits encoding a millisecond timestamp relative to a
    platform-specific epoch.

    Detection requires two filters together:
      1. Length 17-20 and ASCII digits only (SNOWFLAKE_REGEX).
      2. The implied timestamp (top 42 bits + Discord epoch) decodes to a
         date in [2015-01-01, today + 5y]. This rejects almost all
         non-snowflake decimals (bank accounts, phone numbers, random
         integers): random 18-digit decimals fall inside the 5-year
         window about 3.6% of the time, and longer or shorter decimals
         are rejected by length first.

    The integer must fit in 64 bits — a 20-digit decimal can overflow
    (max uint64 = 18446744073709551615, 20 digits). We reject the
    overflow case explicitly.

    Returns Parsed("snowflake", DECIMAL, None, text, None) on a match.
    The core is the verbatim decimal string the user typed — see
    `this.i:sn0wfl4k` for why we deliberately do NOT re-encode to hex.
    """
    if not text:
        return None
    if not SNOWFLAKE_REGEX.match(text):
        return None
    n = int(text)
    if n.bit_length() > 64:
        return None
    ts_ms = (n >> 22) + DISCORD_EPOCH_MS
    now_ms = _now_ms()
    if ts_ms < DISCORD_EPOCH_MS or ts_ms > now_ms + _SNOWFLAKE_FUTURE_WINDOW_MS:
        return None
    return Parsed("snowflake", DECIMAL, None, text, None)


def _lei_checksum_ok(lei: str) -> bool:
    """
    Validate a 20-char uppercase LEI candidate against the ISO/IEC 7064
    MOD 97-10 check. Replace each letter with its base36 numeric value
    (A=10..Z=35), interpret the resulting digit string as a base-10
    integer, and require it ≡ 1 (mod 97). Same algorithm IBAN uses, but
    without the country-code rotation.
    """
    digits = []
    for c in lei:
        if c.isdigit():
            digits.append(c)
        elif 'A' <= c <= 'Z':
            digits.append(str(ord(c) - ord('A') + 10))
        else:
            return False
    return int(''.join(digits)) % 97 == 1

def parse_lei(text) -> Parsed:
    """
    See if we can parse text as a GLEIF Legal Entity Identifier (ISO 17442).
    20 chars total: 4-char LOU + "00" reserved + 12-char entity body +
    2-char MOD 97-10 checksum. Case-insensitive; normalized to upper.

    Returns the ISO 17442 split:
      * prefix = None — the LOU issuer code is IDENTITY, not structural
      * core   = LOU + "00" + 12-char entity body (18 chars, base36)
      * suffix = 2-char MOD 97-10 checksum (bound; see this.i:sufxbind)

    The LOU (the issuing organization's 4-char code) is part of the LEI's
    identity, not framing: the same 12-char entity body under a different
    LOU is a *different registration* (swap test). It is base36 like the
    rest and contiguous at the front, so it stays IN the core — rendered in
    the cells AND bound by the fingerprint. (Earlier versions split LOU+"00"
    off as a structural prefix, leaving the LOU out of the fingerprint — the
    same bug we fixed for CESR codes.) The reserved "00" is constant framing
    but is kept in the core to keep the core a contiguous substring of the
    input (verbatim-fidelity for the text channel); being constant it adds
    no distinguishing bits. See `this.i:s3mpr3fx`.
    """
    if not text:
        return None
    m = LEI_REGEX.match(text)
    if not m:
        return None
    upper = text.upper()
    if upper[4:6] != "00":
        return None
    if not _lei_checksum_ok(upper):
        return None
    return Parsed("LEI", BASE36, None, upper[:18], upper[18:])

def parse_did(text) -> Parsed:
    """
    See if we can parse text as a DID or DID URL.
    If yes, return Parsed("DID", "did:" + method + ":", body (rest of DID1), URL if any).
    """
    m = DID_REGEX.match(text)
    if m:
        # DID method-specific identifiers vary by method; base64url is
        # the common case (e.g., did:key). Generic fallback.
        return Parsed("DID", BASE64URL, m.group(1), m.group(2), m.group(3))
    
def parse_swhid(text) -> Parsed:
    """
    See if we can parse text as a Software Heritage IDentifier (SWHID v1).

    Core form: `swh:1:<type>:<40-hex-sha1>`, where <type> is one of
    snp/rel/rev/dir/cnt. A git *commit* is the `rev` (revision) object
    type. The 40-char hex is a git-style SHA-1; SWHID v1 is sha1-only, so
    a 64-hex (sha256) body does NOT match here.

    The `swh:1:<type>:` scheme+type is non-entropy framing (prefix); the
    hex is the core (declared HEX so the tokenizer reads 4 bits/char). An
    optional `;<qualifiers>` tail (origin=, lines=, …) is matched so the
    input is still recognized, but it is a FREE annotation — addressing
    context that varies independently of the value (the same blob under any
    origin) and is unbounded — so it is DROPPED, not surfaced as a suffix
    (suffix is reserved for entropy-bound checksums/derivations). See
    `this.i:sufxbind`. The scheme, type, and hex are normalized to lower
    case. See `this.i:g1tha5h0`.
    """
    if not text:
        return None
    m = SWHID_REGEX.match(text)
    if not m:
        return None
    return Parsed(
        # No type: the swh:1:<type>: prefix is self-describing, so a "SWHID"
        # type would just echo it. The label shows the prefix alone.
        # See this.i:lbldedup. The qualifier tail (group 3) is a free
        # annotation and is dropped (suffix=None) per this.i:sufxbind.
        "",
        HEX,
        m.group(1).lower(),
        m.group(2).lower(),
        None,
        # The object-type (cnt/rev/snp/…) is IDENTITY: the same hash under a
        # different type is a different object (swap test). It lives in the
        # prefix (it is letters, a different alphabet from the hex body, so
        # it can't join the hex cell stream), so it binds the fingerprint via
        # the prefix-fold path rather than the cells. See `this.i:s3mpr3fx`.
        prefix_semantic=True,
    )

def parse_gitoid(text) -> Parsed:
    """
    See if we can parse text as a gitoid (OmniBOR git object identifier).

    Form: `gitoid:<object-type>:<hash-algo>:<hex>`, where <object-type>
    is one of blob/tree/commit/tag and <hash-algo> is sha1 (40 hex) or
    sha256 (64 hex). The hex length must match the declared algorithm; a
    mismatch is rejected (returns None) rather than re-tokenized, since a
    wrong-length body means the identifier is malformed.

    The `gitoid:<obj>:<algo>:` scheme is non-entropy framing (prefix); the
    hex is the core, declared HEX. Everything is normalized to lower case.
    See `this.i:g1tha5h0`.
    """
    if not text:
        return None
    m = GITOID_REGEX.match(text)
    if not m:
        return None
    obj, algo, body = m.group(2).lower(), m.group(3).lower(), m.group(4).lower()
    if len(body) != _GITOID_ALGO_LEN[algo]:
        return None
    # No type: the gitoid:<obj>:<algo>: prefix is self-describing, so a type
    # would just echo it. The label shows the prefix alone. See
    # this.i:lbldedup. The object-type (blob/tree/…) and hash-algo are
    # IDENTITY (swap test) and live in the prefix (a different alphabet from
    # the hex body), so they bind the fingerprint via the prefix-fold path.
    # Without this, a gitoid and a SWHID over the same git hash would collide
    # in every fingerprint channel. See `this.i:s3mpr3fx`.
    return Parsed("", HEX, m.group(1).lower(), body, None, prefix_semantic=True)

def _bech32_polymod(values):
    """BIP-173 bech32 checksum polymod over a list of 5-bit values."""
    gen = (0x3b6a57b2, 0x26508e6d, 0x1ea119fa, 0x3d4233dd, 0x2a1462b3)
    chk = 1
    for v in values:
        top = chk >> 25
        chk = ((chk & 0x1ffffff) << 5) ^ v
        for i in range(5):
            chk ^= gen[i] if ((top >> i) & 1) else 0
    return chk


def _bech32_hrp_expand(hrp):
    return [ord(c) >> 5 for c in hrp] + [0] + [ord(c) & 31 for c in hrp]


def _bech32_checksum_const(hrp, data):
    """Return the polymod constant for hrp+data: 1 for bech32, 0x2bc830a3 for
    bech32m, or anything else when the checksum is invalid. `data` is the
    bech32 char string (including the 6 trailing checksum chars)."""
    values = [BECH32_ALPHABET.index(c) for c in data]
    return _bech32_polymod(_bech32_hrp_expand(hrp) + values)


def parse_bech32_address(text) -> Parsed:
    """
    See if we can parse text as a generic, checksum-valid bech32 address —
    the encoding used by Cosmos-SDK chains (cosmos1…, osmo1…, juno1…, …) and
    many others.

    Detection is made SOUND by validating the BIP-173 (bech32) or BIP-350
    (bech32m) checksum rather than merely matching a prefix; a random
    <letters>1<chars> string passes the polymod with probability ~2⁻³⁰. The
    HRP becomes part of the type label (e.g. "bech32 cosmos"), so the chain
    is named from the input itself rather than a hard-coded list.

    The `<hrp>1` is split off as the non-entropy prefix; the 6-char checksum
    is the suffix (as for LEI / Bitcoin-legacy); the remaining bech32 data is
    the core, declared BECH32. Specific bech32 formats (Bitcoin segwit,
    Litecoin, Cardano, Bitcoin Cash) have dedicated parsers that run first.
    See `this.i:xtra4lph`.
    """
    if not text:
        return None
    m = BECH32_GENERIC_REGEX.match(text)
    if not m:
        return None
    hrp = m.group(1).lower()
    data = m.group(2).lower()
    if _bech32_checksum_const(hrp, data) not in (1, 0x2bc830a3):
        return None
    # Type is just "bech32"; the chain is named by the displayed prefix
    # (cosmos1/osmo1/…), not repeated in the type. See this.i:lbldedup.
    return Parsed("bech32", BECH32, hrp + "1", data[:-6], data[-6:])

def parse_ipfs_cid(text) -> Parsed:
    """
    See if we can parse text as an IPFS CID.
    If yes, return Parsed("IPFS CID...", prefix (Qm or b), body, None)
    """
    m = IPFS_CIDV0_REGEX.match(text)
    if m:
        # A v0 CID is, by definition, dag-pb content under a sha2-256
        # multihash, so both are the assumable default and are elided.
        return Parsed("CIDv0", BASE58, m.group(1), m.group(2), None)
    m = IPFS_CIDV1_REGEX.match(text)
    if m:
        # IPFS CID v1 uses base32 (RFC 4648). Decode the self-describing
        # interior (version/codec/hash varints) to label the content codec.
        # Per the "silent default, loud departure" rule (this.i:lbldedup),
        # the content codec ALWAYS shows (it varies: dag-pb / raw / dag-cbor)
        # but the hash is shown ONLY when it is not the near-universal
        # sha2-256 default. Label-only: the core stays the full base32 body
        # so the fingerprint is unchanged; falls back to a plain label if the
        # interior does not decode. See `this.i:mult1c0d`.
        label = "CIDv1"
        try:
            # binascii.Error (bad base32) subclasses ValueError.
            described = decode_multicodec(_b32_nopad_decode(m.group(2)))
            if described:
                codec_name, hash_name = described
                label = f"CIDv1 {codec_name}"
                if hash_name != "sha2-256":
                    label += f"/{hash_name}"
        except ValueError:
            pass
        return Parsed(label, BASE32, m.group(1), m.group(2).upper(), None)
    
def parse_hex(text) -> Parsed:
    """
    See if we can parse text as a hex string.
    If yes, return Parsed("hex", prefix (either None or "0x"), body, None).
    """
    if text:
        prefix = None
        if (text.startswith('0x') or text.startswith('0X')) and len(text) > 2:
            prefix = "0x"
            text = text[2:]
        elif len(text) % 2 != 0: return 
        m = HEX_REGEX.match(text)
        if m:
            # Normalize to lowercase so oral reading doesn't need
            # "cap A" prefixes for A-F. UUIDs already lowercase via
            # parse_uuid; Ethereum is exempt (EIP-55 mixed case is
            # the checksum).
            return Parsed("hex", HEX, prefix, text.lower(), None)

# Parser dispatch order. parse() tries each in turn and returns the first
# match, so ORDER IS SEMANTICS: a narrow/checksummed format must precede any
# broader one that would also accept the same input. This list was previously
# materialized by a globals() scan in definition order (MNT-F4), which hid the
# ordering contract and made it silently fragile to reordering the defs — it is
# now explicit, and tests/test_entropy.py pins the load-bearing constraints.
#
# Two constraints are load-bearing (see reviews/adversarial-2026-05-27.md):
#   * parse_hex sits near the END so structured pure-hex formats (Ethereum's
#     0x…, hex multihashes) get first refusal before the generic hex parser.
#   * parse_eos_address runs AFTER parse_hex (review F1): the EOS alphabet
#     [a-z1-5.] is a superset of lowercase hex for many short strings, so
#     genuine hex must win the race against a speculative EOS short-form match.
parse_funcs = [
    parse_hex_multihash,
    parse_cesr,
    parse_ssh_key,
    parse_bitcoin_address,
    parse_ripple_address,
    parse_ethereum_address,
    parse_litecoin_address,
    parse_bitcoin_cash_address,
    parse_cardano_address,
    parse_stellar_address,
    parse_uuid,
    parse_ulid,
    parse_snowflake,
    parse_lei,
    parse_did,
    parse_swhid,
    parse_gitoid,
    parse_bech32_address,
    parse_ipfs_cid,
    parse_hex,
    parse_eos_address,
]

def parse(entropy: str) -> Parsed:
    """
    See if the entropy can be parsed as a known type. If yes,
    return a Parsed tuple. If no, attempt disproof-based alphabet
    detection over the input as a whole. If still no match, return None
    (the caller falls back to UTF-8 re-encoding as base64url).
    """
    entropy = entropy.strip()
    for func in parse_funcs:
        answer = func(entropy)
        if answer:
            return answer
    # No specific parser recognized the input. Try disproof-based
    # alphabet detection: if every char of the input belongs to some
    # known alphabet's character set, treat the input as that alphabet
    # directly instead of round-tripping through UTF-8 → base64url.
    detected = detect_alphabet_by_disproof(entropy)
    if detected is not None:
        # Normalize case for case-insensitive alphabets so the
        # tokenizer's per-char lookup is consistent AND so the SHA-512
        # fingerprint (computed over `core.encode()`) is case-invariant
        # for those alphabets. HEX is redundant when parse_hex runs but
        # defensive: the disproof path also resolves HEX for short
        # strings that bypass parse_hex's odd-length guard. See review
        # F2 in reviews/adversarial-2026-05-27.md.
        #
        # The canonical case is PER ALPHABET (this.i:c4s3norm, spec §226):
        # base32 canonicalizes to UPPER (RFC 4648), matching the specific
        # base32 parsers (Stellar, IPFS CIDv1); bech32 and hex to lower.
        # Before v8 (SPEC-F3) this path lowercased base32 too, so a bare
        # base32 fragment fingerprinted differently here than via a
        # specific parser. "no re-encoding" on the disproof path means no
        # alphabet re-serialization; it does not waive case normalization.
        if detected is BASE32:
            core = entropy.upper()
        elif detected in (BECH32, HEX):
            core = entropy.lower()
        else:
            core = entropy
        # type name = alphabet name (e.g., "base32:", "bech32:"), so
        # the per-entviz top label can show what was detected.
        return Parsed(detected.name, detected, None, core, None)


# Disproof order: most restrictive (smallest character set) first. The
# tuples are (alphabet, valid-char-set-string). Case-insensitive
# matching is applied uniformly — input "abc" and "ABC" both match
# HEX, BASE32, etc.
#
# Built eagerly at module import time (review F-A1) so concurrent first
# calls from multiple threads (e.g. a server-side parse() loop) cannot
# race on lazy mutation of a module global. Every alphabet constant
# referenced here is already declared above; no forward reference.
_DISPROOF_ORDER = [
    (HEX,       set(HEX_ALPHABET.lower())),
    (BASE32,    set(BASE32_ALPHABET.lower())),
    (BECH32,    set(BECH32_ALPHABET.lower())),
    (BASE58,    set(BASE58_ALPHABET)),  # base58 is case-sensitive
    (BASE64,    set(BASE64_ALPHABET)),  # base64 is case-sensitive
    (BASE64URL, set(BASE64URL_ALPHABET)),
]


def detect_alphabet_by_disproof(text: str):
    """
    Return the most-restrictive Alphabet whose character set contains
    every character of `text`, or None if no alphabet does. Empty input
    returns None.
    """
    if not text:
        return None
    # For each alphabet in order, check whether every input char fits.
    # Use case-sensitive comparison for base58/base64/base64url (which
    # really are case-sensitive); for hex/base32/bech32 use lowered.
    text_cs = text                  # case-sensitive view
    text_ci = text.lower()          # case-insensitive view (lowered)
    for alphabet, char_set in _DISPROOF_ORDER:
        view = text_cs if alphabet in (BASE58, BASE64, BASE64URL) else text_ci
        if all(c in char_set for c in view):
            return alphabet
    return None


def tokenize(text: str, alphabet, token_len: int = None) -> list[Token]:
    """
    Split the string into tokens and assign a 24-bit quant to each.

    `alphabet` is an `Alphabet` instance (HEX, BASE58, BASE64, BASE64URL).
    For backwards compatibility a legacy string type name (e.g., "hex",
    "base64", "base58") is accepted and translated to the corresponding
    Alphabet, but new callers should pass the Alphabet directly. (See
    the v3 errata commit for why the substring-guess approach was wrong.)
    """
    # Accept a legacy string type for backwards compat.
    if isinstance(alphabet, str):
        type_name = alphabet
        if "hex" in type_name.lower():
            alphabet = HEX
        elif "58" in type_name.lower():
            alphabet = BASE58
        else:
            alphabet = BASE64
    bits_per_char = alphabet.bits_per_char
    alphabet_chars = alphabet.chars
    if token_len is None:
        # Pick token_len so each full token represents at most 24 bits.
        # bits_per_char=4 (hex) → 6 chars (24 bits exact);
        # bits_per_char=6 (base58/64/url) → 4 chars (24 bits exact);
        # bits_per_char=5 (bech32 / base32) → 4 chars (20 bits, extended
        # to 24 by the bit-extension rule). The alternate (5 chars = 25
        # bits) was rejected because it overshoots the 24-bit quant.
        token_len = 24 // bits_per_char

    tokens = []
    for i in range(0, len(text), token_len):
        chunk = text[i:i+token_len]
        if not chunk: continue
        
        # Calculate raw bits
        val = 0
        actual_bits = 0
        for char in chunk:
            char_val = alphabet_chars.find(char)
            if char_val == -1: # Try lower case for hex
                char_val = alphabet_chars.lower().find(char.lower())
            if char_val == -1 and bits_per_char == 6:
                # Cross-alphabet compat: when the configured alphabet is
                # standard base64 (with '+', '/') but the input came from
                # a base64url source (with '-', '_'), or vice versa,
                # accept either pair at indices 62/63 so partial-ftok
                # bit extension is consistent across either spelling.
                if char == '-': char_val = 62
                elif char == '_': char_val = 63
                elif char == '+': char_val = 62
                elif char == '/': char_val = 63
            if char_val == -1: char_val = 0
            
            val = (val << bits_per_char) | char_val
            actual_bits += bits_per_char
        
        # Extend to 24 bits by repeating low-order bits. spec.md lines
        # 155-174: the pad chunk is taken from the low-order bits of the
        # *current (already-extended) quant*, not from the original value.
        # This only differs from `val` once the quant has grown past the
        # original bit width (e.g. a 4-bit value needs three doublings:
        # 0x5 -> 0x55 -> 0x5555 -> 0x555555), but getting it wrong there
        # mis-colors the nucleus of any cell holding a 4-bit partial token.
        quant = val
        if actual_bits > 0 and actual_bits < 24:
            while actual_bits < 24:
                shift = min(actual_bits, 24 - actual_bits)
                # Take low-order 'shift' bits of the current quant and append them
                mask = (1 << shift) - 1
                bits_to_add = quant & mask
                quant = (quant << shift) | bits_to_add
                actual_bits += shift
        elif actual_bits > 24:
            # Should not happen with spec lengths, but for safety:
            quant = val & 0xFFFFFF
            
        tokens.append(Token(chunk, len(tokens), quant))

    return tokens


_MAX_TOKENS = 22
# v6 large-input layout: 8 head + 4 middle (hex fingerprint readout) + 8 tail
# = 20 tokens, renumbered 0..19. Blank cells are placed by the same
# median/quartile shift as short inputs — there are NO fixed separator blanks
# (v5's separators at cell indices 8/13 were removed in v6; see this.i
# v6blnkun). The 4 middle cells are identified at render time by token index
# 8..11 and tagged data-cell-fingerprint.
_HEAD_TOKENS = 8
_MIDDLE_TOKENS = 4
_TAIL_TOKENS = 8
_LARGE_TOKEN_COUNT = _HEAD_TOKENS + _MIDDLE_TOKENS + _TAIL_TOKENS  # 20
# Bits per head/tail = 24 · 8 = 192. Used to size the head/tail char windows
# (rounded to whole characters of the underlying alphabet).
_BITS_PER_SIDE = 24 * _HEAD_TOKENS  # 192


def _alphabet_from_legacy(alphabet):
    """Resolve a legacy string type name to an Alphabet instance.
    Pass-through for an Alphabet instance."""
    if isinstance(alphabet, str):
        name = alphabet.lower()
        if "hex" in name:
            return HEX
        elif "58" in name:
            return BASE58
        else:
            return BASE64
    return alphabet


def _core_byte_length(core: str, alphabet) -> int:
    """
    Return the underlying byte length of the normalized core under its
    declared alphabet. Used by the large-input trigger to decide whether an
    input exceeds 512 bits (64 bytes) and takes the head/middle/tail path.

    For 4-bit alphabets (hex) this is simply len(core)/2. For 5-/6-bit
    alphabets we compute bytes = floor(len(core) · bits_per_char / 8),
    matching the conventional "how many bytes does N base-X chars
    represent" answer for tightly-packed encodings.
    """
    return (len(core) * alphabet.bits_per_char) // 8


# Domain-separation tag for the middle-cell fingerprint (v6). The 4 middle
# cells of a >512-bit input render a SECOND, domain-separated SHA-512 digest
# of the whole normalized core, NOT a slice of the primary fingerprint that
# drives the gestalt channels (color bar / surround / median / quartile).
# Two consequences, addressing adversarial-2026-06-02 F1 and F2:
#   F1 — each cell renders exactly 3 digest bytes as 6 lowercase hex chars =
#        a full 24 bits, injective for EVERY input alphabet (the prior design
#        rendered in the input's alphabet, dropping 4 bits/cell on 5-bit
#        alphabets and mod-aliasing on base58/base36). So "the middle text
#        avalanches on any input change" is now literally true, not
#        probabilistic-or-aliased.
#   F2 — domain separation guarantees this digest differs from the primary
#        fingerprint, so the displayed middle is independent evidence rather
#        than a re-readout of bytes that already drive the surround/color bar.
# NOTE: the "/v6" is the version of THIS fingerprint-middle construction
# (introduced in spec v6, unchanged since) — NOT the spec-document version. It
# is a cryptographic domain-separation constant: do NOT bump it to track the
# spec version (it is "v6" even though the spec is now v7). Changing this byte
# string changes the 4 middle cells of every >512-bit entviz, which would break
# comparison stability and the golden conformance corpus. Change it ONLY on a
# breaking change to this derivation, never to mirror the spec version. (The
# corpus's large-input vectors pin the current value, so an accidental change is
# caught by tests/test_compliance.py.)
_MIDDLE_DOMAIN_TAG = b"entviz/fingerprint-middle/v6\x00"


def _build_fingerprint_middle_tokens(core: str) -> list[Token]:
    """
    Build the 4 middle Tokens from a SECOND, domain-separated SHA-512 digest
    of the whole core: token i renders ``second_digest[3i : 3i+3]`` as 6
    lowercase hex characters (a 24-bit, injective readout). Hex is used
    regardless of the input alphabet, so each cell always carries a full 24
    bits and the text is guaranteed to avalanche on any input change (F1);
    the domain tag keeps it independent of the primary fingerprint (F2).
    Token indices here are 0..3; the caller renumbers into the final 0..19
    sequence. The pipeline paints these nuclei with the entviz background
    color (they carry no entropy in their bg).
    """
    second = hashlib.sha512(_MIDDLE_DOMAIN_TAG + core.encode("utf-8")).digest()
    tokens: list[Token] = []
    for i in range(_MIDDLE_TOKENS):
        b3 = second[3 * i: 3 * i + 3]
        quant = (b3[0] << 16) | (b3[1] << 8) | b3[2]
        tokens.append(Token(b3.hex(), i, quant))
    return tokens


def tokenize_entropy(core: str, alphabet) -> tuple[list[Token], bool]:
    """
    Tokenize entropy with v5 large-input handling.

    `alphabet` is an `Alphabet` instance; legacy string type names are
    accepted via the same compatibility shim used by `tokenize()`.

    For inputs whose underlying byte length exceeds 64 (>512 bits), apply
    the head + fingerprint-middle + tail rule:
      * head: first 8 tokens of the input (covering ≈192 bits, rounded to
        whole characters of the alphabet).
      * middle: 4 tokens rendering a SECOND, domain-separated SHA-512 digest
        of the whole core as hex (6 hex chars = 24 bits per cell; see
        `_build_fingerprint_middle_tokens`). v6: guarantees the middle text
        is injective and avalanches on any input change for every alphabet,
        and is independent of the primary fingerprint (F1/F2).
      * tail: last 8 tokens of the input.
    The 20 tokens are renumbered with indices 0..19. Blank cells are placed
    by the same median/quartile shift as short inputs (no fixed separators);
    the pipeline tags the 4 middle cells with `data-cell-fingerprint`.

    Returns (tokens, is_truncated). The fingerprint is computed over the
    full core, so the binding into every fingerprint-driven channel
    covers the entire input, not just the visible cells.
    """
    alphabet = _alphabet_from_legacy(alphabet)
    bits_per_char = alphabet.bits_per_char
    token_len = 24 // bits_per_char
    n_bytes = _core_byte_length(core, alphabet)
    # Anti-DoS (this.i:1nputcap): tokenize() emits exactly
    # ceil(len(core)/token_len) tokens, so the >22-token guard is decidable
    # from len(core) without materializing every token. The old code ran the
    # full tokenize() here only to read len(all_tokens) and then discard all
    # but head/tail on the large path — ~1.7M throwaway Token objects for a
    # 10 MB input. We now compute the count arithmetically and only tokenize
    # the whole core on the short path (≤22 tokens by definition).
    token_count = -(-len(core) // token_len)  # ceil division
    # v5 trigger: byte length > 64 (>512 bits) per spec line 117. We
    # also fold in the legacy >22-token guard so the bech32 corner case
    # (92 chars × 5 bits = 460 bits = 57.5 bytes, still 23 tokens)
    # stays bounded; for that sub-512-bit edge case the middle-slice
    # offset deriver falls back to evenly-spaced offsets.
    if token_count <= _MAX_TOKENS and n_bytes <= 64:
        return tokenize(core, alphabet), False
    # v5: 8 head tokens + 4 middle slices + 8 tail tokens. On this large path
    # we tokenize only the head and tail windows actually rendered, never the
    # full core.
    head_chars = _HEAD_TOKENS * token_len
    tail_chars = _TAIL_TOKENS * token_len
    head_tokens = tokenize(core[:head_chars], alphabet)
    tail_tokens = tokenize(core[-tail_chars:], alphabet)

    # v6 (F1/F2): the 4 middle cells render a SECOND, domain-separated SHA-512
    # digest of the whole core as hex — 24 injective bits per cell, independent
    # of the primary fingerprint. v5 used entropy body slices (difference only
    # probabilistic); v6.0 used primary-digest bytes in the input's alphabet
    # (lost bits on 5-bit alphabets, mod-aliased on base58/base36, and shared
    # bytes with the gestalt). Hex over a separate digest fixes both.
    middle_tokens = _build_fingerprint_middle_tokens(core)

    combined = head_tokens + middle_tokens + tail_tokens
    renumbered = [Token(t.text, i, t.quant) for i, t in enumerate(combined)]
    return renumbered, True


def get_median_token(tokens: list[Token]) -> Token:
    """
    Identify the first token in the sorted list that contains the median value.
    Sort by ASCII order with a secondary sort by token index.
    """
    if not tokens: return None
    # Sort by text, then by index
    sorted_tokens = sorted(tokens, key=lambda t: (t.text, t.index))
    
    # If count is even, use first from middle pair (index (n/2) - 1 for 0-based)
    mid = (len(sorted_tokens) - 1) // 2
    return sorted_tokens[mid]

def get_quartile_tokens(tokens: list[Token]) -> list[Token]:
    """
    Identify the first token in each quartile.
    Sort by ASCII order of mirror image (reversed text), secondary sort by index.
    """
    if not tokens: return [None] * 4
    
    # Mirror sort
    sorted_tokens = sorted(tokens, key=lambda t: (t.text[::-1], t.index))
    
    # If not divisible by 4, act as if 4 - (count % 4) blank items existed at bottom.
    count = len(sorted_tokens)
    q_size = math.ceil(count / 4)
    
    quartiles = []
    for i in range(4):
        idx = i * q_size
        if idx < count:
            quartiles.append(sorted_tokens[idx])
        else:
            quartiles.append(None)
            
    return quartiles
