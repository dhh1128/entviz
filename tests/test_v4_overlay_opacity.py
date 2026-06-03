"""
Per-bg ellipse-overlay opacity. The v4 baseline was white 20 / gold 30 /
red 40 / blue 40. v6 rebalance (maintainer): white +10 -> 30, red -5 -> 35,
blue +5 -> 45, gold unchanged at 30 — white's darkened overlay needed more
presence, red was reading too heavy, and blue's lightening needed a touch
more pop.

Lookup table is in pipeline._V3_OVERLAY_BY_BG (name kept for
historical continuity; the contents are current now).
"""
from entviz.pipeline import _ellipse_overlay_for_bg


def test_white_bg_opacity_30pct():
    _fill, opacity = _ellipse_overlay_for_bg("#ffffff")
    assert opacity == 0.30


def test_gold_bg_opacity_30pct():
    _fill, opacity = _ellipse_overlay_for_bg("#e7be00")
    assert opacity == 0.30


def test_red_bg_opacity_35pct():
    _fill, opacity = _ellipse_overlay_for_bg("#ff3f2f")
    assert opacity == 0.35


def test_blue_bg_opacity_45pct():
    _fill, opacity = _ellipse_overlay_for_bg("#2f3fbf")
    assert opacity == 0.45


def test_overlay_fill_directions_unchanged():
    """Fill colors (which side of the dichotomy) are unchanged from v3:
    white/gold/red darken, blue lightens."""
    assert _ellipse_overlay_for_bg("#ffffff")[0] == "#000000"
    assert _ellipse_overlay_for_bg("#e7be00")[0] == "#000000"
    assert _ellipse_overlay_for_bg("#ff3f2f")[0] == "#000000"
    assert _ellipse_overlay_for_bg("#2f3fbf")[0] == "#ffffff"
