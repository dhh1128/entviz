"""
v4 hybrid ellipse anchoring: grids with fewer than 6 interior corners
(smaller than 3x4 / 4x3) use *external* (boundary) cell corners as
anchors instead of being skipped entirely. The math works because
external anchors have a much larger d_far (distance to the farthest
grid_rect corner), so r_max = d_far − cell_width stays comfortably
above r_min = nucleus_height even at 2x2.

Visually, this produces a quarter-ellipse-in-a-corner or half-ellipse-
along-an-edge silhouette instead of the centered curve of large grids.
"""
from lxml import etree

from entviz.pipeline import render, enumerate_external_corners
from entviz.layout import Point


def _doc(svg_str):
    return etree.fromstring(svg_str.encode())


def _ellipse(svg):
    eps = svg.xpath('//*[local-name()="ellipse"]')
    return eps[0] if eps else None


# ---- external-corner enumeration ----------------------------------------


def test_external_corners_2x2_has_8_points():
    """2x2 grid: 4 grid_rect vertices + 4 edge midpoints = 8 external corners."""
    pts = enumerate_external_corners(
        cols=2, rows=2, cell_w=10, cell_h=10, origin=Point(0, 0),
    )
    assert len(pts) == 8


def test_external_corners_3x3_has_12_points():
    """3x3 grid: 2·3 + 2·3 = 12 external corners (4 vertices + 8 edge midpoints)."""
    pts = enumerate_external_corners(
        cols=3, rows=3, cell_w=10, cell_h=10, origin=Point(0, 0),
    )
    assert len(pts) == 12


def test_external_corners_2x3_has_10_points():
    """For 2x3 (UUID grid): 2·2 + 2·3 = 10 external corners."""
    pts = enumerate_external_corners(
        cols=2, rows=3, cell_w=10, cell_h=10, origin=Point(0, 0),
    )
    assert len(pts) == 10


def test_external_corners_row_major_2x2():
    """Enumeration order: top edge left→right, then interior rows
    (left and right), then bottom edge left→right."""
    pts = enumerate_external_corners(
        cols=2, rows=2, cell_w=10, cell_h=10, origin=Point(0, 0),
    )
    expected = [
        Point(0, 0), Point(10, 0), Point(20, 0),     # top edge: 3 points
        Point(0, 10), Point(20, 10),                  # row 1 boundary
        Point(0, 20), Point(10, 20), Point(20, 20),  # bottom edge: 3 points
    ]
    assert pts == expected


def test_external_corners_offsets_by_origin():
    pts = enumerate_external_corners(
        cols=2, rows=2, cell_w=10, cell_h=10, origin=Point(100, 200),
    )
    assert pts[0] == Point(100, 200)
    assert pts[-1] == Point(120, 220)


def test_external_corners_lie_on_grid_boundary():
    """No external corner is strictly inside the grid_rect."""
    cols, rows, cw, ch = 4, 5, 10, 10
    pts = enumerate_external_corners(cols, rows, cw, ch, Point(0, 0))
    for p in pts:
        on_x_boundary = p.x in (0, cols * cw)
        on_y_boundary = p.y in (0, rows * ch)
        assert on_x_boundary or on_y_boundary, f"{p} is interior, not boundary"


# ---- hybrid pipeline behavior -------------------------------------------


def test_2x2_input_now_has_ellipse():
    """Smallest possible grid (2x2 from 1 token) now gets an ellipse via
    external corner. Previously skipped because <6 interior corners."""
    svg = _doc(render("ab"))  # 2 hex chars = 1 token → 2x2 grid
    assert _ellipse(svg) is not None


def test_uuid_now_has_ellipse():
    """UUID → 6 tokens → 2x3 grid → only 2 interior corners.
    Now gets an ellipse via external corner."""
    svg = _doc(render("550e8400-e29b-41d4-a716-446655440000"))
    assert _ellipse(svg) is not None


def test_3x3_input_now_has_ellipse():
    """3x3 grid (4 interior corners) now gets an ellipse via external."""
    svg = _doc(render("a" * 36))  # base64 fallback → 9 tokens → 3x3 grid
    assert _ellipse(svg) is not None


def test_small_grid_ellipse_anchor_is_on_boundary():
    """The chosen anchor for a small grid must sit on the grid_rect boundary."""
    svg = _doc(render("ab"))
    e = _ellipse(svg)
    cx, cy = float(e.get("cx")), float(e.get("cy"))
    # grid_rect for 2x2 at 12pt (v6): top-left (28, 27) after the MARGIN
    # quiet ring (issue #31), size 120 × 80.
    # External boundary: cx in {28, 148} OR cy in {27, 107}.
    boundary = (cx in (28.0, 148.0)) or (cy in (27.0, 107.0))
    assert boundary, f"anchor ({cx}, {cy}) is not on grid_rect boundary"


def test_large_grid_ellipse_anchor_is_interior():
    """≥6 interior corners → anchor is an interior corner (not on boundary).
    This confirms the hybrid still picks interior for big grids."""
    svg = _doc(render("deadbeef" * 16))  # 22 hex tokens → 4x6 grid → 15 interior
    e = _ellipse(svg)
    cx, cy = float(e.get("cx")), float(e.get("cy"))
    # grid_rect for 4x6 at 12pt: top-left (17, 6), size 240 × 240.
    # Interior anchor: cx strictly between 17 and 257, cy between 6 and 246.
    interior_x = 17 < cx < 257
    interior_y = 6 < cy < 246
    assert interior_x and interior_y, f"large-grid anchor ({cx}, {cy}) on boundary"
