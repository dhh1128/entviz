"""
V3-4: hex cell text renders at 75% of reference font size.

The reference font size still drives all geometry; only the rendered
size of cell text changes per token type.

  4-char tokens (base64, base58, fallback): rendered_pt = reference_pt
  6-char tokens (hex):                       rendered_pt = round(0.75 × reference_pt)

At 12pt/96 DPI reference:
  4-char: 12pt → 16 px (unchanged)
  6-char: 9pt → 12 px

This also propagates into the SCS via the min(0.9×ref, cell_text_pt)
rule: for hex inputs SCS = min(11pt, 9pt) = 9pt = 12 px, matching
the cell text.
"""
import re
from lxml import etree

from entviz.pipeline import render


def _doc(svg_str):
    return etree.fromstring(svg_str.encode())


def _font_size_px(el):
    style = el.get("style") or ""
    m = re.search(r"font-size:\s*([\d.]+)px", style)
    return float(m.group(1)) if m else None


def _cell_text_pxs(svg):
    return [
        _font_size_px(t)
        for t in svg.xpath('//*[local-name()="text"]')
        if t.get("text-anchor") == "middle"
    ]


def _scs_px(svg):
    for t in svg.xpath('//*[local-name()="text"]'):
        if t.get("text-anchor") == "end":
            return _font_size_px(t)
    return None


def test_hex_input_cell_text_rendered_at_12px():
    # "deadbeef" → hex type → 6-char token length → 9pt rendered →
    # 12 px at 96 DPI.
    svg = _doc(render("deadbeefdeadbeef"))
    pxs = _cell_text_pxs(svg)
    assert pxs, "no cell text rendered"
    for p in pxs:
        assert p == 12, f"hex cell text rendered at {p}px; expected 12"


def test_non_hex_input_cell_text_rendered_at_16px():
    # A non-hex input (Bitcoin address, base58) → 4-char tokens
    # → cell text at full reference = 16 px.
    # (UUID was the v2 example here but post-alphabet-refactor UUID is
    # correctly typed as hex, so it now exercises the 12 px branch.)
    svg = _doc(render("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"))
    pxs = _cell_text_pxs(svg)
    assert pxs
    for p in pxs:
        assert p == 16, f"non-hex cell text rendered at {p}px; expected 16"


def test_hex_scs_matches_cell_text_size():
    # For hex inputs: scs_pt = min(round(0.9×12), 9) = min(11, 9) = 9pt
    # → 12 px. Cell text and SCS are the same size; the visual
    # hierarchy comes entirely from the #444 fill.
    svg = _doc(render("deadbeef" * 16))  # 22 hex tokens, big enough for SCS
    cell_px = _cell_text_pxs(svg)[0]
    scs = _scs_px(svg)
    assert cell_px == scs == 12, (
        f"hex cell={cell_px}px, SCS={scs}px; expected both 12"
    )


def test_non_hex_scs_smaller_than_cell_text():
    # For non-hex inputs: scs_pt = min(11, 12) = 11pt → 14.67 px;
    # cell text is at full reference = 16 px. (See test_v3_scs_styling
    # for the converse test on the SCS-only path.) Bitcoin address
    # (base58) exercises this branch post-alphabet-refactor.
    svg = _doc(render("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"))
    cell_px = _cell_text_pxs(svg)[0]
    scs = _scs_px(svg)
    assert cell_px == 16
    assert scs is not None and 14 < scs < 15


def test_hex_text_fits_inside_nucleus():
    # The whole point of V3-4: 6-char hex tokens at full reference
    # overflowed the 48-px-wide nucleus. At 75% (9pt → 12 px), each
    # monospace char is ~7.2 px wide and 6 chars need ~43 px — fits.
    svg = _doc(render("deadbeefdeadbeef"))
    texts = [t for t in svg.xpath('//*[local-name()="text"]')
             if t.get("text-anchor") == "middle"]
    # All cell texts use the same font size and are centered in 48-px
    # nuclei; with a ~0.6 char-width ratio, 6 chars × 0.6 × 12 px ≈
    # 43.2 px, leaving ~4.8 px of slack. We can't measure rendered
    # glyph widths from outside, but verifying that font-size is 12
    # is the structural guarantee that the fit calculation worked.
    for t in texts:
        assert _font_size_px(t) == 12
