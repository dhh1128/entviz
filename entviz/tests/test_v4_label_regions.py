"""
v4 type/prefix/suffix label regions: a nucleus-height white strip above
the grid showing "<Type>: <prefix>..." (always present), and a matching
strip below showing "...<suffix>" (only when the parsed result has a
suffix). Both strips use the same monospace font + rendered size as the
cell text, filled in #666 (dark gray) so they read as a quiet label,
not competing with the cells.

Margin between strip and grid (and between strip and border) = GM.
Top label left-aligned to grid_rect.left; bottom right-aligned to
grid_rect.right, so the ellipses both point inward toward the cells.
"""
from lxml import etree

from entviz.pipeline import render


def _doc(svg_str):
    return etree.fromstring(svg_str.encode())


def _labels(svg):
    """All <text> elements colored #666 (the label color)."""
    return [t for t in svg.xpath('//*[local-name()="text"]')
            if t.get("fill") == "#666666"]


def test_top_label_always_present_for_hex():
    """Even a plain hex input with no prefix shows a top label
    ('hex:' or similar). Use chars including 6/7/8/9 so the input
    doesn't also match the EOS account-name regex (which is just
    [a-z1-5.])."""
    svg = _doc(render("6789abcd6789abcd"))
    labels = _labels(svg)
    assert labels, "no label text found"
    top = min(labels, key=lambda t: float(t.get("y")))
    assert top.text.startswith("hex:"), f"unexpected top label: {top.text!r}"


def test_ethereum_top_label_includes_0x_prefix_and_ellipsis():
    """For Ethereum: 'Ethereum: 0x...'."""
    svg = _doc(render("0x742d35cc6634c0532925a3b844bc454e4438f44e"))
    labels = _labels(svg)
    top = min(labels, key=lambda t: float(t.get("y")))
    assert top.text == "Ethereum: 0x..."


def test_uuid_top_label_no_prefix():
    """UUID has no prefix; label is just 'UUID:'."""
    svg = _doc(render("550e8400-e29b-41d4-a716-446655440000"))
    labels = _labels(svg)
    top = min(labels, key=lambda t: float(t.get("y")))
    assert top.text == "UUID:"


def test_bottom_label_only_present_with_suffix():
    """Inputs with no suffix get no bottom label."""
    # hex has no suffix
    svg = _doc(render("deadbeefcafe1234"))
    labels = _labels(svg)
    assert len(labels) == 1, f"expected only top label, got {len(labels)}"


def test_bitcoin_legacy_has_top_and_bottom_labels():
    """Bitcoin legacy has both prefix and (true) suffix.
    Top: 'Bitcoin legacy: 1...'  Bottom: '...<4-char-base58-checksum>'."""
    svg = _doc(render("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"))
    labels = _labels(svg)
    assert len(labels) == 2, f"expected 2 labels, got {len(labels)}"
    sorted_labels = sorted(labels, key=lambda t: float(t.get("y")))
    top, bottom = sorted_labels
    assert top.text.startswith("Bitcoin legacy: 1"), f"top: {top.text!r}"
    assert top.text.endswith("..."), f"top: {top.text!r}"
    assert bottom.text.startswith("..."), f"bottom: {bottom.text!r}"
    # The suffix is 4 base58 chars; the label is "...XXXX" → length 7.
    assert len(bottom.text) == 7, f"bottom: {bottom.text!r}"


def test_label_text_fill_is_666():
    """All label text is filled in #666666."""
    svg = _doc(render("0x742d35cc6634c0532925a3b844bc454e4438f44e"))
    labels = _labels(svg)
    assert labels  # don't pass vacuously
    for t in labels:
        assert t.get("fill") == "#666666"


def test_label_text_font_matches_cell_text():
    """Labels use the same font-family (monospace) and the same rendered
    font size as the cell text."""
    svg = _doc(render("0x742d35cc6634c0532925a3b844bc454e4438f44e"))
    cell_texts = [t for t in svg.xpath('//*[local-name()="text"]')
                  if t.get("text-anchor") == "middle"]
    cell_text_style = cell_texts[0].get("style")
    labels = _labels(svg)
    assert labels  # don't pass vacuously
    for t in labels:
        # Same style string → same family and size.
        assert t.get("style") == cell_text_style, (
            f"label style {t.get('style')!r} != cell style {cell_text_style!r}"
        )


def test_top_label_left_aligned_to_grid():
    """Top label starts at grid_rect.left."""
    svg = _doc(render("0x742d35cc6634c0532925a3b844bc454e4438f44e"))
    labels = _labels(svg)
    top = min(labels, key=lambda t: float(t.get("y")))
    # At 12pt with 7-token Ethereum, grid_rect.left = 17.
    assert float(top.get("x")) == 17
    assert top.get("text-anchor") in (None, "start")


def test_bottom_label_right_aligned_to_grid():
    """Bottom label ends at grid_rect.right."""
    svg = _doc(render("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"))
    labels = _labels(svg)
    bottom = max(labels, key=lambda t: float(t.get("y")))
    # text-anchor=end with x at grid_rect.right means the right edge of
    # the text sits at the grid's right edge.
    assert bottom.get("text-anchor") == "end"


def test_disproof_alphabet_label_uses_alphabet_name():
    """When parse() finds an alphabet by disproof (no specific parser
    matched), the label shows the alphabet name, e.g. 'base32:', not
    'auto-detected:'."""
    # An uppercase base32-only string (no specific format prefix).
    svg = _doc(render("ABCDEFGHIJKLMNOPQR234567"))
    labels = _labels(svg)
    top = min(labels, key=lambda t: float(t.get("y")))
    assert top.text == "base32:"


def test_utf8_fallback_label_says_txt_to_b64url():
    """When the input has chars no alphabet can encode (e.g. a space),
    the UTF-8 → base64url re-encode path activates. Label is shortened
    to 'txt->b64url:' so it fits on narrow grids."""
    svg = _doc(render("hello world"))
    labels = _labels(svg)
    top = min(labels, key=lambda t: float(t.get("y")))
    assert top.text == "txt->b64url:"


def test_canvas_height_grows_with_top_label_only():
    """Hex input → top label, no bottom label. Canvas height grows by
    nucleus_height + GM (= 20 + 5 = 25 at 12pt) over the no-label v4."""
    svg = _doc(render("deadbeef"))
    # deadbeef → 2 tokens → 2x2 grid; previously bounding_h = 92.
    # With top label only: 92 + 25 = 117.
    assert float(svg.get("height")) == 117


def test_canvas_height_grows_with_both_labels():
    """Input with both prefix and suffix → top + bottom labels.
    Canvas grows by 2·(nucleus_height + GM) = 50 over the no-label v4."""
    svg = _doc(render("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"))
    # Bitcoin Legacy: 34 chars - 1 prefix - 4 suffix = 29-char body →
    # 8 base58 tokens (29/4 rounding up). choose_grid(8, 1.0) → 2x4 grid.
    # No labels: bounding_h = 1+5+(4·40)+5+1 = 172. With both labels:
    # 172 + 50 = 222.
    assert float(svg.get("height")) == 222
