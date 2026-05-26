import collections
import re
import hashlib


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
BITCOIN_CASH_REGEX = re.compile(r'^((?:bitcoincash|bchtest):)?([pq][' + BECH32_ALPHABET_EITHER_CASE + ']{41})', re.I)
LITECOIN_LEGACY_REGEX = re.compile(r'^(t?L)([' + BASE58_ALPHABET + ']{33})$')
LITECOIN_REGEX = re.compile(r'^(ltc1)([' + BECH32_ALPHABET_EITHER_CASE + ']{38,68})$', re.I)
ETHEREUM_REGEX = re.compile(r'^(0x)?([a-fA-F0-9]{32})([a-fA-F0-9]{8})$', re.I)
RIPPLE_REGEX = re.compile(r'^(r)([' + BASE58_ALPHABET + ']{33})$')
BITCOIN_LEGACY_REGEX = re.compile(r'^([123mn])([' + BASE58_ALPHABET + ']{21,30})([' + BASE58_ALPHABET + ']{4})$')
BITCOIN_SEGWIT_REGEX = re.compile(r'^(bc1|tb1)([' + BECH32_ALPHABET_EITHER_CASE + ']{39,69})$', re.I)
SSH_KEY_REGEX = re.compile(r'(AAAA)([0-9A-Za-z+/]+={0,3})')
HEX_REGEX = re.compile(r'^[a-fA-F0-9]+$')
BASE64URL_NO_PAD_REGEX = re.compile(r'^[A-Za-z0-9-_]+$') # used by CESR
BASE64URL_ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_'
BASE64URL = Alphabet("base64url", BASE64URL_ALPHABET, 6)

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
    See if we can parse text as an SSH key.
    If yes, return Parsed("SSH", "AAAA", body, None).
    """
    m = SSH_KEY_REGEX.match(text)
    if m:
        return Parsed(f"SSH key", BASE64, m.group(1), m.group(2), None)

def parse_bitcoin_address(text) -> Parsed:
    """
    See if we can parse text as a Bitcoin address.
    If yes, return Parsed("bitcoin", prefix, body, None).
    """
    m = BITCOIN_LEGACY_REGEX.match(text)
    if m:
        return Parsed("Bitcoin legacy", BASE58, m.group(1), m.group(2), m.group(3))
    m = BITCOIN_SEGWIT_REGEX.match(text)
    if m:
        # Bitcoin SegWit uses bech32 (BIP-173).
        return Parsed("Bitcoin SegWit", BECH32, m.group(1).lower(), m.group(2).lower(), None)

def parse_ripple_address(text) -> Parsed:
    """
    See if we can parse text as a Ripple address.
    If yes, return Parsed("Ripple", prefix, body, None).
    """
    m = RIPPLE_REGEX.match(text)
    if m:
        return Parsed("Ripple", BASE58, m.group(1), m.group(2), None)

def to_EIP55_address(address: str) -> str:
    # Remove the '0x' prefix if present
    address = address.lower().replace('0x', '')
    
    # Create a keccak-256 hash of the address
    hash = hashlib.sha3_256(address.encode('utf-8')).hexdigest()
    
    # Apply the checksum
    checksum_address = '0x'
    for i, char in enumerate(address):
        if int(hash[i], 16) >= 8:
            checksum_address += char.upper()
        else:
            checksum_address += char.lower()
    
    return checksum_address

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
    """
    m = ETHEREUM_REGEX.match(text)
    if not m:
        return None
    has_prefix = bool(m.group(1))
    body = m.group(2) + m.group(3)
    if not has_prefix:
        has_lower = any(c.islower() for c in body if c.isalpha())
        has_upper = any(c.isupper() for c in body if c.isalpha())
        if not (has_lower and has_upper):
            return None  # falls through to plain hex
    eip55_format = to_EIP55_address(body)
    return Parsed("Ethereum", HEX, "0x", eip55_format[2:-8], eip55_format[-8:])

def parse_litecoin_address(text) -> Parsed:
    """
    See if we can parse text as a Litecoin address.
    If yes, return Parsed("Litecoin...", prefix, body, None).
    """
    m = LITECOIN_LEGACY_REGEX.match(text)
    if m:
        return Parsed("Litecoin legacy", BASE58, m.group(1), m.group(2), None)
    m = LITECOIN_REGEX.match(text)
    if m:
        # Modern Litecoin "ltc1..." uses bech32.
        return Parsed("Litecoin", BECH32, m.group(1).lower(), m.group(2).lower(), None)

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
        return Parsed("Bitcoin Cash", BECH32, m.group(1), m.group(2).lower(), None)

def parse_cardano_address(text) -> Parsed:
    """
    See if we can parse text as a Cardano address.
    If yes, return Parsed("Cardano...", prefix ("addr", "stake", etc.), body, checksum).
    """
    m = CARDANO_SHORT_BYRON_REGEX.match(text)
    if m:
        return Parsed("Cardano Byron", BASE58, m.group(1), m.group(2), m.group(3))
    m = CARDANO_LONG_BYRON_REGEX.match(text)
    if m:
        return Parsed("Cardano Byron", BASE58, m.group(1), m.group(2), m.group(3))
    m = CARDANO_SHELLEY_REGEX.match(text)
    if m:
        # Cardano Shelley uses bech32.
        return Parsed("Cardano Shelley", BECH32, m.group(1), m.group(2).lower(), m.group(3).lower())

