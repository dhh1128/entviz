"""
v5: color-bar band letters.

Each visible band in the color bar carries a single lowercase letter
centered horizontally and vertically:

    #ffffff → w   (black text)
    #e7be00 → g   (black text)
    #ff3f2f → r   (white text)
    #2f3fbf → b   (white text)
    #000000 → k   (white text)

Letter color follows the existing Oklab L threshold rule from
entviz.colors: L < 0.6 → white text; else black. For these five colors
that yields the mapping above (verified at test time, not hard-coded).

Letter font: same monospace family as cell text.
Font size = min(band_height * 0.7, bar_width * 0.85) so the glyph fits
both axes. There is no minimum: very small bands get very small letters
(and bands too small for legibility skip the letter entirely).
"""
from lxml import etree

from entviz.pipeline import render
from entviz.colors import oklab_lightness


def _doc(svg_str):
    return etree.fromstring(svg_str.encode())


BAND_LETTER = {
    "#ffffff": "w",
    "#e7be00": "g",
    "#ff3f2f": "r",
    "#2f3fbf": "b",
    "#000000": "k",
}


def _hex_to_rgb(h):
    return (int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16))


def _expected_fg_for_band(bg_hex):
    """Apply the documented contrast rule directly."""
    L = oklab_lightness(_hex_to_rgb(bg_hex))
    return "#ffffff" if L < 0.6 else "#000000"


def _band_rects(svg):
    return [
        r for r in svg.xpath('//*[local-name()="rect"]')
        if float(r.get("x", -1)) == 1 and float(r.get("width", -1)) == 20
    ]


def _band_letters(svg):
    """Return the band-letter <text> elements (those flagged with
    data-color-bar-letter='true')."""
    return svg.xpath(
        '//*[local-name()="text" and @data-color-bar-letter="true"]'
    )


def test_oklab_contrast_rule_produces_expected_letter_colors():
    """Sanity-check the rule itself for the 5 palette colors. Note: the
    documented L<0.6 rule from entviz.colors yields BLACK text on red
    (Oklab L≈0.657 for #ff3f2f sits just above the threshold). The
    parallel v5 spec draft asserted white-on-red; the maintainer needs
    to reconcile, but this test pins behavior to the rule actually in
    the codebase."""
    expected = {
        "#ffffff": "#000000",  # W on white → black (L≈1.000)
        "#e7be00": "#000000",  # G on gold  → black (L≈0.814)
        "#ff3f2f": "#000000",  # R on red   → black (L≈0.657, above 0.6)
        "#2f3fbf": "#ffffff",  # B on blue  → white (L≈0.445)
        "#000000": "#ffffff",  # K on black → white (L≈0.000)
    }
    for bg, fg in expected.items():
        assert _expected_fg_for_band(bg) == fg, (
            f"Oklab rule for {bg}: expected {fg}, got {_expected_fg_for_band(bg)}"
        )


def test_each_band_has_one_letter_text():
    """Every visible band has exactly one corresponding letter text."""
    svg = _doc(render("550e8400-e29b-41d4-a716-446655440000"))
    bands = _band_rects(svg)
    letters = _band_letters(svg)
    assert len(letters) == len(bands), (
        f"{len(letters)} letters vs {len(bands)} bands"
    )


def _band_fill_of_letter(t):
    """The band a letter belongs to is its parent group's rect — robust to
    the v6 bottom-anchoring where the letter's y may sit outside its band."""
    parent = t.getparent()
    rects = [c for c in parent if c.tag.endswith("}rect")]
    assert rects, "letter's parent group has no band rect"
    return rects[0].get("fill")


def test_letter_content_matches_palette():
    """Letter text content must be one of w, g, r, b, k and match its
    band's fill color."""
    svg = _doc(render("550e8400-e29b-41d4-a716-446655440000"))
    letters = _band_letters(svg)
    assert letters
    for t in letters:
        fill = _band_fill_of_letter(t)
        assert t.text == BAND_LETTER[fill], (
            f"letter '{t.text}' on band {fill} != expected {BAND_LETTER[fill]}"
        )


def test_letter_fill_follows_oklab_contrast_rule():
    svg = _doc(render("550e8400-e29b-41d4-a716-446655440000"))
    letters = _band_letters(svg)
    assert letters
    for t in letters:
        fill = _band_fill_of_letter(t)
        expected = _expected_fg_for_band(fill)
        assert t.get("fill") == expected, (
            f"letter on {fill}: expected fill {expected}, got {t.get('fill')}"
        )


def test_letter_is_centered_horizontally_in_color_bar():
    svg = _doc(render("550e8400-e29b-41d4-a716-446655440000"))
    bands = _band_rects(svg)
    letters = _band_letters(svg)
    assert bands and letters
    # Bar drawing region: x=1, width=bar_width=20. Center x = 11.
    expected_cx = 1 + 20 / 2
    for t in letters:
        assert abs(float(t.get("x")) - expected_cx) < 0.01, (
            f"letter x={t.get('x')} not centered (expected {expected_cx})"
        )
        # Text anchor must be 'middle' for centering to render correctly.
        assert t.get("text-anchor") == "middle"


def test_letter_font_family_is_monospace():
    svg = _doc(render("550e8400-e29b-41d4-a716-446655440000"))
    letters = _band_letters(svg)
    assert letters
    # font-family is now hoisted onto the root <svg> as an inherited property;
    # the band letters inherit it rather than carrying a per-text style.
    root_ff = svg.get("font-family") or ""
    assert "monospace" in root_ff, (
        f"root <svg> font-family is not monospace (font-family={root_ff!r})"
    )
    for t in letters:
        assert t.get("style") is None, (
            f"band letter should not carry a per-text style (got {t.get('style')!r})"
        )


import re


def _font_size_px(text_el):
    attr = text_el.get("font-size")
    if attr is not None:
        attr = attr.strip()
        if attr.endswith("px"):
            attr = attr[:-2]
        return float(attr)
    m = re.search(r'font-size:\s*([0-9.]+)px', text_el.get("style") or "")
    assert m, f"font-size not found in style={text_el.get('style')!r}"
    return float(m.group(1))


def test_letter_font_size_equals_cell_text_size():
    """v6: each color-bar letter renders at exactly the cell-text size (no
    scaling to the band), for uniform type across the entviz."""
    svg = _doc(render("550e8400-e29b-41d4-a716-446655440000"))
    letters = _band_letters(svg)
    assert letters
    # Cell-text size: a token <text> living inside a cell group.
    cell_texts = svg.xpath(
        '//*[local-name()="g"][@data-cell-index]//*[local-name()="text"]'
    )
    assert cell_texts, "no cell text found"
    cell_size = _font_size_px(cell_texts[0])
    for t in letters:
        assert _font_size_px(t) == cell_size, (
            f"color-bar letter {_font_size_px(t)} != cell text {cell_size}"
        )


def test_letter_bottom_does_not_bleed_below_its_band():
    """The baseline is placed so the glyph bottom stays within the band;
    the top may bleed above on a short band."""
    svg = _doc(render("550e8400-e29b-41d4-a716-446655440000"))
    for t in _band_letters(svg):
        parent = t.getparent()
        rect = [c for c in parent if c.tag.endswith("}rect")][0]
        band_bottom = float(rect.get("y")) + float(rect.get("height"))
        baseline = float(t.get("y"))
        fs = _font_size_px(t)
        # Glyph bottom ≈ baseline + descender (~0.2*fs) must not exceed the band.
        assert baseline + 0.2 * fs <= band_bottom + 0.01, (
            f"letter bottom {baseline + 0.2*fs} bleeds below band {band_bottom}"
        )
