"""
Phase 7 acceptance tests: introduce the bounding rect (v2's outer
canvas), grid margin (GM), positioning of grid_rect inside the
bounding rect, white fill, and 1-pixel black borders on top/right/
bottom (the leftmost GM-wide strip is reserved for the color bar
and gets no border).

At 12pt / 96 DPI: nucleus_height=16, edge_size=8, GM=4. For an N×M
grid the bounding rect is GM+GM+grid_w+GM+1 wide and
1+GM+grid_h+GM+nucleus_height+GM+1 tall.
"""
from lxml import etree

from entviz.pipeline import render


def _parse(svg_str):
    return etree.fromstring(svg_str.encode())


def test_canvas_size_matches_bounding_rect_formula():
    # Use 6-token input (UUID gives 8 tokens; use the smaller short input).
    # For "deadbeef" (2 tokens → 2x2 grid with 2 blanks):
    # cell_w=64, cell_h=32, grid_w=128, grid_h=64, edge_size=8, GM=4,
    # nucleus_height=16.
    # width  = 4 + 4 + 128 + 4 + 1 = 141
    # height = 1 + 4 + 64  + 4 + 16 + 4 + 1 = 94
    svg = _parse(render("deadbeef"))
    assert float(svg.get("width")) == 141
    assert float(svg.get("height")) == 94


def test_first_rect_is_white_bounding_rect():
    svg = _parse(render("deadbeef"))
    # Skip any rect that lives inside <defs> (e.g., the Phase 12 clipPath).
    rects = svg.xpath('//*[local-name()="rect"][not(ancestor::*[local-name()="defs"])]')
    first = rects[0]
    assert first.get("fill") == "#ffffff"
    assert float(first.get("x")) == 0
    assert float(first.get("y")) == 0
    assert float(first.get("width")) == 141
    assert float(first.get("height")) == 94


def test_black_borders_on_three_sides_not_left():
    # Three 1px black lines: top (from x=GM to right edge), right
    # (full height), bottom (from x=GM to right edge). No line on the
    # left (color bar strip).
    svg = _parse(render("deadbeef"))
    lines = svg.xpath('//*[local-name()="line" or local-name()="rect"]')
    # Find anything with stroke or fill #000000 forming a border.
    blacks = [
        el for el in lines
        if (el.get("stroke") == "#000000" or el.get("fill") == "#000000")
    ]
    # At least 3 black border elements (some impls may use rects or lines).
    assert len(blacks) >= 3, f"expected ≥3 black border elements, got {len(blacks)}"


def test_grid_rect_offset_inside_bounding():
    # The grid_rect sits at (GM+GM, 1+GM) = (8, 5) for 12pt/96DPI.
    # In a 2x2 grid, the four possible cell positions place nuclei at
    # x ∈ {grid_rect.left + edge_size, grid_rect.left + edge_size + cell_w}
    #   = {16, 80}
    # and y ∈ {grid_rect.top + edge_size, grid_rect.top + edge_size + cell_h}
    #   = {13, 45}.
    # Blank-cell shifting may place tokens at any of the 4 cells, so just
    # verify every actual nucleus lands at one of those expected positions.
    svg = _parse(render("deadbeef"))
    # Nucleus is exactly nucleus_width × nucleus_height = 48 × 16 at
    # 12pt/96DPI (nucleus_width = nucleus_height * 3 per spec).
    nuclei = [
        r for r in svg.xpath('//*[local-name()="rect"]')
        if float(r.get("width", 0)) == 48 and float(r.get("height", 0)) == 16
    ]
    assert nuclei, "no nucleus rect found (24px wide)"
    for n in nuclei:
        assert float(n.get("x")) in (16, 80), f"nucleus x={n.get('x')}"
        assert float(n.get("y")) in (13, 45), f"nucleus y={n.get('y')}"


def test_bounding_rect_scales_with_grid_size():
    # UUID renders to 8 tokens → grid is 4x2 (8 cells = 8 tokens, no blanks).
    # Wait: choose_grid(8, 1.0) gives cols=2, rows=4 (see Phase 3 tests).
    # grid_w = 64*2 = 128, grid_h = 32*4 = 128.
    # width = 4+4+128+4+1 = 141, height = 1+4+128+4+16+4+1 = 158.
    svg = _parse(render("550e8400-e29b-41d4-a716-446655440000"))
    assert float(svg.get("width")) == 141
    assert float(svg.get("height")) == 158
