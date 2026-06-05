"""
Tests for snowflake-ID parsing (Twitter/Discord/Mastodon-style 64-bit
integer IDs serialized as 17-20 decimal digits).

See `this.i:sn0wfl4k` for the three decisions exercised here:
  (1) DECIMAL alphabet, verbatim rendering.
  (2) Plausible-timestamp range check (Discord epoch ± window).
  (3) Parser order: parse_snowflake precedes parse_hex.
"""
import pytest

from entviz import entropy
from entviz.entropy import (
    DECIMAL,
    DISCORD_EPOCH_MS,
    _SNOWFLAKE_FUTURE_WINDOW_MS,
    parse,
    parse_hex,
    parse_snowflake,
)

# A fixed reference clock (2026-01-01T00:00:00Z, in unix ms). The future-window
# tests pin entropy._now_ms() to this so they exercise the window boundary
# deterministically instead of drifting with the real wall clock (TST-F3): both
# the constructed snowflake and the parser's "now" share this one reference.
FIXED_NOW_MS = 1767225600000


@pytest.fixture
def fixed_clock(monkeypatch):
    """Pin parse_snowflake's notion of 'now' to FIXED_NOW_MS."""
    monkeypatch.setattr(entropy, "_now_ms", lambda: FIXED_NOW_MS)
    return FIXED_NOW_MS


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
    # Exactly at the Discord epoch -> delta=0, but we still need 17+ digits.
    # A worker/process/seq combination at the epoch gives a tiny number,
    # so this case actually shouldn't parse (< 17 digits). Verify behavior.
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


# --- Rejection: out-of-range timestamps ---------------------------------

def test_pre_2015_timestamp_unreachable_for_valid_length():
    # The parser rejects a decoded timestamp before the Discord epoch, but
    # that branch is unreachable for any length-valid snowflake: the smallest
    # 17-digit decimal (10**16) already has top-42-bits >= 1, so its decoded
    # timestamp is strictly after the epoch. This pins the invariant the
    # `ts_ms < DISCORD_EPOCH_MS` guard relies on (and is robust to the wall
    # clock — an early-2015 timestamp is inside the window for any real now).
    smallest_17_digit = 10 ** 16
    assert len(str(smallest_17_digit)) == 17
    ts_ms = (smallest_17_digit >> 22) + DISCORD_EPOCH_MS
    assert ts_ms > DISCORD_EPOCH_MS
    # And it parses as a real (early-2015) snowflake.
    parsed = parse_snowflake(str(smallest_17_digit))
    assert parsed is not None
    assert parsed.type == "snowflake"


def test_reject_decimal_with_far_future_timestamp(fixed_clock):
    # 100 years past the pinned now -> way beyond the 5-year window.
    far_future_ms = fixed_clock + (100 * 365 * 86400 * 1000)
    snowflake = _snowflake_from_ms(far_future_ms)
    # Sanity: should still be a 17-20 digit string.
    assert 17 <= len(snowflake) <= 20
    assert parse_snowflake(snowflake) is None


def test_reject_decimal_at_5_year_window_boundary_plus_one(fixed_clock):
    # 1 ms past the accept window's far edge -> rejected. Pinning the clock
    # makes this an exact boundary assertion, not an approximate one.
    just_outside_ms = fixed_clock + _SNOWFLAKE_FUTURE_WINDOW_MS + 1
    snowflake = _snowflake_from_ms(just_outside_ms)
    assert 17 <= len(snowflake) <= 20
    assert parse_snowflake(snowflake) is None


def test_accept_decimal_just_inside_future_window(fixed_clock):
    # Exactly at the window's far edge (now + 5y) -> still accepted: the guard
    # rejects only ts_ms strictly greater than now + window.
    at_edge_ms = fixed_clock + _SNOWFLAKE_FUTURE_WINDOW_MS
    snowflake = _snowflake_from_ms(at_edge_ms)
    assert 17 <= len(snowflake) <= 20
    parsed = parse_snowflake(snowflake)
    assert parsed is not None
    assert parsed.type == "snowflake"


# --- Rejection: wrong length --------------------------------------------

def test_reject_too_short():
    # 16-digit decimal is below the snowflake-length floor.
    assert parse_snowflake("1234567890123456") is None


def test_reject_too_long():
    # 21-digit decimal exceeds 64 bits — cannot be a snowflake.
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


def test_parse_falls_through_to_hex_for_non_snowflake_decimal(fixed_clock):
    # An 18-digit decimal whose implied timestamp is far in the future
    # should NOT be classified as a snowflake. It should fall through to
    # hex (pure digits are valid hex; even length, so parse_hex accepts).
    far_future_ms = fixed_clock + (100 * 365 * 86400 * 1000)
    candidate = _snowflake_from_ms(far_future_ms)
    if len(candidate) % 2 != 0:
        candidate = candidate[:-1]  # parse_hex requires even length
        if len(candidate) < 17:
            pytest.skip("constructed candidate too short after even-length trim")
    parsed = parse(candidate)
    assert parsed is not None
    assert parsed.type != "snowflake"
    # Either parse_hex picks it up, or disproof-detection picks HEX.
    assert parsed.alphabet.name == "hex"


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
