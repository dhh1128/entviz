"""
v4 overlay opacity rebalance: bump red and blue to 40%, gold to 30%,
keep white at 20%. The earlier per-bg values (20/20/30/30) didn't
register strongly enough on the colored backgrounds — particularly
in the smaller-grid hybrid overlays where the visible portion is
a corner/edge silhouette rather than a centered curve.

Lookup table is in pipeline._V3_OVERLAY_BY_BG (name kept for
historical continuity; the contents are v4 now).
"""
from entviz.pipeline import _ellipse_overlay_for_bg


def test_white_bg_opacity_20pct():
    _fill, opacity = _ellipse_overlay_for_bg("#ffffff")
    assert opacity == 0.20


def test_gold_bg_opacity_30pct():
    _fill, opacity = _ellipse_overlay_for_bg("#e7be00")
    assert opacity == 0.30


def test_red_bg_opacity_40pct():
    _fill, opacity = _ellipse_overlay_for_bg("#ff3f2f")
    assert opacity == 0.40


def test_blue_bg_opacity_40pct():
    _fill, opacity = _ellipse_overlay_for_bg("#2f3fbf")
    assert opacity == 0.40


def test_overlay_fill_directions_unchanged():
    """Fill colors (which side of the dichotomy) are unchanged from v3:
    white/gold/red darken, blue lightens."""
    assert _ellipse_overlay_for_bg("#ffffff")[0] == "#000000"
    assert _ellipse_overlay_for_bg("#e7be00")[0] == "#000000"
    assert _ellipse_overlay_for_bg("#ff3f2f")[0] == "#000000"
    assert _ellipse_overlay_for_bg("#2f3fbf")[0] == "#ffffff"