def parse_eos_address(text) -> Parsed:
    """
    See if we can parse text as an EOS address.
    If yes, return Parsed("EOS", None, body (address), None).
    """
    m = EOS_REGEX.match(text)
    if m:
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
        return Parsed("Stellar", BASE32, m.group(1).upper(), m.group(2).upper(), None)
    
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
    
# Register all the functions that do parsing (with one exception below).
def register_parse_funcs():
    g = globals()
    parse_funcs = []
    for name, value in g.items():
        if name.startswith("parse_") and callable(value):
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
            return Parsed("hex", HEX, prefix, text.upper(), None)

# We put parse_hex at the end so it won't be attempted until after
# we try many other parsers -- especially the Ethereum one, which
# starts with "0x" and consists of pure hex, and the hex_multihash
# one, which is also pure hex.
parse_funcs.append(parse_hex)

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
        # tokenizer's per-char lookup is consistent.
        core = entropy.lower() if detected in (BECH32,) else entropy
        return Parsed("auto-detected", detected, None, core, None)


# Disproof order: most restrictive (smallest character set) first. The
# tuples are (alphabet, valid-char-set-string). Case-insensitive
# matching is applied uniformly — input "abc" and "ABC" both match
# HEX, BASE32, etc.
_DISPROOF_ORDER = None  # populated after all alphabets are declared


def detect_alphabet_by_disproof(text: str):
    """
    Return the most-restrictive Alphabet whose character set contains
    every character of `text`, or None if no alphabet does. Empty input
    returns None.
    """
    if not text:
        return None
    global _DISPROOF_ORDER
    if _DISPROOF_ORDER is None:
        # Build (alphabet, char_set) tuples. Char sets are case-
        # insensitive (we test the lower form against the lowered text)
        # because every alphabet here can be written in either case.
        _DISPROOF_ORDER = [
            (HEX,       set(HEX_ALPHABET.lower())),
            (BASE32,    set(BASE32_ALPHABET.lower())),
            (BECH32,    set(BECH32_ALPHABET.lower())),
            (BASE58,    set(BASE58_ALPHABET)),  # base58 is case-sensitive
            (BASE64,    set(BASE64_ALPHABET)),  # base64 is case-sensitive
            (BASE64URL, set(BASE64URL_ALPHABET)),
        ]
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
        
        # Extend to 24 bits by repeating low-order bits
        quant = val
        if actual_bits > 0 and actual_bits < 24:
            while actual_bits < 24:
                shift = min(actual_bits, 24 - actual_bits)
                # Take low-order 'shift' bits and append them
                mask = (1 << shift) - 1
                bits_to_add = val & mask
                quant = (quant << shift) | bits_to_add
                actual_bits += shift
        elif actual_bits > 24:
            # Should not happen with spec lengths, but for safety:
            quant = val & 0xFFFFFF
            
        tokens.append(Token(chunk, len(tokens), quant))

    return tokens


_MAX_TOKENS = 22
_BITS_PER_SIDE = 256


def tokenize_entropy(core: str, alphabet) -> tuple[list[Token], bool]:
    """
    Tokenize entropy with v3 large-input handling.

    `alphabet` is an `Alphabet` instance; legacy string type names are
    accepted via the same compatibility shim used by `tokenize()`.

    For inputs whose tokenization would yield more than 22 tokens, take
    only the first 256 bits and the last 256 bits of the normalized core,
    tokenize each side independently, and renumber the combined indices
    0..21. Returns (tokens, is_truncated). The caller is responsible for
    inserting a blank separator cell between the two halves when rendering.

    The fingerprint is computed separately over the full core, so a
    truncated middle still binds into every fingerprint-driven channel.
    """
    if isinstance(alphabet, str):
        type_name = alphabet
        if "hex" in type_name.lower():
            alphabet = HEX
        elif "58" in type_name.lower():
            alphabet = BASE58
        else:
            alphabet = BASE64
    bits_per_char = alphabet.bits_per_char
    all_tokens = tokenize(core, alphabet)
    if len(all_tokens) <= _MAX_TOKENS:
        return all_tokens, False
    # chars_per_side must produce ≤ 11 tokens, so cap it by 11 · token_len.
    # For hex (token_len=6) and base64 (token_len=4) the bit-based bound
    # (ceil(256/bits_per_char)) is smaller and dominates. For bech32
    # (token_len=4, bits_per_char=5) the bit-based bound is 52 chars =
    # 13 tokens, so the token-count bound (44 chars = 11 tokens) wins.
    # In bech32's case each side captures 220 bits instead of 256 — a
    # minor info reduction in the text channel, but the fingerprint still
    # covers the full input and the token-count cap is what the rest of
    # the spec assumes.
    token_len = 24 // bits_per_char
    chars_per_side = min(
        math.ceil(_BITS_PER_SIDE / bits_per_char),
        11 * token_len,
    )
    head_tokens = tokenize(core[:chars_per_side], alphabet)
    tail_tokens = tokenize(core[-chars_per_side:], alphabet)
    combined = head_tokens + tail_tokens
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
