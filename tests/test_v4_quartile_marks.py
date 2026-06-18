"""
v4 quartile mark: small right triangle in one corner of the nucleus,
filled with the cell text's foreground color (white or black by
luminance contrast against the nucleus_bg). Legs = nucleus_height / 2.
Orientation distinguishes quartiles: 1st=TL, 2nd=TR, 3rd=BR, 4th=BL.
"""
from lxml import etree

from entviz.pipeline import render


def _doc(svg_str):
    return etree.fromstring(svg_str.encode())


def test_four_quartile_triangles_per_render():
    """An entviz with token_count divisible by 4 (or ≥ 8) gets exactly 4
    quartile triangles (each is a <polygon>). With 6 tokens (UUID), the
    last quartile ftok lands on a padded blank, so only 3 are drawn."""
    # Use a 16-token base64-encoded input ("Lorem ipsum..." → 16 tokens,
    # divisible by 4 so all 4 quartile ftoks are real).
    svg = _doc(render("Lorem ipsum dolor sit amet, consectetur adipiscing elit."))
    polygons = svg.xpath('//*[local-name()="polygon"][not(@data-bar-marker)]')
    assert len(polygons) == 4, f"expected 4 quartile triangles, got {len(polygons)}"


def test_quartile_count_is_three_when_last_quartile_is_padding():
    """UUID has 6 tokens → padded to 8 for the quartile divide → last
    quartile's first entry is a padding blank → only 3 triangles drawn."""
    svg = _doc(render("550e8400-e29b-41d4-a716-446655440000"))
    polygons = svg.xpath('//*[local-name()="polygon"][not(@data-bar-marker)]')
    assert len(polygons) == 3


def test_quartile_triangle_color_is_fg_color():
    """Each triangle's fill is either #ffffff (white) or #000000 (black) —
    the cell text's foreground color."""
    svg = _doc(render("550e8400-e29b-41d4-a716-446655440000"))
    polygons = svg.xpath('//*[local-name()="polygon"][not(@data-bar-marker)]')
    for p in polygons:
        assert p.get("fill") in ("#ffffff", "#000000")


def test_quartile_triangle_has_three_vertices():
    """A right triangle has 3 vertices, expressed as 3 'x,y' points."""
    svg = _doc(render("550e8400-e29b-41d4-a716-446655440000"))
    polygons = svg.xpath('//*[local-name()="polygon"][not(@data-bar-marker)]')
    for p in polygons:
        points = p.get("points", "")
        # 3 'x,y' tokens
        vertex_count = len(points.split())
        assert vertex_count == 3, f"polygon has {vertex_count} points; expected 3"


def test_quartile_triangle_legs_equal_nucleus_height_over_2():
    """At 12pt, nucleus_height = 20, so each leg of the right triangle
    is 10 px. Inspecting one polygon should show the two legs aligning
    along axes with length 10."""
    svg = _doc(render("550e8400-e29b-41d4-a716-446655440000"))
    polygons = svg.xpath('//*[local-name()="polygon"][not(@data-bar-marker)]')
    for p in polygons:
        pts = [tuple(map(float, pair.split(",")))
               for pair in p.get("points").split()]
        # Find the right-angle vertex: the one shared by both legs (the
        # other 2 vertices form the hypotenuse).
        # Compute pairwise distances; the leg lengths are the two
        # shortest sides (both = nucleus_height/2 = 10); the hypotenuse
        # is the longest.
        def dist(a, b):
            return ((a[0] - b[0])**2 + (a[1] - b[1])**2) ** 0.5
        d01 = dist(pts[0], pts[1])
        d12 = dist(pts[1], pts[2])
        d02 = dist(pts[0], pts[2])
        sides = sorted([d01, d12, d02])
        assert abs(sides[0] - 10) < 0.01, f"shortest side {sides[0]}"
        assert abs(sides[1] - 10) < 0.01, f"second side {sides[1]}"
        assert abs(sides[2] - 10 * (2 ** 0.5)) < 0.01, f"hypotenuse {sides[2]}"
