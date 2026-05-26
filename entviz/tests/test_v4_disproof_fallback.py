"""
v4 disproof-based fallback: when the input doesn't match any
specific-format parser, attempt to identify its alphabet by elimination
— iterate from most restrictive to least, returning the first alphabet
whose character set contains every char of the input. Order:

  hex (4 bits/char, [0-9a-f])
  base32 (5 bits/char, [A-Z2-7] case-insensitive)
  bech32 (5 bits/char, qpzry9x8gf2tvdw0s3jn54khce6mua7l)
  base58 (6 bits/char, [1-9A-HJ-NP-Za-km-z])
  base64 (6 bits/char, [A-Za-z0-9+/])
  base64url (6 bits/char, [A-Za-z0-9_-])

If none applies, the existing behavior continues: re-encode the UTF-8
bytes of the input as base64url and treat as a base64url core.
"""
from entviz.entropy import (
    parse, detect_alphabet_by_disproof,
    HEX, BASE32, BECH32, BASE58, BASE64, BASE64URL,
)


# ---- direct detection function -----------------------------------------


def test_disproof_picks_hex_for_all_hex_chars():
    """All chars in [0-9a-f] → hex wins (most restrictive)."""
    assert detect_alphabet_by_disproof("deadbeef12345678") is HEX


def test_disproof_picks_hex_for_uppercase_hex():
    """Hex is case-insensitive — uppercase hex letters still match."""
    assert detect_alphabet_by_disproof("DEADBEEFCAFE") is HEX


def test_disproof_picks_base32_when_hex_disproven():
    """Uppercase letters past F → not hex; falls through to base32."""
    # 'G' is in base32 (RFC 4648) but not hex.
    assert detect_alphabet_by_disproof("ABCDEFG234567") is BASE32


def test_disproof_picks_bech32_for_bech32_only_chars():
    """A char unique to bech32 (e.g., '0' lowercase '8', '9') with all
    other chars also fitting bech32 → bech32 wins after base32 is
    disproven."""
    # '0' is in bech32 but not in base32 (RFC 4648).
    assert detect_alphabet_by_disproof("qpzry9x8gf0") is BECH32


def test_disproof_picks_base58_when_5bit_disproven():
    """An input that uses '1' (disproves base32 AND bech32, both
    excluding it) and 'G' (disproves hex which stops at F), but every
    char is in base58, lands on BASE58."""
    # Disproof chain:
    #   '1' disproves base32 (alphabet is A-Z + 2-7, no 1)
    #   '1' disproves bech32 (alphabet excludes 1 as the separator)
    #   'G' disproves hex (alphabet stops at F)
    # All chars in {1, A..H} are in base58 (123456789ABCDEFGHJKL... includes
    # 1-9 and A-H), so base58 wins.
    s = "1ABCDEFGH"
    assert detect_alphabet_by_disproof(s) is BASE58


def test_disproof_picks_base64_for_plus_or_slash():
    """'+' or '/' is only in base64."""
    assert detect_alphabet_by_disproof("ABC+/DEF") is BASE64


def test_disproof_picks_base64url_for_dash_or_underscore():
    """'-' or '_' is only in base64url."""
    assert detect_alphabet_by_disproof("ABC-_DEF") is BASE64URL


def test_disproof_returns_none_for_unencodable_input():
    """An input with chars in no alphabet (e.g. space) → None
    (caller falls back to UTF-8 re-encoding)."""
    assert detect_alphabet_by_disproof("hello world") is None


def test_disproof_returns_none_for_empty_input():
    assert detect_alphabet_by_disproof("") is None


# ---- integration with parse() / render() -------------------------------


def test_unrecognized_uppercase_alphanumeric_uses_base32():
    """An input like 'ABCDEFGHIJKLMNOPQR' (all base32 chars but no
    specific format prefix) should be parsed with BASE32, not fallback
    re-encoded as base64url."""
    p = parse("ABCDEFGHIJKLMNOPQR234567")
    assert p is not None
    assert p.alphabet is BASE32


def test_unrecognized_with_bech32_only_chars_uses_bech32():
    """An input that uses chars unique to bech32 (e.g., includes 0)
    but isn't a recognized bech32 address format."""
    # qpzry9x8gf2tvdw0s3 — 18 bech32 chars, no recognizable prefix.
    p = parse("qpzry9x8gf2tvdw0s3")
    assert p is not None
    assert p.alphabet is BECH32


def test_render_unrecognized_base32_alphabet_input():
    """End-to-end: render an unrecognized base32-shaped string."""
    from entviz.pipeline import render
    svg = render("ABCDEFGHIJKLMNOPQR234567")
    assert svg.startswith("<svg")
    assert "</svg>" in svg
