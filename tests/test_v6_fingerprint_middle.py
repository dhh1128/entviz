"""
v6: for >512-bit inputs the 4 middle tokens display bytes from the MIDDLE of
the SHA-512 fingerprint (digest bytes 24-35), rendered in the INPUT's alphabet
— replacing v5's entropy body slices, so the middle text avalanches on ANY
input change (matters for a screen-reader / read-aloud comparison that can't
rely on the gestalt channels).

Head/tail stay real entropy. The fingerprint nuclei use the entviz background
color (neutral) and a 1-px gold/white frame; their surround stays
fingerprint-driven. Blank placement uses the SAME median/quartile shift as
short inputs (no fixed separators), so the fingerprint cells no longer sit at
fixed cell indices — they're tagged data-cell-fingerprint and identified in
token reading order.
"""
from lxml import etree

from entviz.pipeline import render

BG_CANDIDATES = {"#ffffff", "#ffd966", "#ff3f2f", "#2f3fbf"}
GOLD, WHITE = "#ffd966", "#ffffff"


def _parse(svg_str):
    svg = etree.fromstring(svg_str.encode())
    groups = {int(g.get("data-cell-index")): g
              for g in svg.xpath('//*[local-name()="g"][@data-cell-index]')}
    return svg, groups


def _cell_text(g):
    return "".join(t.text or "" for t in g if t.tag.endswith("}text"))


def _nucleus_fill(g):
    for r in g:
        if (r.tag.endswith("}rect") and float(r.get("width", 0)) == 48
                and float(r.get("height", 0)) == 20 and r.get("rx") is None):
            return r.get("fill")
    return None


def _entviz_bg(svg):
    cols = int(svg.get("data-cols"))
    for r in svg.xpath('//*[local-name()="rect"]'):
        if (float(r.get("x", -1)) == 27 and float(r.get("y", -1)) == 26
                and float(r.get("width", 0)) == cols * 60
                and r.get("fill") in BG_CANDIDATES):
            return r.get("fill")
    return None


def _fp_indices(svg):
    """Cell indices of the fingerprint-middle cells (sorted = reading order)."""
    return sorted(int(g.get("data-cell-index"))
                  for g in svg.xpath('//*[local-name()="g"][@data-cell-fingerprint="true"]'))


def _used_texts_in_order(svg, groups):
    """Texts of the non-blank cells in reading order = tokens 0..19."""
    return [_cell_text(groups[ci]) for ci in sorted(groups)
            if groups[ci].get("data-cell-blank") is None]


# A >512-bit (65-byte / 130-hex) input with a LOW-ENTROPY body, and a sibling
# differing by ONE body nibble — head and tail identical. Under v5 body slices
# this could render identical middle cells; under v6 it must not.
BASE = "ab" * 65
_alt = list(BASE)
_alt[64] = "c"
ALT = "".join(_alt)


def test_fixtures_are_large_and_share_head_tail():
    assert len(BASE) * 4 == 520 and len(ALT) * 4 == 520
    assert BASE != ALT and BASE[:48] == ALT[:48] and BASE[-48:] == ALT[-48:]


def test_exactly_four_fingerprint_cells_at_token_positions_8_to_11():
    svg, groups = _parse(render(BASE))
    fp = _fp_indices(svg)
    assert len(fp) == 4
    # In reading order the used (non-blank) cells are tokens 0..19; the
    # fingerprint cells are tokens 8..11 → positions 8,9,10,11 of that list.
    used = [ci for ci in sorted(groups) if groups[ci].get("data-cell-blank") is None]
    assert [used.index(ci) for ci in fp] == [8, 9, 10, 11]


def test_all_fingerprint_cells_differ_on_any_input_change():
    """Even with a low-entropy body and identical head/tail, every
    fingerprint cell's text differs — guaranteed by the fingerprint avalanche.
    Compared in reading order, since blank shifts may place the cells at
    different absolute indices in the two entvizes."""
    sa, ga = _parse(render(BASE))
    sb, gb = _parse(render(ALT))
    mid_a = _used_texts_in_order(sa, ga)[8:12]
    mid_b = _used_texts_in_order(sb, gb)[8:12]
    assert all(a and a != b for a, b in zip(mid_a, mid_b)), (mid_a, mid_b)


def test_head_and_tail_text_unchanged_entropy():
    sa, ga = _parse(render(BASE))
    sb, gb = _parse(render(ALT))
    a, b = _used_texts_in_order(sa, ga), _used_texts_in_order(sb, gb)
    assert a[:8] == b[:8] and a[12:] == b[12:]   # head + tail identical
    assert a[0] == "ababab"                      # real input head


def test_fingerprint_text_uses_input_alphabet_token_length():
    svg, g = _parse(render(BASE))
    used = _used_texts_in_order(svg, g)
    assert len(used[0]) == 6  # hex head token
    for t in used[8:12]:
        assert len(t) == 6


def test_fingerprint_nucleus_bg_is_entviz_background():
    svg, g = _parse(render(BASE))
    bg = _entviz_bg(svg)
    assert bg is not None
    for ci in _fp_indices(svg):
        assert _nucleus_fill(g[ci]) == bg


def test_only_fingerprint_nuclei_are_neutralized():
    svg, g = _parse(render(BASE))
    bg = _entviz_bg(svg)
    assert {_nucleus_fill(g[ci]) for ci in _fp_indices(svg)} == {bg}


def test_fingerprint_text_is_not_a_body_slice():
    svg, g = _parse(render(BASE))
    mid = _used_texts_in_order(svg, g)[8:12]
    assert any(m not in ("ababab", "bababa") for m in mid), mid


def test_fingerprint_text_matches_core_case():
    svg, g = _parse(render(BASE))   # lowercase hex core
    for t in _used_texts_in_order(svg, g)[8:12]:
        assert t == t.lower(), t


def test_fingerprint_cells_have_inner_border():
    svg, g = _parse(render(BASE))
    expected = GOLD if _entviz_bg(svg) == WHITE else WHITE
    for ci in _fp_indices(svg):
        borders = [r for r in g[ci]
                   if r.tag.endswith("}rect") and r.get("fill") == "none"
                   and r.get("stroke") == expected and r.get("stroke-width") == "1"]
        assert borders, f"fingerprint cell {ci} missing inner border {expected}"


def test_non_fingerprint_cells_have_no_inner_border():
    svg, g = _parse(render(BASE))
    fp = set(_fp_indices(svg))
    for ci, grp in g.items():
        if ci in fp or grp.get("data-cell-blank") == "true":
            continue
        stroked = [r for r in grp
                   if r.tag.endswith("}rect") and r.get("fill") == "none"
                   and r.get("stroke") in (GOLD, WHITE)]
        assert not stroked, f"non-fingerprint cell {ci} has an inner border"
