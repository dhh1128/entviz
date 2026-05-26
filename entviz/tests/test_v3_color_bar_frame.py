"""
V3-2: color bar frame and width = edge_size.

  bounding_rect.width = 1 + edge_size + 1 + GM + grid_w + GM + 1
                          ↑          ↑     ↑                  ↑
                       left      interior  L margin       right
                       border    separator                border

  bounding_rect.height unchanged from v2.

The color bar lives in the inset rect at x=1, width=edge_size, with
drawing region y in [1, bounding_h - 1] (top/bottom 1-px black borders
cover the outermost pixel rows). The grid_rect shifts to (1 + edge_size
+ 1 + GM, 1 + GM).

Four black border lines (all four sides) plus one interior separator
between the color bar and the grid margin.
"""
from lxml import etree

from entviz.pipeline import render


def _doc(svg_str):
    return etree.fromstring(svg_str.encode())


# Nominal 12pt/96 DPI constants used in the assertions below.
NUCLEUS_H = 16
CELL_W, CELL_H = 64, 32
EDGE_SIZE = 8
GM = 4
SCS_H = NUCLEUS_H


def _bounding_w_for(grid_w):
    return 1 + EDGE_SIZE + 1 + GM + grid_w + GM + 1


def _bounding_h_for(grid_h):
    return 1 + GM + grid_h + GM + SCS_H + GM + 1


def test_canvas_size_matches_v3_bounding_rect_formula():
    # "deadbeef" produces a 2x2 grid → grid_w = 128, grid_h = 64.
    # bounding_w = 1 + 8 + 1 + 4 + 128 + 4 + 1 = 147
    # bounding_h = 1 + 4 + 64 + 4 + 16 + 4 + 1 = 94  (unchanged)
    svg = _doc(render("deadbeef"))
    assert float(svg.get("width")) == _bounding_w_for(128) == 147
    assert float(svg.get("height")) == _bounding_h_for(64) == 94


def test_uuid_canvas_size_matches_v3_formula():
    # UUID → 6 tokens (hex tokenization post-alphabet refactor) →
    # 2x3 grid → grid_w=128, grid_h=96.
    # bounding_w = 147; bounding_h = 1 + 4 + 96 + 4 + 16 + 4 + 1 = 126
    svg = _doc(render("550e8400-e29b-41d4-a716-446655440000"))
    assert float(svg.get("width")) == 147
    assert float(svg.get("height")) == 126


def test_black_border_on_all_four_sides():
    svg = _doc(render("deadbeef"))
    bw = float(svg.get("width"))
    bh = float(svg.get("height"))
    lines = svg.xpath('//*[local-name()="line"]')
    blacks = [l for l in lines if l.get("stroke") == "#000000"]
    # 4 outer borders + 1 interior separator = 5 black lines.
    assert len(blacks) >= 5

    # Find each border by its endpoints.
    def has_line(x1, y1, x2, y2):
        return any(
            float(l.get("x1")) == x1 and float(l.get("y1")) == y1
            and float(l.get("x2")) == x2 and float(l.get("y2")) == y2
            for l in blacks
        )

    assert has_line(0, 0, bw - 1, 0),               "missing top border"
    assert has_line(bw - 1, 0, bw - 1, bh - 1),     "missing right border"
    assert has_line(0, bh - 1, bw - 1, bh - 1),     "missing bottom border"
    assert has_line(0, 0, 0, bh - 1),               "missing left border"


def test_interior_separator_between_color_bar_and_grid_margin():
    # The interior separator runs vertically at x = 1 + edge_size = 9,
    # from y=0 to y=bounding_h-1.
    svg = _doc(render("deadbeef"))
    bh = float(svg.get("height"))
    lines = svg.xpath('//*[local-name()="line"]')
    separator = [
        l for l in lines
        if l.get("stroke") == "#000000"
        and float(l.get("x1")) == float(l.get("x2")) == 1 + EDGE_SIZE
    ]
    assert len(separator) == 1
    s = separator[0]
    assert float(s.get("y1")) == 0
    assert float(s.get("y2")) == bh - 1


def test_color_bar_bands_at_x_1_width_edge_size():
    svg = _doc(render("550e8400-e29b-41d4-a716-446655440000"))
    bands = [
        r for r in svg.xpath('//*[local-name()="rect"]')
        if float(r.get("x", -1)) == 1 and float(r.get("width", -1)) == EDGE_SIZE
    ]
    assert len(bands) >= 1


def test_color_bar_drawing_region_avoids_borders():
    # The color bar drawing region is y in [1, bounding_h - 1]. Bands
    # should sum to bounding_h - 2 (the 2 pixels covered by top/bottom
    # borders are not part of the color bar's drawing area).
    svg = _doc(render("550e8400-e29b-41d4-a716-446655440000"))
    bands = [
        r for r in svg.xpath('//*[local-name()="rect"]')
        if float(r.get("x", -1)) == 1 and float(r.get("width", -1)) == EDGE_SIZE
    ]
    total_h = sum(float(b.get("height")) for b in bands)
    bh = float(svg.get("height"))
    assert abs(total_h - (bh - 2)) < 0.01
    # And the topmost band should start at y=1 (just below the top border).
    sorted_bands = sorted(bands, key=lambda b: float(b.get("y")))
    assert float(sorted_bands[0].get("y")) == 1


def test_grid_rect_offset_is_1_plus_edge_size_plus_1_plus_gm():
    # grid_rect.left = 1 + edge_size + 1 + GM = 14
    # The first cell's nucleus is therefore at x = grid_rect.left
    # + edge_size = 14 + 8 = 22 (for the leftmost-column cells).
    svg = _doc(render("deadbeef"))
    nuclei = [
        r for r in svg.xpath('//*[local-name()="rect"]')
        if float(r.get("width", 0)) == 48 and float(r.get("height", 0)) == 16
    ]
    assert nuclei
    # 2x2 grid, second-column cell at x = 14 + cell_w + edge_size = 86.
    valid_xs = {22, 14 + CELL_W + EDGE_SIZE}
    for n in nuclei:
        assert float(n.get("x")) in valid_xs, f"nucleus x={n.get('x')} not in {valid_xs}"
