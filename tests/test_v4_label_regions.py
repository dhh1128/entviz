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
    """v14: a plain hex input shows the projected label 'hex, <bits>-bit'.
    Use chars including 6/7/8/9 so the input doesn't also match the EOS
    account-name regex (which is just [a-z1-5.])."""
    svg = _doc(render("6789abcd6789abcd"))  # 16 hex chars -> 64 bits
    labels = _labels(svg)
    assert labels, "no label text found"
    top = min(labels, key=lambda t: float(t.get("y")))
    assert top.text == "hex, 64-bit", f"unexpected top label: {top.text!r}"


def test_hex_with_0x_prefix_shows_projected_size():
    """v15: '0x'-prefixed hex projects to 'hex, <bits>-bit, 0x' — the stripped
    '0x' front prefix is echoed as a trailing slot (so the reader sees the cells
    start past it), not normalized away."""
    svg = _doc(render("0xdeadbeefcafe6789"))  # body 'deadbeefcafe6789' = 64 bits
    labels = _labels(svg)
    top = min(labels, key=lambda t: float(t.get("y")))
    assert top.text == "hex, 64-bit, 0x"


def test_txt_fallback_label_is_text_with_byte_size():
    """v14: the UTF-8 -> b64url fallback projects to 'text, <bytes>-byte'
    (size over the ORIGINAL input bytes)."""
    svg = _doc(render("hello world"))  # 11 bytes
    labels = _labels(svg)
    top = min(labels, key=lambda t: float(t.get("y")))
    assert top.text == "text, 11-byte"


def test_base64_disproof_label_is_b64_with_size():
    """v14: when disproof picks base64 (input has '+' or '/'), the label is
    'b64, <bits>-bit'."""
    # 12 chars with a '+' triggers base64 (not base64url). 12*6//8*8 = 72 bits.
    svg = _doc(render("ABCD+/EFGHIJ"))
    labels = _labels(svg)
    top = min(labels, key=lambda t: float(t.get("y")))
    assert top.text == "b64, 72-bit"


def test_base64url_disproof_label_is_b64url_with_size():
    """v14: when disproof picks base64url (input has '-' or '_'), the label is
    'b64url, <bits>-bit'."""
    # 12 chars with a '-' triggers base64url. 12*6//8*8 = 72 bits.
    svg = _doc(render("ABCD-_EFGHIJ"))
    labels = _labels(svg)
    top = min(labels, key=lambda t: float(t.get("y")))
    assert top.text == "b64url, 72-bit"


def test_ethereum_top_label_is_ticker_with_prefix():
    """v15: Ethereum projects to 'ETH, 0x' (a fixed-size address scheme omits
    SIZE, but the stripped '0x' front prefix is echoed as a trailing slot)."""
    svg = _doc(render("0x742d35cc6634c0532925a3b844bc454e4438f44e"))
    labels = _labels(svg)
    top = min(labels, key=lambda t: float(t.get("y")))
    assert top.text == "ETH, 0x"


def test_uuid_top_label_no_prefix():
    """v14: UUID projects to just 'UUID' (no size, no trailing ':')."""
    svg = _doc(render("550e8400-e29b-41d4-a716-446655440000"))
    labels = _labels(svg)
    top = min(labels, key=lambda t: float(t.get("y")))
    assert top.text == "UUID"


def test_bottom_label_only_present_with_suffix():
    """Inputs with no suffix get no bottom label."""
    # hex has no suffix
    svg = _doc(render("deadbeefcafe1234"))
    labels = _labels(svg)
    assert len(labels) == 1, f"expected only top label, got {len(labels)}"


def test_bitcoin_legacy_has_top_and_bottom_labels():
    """v15: Bitcoin legacy projects PRIMARY 'BTC' with the stripped '1' version
    prefix echoed ('BTC, 1'; legacy variant dropped, mainnet silent, fixed-size
    address omits SIZE) on top, and the verified base58check checksum
    '...<4-char>' on the bottom."""
    svg = _doc(render("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"))
    labels = _labels(svg)
    assert len(labels) == 2, f"expected 2 labels, got {len(labels)}"
    sorted_labels = sorted(labels, key=lambda t: float(t.get("y")))
    top, bottom = sorted_labels
    assert top.text == "BTC, 1", f"top: {top.text!r}"
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


