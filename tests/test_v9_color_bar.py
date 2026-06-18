"""
v9 color-bar changes (this.i:b4rm4rks / d1scr3t3).

  * Band ORDER is decoupled from height: bands stack by each 2-bit pattern's
    FIRST appearance among the 256 disjoint digest slices (tie-break by pattern
    value), independent of the count^4 heights. Through v8 the order was
    descending count, which carried no information beyond the heights.
  * Two fixed-slot discrete MARKERS: a square in the left gutter at slot
    second[12] mod K, an equilateral triangle (apex up) in the right gutter at
    slot second[13] mod K, with K = clamp(floor(bar_height / 12px), 4, 16).
    Driven by the domain-separated `second` digest, so present on EVERY input
    (closing the coverage hole where the blank-cell map vanishes on a fully
    packed grid). Drawn OPAQUE — white fill + ~0.75px black halo, never a
    blend mode — for cross-rasterizer portability (F-A6).
"""
import re

from lxml import etree

from entviz.entropy import parse, fingerprint_middle_digest
from entviz.pipeline import render, _two_bit_first_appearance

SHORT = "deadbeef" * 8     # 256-bit hex, short input (markers, no middle cells)
BIG = "deadbeef" * 50      # >512-bit input (markers AND fingerprint-middle cells)


def _bar(svg_str):
    root = etree.fromstring(svg_str.encode())
    return root, root.xpath('//*[@data-channel="color-bar"]')[0]


# --- band order is decoupled from count ---

def test_first_appearance_orders_by_first_slice():
    # byte0 = 86 = 0b01010110 → LSB-first 2-bit slices are 2,1,1,1, so the
    # first-appearance order starts 2,1; trailing bytes only repeat seen ones.
    edge = ["a", "b", "c", "d"]
    order = _two_bit_first_appearance(bytes([86, 0, 0, 0]), edge)
    assert order[:2] == ["c", "b"]   # pattern 2 first, then pattern 1


def test_first_appearance_is_independent_of_counts():
    # slice0 = pattern 2 (appears first), then a flood of pattern 1 (by far the
    # highest count). Count order would put 1 first; first-appearance puts 2.
    edge = ["a", "b", "c", "d"]
    digest = bytes([0b01010110]) + bytes([0x55] * 31)
    order = _two_bit_first_appearance(digest, edge)
    assert order[0] == "c"   # pattern 2, despite pattern 1 dominating the count


# --- markers: present, in range, and pinned to the second digest ---

def test_markers_present_and_in_range_on_short_input():
    _, bar = _bar(render(SHORT))
    K = int(bar.get("data-bar-slots"))
    assert 4 <= K <= 16
    sq = int(bar.get("data-bar-marker-square"))
    tri = int(bar.get("data-bar-marker-triangle"))
    assert 0 <= sq < K and 0 <= tri < K


def test_marker_slots_match_second_digest():
    second = fingerprint_middle_digest(parse(SHORT).core)
    _, bar = _bar(render(SHORT))
    K = int(bar.get("data-bar-slots"))
    assert int(bar.get("data-bar-marker-square")) == second[12] % K
    assert int(bar.get("data-bar-marker-triangle")) == second[13] % K


def test_markers_present_on_large_input_too():
    _, bar = _bar(render(BIG))
    assert bar.get("data-bar-slots") is not None
    assert bar.get("data-bar-marker-square") is not None
    assert bar.get("data-bar-marker-triangle") is not None


# --- marker shapes: opaque, haloed, no blend mode ---

def test_square_is_opaque_rect_with_black_halo():
    root, _ = _bar(render(SHORT))
    sq = root.xpath('//*[@data-bar-marker="square"]')
    assert len(sq) == 1 and sq[0].tag.endswith("rect")
    assert sq[0].get("fill") == "#ffffff" and sq[0].get("stroke") == "#000000"


def test_triangle_is_opaque_polygon_apex_up():
    root, _ = _bar(render(SHORT))
    tri = root.xpath('//*[@data-bar-marker="triangle"]')
    assert len(tri) == 1 and tri[0].tag.endswith("polygon")
    assert tri[0].get("fill") == "#ffffff" and tri[0].get("stroke") == "#000000"
    pts = [tuple(map(float, p.split(","))) for p in tri[0].get("points").split()]
    assert len(pts) == 3
    ys = sorted(p[1] for p in pts)
    # apex up: one point above (smallest y), two on a level base below
    assert ys[0] < ys[1] and abs(ys[1] - ys[2]) < 1e-6


def test_no_mix_blend_mode_anywhere():
    # v9 markers (like the v6 blank-cell map) avoid blend modes for identical
    # rendering across browsers and non-browser rasterizers (F-A6).
    assert "mix-blend-mode" not in render(SHORT)
    assert "mix-blend-mode" not in render(BIG)
