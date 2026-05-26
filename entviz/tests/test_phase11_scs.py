"""
Phase 11 acceptance tests: shape count summary (SCS) line below the
grid, plus SVG <title> tooltips on each edge shape.

SCS format: each shape with count > 0 becomes "X##" (capital letter +
zero-padded count). Tokens are sorted descending by count with
alphabetical letter as the tiebreak, joined by single spaces, right-
justified to the right edge of the grid_rect on the reserved line
beneath the grid (top = grid_rect.bottom + GM, height = nucleus_height).
"""
from lxml import etree
import re

from entviz.pipeline import render


def _doc(svg_str):
    return etree.fromstring(svg_str.encode())


def _scs_text(svg):
    """Return the SCS text element, or None."""
    # The SCS text is right-anchored at grid_rect.right and lives at the
    # bottom region of the SVG. The cell texts are middle-anchored.
    for t in svg.xpath('//*[local-name()="text"]'):
        if t.get("text-anchor") == "end":
            return t
    return None


def test_scs_text_element_present():
    svg = _doc(render("550e8400-e29b-41d4-a716-446655440000"))
    assert _scs_text(svg) is not None, "no right-anchored SCS text element"


def test_scs_format_is_tokens_of_digit_plus_2digit_count():
    # V3 SCS: tokens are "X##" where X is the slot digit (1, 2, or 3)
    # and ## is the zero-padded count. Slot 4 (empty) is omitted.
    svg = _doc(render("550e8400-e29b-41d4-a716-446655440000"))
    scs = _scs_text(svg)
    assert scs is not None
    tokens = scs.text.split()
    for tok in tokens:
        assert re.fullmatch(r"[123]\d{2}", tok), (
            f"SCS token {tok!r} not in v3 digit format"
        )


def test_scs_tokens_sorted_descending_by_count():
    svg = _doc(render("550e8400-e29b-41d4-a716-446655440000"))
    scs = _scs_text(svg)
    tokens = scs.text.split()
    counts = [int(t[1:]) for t in tokens]
    for i in range(len(counts) - 1):
        assert counts[i] >= counts[i + 1], (
            f"SCS not sorted descending: {tokens}"
        )


def test_scs_tied_counts_sorted_alphabetically():
    # Find any adjacent pair with equal counts; their letters must be
    # in alphabetical order.
    svg = _doc(render("550e8400-e29b-41d4-a716-446655440000"))
    scs = _scs_text(svg)
    tokens = scs.text.split()
    for a, b in zip(tokens, tokens[1:]):
        if int(a[1:]) == int(b[1:]):
            assert a[0] < b[0], f"tied tokens out of letter order: {a} {b}"


def test_scs_right_justified_to_grid_right_edge():
    # v3: grid_rect.left = 1 + edge_size + 1 + GM = 14; grid_rect.right
    # = grid_rect.left + grid_w. For UUID 2-col grid (grid_w=128): 142.
    svg = _doc(render("550e8400-e29b-41d4-a716-446655440000"))
    scs = _scs_text(svg)
    assert float(scs.get("x")) == 142


def test_scs_uses_v3_rendered_font_size():
    # V3-3a: SCS rendered font size = round(0.9 × reference_pt) = 11pt
    # at 12pt reference → 14.67 px (was 16 px in v2; the cell text stays
    # at 16 px until V3-4 makes per-token shrinking happen).
    svg = _doc(render("550e8400-e29b-41d4-a716-446655440000"))
    scs = _scs_text(svg)
    style = scs.get("style") or ""
    assert "font-size: 14.6" in style or "font-size: 14.7" in style


def test_shapes_carry_title_tooltips():
    # V3-6b: tooltip text is now the v3 shape name (C1..C3, P1..P3).
    # Empty members (C4/P4) don't render a tooltip because they don't
    # render at all.
    svg = _doc(render("550e8400-e29b-41d4-a716-446655440000"))
    titles = svg.xpath('//*[local-name()="title"]')
    assert len(titles) > 0, "no <title> tooltip elements found"
    valid = {"C1", "C2", "C3", "P1", "P2", "P3"}
    for t in titles:
        assert t.text in valid, f"unexpected tooltip text {t.text!r}"
