"""
v5 large-input handling: head (8 tokens) + 4 fingerprint-selected middle
slices + tail (8 tokens), separated by two blank cells. Replaces v4's
head-256 + blank + tail-256 truncation scheme.

Spec authority: docs/spec.md §"What's new in v5" and the "Large-input
handling" subsection.
"""
import base64
import re

import pytest
from lxml import etree

from entviz.entropy import (
    BASE64,
    HEX,
    derive_middle_slice_offsets,
    middle_slice_char_offset,
    tokenize_entropy,
)
from entviz.fingerprint import compute_fingerprint
from entviz.pipeline import render


# ---- Part 1: middle-slice offset selector --------------------------------


def _hex_byte_length(core: str) -> int:
    return len(core) // 2


def test_middle_slice_offsets_deterministic_for_fixed_input():
    """For a 200-byte all-`aa` hex input, the four selected byte offsets
    are determined by digest[32..40] interpreted as four big-endian
    uint16s mod (N - 35), plus 16.

    Hand-computation: digest = SHA-512("aa"*200 as ascii bytes). N=200.
    Modulus = 200 - 3 - 32 = 165. Each raw_i = (digest[32+2i] << 8) |
    digest[33+2i]; offset_i = 16 + (raw_i mod 165).
    """
    core = "aa" * 200
    digest = compute_fingerprint(core)
    n = _hex_byte_length(core)
    expected = []
    modulus = n - 3 - 32  # 165
    for i in range(4):
        raw = (digest[32 + 2 * i] << 8) | digest[33 + 2 * i]
        expected.append(16 + (raw % modulus))
    expected_sorted = sorted(expected)

    offsets = derive_middle_slice_offsets(digest, n, num_slices=4)
    assert offsets == expected_sorted


def test_middle_slice_offsets_ascending_and_non_overlapping():
    """Spec rule: offsets are presented in ascending order and pairwise
    differ by ≥3 bytes (the dedup retry steps by 3 if a candidate is
    within ±3 bytes of any prior pick)."""
    digest = compute_fingerprint("deadbeef" * 100)  # arbitrary
    offsets = derive_middle_slice_offsets(digest, 400, num_slices=4)
    assert offsets == sorted(offsets)
    for a, b in zip(offsets, offsets[1:]):
        assert b - a >= 3, f"offsets too close: {offsets}"


def test_middle_slice_offsets_strictly_inside_middle_region():
    """Offsets must fall strictly inside [16, N - 16 - 3 + 1] so the
    3-byte read does not touch the head-32 or tail-32 zones."""
    digest = compute_fingerprint("cafebabe" * 50)
    n = 200
    offsets = derive_middle_slice_offsets(digest, n, num_slices=4)
    for off in offsets:
        assert off >= 16
        assert off + 3 <= n - 16


# ---- Part 2: token construction for >512-bit inputs ---------------------


def test_above_512_bit_hex_produces_8_head_4_middle_8_tail_tokens():
    """v5 large-input layout: 20 tokens (8 head + 4 middle + 8 tail) plus
    two separator blanks rendered by the pipeline. tokenize_entropy
    returns the 20 tokens with indices 0..19."""
    core = "ab" * 200  # 400 hex chars; way over the 22-token budget
    tokens, is_truncated = tokenize_entropy(core, HEX)
    assert is_truncated
    assert len(tokens) == 20
    # Head tokens 0..7 — first 8 tokens of the input, each 6 hex chars.
    for i in range(8):
        assert tokens[i].text == core[i * 6: (i + 1) * 6]
    # Tail tokens 12..19 — last 8 tokens of the input, each 6 hex chars.
    for k in range(8):
        expected = core[len(core) - (8 - k) * 6: len(core) - (8 - k - 1) * 6]
        assert tokens[12 + k].text == expected
    # Middle tokens 8..11 are 6 hex chars each.
    for j in range(8, 12):
        assert len(tokens[j].text) == 6


def test_middle_slice_cell_text_is_verbatim_substring_of_hex_input():
    """For hex, each middle-slice cell text is exactly the 6 chars at
    char_offset = byte_offset * 2 of the input string."""
    core = "0123456789abcdef" * 25  # 400 hex chars
    digest = compute_fingerprint(core)
    n = _hex_byte_length(core)
    offsets = derive_middle_slice_offsets(digest, n, num_slices=4)
    tokens, _ = tokenize_entropy(core, HEX)
    middle = tokens[8:12]
    for i, off in enumerate(offsets):
        expected = core[off * 2: off * 2 + 6]
        assert middle[i].text == expected, (
            f"slice {i} at byte offset {off} → char {off*2}: "
            f"got {middle[i].text!r}, want {expected!r}"
        )


