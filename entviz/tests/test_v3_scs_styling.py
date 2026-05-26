"""
SCS rendered font size = min(round(0.84 × reference_pt),
cell_text_pt); fill = #444.

The min keeps SCS from ever being larger than the cell text. For
non-hex inputs cell_text_pt == reference_pt so the min picks the
0.84 branch; for hex inputs cell_text_pt = round(0.75 × ref), and
the min picks cell_text_pt so SCS matches cell text size.

At 12pt/96 DPI:
  scs_pt = min(round(0.84 × 12), 12) = min(10, 12) = 10pt
  scs_px = 10 × 96/72 ≈ 13.33 px
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
    svg = _doc(render("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"))
    scs = _scs_text(svg)
    fill = scs.get("fill") or ""
    assert fill in ("#444", "#444444"), f"SCS fill is {fill!r}; expected #444"


def test_scs_font_size_at_84_percent_of_reference():
    # Default reference is 12pt → 10pt rendered → 13.33 px.
    svg = _doc(render("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"))
    scs = _scs_text(svg)
    style = scs.get("style") or ""
    assert any(s in style for s in ["font-size: 13.3", "font-size: 13.4"]), (
        f"SCS font-size in style {style!r} is not ~13.33 px"
    )


def test_scs_font_size_smaller_than_cell_text():
    # The cell text in v2/v3 (pre-V3-4) renders at nucleus_height = 16 px.
    # SCS should be visibly smaller, which is the whole point of 90%.
    svg = _doc(render("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"))
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
    # 18pt reference → 0.84 × 18 = 15.12 → round to 15pt → 20 px.
    svg = _doc(render("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", font_size_pt=18))
    scs = _scs_text(svg)
    style = scs.get("style") or ""
    assert "font-size: 20" in style, (
        f"at 18pt reference, SCS font-size in style {style!r} is not 20 px"
    )
