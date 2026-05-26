"""Layout primitives — Rect, Cell. v4 geometry."""
from ..layout import *


def test_Rect():
    br = Rect(Point(10, 20), Size(30, 40))
    assert br.top_left == Point(10, 20)
    assert br.size == Size(30, 40)
    assert br.bottom_right == Point(40, 60)
    assert br.top_right == Point(40, 20)
    assert br.bottom_left == Point(10, 60)
    assert br.left == 10
    assert br.top == 20
    assert br.right == 40
    assert br.bottom == 60
    assert br.center == Point(25, 40)


def test_Cell_v4_dimensions():
    """v4 cell: 60 × 40 at 12pt. 3:2 aspect, NOT v3's 2:1."""
    cell = Cell(Point(0, 0), Size(60, 40))
    # box_width = cell_width/10 = 6; box_height = cell_height/4 = 10
    assert cell.box_width == 6
    assert cell.box_height == 10
    # nucleus = (box_width, box_height) offset, size (8·box_width, 2·box_height) = 48×20
    assert cell.nucleus == Rect(Point(6, 10), Size(48, 20))


def test_Cell_box_origin_top_row():
    """Top row boxes 0..9, left to right at y=nucleus.top - box_height."""
    cell = Cell(Point(0, 0), Size(60, 40))
    # Top row at y = 10 - 10 = 0
    for i in range(10):
        origin = cell.box_origin(i)
        # x = nucleus.left - box_width + i * box_width = 0 + i*6
        assert origin == Point(i * 6, 0), f"box {i} at {origin}"


def test_Cell_box_origin_right_column():
    """Right column: boxes 10 (top) and 11 (bottom) at x=nucleus.right."""
    cell = Cell(Point(0, 0), Size(60, 40))
    # x = nucleus.right = 6 + 48 = 54
    assert cell.box_origin(10) == Point(54, 10)
    assert cell.box_origin(11) == Point(54, 20)


def test_Cell_box_origin_bottom_row():
    """Bottom row: boxes 12..21, RIGHT to left (clockwise) at y=nucleus.bottom."""
    cell = Cell(Point(0, 0), Size(60, 40))
    # x positions mirror top row, but indexed right-to-left
    # i=12 → x position of top-row i=9; i=21 → x position of top-row i=0
    for i in range(12, 22):
        origin = cell.box_origin(i)
        expected_x = (21 - i) * 6
        assert origin == Point(expected_x, 30), f"box {i} at {origin}"


def test_Cell_box_origin_left_column():
    """Left column: boxes 22 (bottom) and 23 (top), bottom-to-top (clockwise)."""
    cell = Cell(Point(0, 0), Size(60, 40))
    # x = nucleus.left - box_width = 6 - 6 = 0
    assert cell.box_origin(22) == Point(0, 20)
    assert cell.box_origin(23) == Point(0, 10)


def test_Cell_aspect_ratio_assertion():
    """v4 cell aspect must be 3:2 (= cell_width * 2 == cell_height * 3)."""
    # Valid v4 ratios
    Cell(Point(0, 0), Size(60, 40))      # 12pt
    Cell(Point(0, 0), Size(120, 80))     # double
    Cell(Point(0, 0), Size(30, 20))      # half
    # Invalid (e.g. v3's 2:1)
    import pytest
    with pytest.raises(AssertionError):
        Cell(Point(0, 0), Size(64, 32))  # v3 dimensions
