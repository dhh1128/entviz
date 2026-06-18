"""
Phase 10 acceptance tests: a color bar along the left GM-wide strip
of the bounding rect. Bands proportional to actual edge-color usage
(excluding blank cells), sorted descending by count with edge_colors
order as tiebreak.
"""
from lxml import etree

from entviz.pipeline import render


def _doc(svg_str):
    return etree.fromstring(svg_str.encode())


def _color_bar_bands(svg):
    """All rects at x=1 with width=bar_width=20 (the v6 color bar bands)."""
    return [
        r for r in svg.xpath('//*[local-name()="rect"]')
        if float(r.get("x", -1)) == 1 and float(r.get("width", -1)) == 20
    ]


def test_color_bar_bands_exist():
    svg = _doc(render("550e8400-e29b-41d4-a716-446655440000"))
    assert len(_color_bar_bands(svg)) >= 1


def test_color_bar_total_height_equals_drawing_region_height():
    # In v3 the color bar's drawing region is bounding_h - 2 (the top
    # and bottom 1-px black borders cover the outermost pixel rows).
    svg = _doc(render("550e8400-e29b-41d4-a716-446655440000"))
    bands = _color_bar_bands(svg)
    total = sum(float(b.get("height")) for b in bands)
    bounding_h = float(svg.get("height"))
    assert abs(total - (bounding_h - 2)) < 0.01


def test_color_bar_bands_are_contiguous_top_to_bottom():
    svg = _doc(render("550e8400-e29b-41d4-a716-446655440000"))
    bands = _color_bar_bands(svg)
    # Bands sorted by y should be contiguous, starting at y=1 (just below
    # the top border) and ending at bounding_h - 1 (just above the bottom).
    sorted_bands = sorted(bands, key=lambda b: float(b.get("y")))
    prev_bottom = float(sorted_bands[0].get("y"))
    assert prev_bottom == 1
    for b in sorted_bands:
        assert abs(float(b.get("y")) - prev_bottom) < 0.01
        prev_bottom = float(b.get("y")) + float(b.get("height"))
    assert abs(prev_bottom - (float(svg.get("height")) - 1)) < 0.01


def test_color_bar_band_fills_are_from_edge_colors():
    # Each band's fill must be one of the 4 edge colors selected for this
    # rendering. The first rect (white bounding) and second (entviz bg
    # grid fill) are NOT color-bar bands and are excluded by x=0, width=GM.
    from entviz.colors import POSSIBLE_EDGE_COLORS
    svg = _doc(render("550e8400-e29b-41d4-a716-446655440000"))
    bands = _color_bar_bands(svg)
    for b in bands:
        assert b.get("fill") in POSSIBLE_EDGE_COLORS, (
            f"color bar band fill {b.get('fill')!r} is not a possible edge color"
        )


def test_color_bar_bands_tile_without_gaps():
    # v9: the band ORDER is decoupled from count (it follows each pattern's
    # first appearance in the digest scan — see test_v9_color_bar), so band
    # heights are no longer monotonic top-to-bottom. The invariant that
    # survives: every band has positive height and the bands tile the bar
    # contiguously, with no gaps or overlaps.
    svg = _doc(render("550e8400-e29b-41d4-a716-446655440000"))
    bands = sorted(_color_bar_bands(svg), key=lambda b: float(b.get("y")))
    heights = [float(b.get("height")) for b in bands]
    assert heights and all(h > 0 for h in heights)
    for a, b in zip(bands, bands[1:]):
        assert abs((float(a.get("y")) + float(a.get("height"))) - float(b.get("y"))) < 0.01
