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
    """Plain hex input shows 'hex(N):' where N is the length of the core.
    Use chars including 6/7/8/9 so the input doesn't also match the EOS
    account-name regex (which is just [a-z1-5.])."""
    svg = _doc(render("6789abcd6789abcd"))
    labels = _labels(svg)
    assert labels, "no label text found"
    top = min(labels, key=lambda t: float(t.get("y")))
    assert top.text == "hex(16):", f"unexpected top label: {top.text!r}"


def test_hex_with_0x_prefix_shows_count_and_prefix():
    """For '0xdeadbeef': core='deadbeef' (8 chars), prefix='0x'.
    Label = 'hex(8): 0x...'."""
    svg = _doc(render("0xdeadbeefcafe6789"))
    labels = _labels(svg)
    top = min(labels, key=lambda t: float(t.get("y")))
    # 0x + 16 hex chars body = 'deadbeefcafe6789' (16 chars).
    assert top.text == "hex(16): 0x..."


def test_txt_fallback_label_includes_input_byte_count():
    """For UTF-8 → b64url fallback: 'txt(N)->b64url:' where N is the
    length of the original input text (not the re-encoded core)."""
    svg = _doc(render("hello world"))  # 11 chars (includes the space)
    labels = _labels(svg)
    top = min(labels, key=lambda t: float(t.get("y")))
    assert top.text == "txt(11)->b64url:"


def test_base64_disproof_label_renamed_to_b64_with_count():
    """When disproof picks base64 (input has '+' or '/'), label is
    'b64(N):' where N is the char count of the core."""
    # 12 chars with a '+' triggers base64 (not base64url).
    svg = _doc(render("ABCD+/EFGHIJ"))
    labels = _labels(svg)
    top = min(labels, key=lambda t: float(t.get("y")))
    assert top.text == "b64(12):"


def test_base64url_disproof_label_renamed_to_b64url_with_count():
    """When disproof picks base64url (input has '-' or '_'), label is
    'b64url(N):'."""
    # 12 chars with a '-' triggers base64url.
    svg = _doc(render("ABCD-_EFGHIJ"))
    labels = _labels(svg)
    top = min(labels, key=lambda t: float(t.get("y")))
    assert top.text == "b64url(12):"


def test_ethereum_top_label_includes_0x_prefix_and_ellipsis():
    """For Ethereum: 'ETH: 0x...' (ticker abbreviation)."""
    svg = _doc(render("0x742d35cc6634c0532925a3b844bc454e4438f44e"))
    labels = _labels(svg)
    top = min(labels, key=lambda t: float(t.get("y")))
    assert top.text == "ETH: 0x..."


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
    Top: 'BTC legacy: 1...'  Bottom: '...<4-char-base58-checksum>'."""
    svg = _doc(render("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"))
    labels = _labels(svg)
    assert len(labels) == 2, f"expected 2 labels, got {len(labels)}"
    sorted_labels = sorted(labels, key=lambda t: float(t.get("y")))
    top, bottom = sorted_labels
    assert top.text.startswith("BTC legacy: 1"), f"top: {top.text!r}"
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
    # At 12pt with 7-token Ethereum, grid_rect.left = 27 (v6 bar_width=20).
    assert float(top.get("x")) == 27
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


def test_truncated_input_label_prefixed_with_loud_marker():
    """v4→v5: the quiet '^…$ ' prefix is replaced by a loud 'fingerprint of '
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
    assert "fingerprint of hex(200):" in joined, f"got: {joined!r}"


def test_non_truncated_input_label_has_no_loud_marker():
    """v4→v5: short inputs render no 'fingerprint of' marker, same as
    they previously rendered no '^…$' prefix."""
    svg = _doc(render("deadbeefcafe1234"))  # 16 hex chars = 64 bits
    labels = _labels(svg)
    for t in labels:
        if t.text:
            assert not t.text.startswith("fingerprint of"), f"got: {t.text!r}"
            assert not t.text.startswith("^…$"), f"got: {t.text!r}"


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
    # 8 base58 tokens. choose_grid(8, 1.0) → 3x3 (v4 cell AR 3:2 means
    # 2x4 = 0.75 is below 1.0; 3x3 = 1.5 is the closest from above).
    # No labels: bounding_h = 1+5+(3·40)+5+1 = 132. With both labels:
    # 132 + 50 = 182.
    assert float(svg.get("height")) == 182
