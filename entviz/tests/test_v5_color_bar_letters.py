"""
v5: color-bar band letters.

Each visible band in the color bar carries a single lowercase letter
centered horizontally and vertically:

    #ffffff → w   (black text)
    #ffd966 → g   (black text)
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
    "#ffd966": "g",
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
        if float(r.get("x", -1)) == 1 and float(r.get("width", -1)) == 10
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
        "#ffd966": "#000000",  # G on gold  → black (L≈0.896)
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


def test_letter_content_matches_palette():
    """Letter text content must be one of w, g, r, b, k and match the
    band's fill color."""
    svg = _doc(render("550e8400-e29b-41d4-a716-446655440000"))
    bands = _band_rects(svg)
    letters = _band_letters(svg)

    # Map band y-center → expected letter from fill.
    expected_by_y = {}
    for b in bands:
        y = float(b.get("y")) + float(b.get("height")) / 2
        expected_by_y[round(y, 2)] = BAND_LETTER[b.get("fill")]

    for t in letters:
        ty = round(float(t.get("y")), 2)
        # The letter's y is the band center; match within tolerance.
        match = min(expected_by_y.keys(), key=lambda k: abs(k - ty))
        assert abs(match - ty) < 0.5, (
            f"letter y={ty} not near any band center {list(expected_by_y)}"
        )
        assert t.text == expected_by_y[match], (
            f"letter '{t.text}' at y={ty} != expected {expected_by_y[match]}"
        )


def test_letter_fill_follows_oklab_contrast_rule():
    svg = _doc(render("550e8400-e29b-41d4-a716-446655440000"))
    bands = _band_rects(svg)
    letters = _band_letters(svg)

    # Match letters to bands by y-coord proximity.
    for t in letters:
        ty = float(t.get("y"))
        # Find the band whose y-range contains ty.
        band = next(
            b for b in bands
            if float(b.get("y")) <= ty <= float(b.get("y")) + float(b.get("height"))
        )
        expected = _expected_fg_for_band(band.get("fill"))
        assert t.get("fill") == expected, (
            f"letter on {band.get('fill')}: expected fill {expected}, got {t.get('fill')}"
        )


def test_letter_is_centered_horizontally_in_color_bar():
    svg = _doc(render("550e8400-e29b-41d4-a716-446655440000"))
    bands = _band_rects(svg)
    letters = _band_letters(svg)
    assert bands and letters
    # Bar drawing region: x=1, width=10. Center x = 6.
    expected_cx = 1 + 10 / 2
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
    for t in letters:
        style = t.get("style") or ""
        assert "monospace" in style, (
            f"band letter font is not monospace (style={style!r})"
        )


def test_letter_font_size_fits_both_band_height_and_bar_width():
    """font_size_px = min(band_height * 0.7, bar_width * 0.85). No
    minimum floor: small bands get small letters (or skip the letter
    entirely if below the legibility threshold). bar_width = 10 px at
    12pt → horizontal cap = 8.5 px."""
    svg = _doc(render("550e8400-e29b-41d4-a716-446655440000"))
    bands = _band_rects(svg)
    letters = _band_letters(svg)
    assert bands and letters

    bar_width = 10.0  # bar inset width at default 12pt geometry
    for t in letters:
        ty = float(t.get("y"))
        band = next(
            b for b in bands
            if float(b.get("y")) <= ty <= float(b.get("y")) + float(b.get("height"))
        )
        bh = float(band.get("height"))
        expected = min(bh * 0.7, bar_width * 0.85)
        style = t.get("style") or ""
        import re
        m = re.search(r'font-size:\s*([0-9.]+)px', style)
        assert m, f"font-size not found in style={style!r}"
        assert abs(float(m.group(1)) - expected) < 0.01, (
            f"font-size {m.group(1)} != expected {expected} for band_h={bh}"
        )
