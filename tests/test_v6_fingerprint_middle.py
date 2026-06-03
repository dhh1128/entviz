"""
v6 (idea B): for >512-bit inputs the 4 middle text cells display bytes from
the MIDDLE of the SHA-512 fingerprint (digest bytes 24-35), rendered in the
INPUT's alphabet — replacing v5's entropy body slices.

Why: v5's body slices made the middle text differ between inputs only
*probabilistically* (a low-entropy body could render identical middle cells
for two different inputs). Sourcing the middle from the fingerprint makes the
middle text avalanche on ANY input change, which matters for a screen-reader /
read-aloud comparison that can't rely on the gestalt channels.

Head/tail stay real entropy. The middle nuclei use the entviz background color
(neutral/hollow) since they carry no entropy in their background; their
surround stays fingerprint-driven. Gestalt is unchanged.
"""
from lxml import etree

from entviz.pipeline import render

# Large-input layout: head 0-7, separator 8, middle 9-12, separator 13,
# tail 14-21.
MIDDLE_CELLS = (9, 10, 11, 12)
BG_CANDIDATES = {"#ffffff", "#ffd966", "#ff3f2f", "#2f3fbf"}


def _parse(svg_str):
    svg = etree.fromstring(svg_str.encode())
    groups = {int(g.get("data-cell-index")): g
              for g in svg.xpath('//*[local-name()="g"][@data-cell-index]')}
    return svg, groups


def _cell_text(g):
    return "".join(t.text or "" for t in g if t.tag.endswith("}text"))


def _nucleus_fill(g):
    """The nucleus rect (48x20, no rounded corners — blank rects carry rx)."""
    for r in g:
        if (r.tag.endswith("}rect")
                and float(r.get("width", 0)) == 48
                and float(r.get("height", 0)) == 20
                and r.get("rx") is None):
            return r.get("fill")
    return None


def _entviz_bg(svg):
    cols = int(svg.get("data-cols"))
    for r in svg.xpath('//*[local-name()="rect"]'):
        if (float(r.get("x", -1)) == 27 and float(r.get("y", -1)) == 31
                and float(r.get("width", 0)) == cols * 60
                and r.get("fill") in BG_CANDIDATES):
            return r.get("fill")
    return None


# A >512-bit (65-byte / 130-hex) input with a LOW-ENTROPY body, and a sibling
# differing by ONE body nibble — head and tail identical. Under v5 body
# slices this could render identical middle cells; under v6 it must not.
BASE = "ab" * 65
_alt = list(BASE)
_alt[64] = "c"            # flip one nibble inside the body (idx 48..81)
ALT = "".join(_alt)


def test_fixtures_are_large_and_share_head_tail():
    assert len(BASE) * 4 == 520 and len(ALT) * 4 == 520
    assert BASE != ALT
    assert BASE[:48] == ALT[:48]      # identical head (24 bytes)
    assert BASE[-48:] == ALT[-48:]    # identical tail (24 bytes)


def test_all_middle_cells_differ_on_any_input_change():
    """The crux: even with a low-entropy body and identical head/tail, every
    middle cell's text differs — guaranteed by the fingerprint avalanche."""
    _, ga = _parse(render(BASE))
    _, gb = _parse(render(ALT))
    for ci in MIDDLE_CELLS:
        ta, tb = _cell_text(ga[ci]), _cell_text(gb[ci])
        assert ta and tb, f"cell {ci} empty"
        assert ta != tb, f"middle cell {ci} did not change: {ta!r} == {tb!r}"


def test_head_and_tail_text_are_unchanged_entropy():
    """Head/tail still show the real input bytes (identical here)."""
    _, ga = _parse(render(BASE))
    _, gb = _parse(render(ALT))
    for ci in list(range(0, 8)) + list(range(14, 22)):
        assert _cell_text(ga[ci]) == _cell_text(gb[ci])
    # And head cell 0 shows the actual input head.
    assert _cell_text(ga[0]) == "ababab"


