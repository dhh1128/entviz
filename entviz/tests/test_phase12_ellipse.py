"""
Phase 12 acceptance tests: the ellipse overlay derived from digest
bytes 60-63 and the SVG clipPath that confines it (and anything else
that exceeds the bounding rect) to the entviz outline.

Per docs/index2.md:
- anchor: enumerate perimeter cells in cell-index order; for each, visit
  corners TL, TR, BL, BR; emit each unique point the first time it is
  seen. Selection = digest[60] mod (point count).
- axis ratio: digest[61] → 1:1 .. 1:2.5
- rotation: digest[62] → 0° .. 180°
- opacity: digest[63] → 10% .. 30%
- Fill: convert entviz bg to HLS; if L > 0.5 fill black, else white.
- Smaller semi-axis ≥ half the diagonal of bounding rect (so the ellipse
  always extends beyond the bounding rect and clips to an arc).
- Drawn above edges, below nuclei.
"""
import math

from lxml import etree

from entviz.pipeline import (
    enumerate_perimeter_points,
    ellipse_params_from_digest,
    render,
)
from entviz.fingerprint import compute_fingerprint
from entviz.layout import Point


def _doc(svg_str):
    return etree.fromstring(svg_str.encode())


def _ellipse(svg):
    eps = svg.xpath('//*[local-name()="ellipse"]')
    return eps[0] if eps else None


def test_ellipse_present_in_output():
    svg = _doc(render("550e8400-e29b-41d4-a716-446655440000"))
    assert _ellipse(svg) is not None, "no ellipse element rendered"


def test_ellipse_opacity_in_range():
    svg = _doc(render("550e8400-e29b-41d4-a716-446655440000"))
    e = _ellipse(svg)
    op = float(e.get("fill-opacity"))
    assert 0.10 <= op <= 0.30


def test_ellipse_fill_is_black_or_white():
    svg = _doc(render("550e8400-e29b-41d4-a716-446655440000"))
    e = _ellipse(svg)
    assert e.get("fill") in ("#000000", "#ffffff")


def test_ellipse_smaller_semi_axis_at_least_half_diagonal():
    svg = _doc(render("550e8400-e29b-41d4-a716-446655440000"))
    e = _ellipse(svg)
    rx, ry = float(e.get("rx")), float(e.get("ry"))
    bw, bh = float(svg.get("width")), float(svg.get("height"))
    half_diag = math.hypot(bw, bh) / 2
    assert min(rx, ry) >= half_diag - 0.01


def test_clip_path_defined():
    svg = _doc(render("550e8400-e29b-41d4-a716-446655440000"))
    cps = svg.xpath('//*[local-name()="clipPath"]')
    assert len(cps) == 1
    rect = cps[0].xpath('./*[local-name()="rect"]')[0]
    assert float(rect.get("width")) == float(svg.get("width"))
    assert float(rect.get("height")) == float(svg.get("height"))


def test_ellipse_uses_clip_path():
    svg = _doc(render("550e8400-e29b-41d4-a716-446655440000"))
    e = _ellipse(svg)
    cp = e.get("clip-path") or ""
    assert cp.startswith("url(#")


def test_ellipse_between_edges_and_nuclei_in_doc_order():
    svg = _doc(render("550e8400-e29b-41d4-a716-446655440000"))
    elements = svg.xpath('//*')
    e_idx = next(
        i for i, el in enumerate(elements) if el.tag.endswith("}ellipse")
    )
    # Find first nucleus rect (48x16); ellipse must be before it.
    first_nucleus_idx = next(
        i for i, el in enumerate(elements)
        if el.tag.endswith("}rect")
        and float(el.get("width", 0)) == 48 and float(el.get("height", 0)) == 16
    )
    # Find last edge element before the nuclei layer; ellipse must be after.
    last_edge_idx = max(
        i for i, el in enumerate(elements)
        if i < first_nucleus_idx and el.tag.endswith(("}polygon", "}rect"))
        and not (el.tag.endswith("}rect") and float(el.get("width", 0)) == 48
                 and float(el.get("height", 0)) == 16)
    )
    assert last_edge_idx < e_idx < first_nucleus_idx


def test_enumerate_perimeter_points_2x2():
    # 2x2 grid, all cells perimeter. Corners are (0,0),(1,0),(0,1),(1,1)
    # cell-major: cell 0 (0,0) corners → (0,0),(1,0),(0,1),(1,1)
    #             cell 1 (1,0) corners → (1,0)*dup,(2,0),(1,1)*dup,(2,1)
    #             cell 2 (0,1) corners → (0,1)*dup,(1,1)*dup,(0,2),(1,2)
    #             cell 3 (1,1) corners → (1,1)*dup,(2,1)*dup,(1,2)*dup,(2,2)
    # Unique points (in first-seen order):
    #   (0,0),(1,0),(0,1),(1,1),(2,0),(2,1),(0,2),(1,2),(2,2) = 9
    points = enumerate_perimeter_points(
        cols=2, rows=2, cell_w=1, cell_h=1, origin=Point(0, 0),
    )
    assert len(points) == 9
    assert points[0] == Point(0, 0)
    assert points[1] == Point(1, 0)
    assert points[2] == Point(0, 1)
    assert points[3] == Point(1, 1)
    assert points[4] == Point(2, 0)


def test_ellipse_params_from_known_digest():
    # All-zero digest: anchor index 0, axis_ratio 1.0, rotation 0°,
    # opacity 0.10.
    digest = b"\x00" * 64
    p = ellipse_params_from_digest(digest)
    assert p["anchor_index"] == 0
    assert abs(p["axis_ratio"] - 1.0) < 1e-9
    assert abs(p["rotation_deg"] - 0.0) < 1e-9
    assert abs(p["opacity"] - 0.10) < 1e-9


def test_ellipse_params_from_all_ff_digest():
    digest = b"\xff" * 64
    p = ellipse_params_from_digest(digest)
    # anchor_index = 255 mod whatever; can't check without point count.
    assert p["anchor_index"] == 255
    assert abs(p["axis_ratio"] - 2.5) < 0.01
    assert abs(p["rotation_deg"] - 180.0) < 0.01
    assert abs(p["opacity"] - 0.30) < 0.01
