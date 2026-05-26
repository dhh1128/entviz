"""
Geometry acceptance tests — v4 bounding rect, grid margin (GM), positioning
of grid_rect, white fill, and four-sided gray borders + interior separator.

At 12pt / 96 DPI in v4:
  font_size_px = 16
  nucleus_width = 48, nucleus_height = 20
  box_width = 6, box_height = 10
  cell_width = 60, cell_height = 40
  GM = 5

Bounding rect:
  width  = 1 + box_height + 1 + GM + grid_w + GM + 1 = 1 + 10 + 1 + 5 + grid_w + 5 + 1
  height = 1 + GM + grid_h + GM + 1 = 1 + 5 + grid_h + 5 + 1
"""
from lxml import etree

from entviz.pipeline import render


def _parse(svg_str):
    return etree.fromstring(svg_str.encode())


def test_canvas_size_matches_bounding_rect_formula():
    # "deadbeef" → 2 hex tokens → 2x2 grid → grid_w=120, grid_h=80.
    # width  = 1 + 10 + 1 + 5 + 120 + 5 + 1 = 143
    # height = 1 + 5 + 80 + 5 + 1 = 92
    svg = _parse(render("deadbeef"))
    assert float(svg.get("width")) == 143
    assert float(svg.get("height")) == 92


def test_first_rect_is_white_bounding_rect():
    svg = _parse(render("deadbeef"))
    rects = svg.xpath('//*[local-name()="rect"][not(ancestor::*[local-name()="defs"])]')
    first = rects[0]
    assert first.get("fill") == "#ffffff"
    assert float(first.get("x")) == 0
    assert float(first.get("y")) == 0
    assert float(first.get("width")) == 143
    assert float(first.get("height")) == 92


def test_gray_borders_present():
    # v4: borders on all 4 sides + interior separator → 5 gray lines.
    svg = _parse(render("deadbeef"))
    lines = svg.xpath('//*[local-name()="line"]')
    grays = [l for l in lines if l.get("stroke") == "#808080"]
    assert len(grays) >= 5, f"expected ≥5 gray border lines, got {len(grays)}"


def test_grid_rect_offset_inside_bounding():
    # v4 grid_rect sits at (1 + box_height + 1 + GM, 1 + GM)
    # = (1 + 10 + 1 + 5, 1 + 5) = (17, 6).
    # In a 2x2 grid, nuclei land at:
    #   x ∈ {grid_rect.left + box_width, grid_rect.left + box_width + cell_w}
    #     = {17 + 6, 17 + 6 + 60} = {23, 83}
    #   y ∈ {6 + 10, 6 + 10 + 40} = {16, 56}
    svg = _parse(render("deadbeef"))
    nuclei = [
        r for r in svg.xpath('//*[local-name()="rect"]')
        if float(r.get("width", 0)) == 48 and float(r.get("height", 0)) == 20
    ]
    assert nuclei, "no nucleus rect found"
    for n in nuclei:
        assert float(n.get("x")) in (23, 83), f"nucleus x={n.get('x')}"
        assert float(n.get("y")) in (16, 56), f"nucleus y={n.get('y')}"


def test_bounding_rect_scales_with_grid_size():
    # UUID → 6 hex tokens → 2x3 grid → grid_w=120, grid_h=120.
    # width  = 1 + 10 + 1 + 5 + 120 + 5 + 1 = 143
    # height = 1 + 5 + 120 + 5 + 1 = 132
    svg = _parse(render("550e8400-e29b-41d4-a716-446655440000"))
    assert float(svg.get("width")) == 143
    assert float(svg.get("height")) == 132