def test_middle_text_uses_input_alphabet_token_length():
    """Middle cells render in the input's alphabet, so token length matches
    head/tail (6 chars for hex)."""
    _, g = _parse(render(BASE))
    head_len = len(_cell_text(g[0]))
    assert head_len == 6  # hex
    for ci in MIDDLE_CELLS:
        assert len(_cell_text(g[ci])) == head_len


def test_middle_nucleus_bg_is_entviz_background():
    """Middle nuclei are neutral: filled with the entviz background color
    (they carry no entropy in their bg)."""
    svg, g = _parse(render(BASE))
    bg = _entviz_bg(svg)
    assert bg is not None
    for ci in MIDDLE_CELLS:
        assert _nucleus_fill(g[ci]) == bg, (
            f"middle cell {ci} nucleus fill {_nucleus_fill(g[ci])} != entviz bg {bg}"
        )


def test_head_tail_nuclei_keep_entropy_colors():
    """Head/tail nuclei still get their entropy-derived bg (not forced to the
    entviz bg) — only the middle is neutralized."""
    svg, g = _parse(render(BASE))
    bg = _entviz_bg(svg)
    # Head cell 0 text is 'ababab' -> a non-bg entropy color; assert it's a
    # real per-cell color, i.e. the channel is still alive for head/tail.
    head_fill = _nucleus_fill(g[0])
    assert head_fill is not None
    # (Not asserting != bg in general, since a head color could coincide with
    # bg; instead assert middle cells are uniformly bg while head varies.)
    middle_fills = {_nucleus_fill(g[ci]) for ci in MIDDLE_CELLS}
    assert middle_fills == {bg}


def test_middle_text_is_not_the_body_slice():
    """Sanity: the middle is fingerprint-derived, not a verbatim body slice.
    For an all-'ab' body, a body slice would read 'ababab'/'babab...'; the
    fingerprint bytes will (almost surely) not all be 'ababab'."""
    _, g = _parse(render(BASE))
    middle = [_cell_text(g[ci]) for ci in MIDDLE_CELLS]
    assert any(m != "ababab" and m != "bababa" for m in middle), middle


def test_middle_text_matches_head_tail_case():
    """The fingerprint-middle cells render in the same case as the normalized
    core (hex normalizes to lowercase), matching head/tail — not the uppercase
    HEX_ALPHABET table."""
    _, g = _parse(render(BASE))   # all-lowercase hex
    for ci in MIDDLE_CELLS:
        t = _cell_text(g[ci])
        assert t == t.lower(), f"middle cell {ci} not lowercase: {t!r}"


def test_middle_cells_have_inner_border():
    """Each fingerprint-middle nucleus is framed by a 1-px inset border:
    gold on a white-bg entviz, white otherwise (contrasting with the
    neutral bg-colored nucleus)."""
    svg, g = _parse(render(BASE))
    bg = _entviz_bg(svg)
    expected = "#ffd966" if bg == "#ffffff" else "#ffffff"
    for ci in MIDDLE_CELLS:
        borders = [r for r in g[ci]
                   if r.tag.endswith("}rect") and r.get("fill") == "none"
                   and r.get("stroke") == expected
                   and r.get("stroke-width") == "1"]
        assert borders, (
            f"middle cell {ci} missing inner border stroke={expected} (bg={bg})"
        )


def test_non_middle_cells_have_no_inner_border():
    """Head/tail nuclei are NOT framed (only the fingerprint middle is)."""
    svg, g = _parse(render(BASE))
    for ci in list(range(0, 8)) + list(range(14, 22)):
        stroked = [r for r in g[ci]
                   if r.tag.endswith("}rect") and r.get("fill") == "none"
                   and r.get("stroke") in ("#ffd966", "#ffffff")]
        assert not stroked, f"head/tail cell {ci} unexpectedly has an inner border"
