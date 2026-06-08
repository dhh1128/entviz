"""
Tests for snowflake-ID parsing (Twitter/Discord/Mastodon-style 64-bit
integer IDs serialized as 17-20 decimal digits).

See `this.i:sn0wfl4k` for the three decisions exercised here:
  (1) DECIMAL alphabet, verbatim rendering.
  (2) Deterministic structural validity (v8, SPEC-F1): clock-free; a canonical
      snowflake has its sign bit clear (value < 2**63), which structurally
      bounds the 41-bit timestamp field to [2015, ~2084]. The pre-v8 wall-clock
      "future window" was removed because it made the same input render
      differently over time (a determinism-MUST violation).
  (3) Parser order: parse_snowflake precedes parse_hex.
"""
import time

import pytest

from entviz.entropy import (
    DECIMAL,
    parse,
    parse_snowflake,
)

# Discord epoch (2015-01-01T00:00:00.000Z in unix ms). Defined here only to
# build test snowflakes from a timestamp; the parser no longer uses it (v8).
DISCORD_EPOCH_MS = 1420070400000
_SIGN_BIT = 1 << 63  # 2**63 — a canonical snowflake is strictly below this.


def _snowflake_from_ms(ts_ms: int, worker: int = 1, process: int = 0, seq: int = 0) -> str:
    """Build a decimal snowflake string from a unix-ms timestamp."""
    delta = ts_ms - DISCORD_EPOCH_MS
    if delta < 0:
        raise ValueError("timestamp predates Discord epoch")
    n = (delta << 22) | ((worker & 0x1F) << 17) | ((process & 0x1F) << 12) | (seq & 0xFFF)
    return str(n)


# --- Detection: canonical snowflakes -------------------------------------

def test_real_discord_snowflake_from_docs():
    # 80351110224678912 appears in Discord's developer documentation.
    parsed = parse_snowflake("80351110224678912")
    assert parsed is not None
    assert parsed.type == "snowflake"
    assert parsed.alphabet is DECIMAL
    assert parsed.core == "80351110224678912"
    assert parsed.prefix is None
    assert parsed.suffix is None


def test_snowflake_from_2020():
    # 2020-01-01T00:00:00Z -> 1577836800000 ms
    snowflake = _snowflake_from_ms(1577836800000, worker=3, process=2, seq=42)
    parsed = parse_snowflake(snowflake)
    assert parsed is not None
    assert parsed.type == "snowflake"
    assert parsed.core == snowflake


def test_snowflake_at_discord_epoch_minimum():
    # Exactly at the Discord epoch -> delta=0; the worker/process/seq give a
    # tiny number that is < 17 digits, so it shouldn't parse on length.
    snowflake = _snowflake_from_ms(DISCORD_EPOCH_MS)
    assert len(snowflake) < 17
    assert parse_snowflake(snowflake) is None


def test_snowflake_19_digits():
    # 19-digit snowflakes are the modern-era common case.
    snowflake = _snowflake_from_ms(1700000000000, worker=10, process=5, seq=999)
    assert 17 <= len(snowflake) <= 20
    parsed = parse_snowflake(snowflake)
    assert parsed is not None
    assert parsed.core == snowflake


def test_snowflake_uses_decimal_alphabet():
    parsed = parse_snowflake("80351110224678912")
    assert parsed.alphabet is DECIMAL
    assert parsed.alphabet.bits_per_char == 4
    assert parsed.alphabet.chars == "0123456789"


# --- v8 (SPEC-F1): deterministic structural validity ---------------------

def test_detection_is_clock_independent():
    """The headline SPEC-F1 guard: classification MUST NOT depend on the wall
    clock. This boundary decimal sat just past the old now+5y window, so it
    parsed as hex 'today' and snowflake a few years later — different SVG for
    the same input. Under the v8 structural rule it is < 2**63, so it is a
    snowflake deterministically, at every clock value."""
    boundary = "2108553795993600000"  # implied date ~2031, value < 2**63
    assert int(boundary) < _SIGN_BIT
    results = []
    for fake_now in (0, 10 ** 13, 10 ** 18):  # 1970, ~2286, ~year 33658
        # Even if some future refactor reintroduced time.time(), pinning it to
        # wildly different values must not change the classification.
        orig = time.time
        time.time = lambda v=fake_now: v
        try:
            results.append(parse(boundary).type)
        finally:
            time.time = orig
    assert set(results) == {"snowflake"}, results


def test_accept_just_below_sign_bit():
    """2**63 - 1 (19 digits, sign bit clear) is the largest canonical
    snowflake — accepted."""
    candidate = str(_SIGN_BIT - 1)  # 9223372036854775807, 19 digits
    assert 17 <= len(candidate) <= 20
    parsed = parse_snowflake(candidate)
    assert parsed is not None
    assert parsed.type == "snowflake"


