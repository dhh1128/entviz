"""
Phase 12 acceptance tests: the ellipse overlay and its clipPath.

These tests originally covered v2 rules; v3 reworked the overlay
(see test_v3_ellipse.py and spec-improvement-notes.md item 4). The
remaining checks here are the v3-compatible subset: opacity is fixed
at 20%, fill is black or white per the HLS rule, clipPath is defined,
overlay sits in the correct layer.

All tests now use a >256-bit input so the v3 skip rule doesn't suppress
the overlay.
"""
import math

from lxml import etree

from entviz.pipeline import (
    enumerate_interior_corners,
    v3_ellipse_params_from_digest,
    render,
)
from entviz.fingerprint import compute_fingerprint
from entviz.layout import Point


# 22 hex tokens → 4x6 grid → 15 interior corners; well past the v3 threshold.
LARGE_INPUT = "deadbeefdeadbeef" * 8


def _doc(svg_str):
    return etree.fromstring(svg_str.encode())


def _ellipse(svg):
    eps = svg.xpath('//*[local-name()="ellipse"]')
    return eps[0] if eps else None


def test_ellipse_present_in_output():
    svg = _doc(render(LARGE_INPUT))
    assert _ellipse(svg) is not None, "no ellipse element rendered"


def test_ellipse_opacity_is_per_bg():
    # Overlay opacity is per-bg: 0.20 on white/gold (darken), 0.30 on
    # red/blue (lighten). Whatever bg this input lands on, the opacity
    # must be one of those two values.
    svg = _doc(render(LARGE_INPUT))
    e = _ellipse(svg)
    assert float(e.get("fill-opacity")) in (0.20, 0.30)


def test_ellipse_fill_is_black_or_white():
    svg = _doc(render(LARGE_INPUT))
    e = _ellipse(svg)
    assert e.get("fill") in ("#000000", "#ffffff")


def test_clip_path_defined():
    # v4: clipPath id is salted with the first 8 hex chars of the fingerprint
    # and the grid dimensions (e.g. "grid-clip-deadbeef-4x6") to prevent
    # multi-SVG document id collisions.
    svg = _doc(render(LARGE_INPUT))
    cps = svg.xpath('//*[local-name()="clipPath"]')
    grid_clips = [cp for cp in cps if (cp.get("id") or "").startswith("grid-clip-")]
    assert len(grid_clips) == 1, f"expected one grid-clip-*, got {len(grid_clips)}"
    rect = grid_clips[0].xpath('./*[local-name()="rect"]')[0]
    assert float(rect.get("width")) < float(svg.get("width"))
    assert float(rect.get("height")) < float(svg.get("height"))


def test_ellipse_uses_clip_path():
    # clip-path lives on the parent <g> (see test_ellipse_clip_fix.py).
    svg = _doc(render(LARGE_INPUT))
    e = _ellipse(svg)
    parent = e.getparent()
    cp = parent.get("clip-path") or ""
    assert cp.startswith("url(#")


def test_ellipse_between_edges_and_nuclei_in_doc_order():
    svg = _doc(render(LARGE_INPUT))
    elements = svg.xpath('//*')
    e_idx = next(
        i for i, el in enumerate(elements) if el.tag.endswith("}ellipse")
    )
    # v4 nucleus rect: 48 × 20.
    first_nucleus_idx = next(
        i for i, el in enumerate(elements)
        if el.tag.endswith("}rect")
        and float(el.get("width", 0)) == 48 and float(el.get("height", 0)) == 20
        and el.get("rx") is None
    )
    last_edge_idx = max(
        i for i, el in enumerate(elements)
        if i < first_nucleus_idx and el.tag.endswith("}rect")
        and not (float(el.get("width", 0)) == 48 and float(el.get("height", 0)) == 20)
        and el.get("rx") is None
    )
    assert last_edge_idx < e_idx < first_nucleus_idx


# ---- V3-5 helper-function regression coverage ----------------------------


def test_enumerate_interior_corners_3x3():
    pts = enumerate_interior_corners(
        cols=3, rows=3, cell_w=1, cell_h=1, origin=Point(0, 0),
    )
    assert pts == [Point(1, 1), Point(2, 1), Point(1, 2), Point(2, 2)]


def test_v3_params_from_known_digest():
    digest = b"\x00" * 64
    p = v3_ellipse_params_from_digest(digest)
    assert p["anchor_index"] == 0
    assert p["rx_step"] == 0
    assert p["ry_step"] == 0
    assert p["rotation_step"] == 0


def test_v3_params_from_all_ff_digest():
    digest = b"\xff" * 64
    p = v3_ellipse_params_from_digest(digest)
    assert p["anchor_index"] == 255
    # 255 mod 16 = 15 (max step value)
    assert p["rx_step"] == 15
    assert p["ry_step"] == 15
    assert p["rotation_step"] == 15
