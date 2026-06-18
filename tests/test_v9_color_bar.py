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
    left = int(bar.get("data-bar-marker-left"))
    right = int(bar.get("data-bar-marker-right"))
    assert 0 <= left < K and 0 <= right < K


def test_marker_slots_match_second_digest():
    second = fingerprint_middle_digest(parse(SHORT).core)
    _, bar = _bar(render(SHORT))
    K = int(bar.get("data-bar-slots"))
    assert int(bar.get("data-bar-marker-left")) == second[12] % K
    assert int(bar.get("data-bar-marker-right")) == second[13] % K


def test_markers_present_on_large_input_too():
    _, bar = _bar(render(BIG))
    assert bar.get("data-bar-slots") is not None
    assert bar.get("data-bar-marker-left") is not None
    assert bar.get("data-bar-marker-right") is not None


# --- markers are circles distinguished by gutter (side), not by shape ---

def test_both_markers_are_opaque_haloed_circles():
    # v9: both gutter markers are circles (white fill + black halo). Identity
    # is carried by SIDE (left/right), not shape — square-vs-triangle was
    # unreliable on dark bands where the black halo vanishes.
    root, _ = _bar(render(SHORT))
    for side in ("left", "right"):
        m = root.xpath(f'//*[@data-bar-marker="{side}"]')
        assert len(m) == 1 and m[0].tag.endswith("circle"), side
        assert m[0].get("fill") == "#ffffff" and m[0].get("stroke") == "#000000"
        assert float(m[0].get("r")) > 0


def test_markers_sit_in_distinct_gutters():
    # The left marker's center is left of the right marker's, so the two can
    # never overlap regardless of which slots they land in.
    root, _ = _bar(render(SHORT))
    left = root.xpath('//*[@data-bar-marker="left"]')[0]
    right = root.xpath('//*[@data-bar-marker="right"]')[0]
    assert float(left.get("cx")) < float(right.get("cx"))


def test_no_mix_blend_mode_anywhere():
    # v9 markers (like the v6 blank-cell map) avoid blend modes for identical
    # rendering across browsers and non-browser rasterizers (F-A6).
    assert "mix-blend-mode" not in render(SHORT)
    assert "mix-blend-mode" not in render(BIG)
