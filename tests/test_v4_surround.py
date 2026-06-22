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
    palette = ['#ffffff', '#e7be00', '#ff3f2f', '#2f3fbf']
    for target in ['#ff0000', '#00ff00', '#0000ff', '#888888', '#10203c']:
        assert closest_palette_color(target, palette) in palette


def test_closest_palette_color_picks_self_when_in_palette():
    palette = POSSIBLE_EDGE_COLORS
    for c in palette:
        assert closest_palette_color(c, palette) == c


# ---- surround box geometry ----------------------------------------------


def _surround_paths(svg):
    """v10: the surround boxes are emitted as one <path> per cell in the
    surround layer (the only <path> with no data-blank-map-* attribute — the
    blank-map plus marker is the other path)."""
    return [
        p for p in svg.xpath('//*[local-name()="path"]')
        if p.get("data-blank-map-max") is None and p.get("data-blank-map-min") is None
    ]


def test_surround_path_subpath_count_matches_declared_bits():
    """v10: each filled cell DECLARES its surround pattern as
    data-surround-bits (hex), and the surround path draws exactly one box
    (one 'M' subpath) per set bit. The two must round-trip."""
    svg = _doc(render("deadbeefdeadbeef"))
    cells = svg.xpath('//*[local-name()="g"][@data-channel="cell"]')
    total_bits = sum(
        bin(int(g.get("data-surround-bits"), 16)).count("1")
        for g in cells if g.get("data-surround-bits") is not None
    )
    total_subpaths = sum(p.get("d", "").count("M") for p in _surround_paths(svg))
    assert total_bits > 0, "no surround bits set"
    assert total_subpaths == total_bits


def test_surround_path_fill_is_in_palette():
    """Each surround path uses a color from the 4-color edge palette."""
    svg = _doc(render("550e8400-e29b-41d4-a716-446655440000"))
    paths = _surround_paths(svg)
    assert paths, "no surround paths emitted"
    for p in paths:
        assert p.get("fill") in POSSIBLE_EDGE_COLORS


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
