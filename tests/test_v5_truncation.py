"""
Large-input handling: head (8 tokens) + 4 middle tokens + tail (8 tokens),
separated by two blank cells.

v6 changed the middle: it is now taken from the middle of the SHA-512
fingerprint (digest bytes 24-35), rendered in the input's alphabet — see
test_v6_fingerprint_middle.py for the behavior tests. This file keeps the
token-layout and the loud `fingerprint of` truncation-marker tests.

Spec authority: docs/spec.md "Large-input handling" and the marker step.
"""
import pytest
from lxml import etree

from entviz.entropy import HEX, tokenize_entropy
from entviz.pipeline import render


# ---- Token construction for >512-bit inputs -----------------------------


def test_above_512_bit_hex_produces_8_head_4_middle_8_tail_tokens():
    """Large-input layout: 20 tokens (8 head + 4 middle + 8 tail) plus two
    separator blanks rendered by the pipeline. tokenize_entropy returns the
    20 tokens with indices 0..19; head/tail are real entropy, the middle 4
    are fingerprint-derived (v6)."""
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
    # Middle tokens 8..11 are 6 hex chars each (rendered in the input alphabet).
    for j in range(8, 12):
        assert len(tokens[j].text) == 6


def test_head_and_tail_collision_inputs_differ_in_middle_text():
    """Two inputs sharing their head and tail but differing in the middle
    MUST differ in the middle text. v6 guarantees this via the fingerprint
    (any input change avalanches the digest → the middle tokens change)."""
    head = "ab" * 32   # 32 bytes
    tail = "cd" * 32   # 32 bytes
    core_a = head + "33" * 200 + tail
    core_b = head + "77" * 200 + tail

    da = etree.fromstring(render(core_a).encode())
    db = etree.fromstring(render(core_b).encode())

    def middle_texts(svg):
        out = []
        for ci in (9, 10, 11, 12):
            cell = svg.xpath(f'//*[local-name()="g" and @data-cell-index="{ci}"]')
            assert cell, f"missing cell {ci}"
            texts = cell[0].xpath('.//*[local-name()="text"]')
            assert texts, f"no <text> in cell {ci}"
            out.append(texts[0].text)
        return out

    assert middle_texts(da) != middle_texts(db)


# ---- Loud `fingerprint of` truncation marker ----------------------------


def test_truncated_marker_rendered_bold_dark_red():
    """For a >512-bit input the top label carries a bold dark-red
    `fingerprint of` prefix segment."""
    long_hex = "ab" * 100  # 200 hex chars = 100 bytes
    svg = etree.fromstring(render(long_hex).encode())
    candidates = svg.xpath('//*[local-name()="text" or local-name()="tspan"]')
    marker = None
    for el in candidates:
        if el.text and el.text.startswith("fingerprint of"):
            marker = el
            break
    assert marker is not None, "no fingerprint of marker rendered"
    fill = marker.get("fill") or ""
    style = marker.get("style") or ""
    assert "#a00000" in (fill + style).lower()
    weight = marker.get("font-weight") or ""
    assert "bold" in (weight + style).lower()


def test_no_truncated_marker_for_exactly_512_bit_input():
    """An exactly-512-bit input (128 hex chars) must NOT render the marker —
    it follows the 22-token path with no truncation."""
    core = "deadbeef" * 16  # 128 hex chars = 512 bits = 22 tokens, no trunc
    svg = etree.fromstring(render(core).encode())
    assert svg.get("data-truncated") is None
    for el in svg.xpath('//*[local-name()="text" or local-name()="tspan"]'):
        if el.text and el.text.startswith("fingerprint of"):
            pytest.fail(f"unexpected marker on 512-bit input: {el.text!r}")


def test_truncated_label_text_contains_type_with_byte_count():
    """The marker reads `fingerprint of <Type>: ...`; the byte count lives in
    the type-label parenthetical (e.g. `hex(200)`), not in the marker."""
    long_hex = "ab" * 100  # 200-byte hex
    svg = etree.fromstring(render(long_hex).encode())
    label_g = svg.xpath('//*[local-name()="g" and @data-channel="label-top"]')
    assert label_g
    joined = "".join(el.text for el in label_g[0].iter() if el.text)
    assert "fingerprint of" in joined
    assert "hex(200):" in joined