def test_head_and_tail_collision_inputs_differ_in_middle_text():
    """Two inputs A and B sharing first 32 bytes (head zone) and last 32
    bytes (tail zone) but differing in the middle MUST differ in at least
    one middle-slice cell text."""
    head = "ab" * 32   # 32 bytes
    tail = "cd" * 32   # 32 bytes
    # Middle: same length, but differing content. Make A all-3 and B all-7
    # in the middle so middle-slice reads necessarily diverge.
    middle_a = "33" * 200  # 200 bytes
    middle_b = "77" * 200
    core_a = head + middle_a + tail  # 264 bytes total
    core_b = head + middle_b + tail

    sa = render(core_a)
    sb = render(core_b)
    da = etree.fromstring(sa.encode())
    db = etree.fromstring(sb.encode())
    # Extract middle-slice cell text from data-cell-index 9..12 cells
    # (cells 8 and 13 are the separator blanks).
    def middle_texts(svg):
        out = []
        for ci in (9, 10, 11, 12):
            cell = svg.xpath(
                f'//*[local-name()="g" and @data-cell-index="{ci}"]'
            )
            assert cell, f"missing cell {ci}"
            texts = cell[0].xpath('.//*[local-name()="text"]')
            assert texts, f"no <text> in cell {ci}"
            out.append(texts[0].text)
        return out

    ma = middle_texts(da)
    mb = middle_texts(db)
    assert ma != mb, (
        f"head/tail-colliding inputs produced identical middle text: {ma}"
    )


# ---- Part 3: loud truncation marker --------------------------------------


def test_truncated_marker_rendered_bold_dark_red():
    """For a >512-bit input the top label carries a bold dark-red
    `truncated(N bytes)` prefix segment. Implementation: either a
    distinct <text> element or a <tspan> with these styling attributes."""
    long_hex = "ab" * 100  # 200 hex chars = 100 bytes
    svg = etree.fromstring(render(long_hex).encode())
    # Search anywhere for an element whose text matches "truncated(...".
    candidates = svg.xpath(
        '//*[local-name()="text" or local-name()="tspan"]'
    )
    marker = None
    for el in candidates:
        if el.text and el.text.startswith("truncated("):
            marker = el
            break
    assert marker is not None, "no truncated(N bytes) marker rendered"
    # Byte count is len(input.encode('utf-8')) — for plain ascii hex this
    # equals the character count, which is 200 here.
    assert "truncated(200 bytes)" in marker.text
    fill = marker.get("fill") or ""
    style = marker.get("style") or ""
    assert "#a00000" in (fill + style).lower()
    weight = marker.get("font-weight") or ""
    assert "bold" in (weight + style).lower()


def test_no_truncated_marker_for_exactly_512_bit_input():
    """An exactly-512-bit input (128 hex chars) must NOT render the
    truncated marker — it follows the v4 path with 22 tokens."""
    core = "deadbeef" * 16  # 128 hex chars = 512 bits = 22 tokens, no trunc
    svg = etree.fromstring(render(core).encode())
    assert svg.get("data-truncated") is None
    for el in svg.xpath('//*[local-name()="text" or local-name()="tspan"]'):
        if el.text and el.text.startswith("truncated("):
            pytest.fail(
                f"unexpected truncated marker on 512-bit input: {el.text!r}"
            )


def test_truncated_label_text_contains_byte_count_and_type():
    """The marker reads `truncated(N bytes) <Type>: ...` per spec."""
    long_hex = "ab" * 100  # 200-byte hex
    svg = etree.fromstring(render(long_hex).encode())
    # Concatenate any tspan/text that lives in the label-top group, in
    # document order.
    label_g = svg.xpath(
        '//*[local-name()="g" and @data-channel="label-top"]'
    )
    assert label_g
    pieces = []
    for el in label_g[0].iter():
        if el.text:
            pieces.append(el.text)
    joined = "".join(pieces)
    assert "truncated(200 bytes)" in joined
    assert "hex(200):" in joined
