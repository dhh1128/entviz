"""
V3-3a: SCS rendered font size = min(round(0.9 × reference_pt),
cell_text_pt); fill = #444.

The min keeps SCS from ever being larger than the cell text. Before
V3-4 lands, cell_text_pt == reference_pt, so the min has no effect
yet — but the formula is plumbed so V3-4's per-token cell-text
shrinking just changes one argument.

At 12pt/96 DPI:
  scs_pt = min(round(0.9 × 12), 12) = min(11, 12) = 11pt
  scs_px = 11 × 96/72 ≈ 14.67 px
"""
from lxml import etree

from entviz.pipeline import render


def _doc(svg_str):
    return etree.fromstring(svg_str.encode())


def _scs_text(svg):
    for t in svg.xpath('//*[local-name()="text"]'):
        if t.get("text-anchor") == "end":
            return t
    return None


def test_scs_fill_is_dark_gray_not_black():
    svg = _doc(render("550e8400-e29b-41d4-a716-446655440000"))
    scs = _scs_text(svg)
    fill = scs.get("fill") or ""
    assert fill in ("#444", "#444444"), f"SCS fill is {fill!r}; expected #444"


def test_scs_font_size_at_90_percent_of_reference():
    # Default reference is 12pt → 11pt rendered → 14.67 px.
    svg = _doc(render("550e8400-e29b-41d4-a716-446655440000"))
    scs = _scs_text(svg)
    style = scs.get("style") or ""
    # Match a couple of acceptable text forms ("14.67", "14.666...", "14.6").
    assert any(s in style for s in ["font-size: 14.6", "font-size: 14.7"]), (
        f"SCS font-size in style {style!r} is not ~14.67 px"
    )


def test_scs_font_size_smaller_than_cell_text():
    # The cell text in v2/v3 (pre-V3-4) renders at nucleus_height = 16 px.
    # SCS should be visibly smaller, which is the whole point of 90%.
    svg = _doc(render("550e8400-e29b-41d4-a716-446655440000"))
    scs = _scs_text(svg)
    cell_text = next(
        t for t in svg.xpath('//*[local-name()="text"]')
        if t.get("text-anchor") == "middle"
    )

    def _font_size_px(el):
        style = el.get("style") or ""
        import re
        m = re.search(r"font-size:\s*([\d.]+)px", style)
        return float(m.group(1)) if m else None

    scs_px = _font_size_px(scs)
    cell_px = _font_size_px(cell_text)
    assert scs_px is not None and cell_px is not None
    assert scs_px < cell_px, f"SCS {scs_px}px is not smaller than cell text {cell_px}px"


def test_scs_at_larger_reference_size_scales_proportionally():
    # 18pt reference → 0.9 × 18 = 16.2 → round to 16pt → 21.33 px.
    svg = _doc(render("550e8400-e29b-41d4-a716-446655440000", font_size_pt=18))
    scs = _scs_text(svg)
    style = scs.get("style") or ""
    # 21.33 — accept the typical rendered prefixes.
    assert any(s in style for s in ["font-size: 21.3", "font-size: 21.4"]), (
        f"at 18pt reference, SCS font-size in style {style!r} is not ~21.33 px"
    )
