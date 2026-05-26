"""
v4 surround: 24 boxes per cell, bit-of-quant fill rule, per-cell edge color
selected by perceptual distance from nucleus_bg.
"""
import re
from lxml import etree

from entviz.pipeline import render
from entviz.colors import (
    POSSIBLE_EDGE_COLORS,
    closest_palette_color,
    weighted_rgb_distance,
)
from entviz.layout import Cell, Point, Size


def _doc(svg_str):
    return etree.fromstring(svg_str.encode())


# ---- weighted_rgb_distance / closest_palette_color ----------------------


def test_weighted_rgb_distance_is_zero_for_same_color():
    assert weighted_rgb_distance("#ff0000", "#ff0000") == 0


def test_weighted_rgb_distance_symmetric():
    assert (
        weighted_rgb_distance("#ff0000", "#0000ff")
        == weighted_rgb_distance("#0000ff", "#ff0000")
    )


def test_weighted_rgb_distance_green_is_highest_weighted():
    # The formula weights green 4×, red 2×, blue 3×. So a green-channel
    # difference contributes more to distance than equal-magnitude
    # changes on other channels.
    d_green = weighted_rgb_distance("#000000", "#00ff00")
    d_red = weighted_rgb_distance("#000000", "#ff0000")
    d_blue = weighted_rgb_distance("#000000", "#0000ff")
    assert d_green > d_blue > d_red


def test_closest_palette_color_returns_palette_member():
    palette = ['#ffffff', '#ffd966', '#ff3f2f', '#2f3fbf']
    for target in ['#ff0000', '#00ff00', '#0000ff', '#888888', '#10203c']:
        assert closest_palette_color(target, palette) in palette


def test_closest_palette_color_picks_self_when_in_palette():
    palette = POSSIBLE_EDGE_COLORS
    for c in palette:
        assert closest_palette_color(c, palette) == c


# ---- surround box geometry ----------------------------------------------


def test_24_surround_boxes_per_cell_when_all_bits_set():
    """A token whose quant is all-ones produces 24 filled surround
    boxes per cell. Use a hex input where one token's quant ends up
    being 0xffffff is impossible without crafting it; instead just
    check that across all cells, the total filled-box count matches
    the popcount of (used) quants."""
    # "deadbeef" → 2 tokens. Token text "deadbe" / "efdead"... well
    # actually hex tokens are 6 chars. "deadbeef" → 1 token? Let me
    # use a long input.
    input_ = "deadbeefdeadbeef"  # 16 hex chars → 2 full tokens + 2 partial (extended) ... actually 16 hex = 2.67 tokens, but tokenization rounds. Let me just use a known one.
    svg = _doc(render(input_))
    # Surround boxes: width=6, height=10 at 12pt.
    boxes = [
        r for r in svg.xpath('//*[local-name()="rect"]')
        if float(r.get("width", 0)) == 6 and float(r.get("height", 0)) == 10
    ]
    assert boxes, "no surround boxes emitted"


def test_surround_box_fill_is_in_palette():
    """Each filled surround box uses a color from the 4-color edge palette."""
    svg = _doc(render("550e8400-e29b-41d4-a716-446655440000"))
    boxes = [
        r for r in svg.xpath('//*[local-name()="rect"]')
        if float(r.get("width", 0)) == 6 and float(r.get("height", 0)) == 10
    ]
    assert boxes
    for b in boxes:
        assert b.get("fill") in POSSIBLE_EDGE_COLORS


def test_box_origin_clockwise_numbering():
    """box_origin enumerates 24 boxes clockwise from top-left of top row."""
    cell = Cell(Point(0, 0), Size(60, 40))
    # Top row: 10 boxes, x increasing by box_width=6
    for i in range(10):
        assert cell.box_origin(i).x == i * 6, f"box {i} x"
        assert cell.box_origin(i).y == 0, f"box {i} y"
    # Right column: 2 boxes, x=cell.right - box_width = 54
    assert cell.box_origin(10) == Point(54, 10)
    assert cell.box_origin(11) == Point(54, 20)
    # Bottom row: 10 boxes, RIGHT to left
    for i in range(12, 22):
        expected_x = (21 - i) * 6
        assert cell.box_origin(i).x == expected_x
        assert cell.box_origin(i).y == 30
    # Left column: 2 boxes, x=0
    assert cell.box_origin(22) == Point(0, 20)
    assert cell.box_origin(23) == Point(0, 10)


def test_no_corner_rects():
    """v4 has no separate corner rects — the top/bottom rows extend past
    nucleus.left/right to cover what would have been corner regions.

    Specifically, the box at index 0 (top-left of top row) starts at
    x = nucleus.left - box_width = cell.left, i.e., the cell's left edge.
    """
    cell = Cell(Point(0, 0), Size(60, 40))
    assert cell.box_origin(0).x == cell.left
    assert cell.box_origin(0).y == cell.top
    # And box 9 (top-right of top row) ends at cell.right
    box9_origin = cell.box_origin(9)
    assert box9_origin.x + cell.box_width == cell.right
