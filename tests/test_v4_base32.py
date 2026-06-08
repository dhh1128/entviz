"""
v4 base32 alphabet (RFC 4648): 5 bits per character, 32-char alphabet
A-Z + 2-7. Used by Bitcoin Cash CashAddr, Stellar, IPFS CID v1.

This is a DIFFERENT alphabet from bech32 (which uses
"qpzry9x8gf2tvdw0s3jn54khce6mua7l") and from Crockford base32
(0-9, A-Z minus I/L/O/U, used by ULIDs). All three share the same
bits_per_char=5 token length but their character lookup tables differ,
so an input string would produce different quant values depending on
which alphabet is declared.
"""
from entviz.entropy import (
    parse, tokenize_entropy,
    BASE32, BASE32_ALPHABET, BECH32, HEX,
)


def test_base32_alphabet_exists():
    assert BASE32 is not None
    assert BASE32.name == "base32"


def test_base32_alphabet_is_5_bits_per_char():
    assert BASE32.bits_per_char == 5


def test_base32_alphabet_is_rfc_4648():
    """RFC 4648 base32 alphabet: A-Z + 2-7, in that order."""
    assert BASE32_ALPHABET == "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"
    assert len(BASE32_ALPHABET) == 32


def test_base32_distinct_from_bech32():
    """Base32 and bech32 share bits_per_char but differ in alphabet."""
    assert BASE32 is not BECH32
    assert BASE32.bits_per_char == BECH32.bits_per_char == 5
    assert BASE32.chars != BECH32.chars


def test_base32_token_length_is_4_chars():
    """4 chars × 5 bits = 20 bits per token, extended to 24."""
    # "ABCD" → A=0, B=1, C=2, D=3 → (0<<15)|(1<<10)|(2<<5)|3 = 1091 = 0x443
    # Extension: shift=4, pad=0x3 → quant = (0x443 << 4) | 0x3 = 0x4433
    tokens, truncated = tokenize_entropy("ABCD", BASE32)
    assert not truncated
    assert len(tokens) == 1
    assert tokens[0].quant == 0x4433


def test_base32_case_insensitive_tokenization():
    """Lowercase base32 chars tokenize to the same quant as uppercase."""
    upper_tokens, _ = tokenize_entropy("ABCD", BASE32)
    lower_tokens, _ = tokenize_entropy("abcd", BASE32)
    assert upper_tokens[0].quant == lower_tokens[0].quant


def test_base32_partial_token_extends():
    """A 2-char base32 token (10 bits) extends to 24."""
    # "AB" → A=0, B=1 → 10-bit value 0x001
    # shift=10: quant = (1 << 10) | 1 = 0x401, 20 bits
    # shift=4:  quant = (0x401 << 4) | 1 = 0x4011, 24 bits
    tokens, _ = tokenize_entropy("AB", BASE32)
    assert tokens[0].quant == 0x4011


# ---- parser integration ------------------------------------------------


def test_stellar_address_parses_as_base32():
    """Stellar accounts use a 'G' prefix followed by 55 base32 chars."""
    # A real Stellar test account
    addr = "GCKFBEIYTKP5RDBQMUTAPDCDHF2TR4LPNRGW4JBQQTQUYZP4LDKP3SGM"
    p = parse(addr)
    assert p is not None
    assert p.type == "XLM"
    assert p.alphabet is BASE32


def test_ipfs_cid_v1_parses_as_base32():
    """IPFS CID v1 uses 'b' prefix + 58-112 base32 chars."""
    cid = "bafybeigdyrzt5sfp7udm7hu76uh7y26nf3efuylqabf3oclgtqy55fbzdi"
    p = parse(cid)
    assert p is not None
    assert p.type.startswith("CIDv1")
    assert p.alphabet is BASE32


def test_bitcoin_cash_address_parses_as_bech32_not_base32():
    """Bitcoin Cash CashAddr is commonly called 'base32' but actually
    uses the BECH32 alphabet (BIP-173 char set, not RFC 4648). Verify
    we declare bech32, not base32, despite the name."""
    addr = "bitcoincash:qpm2qsznhks23z7629mms6s4cwef74vcwvy22gdx6a"
    p = parse(addr)
    assert p is not None
    assert p.type == "BCH"
    assert p.alphabet is BECH32  # NOT BASE32, despite the name


def test_render_stellar_address_does_not_crash():
    """End-to-end: rendering a Stellar address should produce a valid SVG."""
    from entviz.pipeline import render
    svg = render("GCKFBEIYTKP5RDBQMUTAPDCDHF2TR4LPNRGW4JBQQTQUYZP4LDKP3SGM")
    assert svg.startswith("<svg")


# --- v8 (SPEC-F3): the disproof fallback must canonicalize base32 to UPPER ---
# A bare base32 fragment (one that misses the specific Stellar/CIDv1 parsers and
# resolves via detect_alphabet_by_disproof) must be uppercased, matching the
# specific parsers and RFC 4648 (this.i:c4s3norm, spec §226). Before v8 this path
# lowercased base32, so the same value fingerprinted differently here than via a
# specific parser. We do NOT change base32's rule (always UPPER) — only this path.

def test_disproof_base32_fragment_canonicalizes_to_upper():
    """A bare base32 fragment routed through disproof must uppercase its core."""
    p = parse("mfrggzdfmztwq2lk")
    assert p.alphabet is BASE32
    assert p.core == "MFRGGZDFMZTWQ2LK"  # UPPER, not the lowercase input


def test_disproof_base32_is_case_invariant():
    """Lower-, upper-, and mixed-case base32 fragments produce the same core,
    hence the same SHA-512 fingerprint and the same entviz — the per-alphabet
    case-consistency the specific base32 parsers already guarantee."""
    cores = {parse(t).core for t in
             ("mfrggzdfmztwq2lk", "MFRGGZDFMZTWQ2LK", "MfRgGzDfMzTwQ2Lk")}
    assert cores == {"MFRGGZDFMZTWQ2LK"}
