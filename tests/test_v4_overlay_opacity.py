"""
Per-bg ellipse-overlay styling.

v6 edge-emphasis rebalance (maintainer): instead of a single solid fill, the
overlay uses a SUBTLER fill plus a 2px stroke at a higher (edge) opacity, so
the silhouette stays crisp while the cells under the ellipse remain legible.
`_ellipse_overlay_for_bg` returns (fill_color, fill_opacity, edge_opacity):

    bg      fill_opacity   edge_opacity   fill direction
    white      0.20           0.30          darken (#000000)
    gold       0.20           0.30          darken (#000000)
    red        0.25           0.35          darken (#000000)
    blue       0.35           0.45          lighten (#ffffff)

The 2px edge stroke is drawn in the same color as the fill, with stroke-width
scaling as cell_h/20 (= 2px at the 12pt nominal). Lookup table is in
pipeline._V3_OVERLAY_BY_BG (name kept for historical continuity).
"""
from lxml import etree

from entviz.pipeline import _ellipse_overlay_for_bg, render

EXPECTED = {
    "#ffffff": ("#000000", 0.20, 0.30),
    "#e7be00": ("#000000", 0.20, 0.30),
    "#ff3f2f": ("#000000", 0.25, 0.35),
    "#2f3fbf": ("#ffffff", 0.35, 0.45),
}


def test_per_bg_fill_and_edge_opacities():
    for bg, expected in EXPECTED.items():
        assert _ellipse_overlay_for_bg(bg) == expected, bg


def test_edge_opacity_exceeds_fill_opacity():
    """The whole point of the rebalance: the edge is more opaque than the
    fill, so the silhouette rim reads more strongly than the interior wash."""
    for bg in EXPECTED:
        _fill, fill_op, edge_op = _ellipse_overlay_for_bg(bg)
        assert edge_op > fill_op, bg


def test_overlay_fill_directions_unchanged():
    """Fill colors (which side of the dichotomy): white/gold/red darken,
    blue lightens."""
    assert _ellipse_overlay_for_bg("#ffffff")[0] == "#000000"
    assert _ellipse_overlay_for_bg("#e7be00")[0] == "#000000"
    assert _ellipse_overlay_for_bg("#ff3f2f")[0] == "#000000"
    assert _ellipse_overlay_for_bg("#2f3fbf")[0] == "#ffffff"


def test_unknown_bg_fallback_is_three_tuple():
    fill, fill_op, edge_op = _ellipse_overlay_for_bg("#123456")
    assert fill in ("#000000", "#ffffff")
    assert (fill_op, edge_op) == (0.20, 0.30)


def _ellipse(svg_str):
    svg = etree.fromstring(svg_str.encode())
    els = svg.xpath('//*[local-name()="ellipse"]')
    return els[0] if els else None


def test_rendered_ellipse_has_distinct_fill_and_stroke_opacity():
    """The rendered overlay carries a 2px stroke whose stroke-opacity differs
    from (exceeds) its fill-opacity — proving the edge-emphasis is emitted,
    not just present in the lookup table."""
    el = _ellipse(render("0123456789abcdef" * 8))   # blue-bg large grid
    assert el is not None
    fill_op = float(el.get("fill-opacity"))
    stroke_op = float(el.get("stroke-opacity"))
    assert el.get("stroke") == el.get("fill")
    assert stroke_op > fill_op
    assert float(el.get("stroke-width")) == 2.0      # cell_h/20 at 12pt
