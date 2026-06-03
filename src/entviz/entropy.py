import collections
import re
import hashlib
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


Parsed = collections.namedtuple('Parsed', ['type', 'alphabet', 'prefix', 'core', 'suffix'])

UUID_REGEX = re.compile(r'^\{?[0-9a-f]{8}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{12}\}?$', re.I)
DID_REGEX = re.compile(r'^(did:[a-z0-9]+:)((?:[a-zA-Z0-9_.-]|%[a-fA-F0-9]{2})+)((/[^?]*)?([?].*)?)$')
STELLAR_REGEX = re.compile(r'^(G|g)([' + BASE32_ALPHABET_EITHER_CASE + ']{55})$')
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
                return Parsed(f"multihash {hash_func}", BASE64, text[0:2], text[2:], None)

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
    ("Z", "blinding factor", 44),
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
    ("1AAB", "secp256k1 pubkey", 48),
    ("1AAC", "Ed448 nt pubkey", 80),
    ("1AAD", "Ed448 pubkey", 80),
    ("1AAE", "Ed448 sig", 156),
    ("1AAH", "X25519 100 cipher 24 salt", 100),
    ("1AAI", "secp256r1 nt pubkey", 48),
    ("1AAJ", "secp256r1 pubkey", 48),
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
                        return Parsed(f"CESR {item[1]}", BASE64URL, item[0], text[len(item[0]):], None)

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

    The trailing comment (if any) is returned as `suffix`.

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
    suffix = m.group(2)
    for short_name, match_str, prefix_length in SSH_KEY_TYPES:
        if payload.startswith(match_str) and len(payload) >= prefix_length:
            return Parsed(
                f"SSH {short_name} pubkey",
                BASE64,
                payload[:prefix_length],
                payload[prefix_length:],
                suffix,
            )
    legacy = SSH_KEY_REGEX.match(payload)
    if legacy:
        return Parsed("SSH key", BASE64, legacy.group(1), legacy.group(2), suffix)
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
    now_ms = int(time.time() * 1000)
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
      * prefix = 4-char LOU issuer code + "00" reserved (6 chars, structural)
      * core   = 12-char entity body (the per-entity entropy)
      * suffix = 2-char MOD 97-10 checksum
    Mirrors how Bitcoin legacy reports its version byte and base58 checksum.
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
    return Parsed("LEI", BASE36, upper[:6], upper[6:18], upper[18:])

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
    
def parse_ipfs_cid(text) -> Parsed:
    """
    See if we can parse text as an IPFS CID.
    If yes, return Parsed("IPFS CID...", prefix (Qm or b), body, None)
    """
    m = IPFS_CIDV0_REGEX.match(text)
    if m:
        return Parsed("IPFS CID v0", BASE58, m.group(1), m.group(2), None)
    m = IPFS_CIDV1_REGEX.match(text)
    if m:
        # IPFS CID v1 uses base32 (RFC 4648).
        return Parsed("IPFS CID v1 256", BASE32, m.group(1), m.group(2).upper(), None)
    
# Register all the functions that do parsing (with two exceptions below:
# parse_hex is appended at the end, and parse_eos_address is moved to run
# AFTER parse_hex so that lowercase pure-hex inputs are not silently
# misclassified as EOS addresses — the EOS alphabet [a-z1-5.] is a
# superset of the lowercase hex digits for many short strings, so the
# narrow/checksumed format must lose the race against the strict hex
# parser. See review F1 in reviews/adversarial-2026-05-27.md.
def register_parse_funcs():
    g = globals()
    parse_funcs = []
    for name, value in g.items():
        if name.startswith("parse_") and callable(value):
            if name == "parse_eos_address":
                continue  # re-appended after parse_hex below
            parse_funcs.append(value)
    return parse_funcs
parse_funcs = register_parse_funcs()
del register_parse_funcs

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

# We put parse_hex near the end so it won't be attempted until after
# we try many other parsers -- especially the Ethereum one, which
# starts with "0x" and consists of pure hex, and the hex_multihash
# one, which is also pure hex.
parse_funcs.append(parse_hex)
# parse_eos_address runs AFTER parse_hex (see register_parse_funcs note
# above and review F1): genuine hex inputs that happen to lie inside the
# EOS character class must classify as hex, not as a speculative EOS
# short-form match.
parse_funcs.append(parse_eos_address)

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
        core = entropy.lower() if detected in (BECH32, HEX, BASE32) else entropy
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

import math

Token = collections.namedtuple('Token', ['text', 'index', 'quant'])

BASE64_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"

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
    all_tokens = tokenize(core, alphabet)
    n_bytes = _core_byte_length(core, alphabet)
    # v5 trigger: byte length > 64 (>512 bits) per spec line 117. We
    # also fold in the legacy >22-token guard so the bech32 corner case
    # (92 chars × 5 bits = 460 bits = 57.5 bytes, still 23 tokens)
    # stays bounded; for that sub-512-bit edge case the middle-slice
    # offset deriver falls back to evenly-spaced offsets.
    if len(all_tokens) <= _MAX_TOKENS and n_bytes <= 64:
        return all_tokens, False
    # v5: 8 head tokens + 4 middle slices + 8 tail tokens.
    token_len = 24 // bits_per_char
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
