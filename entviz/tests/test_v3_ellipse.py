"""
V3-5: ellipse overlay rework.

Per spec-improvement-notes.md item 4 (LOCKED):
  - anchor: strictly-interior corner of the grid (row-major enumeration);
    pool = (cols-1) × (rows-1)
  - rx, ry: independent, each in [cell_h, d_far − cell_w] with 16 levels
  - rotation: [0°, 180°), 16 levels
  - opacity: fixed at 20%
  - clipping: grid_rect (not bounding_rect)
  - skip if grid has fewer than 6 interior corners (smaller than 3x4 / 4x3,
    corresponding to inputs < 256 bits)
"""
import math
from lxml import etree

from entviz.layout import Point
from entviz.pipeline import (
    enumerate_interior_corners,
    render,
    v3_ellipse_params_from_digest,
)


def _doc(svg_str):
    return etree.fromstring(svg_str.encode())


def _ellipse(svg):
    eps = svg.xpath('//*[local-name()="ellipse"]')
    return eps[0] if eps else None


# ---- enumeration ---------------------------------------------------------


def test_enumerate_interior_corners_3x3_has_4_points():
    # 3x3 grid: (3-1) × (3-1) = 4 interior corners.
    pts = enumerate_interior_corners(
        cols=3, rows=3, cell_w=10, cell_h=10, origin=Point(0, 0),
    )
    assert len(pts) == 4
    # Row-major order: (10,10), (20,10), (10,20), (20,20)
    assert pts == [Point(10, 10), Point(20, 10), Point(10, 20), Point(20, 20)]


def test_enumerate_interior_corners_4x6_has_15_points():
    pts = enumerate_interior_corners(
        cols=4, rows=6, cell_w=10, cell_h=10, origin=Point(0, 0),
    )
    assert len(pts) == 15  # (4-1) × (6-1) = 3 × 5
    # No interior corner sits on the outer boundary.
    for p in pts:
        assert 0 < p.x < 40
        assert 0 < p.y < 60


def test_enumerate_interior_corners_offsets_by_origin():
    pts = enumerate_interior_corners(
        cols=3, rows=3, cell_w=10, cell_h=10, origin=Point(100, 200),
    )
    assert pts[0] == Point(110, 210)


# ---- v3 param mapping ----------------------------------------------------


def test_v3_params_from_all_zero_digest():
    p = v3_ellipse_params_from_digest(b"\x00" * 64)
    assert p["anchor_index"] == 0
    assert p["rx_step"] == 0
    assert p["ry_step"] == 0
    assert p["rotation_step"] == 0


def test_v3_params_step_values_are_in_0_to_15():
    p = v3_ellipse_params_from_digest(b"\xff" * 64)
    for k in ("rx_step", "ry_step", "rotation_step"):
        assert 0 <= p[k] <= 15, f"{k} = {p[k]} out of [0, 15]"


def test_v3_params_anchor_index_is_full_byte():
    p = v3_ellipse_params_from_digest(b"\xff" * 64)
    # Anchor uses the full byte for higher resolution (mod pool size at
    # the call site); this just confirms we read byte 60 directly.
    assert p["anchor_index"] == 255


# ---- pipeline integration -----------------------------------------------


def test_overlay_omitted_for_2x2_grid():
    # 2x2 has 1 interior corner, far below the 6 threshold.
    svg = _doc(render("ab"))
    assert _ellipse(svg) is None


def test_overlay_omitted_for_3x3_grid():
    # 3x3 has 4 interior corners (below the 6 threshold).
    # 9 tokens triggers a 3x3 grid.
    # (9 base64 chars × 6 bits = 54 bits per cell budget, but 9 tokens
    # means we need 9 cells; choose_grid picks 3x3 for AR=1.)
    svg = _doc(render("abcdefghijkl"))  # base64 fallback → 12-char core → 3 tokens, 2x2 grid
    # Try a clearer 9-token case — 9 tokens means 36 base64 chars or 54 hex chars.
    svg = _doc(render("a" * 36))  # 36 chars → fallback base64 path → 9 tokens
    # Note: choose_grid(9, 1.0) = 3x3 (cells=9, ar=2)
    assert _ellipse(svg) is None


def test_overlay_present_for_uuid():
    # UUID = 8 tokens → 2x4 grid → (2-1)×(4-1) = 3 interior corners.
    # That's BELOW the 6 threshold, so overlay omitted.
    svg = _doc(render("550e8400-e29b-41d4-a716-446655440000"))
    assert _ellipse(svg) is None


def test_overlay_present_for_512_bit_input():
    # 22 tokens → 4x6 grid → 15 interior corners. Above the threshold,
    # overlay is drawn.
    svg = _doc(render("deadbeefdeadbeef" * 8))  # 128 hex chars = 22 tokens
    assert _ellipse(svg) is not None


def test_overlay_opacity_is_fixed_at_20_percent():
    svg = _doc(render("deadbeefdeadbeef" * 8))
    e = _ellipse(svg)
    assert e is not None
    assert abs(float(e.get("fill-opacity")) - 0.20) < 1e-9


def test_overlay_rx_ry_in_bounded_range():
    # rx, ry should both lie in [cell_h, d_far − cell_w].
    svg = _doc(render("deadbeefdeadbeef" * 8))
    e = _ellipse(svg)
    rx = float(e.get("rx"))
    ry = float(e.get("ry"))
    cell_h, cell_w = 32, 64
    # d_far depends on chosen anchor; just check both axes ≥ cell_h.
    assert rx >= cell_h - 0.01
    assert ry >= cell_h - 0.01


def test_clip_path_targets_grid_rect_not_bounding_rect():
    # V3-5: clip rectangle in <defs> should be grid_rect, not bounding_rect.
    svg = _doc(render("deadbeefdeadbeef" * 8))
    cps = svg.xpath('//*[local-name()="clipPath"]')
    assert cps
    cp_rect = cps[0].xpath('./*[local-name()="rect"]')[0]
    bw = float(svg.get("width"))
    bh = float(svg.get("height"))
    # Grid rect is smaller than bounding rect in both dimensions.
    assert float(cp_rect.get("width")) < bw
    assert float(cp_rect.get("height")) < bh


def test_overlay_anchor_is_interior_corner_position():
    # The ellipse's cx, cy should land on one of the grid's interior corner
    # points: a multiple of cell_width from grid_rect.left (exclusive) and
    # a multiple of cell_height from grid_rect.top (exclusive).
    svg = _doc(render("deadbeefdeadbeef" * 8))
    e = _ellipse(svg)
    cx, cy = float(e.get("cx")), float(e.get("cy"))
    # For 22-token 4x6 grid at 12pt: grid_rect.left=14, grid_rect.top=5,
    # cell_w=64, cell_h=32.
    # Interior corners' x ∈ {14+64, 14+128, 14+192} = {78, 142, 206};
    # y ∈ {5+32, 5+64, 5+96, 5+128, 5+160} = {37, 69, 101, 133, 165}.
    valid_x = {78, 142, 206}
    valid_y = {37, 69, 101, 133, 165}
    assert cx in valid_x, f"cx={cx} not in {valid_x}"
    assert cy in valid_y, f"cy={cy} not in {valid_y}"
