"""
Regression test for the ellipse overlay's radius clamp.

v6 (spec.md, "Draw the ellipse overlay") specifies the semi-axes as
    rx = r_min + (rx_step / 15) * (r_max - r_min)
    ry = r_min + (ry_step / 15) * (r_max - r_min)
with **r_min = 0.22 · d_far** and **r_max = 0.58 · d_far**, where d_far is the
distance from the anchor to the farthest grid_rect corner. This replaced v5's
`[nucleus_height, d_far - cell_width]`, which let small grids be swamped and
large grids show invisible slivers (see reviews/ellipse-audit-2026-06-02.md).

These tests recompute the expected radii purely from the rendered SVG (grid
geometry from the clipPath rect, anchor + radii from the ellipse group's
data-* attributes) and the digest-derived step values.
"""
import math

from lxml import etree

from entviz.entropy import parse
from entviz.fingerprint import compute_fingerprint
from entviz.pipeline import render, v3_ellipse_params_from_digest


# 64-byte hex input -> 22 tokens -> 4x6 grid (interior-anchored overlay).
LARGE_INPUT = "deadbeefdeadbeef" * 8

R_MIN_FRACTION = 0.22
R_MAX_FRACTION = 0.58


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


def _measure(svg_str):
    svg = _doc(svg_str)
    gx, gy, gw, gh = _grid_rect_from_clip(svg)
    g = _ellipse_group(svg)
    anchor_x = float(g.get("data-ellipse-anchor-x"))
    anchor_y = float(g.get("data-ellipse-anchor-y"))
    rendered_rx = float(g.get("data-ellipse-rx"))
    rendered_ry = float(g.get("data-ellipse-ry"))
    corners = [(gx, gy), (gx + gw, gy), (gx, gy + gh), (gx + gw, gy + gh)]
    d_far = max(math.hypot(cx - anchor_x, cy - anchor_y) for cx, cy in corners)
    return rendered_rx, rendered_ry, d_far


def test_ellipse_radii_match_dfar_relative_clamp():
    rendered_rx, rendered_ry, d_far = _measure(render(LARGE_INPUT))
    r_min = R_MIN_FRACTION * d_far
    r_max = R_MAX_FRACTION * d_far
    digest = compute_fingerprint(parse(LARGE_INPUT).core)
    p = v3_ellipse_params_from_digest(digest)
    expected_rx = r_min + (p["rx_step"] / 15.0) * (r_max - r_min)
    expected_ry = r_min + (p["ry_step"] / 15.0) * (r_max - r_min)
    assert math.isclose(rendered_rx, expected_rx, rel_tol=1e-9)
    assert math.isclose(rendered_ry, expected_ry, rel_tol=1e-9)


def test_ellipse_radii_stay_within_clamp_bounds():
    """Across a range of inputs/grids, both semi-axes stay inside
    [0.22·d_far, 0.58·d_far] — never below the floor, never above the cap."""
    inputs = [
        "ab",
        "deadbeef",
        "550e8400-e29b-41d4-a716-446655440000",
        "0123456789abcdef" * 2,
        "0123456789abcdef" * 8,
        LARGE_INPUT,
        "a" * 36,
    ]
    for inp in inputs:
        rx, ry, d_far = _measure(render(inp))
        lo = R_MIN_FRACTION * d_far - 1e-6
        hi = R_MAX_FRACTION * d_far + 1e-6
        assert lo <= rx <= hi, f"{inp!r}: rx={rx} outside [{lo}, {hi}]"
        assert lo <= ry <= hi, f"{inp!r}: ry={ry} outside [{lo}, {hi}]"
