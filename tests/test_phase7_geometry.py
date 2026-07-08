"""
Geometry acceptance tests — v4 bounding rect, grid margin (GM), positioning
of grid_rect, white fill, and four-sided gray borders + interior separator.

At 12pt / 96 DPI in v4:
  font_size_px = 16
  nucleus_width = 48, nucleus_height = 20
  box_width = 6, box_height = 10
  cell_width = 60, cell_height = 40
  GM = 5

Bounding rect height includes the always-present top label strip
(nucleus_height + GM = 25 px) and, when the parsed result has a suffix,
a matching bottom label strip:

  height = 1 + GM + nucleus_height + GM + grid_h
             + [GM + nucleus_height +] GM + 1
"""
from lxml import etree

from entviz.pipeline import render


def _parse(svg_str):
    return etree.fromstring(svg_str.encode())


def test_canvas_size_matches_bounding_rect_formula():
    # "deadbeef" → hex (no prefix, no suffix), 2 tokens → 2x2 grid
    # → grid_w=120, grid_h=80. Top label only (no suffix → no bottom).
    # inner_w  = 1 + 20 + 1 + 5 + 120 + 5 + 1 = 153
    # inner_h  = 1 + 5 + 20 + 80 + 5 + 1 = 112
    # bounding = inner + 2·MARGIN (MARGIN=1) → 155 x 114 (issue #31).
    svg = _parse(render("deadbeef"))
    assert float(svg.get("width")) == 155
    assert float(svg.get("height")) == 114


def test_first_rect_is_white_field_inside_margin():
    # The white fill is now the field rect, inset by MARGIN=1 so the outer
    # quiet ring stays transparent (issue #31): x=y=1, size = inner_w x inner_h.
    svg = _parse(render("deadbeef"))
    rects = svg.xpath('//*[local-name()="rect"][not(ancestor::*[local-name()="defs"])]')
    first = rects[0]
    assert first.get("fill") == "#ffffff"
    assert float(first.get("x")) == 1
    assert float(first.get("y")) == 1
    assert float(first.get("width")) == 153
    assert float(first.get("height")) == 112


def test_gray_borders_present():
    # v4: borders on all 4 sides + interior separator → 5 gray lines.
    svg = _parse(render("deadbeef"))
    lines = svg.xpath('//*[local-name()="line"]')
    grays = [l for l in lines if l.get("stroke") == "#808080"]
    assert len(grays) >= 5, f"expected ≥5 gray border lines, got {len(grays)}"


def test_grid_rect_offset_inside_bounding():
    # v6 grid_rect sits at (MARGIN + 1 + bar_width + 1 + GM,
    #                       MARGIN + 1 + GM + nucleus_height)  ← band abuts grid
    # = (28, 27) with MARGIN=1 (issue #31). In a 2x2 grid, nuclei land at:
    #   x ∈ {28 + 6, 28 + 6 + 60} = {34, 94}
    #   y ∈ {27 + 10, 27 + 10 + 40} = {37, 77}
    svg = _parse(render("deadbeef"))
    nuclei = [
        r for r in svg.xpath('//*[local-name()="rect"]')
        if float(r.get("width", 0)) == 48 and float(r.get("height", 0)) == 20
    ]
    assert nuclei, "no nucleus rect found"
    for n in nuclei:
        assert float(n.get("x")) in (34, 94), f"nucleus x={n.get('x')}"
        assert float(n.get("y")) in (37, 77), f"nucleus y={n.get('y')}"


def test_bounding_rect_scales_with_grid_size():
    # UUID → 6 hex tokens → 2x3 grid → grid_w=120, grid_h=120.
    # No suffix → top label only.
    # inner_w  = 1 + 20 + 1 + 5 + 120 + 5 + 1 = 153
    # inner_h  = 1 + 5 + 20 + 120 + 5 + 1 = 152
    # bounding = inner + 2·MARGIN → 155 x 154 (issue #31).
    svg = _parse(render("550e8400-e29b-41d4-a716-446655440000"))
    assert float(svg.get("width")) == 155
    assert float(svg.get("height")) == 154
