"""
v4 foreground contrast: pick black/white text by perceptual lightness in
Oklab — a modern perceptually uniform color space — with a slight bias
toward white past the midpoint.

Threshold: Oklab L > 0.6 → black, else white.

Why Oklab and not the WCAG luminance Y? WCAG Y over-weights green
(0.7152 × G), so saturated dark greens like #55841c land at Y=0.185 —
just past the WCAG-AA equal-contrast crossover (Y=0.179) and thus
"technically prefer black", even though the eye reads them as dark
and expects white text. Oklab's perceptual lightness puts that same
dark green at L=0.559 — closer to the perceptual midpoint than Y
suggests, but still nominally on the "black-preferring" side of a
strict L>0.5 threshold.

Why 0.6 rather than the rigorous 0.5 midpoint? At "equal lightness
gap" (L=0.5), small dark glyphs are slightly harder to read on a
mid-gray than small light glyphs of the same gap — the eye's
bright-adaptation handles small light marks on darker fields more
crisply than the inverse. A 0.6 threshold flips dark-green-class
colors (L≈0.54–0.59) to white where they read better.
"""
from entviz.colors import get_nucleus_colors


def test_dark_green_picks_white():
    """#55841c (Oklab L≈0.559) sat just above the old WCAG crossover and
    picked black — visually wrong for a saturated dark green. With
    Oklab L>0.6, it now picks white."""
    bg, fg = get_nucleus_colors(0x1c8455)  # b=0x1c, g=0x84, r=0x55 → #55841c
    assert bg == "#55841c"
    assert fg == "#ffffff", f"dark green should pick white, got {fg}"


def test_medium_beige_picks_black_not_white():
    """A1B2C3 → rgb(195, 178, 161), Oklab L≈0.773. Clearly above 0.6,
    picks black."""
    bg, fg = get_nucleus_colors(0xA1B2C3)
    assert bg == "#c3b2a1"
    assert fg == "#000000"


def test_pure_white_bg_picks_black():
    _bg, fg = get_nucleus_colors(0xFFFFFF)
    assert fg == "#000000"


def test_pure_black_bg_picks_white():
    _bg, fg = get_nucleus_colors(0x000000)
    assert fg == "#ffffff"


def test_very_dark_bg_picks_white():
    """rgb(20, 20, 20) → Oklab L≈0.191, well below threshold."""
    _bg, fg = get_nucleus_colors(0x141414)
    assert fg == "#ffffff"


def test_borderline_dark_picks_white():
    """rgb(100, 100, 100) → Oklab L≈0.503, below 0.6 → white."""
    _bg, fg = get_nucleus_colors(0x646464)
    assert fg == "#ffffff"


def test_midgray_under_threshold_picks_white():
    """rgb(125, 125, 125) → Oklab L≈0.590, still below 0.6 → white.
    (Under the old WCAG threshold this picked black; under Oklab L>0.6
    it picks white — intentional bias for readability of small dark
    glyphs on mid-gray fields.)"""
    _bg, fg = get_nucleus_colors(0x7D7D7D)
    assert fg == "#ffffff"


def test_midgray_over_threshold_picks_black():
    """rgb(160, 160, 160) → Oklab L≈0.685, above 0.6 → black."""
    _bg, fg = get_nucleus_colors(0xA0A0A0)
    assert fg == "#000000"


def test_mid_luminance_gold_picks_black():
    """Palette gold #e7be00 → Oklab L≈0.814 → black."""
    _bg, fg = get_nucleus_colors(0x00BEE7)  # r=e7 g=be b=00 → #e7be00
    assert fg == "#000000"


def test_red_bg_picks_black():
    """Red #ff3f2f → Oklab L≈0.657, just above 0.6 → black."""
    bg, fg = get_nucleus_colors(0x2f3fff)
    assert bg == "#ff3f2f"
    assert fg == "#000000"


def test_blue_bg_picks_white():
    """Blue #2f3fbf → Oklab L≈0.445, below 0.6 → white."""
    bg, fg = get_nucleus_colors(0xbf3f2f)  # quant b=0xbf, g=0x3f, r=0x2f
    assert bg == "#2f3fbf"
    assert fg == "#ffffff"
