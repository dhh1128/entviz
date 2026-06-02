"""
Regression test for the ellipse overlay's minimum radius.

spec.md line 274 specifies the ellipse semi-axes as
    rx = r_min + (rx_step / 15) * (r_max - r_min)
    ry = r_min + (ry_step / 15) * (r_max - r_min)
with **r_min = nucleus_height** (= cell_height / 2) and
r_max = d_far - cell_width.

An earlier implementation used r_min = cell_height (twice the spec value),
which both inflated every overlay and, via the r_max <= r_min guard, could
suppress the overlay entirely on smaller grids. These tests pin r_min to
nucleus_height by recomputing the expected radii purely from the rendered
SVG (grid geometry from the clipPath rect, anchor + radii from the ellipse
group's data-* attributes) and the digest-derived step values.
"""
import math

from lxml import etree

from entviz.entropy import parse
from entviz.fingerprint import compute_fingerprint
from entviz.pipeline import render, v3_ellipse_params_from_digest


# 64-byte hex input -> 22 tokens -> 4x6 grid (interior-anchored overlay).
LARGE_INPUT = "deadbeefdeadbeef" * 8


def _doc(svg_str):
    return etree.fromstring(svg_str.encode())


def _grid_rect_from_clip(svg):
    rect = svg.xpath('//*[local-name()="clipPath"]/*[local-name()="rect"]')[0]
    return (
        float(rect.get("x")),
        float(rect.get("y")),
        float(rect.get("width")),
        float(rect.get("height")),
    )


def _ellipse_group(svg):
    return svg.xpath('//*[local-name()="g"][@data-channel="ellipse"]')[0]


def test_ellipse_rmin_is_nucleus_height():
    svg_str = render(LARGE_INPUT)
    svg = _doc(svg_str)

    cols = int(svg.get("data-cols"))
    rows = int(svg.get("data-rows"))
    gx, gy, gw, gh = _grid_rect_from_clip(svg)
    cell_w = gw / cols
    cell_h = gh / rows

    g = _ellipse_group(svg)
    anchor_x = float(g.get("data-ellipse-anchor-x"))
    anchor_y = float(g.get("data-ellipse-anchor-y"))
    rendered_rx = float(g.get("data-ellipse-rx"))
    rendered_ry = float(g.get("data-ellipse-ry"))

    corners = [(gx, gy), (gx + gw, gy), (gx, gy + gh), (gx + gw, gy + gh)]
    d_far = max(math.hypot(cx - anchor_x, cy - anchor_y) for cx, cy in corners)

    digest = compute_fingerprint(parse(LARGE_INPUT).core)
    p = v3_ellipse_params_from_digest(digest)

    r_min_correct = cell_h / 2  # == nucleus_height
    r_max = d_far - cell_w
    expected_rx = r_min_correct + (p["rx_step"] / 15.0) * (r_max - r_min_correct)
    expected_ry = r_min_correct + (p["ry_step"] / 15.0) * (r_max - r_min_correct)

    assert rendered_rx == expected_rx
    assert rendered_ry == expected_ry

    # And ensure the test is meaningful: the buggy r_min = cell_h would give
    # a materially different value on at least one axis (a step of 15 puts
    # that axis at r_max regardless of r_min, so guard on the pair, not a
    # single axis).
    r_min_buggy = cell_h
    buggy_rx = r_min_buggy + (p["rx_step"] / 15.0) * (r_max - r_min_buggy)
    buggy_ry = r_min_buggy + (p["ry_step"] / 15.0) * (r_max - r_min_buggy)
    assert not (
        math.isclose(rendered_rx, buggy_rx) and math.isclose(rendered_ry, buggy_ry)
    ), "r_min appears to still be cell_h, not nucleus_height"
