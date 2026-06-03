"""
v6 long-input middle (adversarial-2026-06-02 F1 + F2 fix).

For >512-bit inputs the 4 middle tokens render a SECOND, domain-separated
SHA-512 digest of the whole normalized core, as HEX:

    second = SHA-512(b"entviz/fingerprint-middle/v6\\0" || core)
    middle[i] = second[3i : 3i+3].hex()        # 6 lowercase hex chars = 24 bits

This replaces v6.0's "primary-digest bytes 24-35 rendered in the input's
alphabet", which (F1) dropped 4 bits/cell on 5-bit alphabets and mod-aliased
on base58/base36 — so the avalanche was only probabilistic — and (F2) re-read
bytes that already drive the surround/color bar, so the middle was not
independent evidence. Hex over a separate digest fixes both: every cell carries
a full 24 injective bits for EVERY alphabet, and the middle is independent of
the primary fingerprint.

Head/tail stay real entropy; the middle nuclei use the entviz background color
(neutral) with a 1-px gold/white frame, and their surround stays
primary-fingerprint-driven. Blank placement uses the same median/quartile
shift as short inputs (no fixed separators); the middle cells are tagged
data-cell-fingerprint and identified in token reading order (indices 8..11).
"""
import hashlib
import re

from lxml import etree

from entviz.entropy import parse, _MIDDLE_DOMAIN_TAG
from entviz.pipeline import render

BG_CANDIDATES = {"#ffffff", "#e7be00", "#ff3f2f", "#2f3fbf"}
GOLD, WHITE = "#e7be00", "#ffffff"

# A >512-bit hex input and a sibling differing by ONE body nibble (head and
# tail identical), plus non-hex large inputs to prove the middle is hex
# regardless of the input alphabet.
BASE = "ab" * 65                      # hex, 130 chars / 520 bits
_alt = list(BASE); _alt[64] = "c"
ALT = "".join(_alt)
B32 = "ABCDEFGHIJKLMNOP" * 8          # base32 (5-bit), uppercase core
B32_ALT = "BBCDEFGHIJKLMNOP" * 8      # one char flipped
B64 = "aB-_" * 30                     # base64url (6-bit)


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
    return sorted(int(g.get("data-cell-index"))
                  for g in svg.xpath('//*[local-name()="g"][@data-cell-fingerprint="true"]'))


def _used_texts_in_order(svg, groups):
    return [_cell_text(groups[ci]) for ci in sorted(groups)
            if groups[ci].get("data-cell-blank") is None]


def _middle_in_order(raw):
    svg, g = _parse(render(raw))
    return _used_texts_in_order(svg, g)[8:12]


def _expected_middle(raw):
    core = parse(raw).core
    second = hashlib.sha512(_MIDDLE_DOMAIN_TAG + core.encode("utf-8")).digest()
    return [second[3 * i: 3 * i + 3].hex() for i in range(4)]


def _primary_middle_bytes(raw):
    core = parse(raw).core
    d = hashlib.sha512(core.encode("utf-8")).digest()
    return [d[24 + 3 * i: 27 + 3 * i].hex() for i in range(4)]


# --- fixtures are actually large / truncated ---

def test_fixtures_are_large_and_share_head_tail():
    assert len(BASE) * 4 == 520 and len(ALT) * 4 == 520
    assert BASE != ALT and BASE[:48] == ALT[:48] and BASE[-48:] == ALT[-48:]


def test_exactly_four_fingerprint_cells_at_token_positions_8_to_11():
    svg, groups = _parse(render(BASE))
    fp = _fp_indices(svg)
    assert len(fp) == 4
    used = [ci for ci in sorted(groups) if groups[ci].get("data-cell-blank") is None]
    assert [used.index(ci) for ci in fp] == [8, 9, 10, 11]


# --- F1: 24-bit injective hex, regardless of input alphabet ---

def test_middle_renders_domain_separated_second_digest():
    """Pins the exact algorithm: each middle cell is 6 hex chars of the
    domain-separated second SHA-512 of the whole core."""
    for raw in (BASE, B32, B64):
        assert _middle_in_order(raw) == _expected_middle(raw), raw


def test_middle_is_hex_regardless_of_input_alphabet():
    """base32 (5-bit) and base64url (6-bit) inputs still render a HEX middle —
    6 lowercase hex chars per cell — not their own alphabet."""
    hexcell = re.compile(r"^[0-9a-f]{6}$")
    for raw in (B32, B64):
        mid = _middle_in_order(raw)
        assert len(mid) == 4 and all(hexcell.match(t) for t in mid), (raw, mid)


def test_middle_is_lowercase_hex_even_for_uppercase_core():
    """B32's core is uppercase; the middle is still lowercase hex (it is the
    second digest, not a case-matched slice of the core)."""
    for t in _middle_in_order(B32):
        assert t == t.lower() and len(t) == 6, t


def test_five_bit_alphabet_middle_is_injective_and_avalanches():
    """The case v6.0 could fail: a 5-bit-alphabet input whose digest differs
    only in dropped low nibbles rendered identical middle cells. With 24-bit
    hex, one input-char change flips every middle cell."""
    a, b = _middle_in_order(B32), _middle_in_order(B32_ALT)
    assert all(x and x != y for x, y in zip(a, b)), (a, b)


def test_hex_input_middle_avalanches_on_one_nibble():
    a, b = _middle_in_order(BASE), _middle_in_order(ALT)
    assert all(x and x != y for x, y in zip(a, b)), (a, b)


# --- F2: independent of the primary fingerprint ---

def test_middle_is_independent_of_primary_digest():
    """Domain separation: the displayed middle is NOT the hex of the primary
    digest's bytes 24-35 (which feed the surround / color bar). The two
    digests differ, so the middle is independent evidence."""
    for raw in (BASE, B32, B64):
        assert _middle_in_order(raw) != _primary_middle_bytes(raw), raw


def test_middle_token_length_is_six_hex_chars():
    svg, g = _parse(render(BASE))
    used = _used_texts_in_order(svg, g)
    assert len(used[0]) == 6        # hex head token
    for t in used[8:12]:
        assert len(t) == 6


def test_head_and_tail_text_unchanged_entropy():
    sa, ga = _parse(render(BASE))
    sb, gb = _parse(render(ALT))
    a, b = _used_texts_in_order(sa, ga), _used_texts_in_order(sb, gb)
    assert a[:8] == b[:8] and a[12:] == b[12:]
    assert a[0] == "ababab"          # real input head


def test_fingerprint_text_is_not_a_body_slice():
    mid = _middle_in_order(BASE)
    assert any(m not in ("ababab", "bababa") for m in mid), mid


# --- presentation: neutral bg + framed, as before ---

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