def test_label_text_font_is_always_hex_equivalent_size():
    """Labels always use the hex-equivalent rendered font size
    (round(font_size_pt * 0.75) px at 96 dpi → 12px at 12pt), regardless
    of whether the cell text is full-size (e.g. base64) or shrunk
    (hex). This keeps labels visually consistent across inputs."""
    # Reference: a hex input — cell text IS hex-size, so labels match cells.
    hex_svg = _doc(render("0x742d35cc6634c0532925a3b844bc454e4438f44e"))
    hex_cells = [t for t in hex_svg.xpath('//*[local-name()="text"]')
                 if t.get("text-anchor") == "middle"]
    hex_cell_style = hex_cells[0].get("style")

    # Non-hex input (UUID is base16-ish but parsed as UUID with full cells,
    # so use a base58 example to ensure full-size cell text).
    nonhex_svg = _doc(render("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"))
    nonhex_labels = _labels(nonhex_svg)
    assert nonhex_labels
    for t in nonhex_labels:
        # Labels must still use the hex-equivalent style.
        assert t.get("style") == hex_cell_style, (
            f"label style {t.get('style')!r} != hex-equivalent style "
            f"{hex_cell_style!r}"
        )


def test_top_label_left_aligned_to_grid():
    """Top label starts at grid_rect.left."""
    svg = _doc(render("0x742d35cc6634c0532925a3b844bc454e4438f44e"))
    labels = _labels(svg)
    top = min(labels, key=lambda t: float(t.get("y")))
    # At 12pt with 7-token Ethereum, grid_rect.left = 28 (v6 bar_width=20;
    # +1 for the MARGIN quiet ring, issue #31).
    assert float(top.get("x")) == 28
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
    # v14: projects to 'base32, <bits>-bit' (24 chars * 5 // 8 * 8 = 120 bits).
    svg = _doc(render("ABCDEFGHIJKLMNOPQR234567"))
    labels = _labels(svg)
    top = min(labels, key=lambda t: float(t.get("y")))
    assert top.text == "base32, 120-bit"


def test_truncated_input_label_prefixed_with_loud_marker():
    """v4→v5: the quiet '^…$ ' prefix is replaced by a loud '+hash '
    marker rendered in bold dark-red, followed by the standard
    '<Type>: ...' label in #666. The marker is a bold-red <tspan> and the
    rest is its tail, inside one <text>; this test concatenates all text
    (itertext) to assert the joined label content. The byte count is
    conveyed by the type-label parenthetical (e.g. 'hex(200)')."""
    long_hex = "ab" * 100  # 200 hex chars = 800 bits ≫ 512
    svg = _doc(render(long_hex))
    # v4→v5: the loud marker has fill="#a00000" rather than #666666, so
    # the legacy `_labels` filter (only #666) misses it. Read the full
    # label-top group directly and concatenate in document order.
    top_g = svg.xpath('//*[local-name()="g" and @data-channel="label-top"]')
    assert top_g, "missing label-top group"
    joined = "".join(top_g[0].itertext())
    # v14: the projected label for a bare 800-bit hex is 'hex, 800-bit'.
    assert "+hash hex, 800-bit" in joined, f"got: {joined!r}"


def test_non_truncated_input_label_has_no_loud_marker():
    """v4→v5: short inputs render no '+hash' marker, same as
    they previously rendered no '^…$' prefix."""
    svg = _doc(render("deadbeefcafe1234"))  # 16 hex chars = 64 bits
    labels = _labels(svg)
    for t in labels:
        if t.text:
            assert not t.text.startswith("+hash"), f"got: {t.text!r}"
            assert not t.text.startswith("^…$"), f"got: {t.text!r}"


def test_canvas_height_grows_with_top_label_only():
    """Hex input → top label, no bottom label. v6: the label band abuts the
    grid (GM only on the border side), so the top label adds just
    nucleus_height (= 20 at 12pt) over the no-label baseline."""
    svg = _doc(render("deadbeef"))
    # deadbeef → 2 tokens → 2x2 grid; no-label inner_h = 92.
    # With top label only: 92 + 20 = 112; + 2·MARGIN quiet ring = 114 (#31).
    assert float(svg.get("height")) == 114


def test_canvas_height_grows_with_both_labels():
    """Input with both prefix and suffix → top + bottom labels.
    v6: each band abuts the grid, so canvas grows by 2·nucleus_height = 40."""
    svg = _doc(render("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"))
    # Bitcoin Legacy: 34 chars - 1 prefix - 4 suffix = 29-char body →
    # 8 base58 tokens. choose_grid(8, 1.0) → 3x3 (v4 cell AR 3:2 means
    # 2x4 = 0.75 is below 1.0; 3x3 = 1.5 is the closest from above).
    # No labels: inner_h = 1+5+(3·40)+5+1 = 132. With both labels:
    # 132 + 40 = 172; + 2·MARGIN quiet ring = 174 (issue #31).
    assert float(svg.get("height")) == 174