def test_reject_when_sign_bit_set():
    """A 17-20 digit decimal with bit 63 set (value >= 2**63) is not a
    canonical snowflake — its implied timestamp overflows the 41-bit field
    (a date past ~2084). Rejected by parse_snowflake; dispatches to hex."""
    for candidate in (
        str(_SIGN_BIT),              # 9223372036854775808 (19 digits)
        "18446744073709551615",      # 2**64 - 1 (20 digits, the old overflow case)
    ):
        assert 17 <= len(candidate) <= 20
        assert parse_snowflake(candidate) is None
        # Falls through to hex at the top level (even length -> parse_hex, else
        # disproof resolves HEX).
        p = parse(candidate)
        assert p is not None and p.alphabet.name == "hex"


def test_far_future_timestamp_overflows_and_is_rejected():
    """A timestamp ~100 years past 2026 overflows the 41-bit field (sets bit
    63), so it is rejected — deterministically, without any clock."""
    far_future_ms = 1767225600000 + (100 * 365 * 86400 * 1000)  # ~2126
    n = ((far_future_ms - DISCORD_EPOCH_MS) << 22)
    assert n >= _SIGN_BIT  # the 41-bit timestamp field overflowed
    candidate = str(n)
    if len(candidate) > 20:
        pytest.skip("constructed candidate exceeds the 20-digit length filter")
    assert parse_snowflake(candidate) is None


def test_smallest_17_digit_is_a_snowflake():
    """The smallest 17-digit decimal (10**16) has its sign bit clear, so it is
    a valid (early-2015) snowflake — no lower timestamp bound is needed."""
    candidate = str(10 ** 16)
    assert len(candidate) == 17
    parsed = parse_snowflake(candidate)
    assert parsed is not None
    assert parsed.type == "snowflake"


# --- Rejection: wrong length / shape ------------------------------------

def test_reject_too_short():
    # 16-digit decimal is below the snowflake-length floor.
    assert parse_snowflake("1234567890123456") is None


def test_reject_too_long():
    # 21-digit decimal exceeds the SNOWFLAKE_REGEX {17,20} length filter.
    assert parse_snowflake("123456789012345678901") is None


def test_reject_non_digit():
    assert parse_snowflake("80351110224678912x") is None
    assert parse_snowflake("8035111022467891a") is None
    assert parse_snowflake("") is None
    assert parse_snowflake(None) is None


def test_reject_unicode_digits():
    # \d in Python re matches Unicode digits by default; the parser must
    # use [0-9] to avoid accepting Arabic-Indic etc. as snowflakes.
    arabic_18 = "٠" * 18
    assert parse_snowflake(arabic_18) is None


# --- Top-level parse() dispatch ordering --------------------------------

def test_parse_dispatch_prefers_snowflake_over_hex():
    # 80351110224678912 is all digits, so parse_hex WOULD match it
    # (digits are valid hex). The parser registration order must run
    # parse_snowflake first.
    parsed = parse("80351110224678912")
    assert parsed is not None
    assert parsed.type == "snowflake"


def test_parse_treats_16_digit_decimal_as_hex():
    # 16 digits is below snowflake floor but pure-digit => valid hex.
    parsed = parse("1234567890123456")
    assert parsed is not None
    assert parsed.type == "hex"


# --- Pipeline smoke test -------------------------------------------------

def test_pipeline_renders_snowflake_without_error():
    from entviz.pipeline import render
    svg = render("80351110224678912")
    assert svg.startswith("<")
    assert "80351110224678912" in svg or "8035" in svg  # cells visible


def test_pipeline_uses_shrunk_font_for_6char_decimal_tokens():
    """
    DECIMAL has bits_per_char=4 like HEX, so its tokens are 6 chars and
    must render at 0.75× the reference font size to fit inside the
    nucleus. Regression guard for the pipeline check that used to be
    `alphabet.name == "hex"` — too narrow, would have left decimal text
    overflowing the nucleus.
    """
    from entviz.pipeline import render
    # Render at 12pt (reference). Expect cell text font-size = 12 * 0.75
    # = 9pt = 12px @ 96 dpi.
    svg = render("80351110224678912", font_size_pt=12)
    # The shrunken cell text size is 12px. The label strip text is also
    # 12px (round(12*0.75)*4/3 = 12), so we look for a 6-digit decimal
    # chunk specifically to disambiguate.
    assert 'font-size: 12.0px' in svg or 'font-size: 12px' in svg
    # Confirm: an unshrunken 16px cell text for the snowflake digits is
    # NOT present.
    import re
    big_digit_cell = re.search(
        r'font-size: 16(?:\.0)?px[^<]*>\d{4,6}<',
        svg,
    )
    assert big_digit_cell is None, f"decimal cell text rendered at full size: {big_digit_cell.group(0)}"
