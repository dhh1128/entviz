"""
v4 color bar: bands sourced from a 4-element histogram of 2-bit patterns
across the 256 disjoint 2-bit slices of the SHA-512 digest. Total count
always = 256 (every input). Pattern binary value i → edge_colors[i].
"""
from lxml import etree

from entviz.pipeline import _two_bit_color_usage, render


def _doc(svg_str):
    return etree.fromstring(svg_str.encode())


def test_two_bit_histogram_sums_to_256():
    """A 64-byte digest yields 256 disjoint 2-bit slices."""
    palette = ['#ffffff', '#e7be00', '#ff3f2f', '#2f3fbf']
    digest = bytes(range(64))  # arbitrary 64-byte digest
    usage = _two_bit_color_usage(digest, palette)
    assert sum(usage.values()) == 256


def test_two_bit_histogram_uniform_for_uniform_digest():
    """A digest of all 0x55 (binary 01010101) puts every 2-bit slice
    at value 01 → all 256 slices land in palette[1]."""
    palette = ['#ffffff', '#e7be00', '#ff3f2f', '#2f3fbf']
    digest = b"\x55" * 64
    usage = _two_bit_color_usage(digest, palette)
    assert usage['#e7be00'] == 256
    assert usage['#ffffff'] == 0
    assert usage['#ff3f2f'] == 0
    assert usage['#2f3fbf'] == 0


def test_two_bit_histogram_all_zero():
    """All-zero digest → all slices are 00 → all in palette[0]."""
    palette = ['#ffffff', '#e7be00', '#ff3f2f', '#2f3fbf']
    digest = b"\x00" * 64
    usage = _two_bit_color_usage(digest, palette)
    assert usage['#ffffff'] == 256


def test_two_bit_histogram_all_one():
    """All-0xff digest → all slices are 11 → all in palette[3]."""
    palette = ['#ffffff', '#e7be00', '#ff3f2f', '#2f3fbf']
    digest = b"\xff" * 64
    usage = _two_bit_color_usage(digest, palette)
    assert usage['#2f3fbf'] == 256


def test_color_bar_bands_sum_to_drawing_region_height():
    """In rendered output, color-bar band heights sum to bounding_h - 4.

    The bar runs between the frame lines (y = MARGIN+1 .. bounding_h-MARGIN-1),
    a height of bounding_h - 2·MARGIN - 2 = bounding_h - 4 with MARGIN=1 (#31).
    """
    svg = _doc(render("550e8400-e29b-41d4-a716-446655440000"))
    bands = [
        r for r in svg.xpath('//*[local-name()="rect"]')
        if float(r.get("x", -1)) == 2 and float(r.get("width", -1)) == 20
    ]
    total = sum(float(b.get("height")) for b in bands)
    bh = float(svg.get("height"))
    assert abs(total - (bh - 4)) < 0.01
