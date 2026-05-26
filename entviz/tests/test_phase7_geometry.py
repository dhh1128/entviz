"""
Phase 7 / V3-2 acceptance tests: the bounding rect, grid margin (GM),
positioning of grid_rect, white fill, and four-sided black borders +
interior separator.

At 12pt / 96 DPI: nucleus_height=16, edge_size=8, GM=4. For an N×M
grid the v3 bounding rect is:
  width  = 1 + edge_size + 1 + GM + grid_w + GM + 1
  height = 1 + GM + grid_h + GM + nucleus_height + GM + 1
"""
from lxml import etree

from entviz.pipeline import render


def _parse(svg_str):
    return etree.fromstring(svg_str.encode())


def test_canvas_size_matches_bounding_rect_formula():
    # "deadbeef" → 2x2 grid → grid_w=128, grid_h=64.
    # width  = 1 + 8 + 1 + 4 + 128 + 4 + 1 = 147
    # height = 1 + 4 + 64 + 4 + 16 + 4 + 1 = 94
    svg = _parse(render("deadbeef"))
    assert float(svg.get("width")) == 147
    assert float(svg.get("height")) == 94


def test_first_rect_is_white_bounding_rect():
    svg = _parse(render("deadbeef"))
    rects = svg.xpath('//*[local-name()="rect"][not(ancestor::*[local-name()="defs"])]')
    first = rects[0]
    assert first.get("fill") == "#ffffff"
    assert float(first.get("x")) == 0
    assert float(first.get("y")) == 0
    assert float(first.get("width")) == 147
    assert float(first.get("height")) == 94


def test_black_borders_present():
    # v3: borders on all 4 sides + interior separator → ≥ 5 black lines.
    svg = _parse(render("deadbeef"))
    lines = svg.xpath('//*[local-name()="line"]')
    blacks = [l for l in lines if l.get("stroke") == "#000000"]
    assert len(blacks) >= 5, f"expected ≥5 black border lines, got {len(blacks)}"


def test_grid_rect_offset_inside_bounding():
    # The v3 grid_rect sits at (1 + edge_size + 1 + GM, 1 + GM)
    # = (1 + 8 + 1 + 4, 5) = (14, 5).
    # In a 2x2 grid, nuclei land at x ∈ {grid_rect.left + edge_size,
    # grid_rect.left + edge_size + cell_w} = {22, 86}
    # and y ∈ {13, 45}.
    svg = _parse(render("deadbeef"))
    nuclei = [
        r for r in svg.xpath('//*[local-name()="rect"]')
        if float(r.get("width", 0)) == 48 and float(r.get("height", 0)) == 16
    ]
    assert nuclei, "no nucleus rect found"
    for n in nuclei:
        assert float(n.get("x")) in (22, 86), f"nucleus x={n.get('x')}"
        assert float(n.get("y")) in (13, 45), f"nucleus y={n.get('y')}"


def test_bounding_rect_scales_with_grid_size():
    # UUID → 6 tokens (hex tokenization post-alphabet refactor) →
    # 2x3 grid → grid_w=128, grid_h=96.
    # width  = 1 + 8 + 1 + 4 + 128 + 4 + 1 = 147
    # height = 1 + 4 + 96 + 4 + 16 + 4 + 1 = 126
    svg = _parse(render("550e8400-e29b-41d4-a716-446655440000"))
    assert float(svg.get("width")) == 147
    assert float(svg.get("height")) == 126
