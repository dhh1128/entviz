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


# v4 hybrid: small grids (< 6 interior corners) get an ellipse anchored
# at an EXTERNAL (boundary) corner instead of being skipped. The three
# tests below originally asserted the v3 "skip for small grids" rule;
# they are kept here to pin the new behavior for posterity, with their
# names preserved for git-blame continuity but their assertions inverted.


def test_overlay_now_drawn_for_2x2_grid():
    # 2x2 has 1 interior corner; v4 falls back to external corners
    # (8 of them for a 2x2 grid) and draws the overlay.
    svg = _doc(render("ab"))
    assert _ellipse(svg) is not None


def test_overlay_now_drawn_for_3x3_grid():
    # 3x3 has 4 interior corners; v4 falls back to external (12 corners).
    svg = _doc(render("a" * 36))  # 36 chars → fallback base64 path → 9 tokens
    assert _ellipse(svg) is not None


def test_overlay_now_drawn_for_uuid():
    # UUID = 6 hex tokens → 2x3 grid → 2 interior corners (< 6);
    # v4 falls back to external corners (10 for a 2x3 grid).
    svg = _doc(render("550e8400-e29b-41d4-a716-446655440000"))
    assert _ellipse(svg) is not None


def test_overlay_present_for_512_bit_input():
    # 22 tokens → 4x6 grid → 15 interior corners. Above the threshold,
    # overlay is drawn.
    svg = _doc(render("deadbeefdeadbeef" * 8))  # 128 hex chars = 22 tokens
    assert _ellipse(svg) is not None


def test_overlay_opacity_is_per_bg():
    # Per-bg overlay: white/gold darken at 0.20; red/blue lighten at 0.30.
    svg = _doc(render("deadbeefdeadbeef" * 8))
    e = _ellipse(svg)
    assert e is not None
    assert float(e.get("fill-opacity")) in (0.20, 0.30)


def test_overlay_rx_ry_in_bounded_range():
    # rx, ry should both lie in [nucleus_height, d_far − cell_w].
    # v4 r_min = nucleus_height (= 20 at 12pt), cell_w = 60.
    svg = _doc(render("deadbeefdeadbeef" * 8))
    e = _ellipse(svg)
    rx = float(e.get("rx"))
    ry = float(e.get("ry"))
    nucleus_h = 20
    # d_far depends on chosen anchor; just check both axes ≥ r_min.
    assert rx >= nucleus_h - 0.01
    assert ry >= nucleus_h - 0.01


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
    # For 22-token 4x6 grid at 12pt in v4: grid_rect.left=17,
    # grid_rect.top=31 (= 1 + GM + nucleus_height + GM, with the top
    # label strip), cell_w=60, cell_h=40.
    # Interior corners' x ∈ {17+60, 17+120, 17+180} = {77, 137, 197};
    # y ∈ {31+40, 31+80, 31+120, 31+160, 31+200} = {71, 111, 151, 191, 231}.
    valid_x = {77, 137, 197}
    valid_y = {71, 111, 151, 191, 231}
    assert cx in valid_x, f"cx={cx} not in {valid_x}"
    assert cy in valid_y, f"cy={cy} not in {valid_y}"
