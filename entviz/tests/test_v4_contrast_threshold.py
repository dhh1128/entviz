"""
v4 foreground contrast: pick black/white text per WCAG-style luminance
contrast, not a naive `luminance < 0.5` split. The crossover where
black-text-on-bg has equal WCAG contrast to white-text-on-bg sits at
luminance ≈ 0.179, NOT 0.5:

    (1 + 0.05) / (Y + 0.05) = (Y + 0.05) / (0 + 0.05)
  → (Y + 0.05)² = 0.0525
  → Y = √0.0525 − 0.05 ≈ 0.1791

Previously the v3 rule `lum < 0.5 → white, else black` mis-classified
medium-luminance backgrounds (0.179 < Y < 0.5): pairing them with
white gave WCAG contrast 2-3:1 (fails AA), where black would have
given 6-12:1.
"""
from entviz.colors import get_nucleus_colors


def test_medium_beige_picks_black_not_white():
    """A1B2C3 → rgb(195, 178, 161), luminance ≈ 0.47. Sits in the
    0.179-0.5 zone where v3 picked white (poor contrast); v4 picks
    black."""
    bg, fg = get_nucleus_colors(0xA1B2C3)
    assert bg == "#c3b2a1"  # confirms r/g/b order
    assert fg == "#000000", f"expected black fg for medium-luminance bg, got {fg}"


def test_pure_white_bg_picks_black():
    """Y=1.0 → always black."""
    _bg, fg = get_nucleus_colors(0xFFFFFF)
    assert fg == "#000000"


def test_pure_black_bg_picks_white():
    """Y=0.0 → always white."""
    _bg, fg = get_nucleus_colors(0x000000)
    assert fg == "#ffffff"


def test_very_dark_bg_picks_white():
    """A dark-but-not-black bg below the 0.179 crossover gets white."""
    # rgb(20, 20, 20) → Y ≈ 0.006, well below crossover.
    _bg, fg = get_nucleus_colors(0x141414)
    assert fg == "#ffffff"


def test_borderline_dark_picks_white():
    """A bg with Y just below 0.179 gets white."""
    # rgb(100, 100, 100) → Y ≈ 0.127
    _bg, fg = get_nucleus_colors(0x646464)
    assert fg == "#ffffff"


def test_borderline_light_picks_black():
    """A bg with Y just above 0.179 gets black — the WCAG choice."""
    # rgb(125, 125, 125) → Y ≈ 0.205, just above crossover.
    _bg, fg = get_nucleus_colors(0x7D7D7D)
    assert fg == "#000000"


def test_mid_luminance_gold_picks_black():
    """Gold #ffd966, the entviz background candidate, has Y ≈ 0.71 — way
    above crossover; clearly black."""
    _bg, fg = get_nucleus_colors(0xFFD966)
    assert fg == "#000000"


def test_red_bg_picks_black():
    """Red #ff3f2f → Y ≈ 0.265 (above 0.179 crossover) → black.
    Quant encoding: r = low byte, g = mid byte, b = high byte, so the
    quant for bg #ff3f2f is 0x2f3fff (b=0x2f, g=0x3f, r=0xff)."""
    bg, fg = get_nucleus_colors(0x2f3fff)
    assert bg == "#ff3f2f"
    assert fg == "#000000"
