"""
v4 ULID parser & Crockford base32 alphabet.

A ULID is 26 characters of Crockford base32 — a 32-char alphabet
(0-9, A-Z minus I, L, O, U) at 5 bits per char. The official ULID spec
also accepts I→1, L→1, O→0 as case-insensitive input aliases; this
parser normalizes those, plus any lowercase letters, to canonical
uppercase Crockford form.

Crockford base32 is a DIFFERENT alphabet from RFC 4648 base32 (which
uses A-Z + 2-7) and from bech32 (which uses qpzry9x8gf2tvdw0s3jn54khce6mua7l).
All three share bits_per_char=5 but their character lookup tables differ,
so the same input text would yield different quant values depending on
which alphabet is declared.
"""
from entviz.entropy import (
    parse, parse_ulid, tokenize_entropy,
    CROCKFORD32, CROCKFORD32_ALPHABET,
    BASE32, BECH32, HEX,
)


# ---- alphabet object ---------------------------------------------------


def test_crockford32_alphabet_exists():
    assert CROCKFORD32 is not None
    assert CROCKFORD32.name == "crockford32"


def test_crockford32_alphabet_is_5_bits_per_char():
    assert CROCKFORD32.bits_per_char == 5


def test_crockford32_alphabet_is_32_chars():
    assert len(CROCKFORD32_ALPHABET) == 32
    assert CROCKFORD32_ALPHABET == "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def test_crockford32_alphabet_excludes_iluo():
    """Crockford base32 excludes I, L, O, U to reduce ambiguity."""
    assert 'I' not in CROCKFORD32_ALPHABET
    assert 'L' not in CROCKFORD32_ALPHABET
    assert 'O' not in CROCKFORD32_ALPHABET
    assert 'U' not in CROCKFORD32_ALPHABET


def test_crockford32_distinct_from_base32_and_bech32():
    """All three share bits_per_char=5 but use different character sets."""
    assert CROCKFORD32 is not BASE32
    assert CROCKFORD32 is not BECH32
    assert CROCKFORD32.bits_per_char == BASE32.bits_per_char == BECH32.bits_per_char == 5
    assert CROCKFORD32.chars != BASE32.chars
    assert CROCKFORD32.chars != BECH32.chars


# ---- tokenization ------------------------------------------------------


def test_crockford32_token_length_is_4_chars():
    """4 chars * 5 bits = 20 bits per token, extended to 24."""
    # A 26-char ULID should tokenize to ceil(26/4) = 7 tokens
    # (6 full + 1 partial of 2 chars)
    text = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
    tokens, truncated = tokenize_entropy(text, CROCKFORD32)
    assert not truncated
    assert len(tokens) == 7
    assert tokens[0].text == "01AR"
    assert tokens[6].text == "AV"


def test_crockford32_full_token_quant_is_extended_from_20_to_24_bits():
    """A 4-char Crockford32 token represents 20 bits; the quant extension
    rule pads up to 24 bits by appending low-order bits."""
    # "0123" in Crockford32 -> 0=0, 1=1, 2=2, 3=3 -> 20-bit value
    #   (0 << 15) | (1 << 10) | (2 << 5) | 3 = 0x443
    # Extension: shift = min(20, 4) = 4 -> pad = quant & 0xF = 0x3
    #   quant = (0x443 << 4) | 0x3 = 0x4433
    tokens, _ = tokenize_entropy("0123", CROCKFORD32)
    assert len(tokens) == 1
    assert tokens[0].quant == 0x4433


# ---- parser integration ------------------------------------------------


def test_parse_canonical_ulid():
    """A canonical 26-char Crockford32 ULID should parse as type='ULID'."""
    s = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
    p = parse(s)
    assert p is not None
    assert p.type == "ULID"
    assert p.alphabet is CROCKFORD32
    assert p.prefix is None
    assert p.suffix is None
    assert p.core == s


def test_parse_ulid_lowercase_normalizes_to_uppercase():
    """ULIDs are case-insensitive on input; output is canonical uppercase."""
    s = "01arz3ndektsv4rrffq69g5fav"
    p = parse(s)
    assert p is not None
    assert p.type == "ULID"
    assert p.core == "01ARZ3NDEKTSV4RRFFQ69G5FAV"


def test_parse_ulid_mixed_case():
    s = "01ArZ3NdEkTsV4RrFfQ69G5fAv"
    p = parse(s)
    assert p is not None
    assert p.type == "ULID"
    assert p.core == "01ARZ3NDEKTSV4RRFFQ69G5FAV"


def test_parse_ulid_accepts_I_L_O_aliases():
    """Per the ULID spec, I and L map to 1, O maps to 0 (case-insensitive)
    on input; the parser normalizes to canonical uppercase Crockford."""
    # Replace some canonical chars with their aliases, both case forms.
    # Canonical:    01ARZ3NDEKTSV4RRFFQ69G5FAV
    # With aliases: OIARZ3NDEKTSV4RRFFQ69G5FAV  (O->0, I->1)
    s = "OIARZ3NDEKTSV4RRFFQ69G5FAV"
    p = parse(s)
    assert p is not None
    assert p.type == "ULID"
    assert p.core == "01ARZ3NDEKTSV4RRFFQ69G5FAV"

    # Lowercase 'l' -> 1
    # Canonical 01ARZ3NDEKTSV4RRFFQ69G5FA1 (replace last V with 1 first to
    # make a known-good string), then put 'l' in for that '1'.
    s2 = "0lARZ3NDEKTSV4RRFFQ69G5FAV"  # 'l' -> '1'
    p2 = parse(s2)
    assert p2 is not None
    assert p2.type == "ULID"
    assert p2.core == "01ARZ3NDEKTSV4RRFFQ69G5FAV"


def test_parse_ulid_rejects_forbidden_chars():
    """U is not in the Crockford alphabet and is not aliased to anything,
    so a string containing U must not parse as ULID."""
    # 26 chars, but contains 'U' which is forbidden
    s = "U1ARZ3NDEKTSV4RRFFQ69G5FAV"
    p = parse_ulid(s)
    assert p is None


def test_parse_ulid_rejects_wrong_length():
    """ULID is strictly 26 characters."""
    assert parse_ulid("01ARZ3NDEKTSV4RRFFQ69G5FA") is None  # 25 chars
    assert parse_ulid("01ARZ3NDEKTSV4RRFFQ69G5FAVX") is None  # 27 chars
    assert parse_ulid("") is None


def test_parse_ulid_rejects_punctuation():
    """A string with a hyphen or other punctuation is not a ULID."""
    s = "01ARZ3NDEK-SV4RRFFQ69G5FAV"  # 26 chars but contains '-'
    assert parse_ulid(s) is None


def test_parse_ulid_runs_before_parse_hex():
    """A ULID-shaped input made of only 0-9A-F chars (still valid Crockford32)
    should be recognized as ULID, not as plain hex. This requires parse_ulid
    to appear before parse_hex in the parser dispatch order."""
    # 26 hex chars (all in CROCKFORD32 too) -> would match parse_hex if
    # parse_ulid weren't tried first.
    s = "0123456789ABCDEF0123456789"  # 26 chars, all valid Crockford32 (and hex-ish)
    p = parse(s)
    assert p is not None
    assert p.type == "ULID"
    assert p.alphabet is CROCKFORD32


def test_render_ulid_does_not_crash():
    """End-to-end: rendering a ULID should produce a valid SVG."""
    from entviz.pipeline import render
    svg = render("01ARZ3NDEKTSV4RRFFQ69G5FAV")
    assert svg.startswith("<svg")
    assert "</svg>" in svg
