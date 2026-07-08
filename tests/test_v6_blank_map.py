"""
v6 blank-cell marker: every blank cell carries a black-outlined rounded
rectangle coincident with the nucleus rect. The FIRST blank cell (lowest
cell index) additionally becomes a "map" — a miniature scale model of the
grid, filled (white, or gold on a white-background entviz), with a red PLUS
at the maxftok cell's grid position and a blue DOT at the minftok cell's.

v8 (PSY-F1 + SPEC-F2): the markers differ in SHAPE — minftok = blue dot
(<circle>), maxftok = red plus (<path>) — so the max/min semantic survives
total colour blindness (where red and blue collapse to near-equal grays), not
just colour. Each marker carries its cell's literal "row,col" in
data-blank-map-min / data-blank-map-max, so a checker reads the position from
the named attribute rather than reverse-engineering it from pixel geometry.

This replaces v5's white-disc + clock-hands marker. Crucially it uses no
`mix-blend-mode`, so it renders identically in browsers and non-browser SVG
rasterizers (closing adversarial finding F-A6 for this channel).
"""
import base64

from lxml import etree

from entviz.pipeline import render
from entviz.layout import choose_grid, assign_cell_indices
from entviz.entropy import parse, tokenize_entropy, BASE64URL
from entviz.fingerprint import (
    compute_fingerprint, tokenize_fingerprint, get_median_ftok,
)

# Fixture: long-ish text → base64url fallback → ~19 tokens → 4x5 grid with a
# single blank (the map cell), and distinct min/max ftok cells.
FIXTURE = "Lorem ipsum dolor sit amet, consectetur adipiscing elit."

RED = "#d62828"
BLUE = "#1d4ed8"
GOLD = "#e7be00"
WHITE = "#ffffff"

# v10: the map blank's fill/markers are hybrid — fingerprint-coloured (markers
# recoloured to luminance contrast) when it is the SOLE blank, but the v9
# white/gold anchor + red/blue markers when there are siblings. The sole-blank
# hybrid is covered in test_v10_casual_avalanche.py; the tests below that assert
# the anchor + red/blue behaviour use a MULTI-blank input. 128 hex (512 bit,
# non-truncated) → 22 tokens → 24-cell grid → 2 blanks.
MULTI = "0123456789abcdef" * 8


def _doc(svg_str):
    return etree.fromstring(svg_str.encode())


def _cell_groups(svg):
    return svg.xpath('//*[local-name()="g"][@data-cell-index]')


def _blank_groups(svg):
    return [g for g in _cell_groups(svg) if g.get("data-cell-blank") == "true"]


def _children(g, tag):
    return [c for c in g if etree.QName(c).localname == tag]


def _circles(g):
    return _children(g, "circle")


def _paths(g):
    return _children(g, "path")


# ---- F-A6: no mix-blend-mode anywhere -----------------------------------


def test_no_mix_blend_mode_in_output():
    """The v5 long hand used mix-blend-mode (invisible outside browsers).
    v6 must not emit it anywhere."""
    for inp in [FIXTURE, "deadbeef", "0123456789abcdef" * 16, "ab"]:
        assert "mix-blend-mode" not in render(inp)


# ---- Outlined rounded rect on every blank -------------------------------


def test_every_blank_cell_has_rounded_outline_rect():
    svg = _doc(render(FIXTURE))
    blanks = _blank_groups(svg)
    assert blanks, "fixture should produce at least one blank cell"
    for g in blanks:
        rects = _children(g, "rect")
        assert len(rects) == 1, "each blank cell has exactly one rect"
        r = rects[0]
        assert float(r.get("width")) == 48 and float(r.get("height")) == 20
        assert r.get("stroke") == "#000000"
        assert r.get("stroke-width") == "1"
        assert float(r.get("rx")) == 10  # nucleus_height / 2 at 12pt


def test_corner_radius_scales_with_font_size():
    # rx = nucleus_height / 2 = (1.25 * pt*96/72) / 2. 12pt → 10; 24pt → 20.
    svg12 = _doc(render(FIXTURE, font_size_pt=12))
    svg24 = _doc(render(FIXTURE, font_size_pt=24))
    rx12 = float(_children(_blank_groups(svg12)[0], "rect")[0].get("rx"))
    rx24 = float(_children(_blank_groups(svg24)[0], "rect")[0].get("rx"))
    assert rx12 == 10
    assert rx24 == 20


# ---- Exactly one map cell, the first blank ------------------------------


def _map_group(svg):
    maps = [g for g in _cell_groups(svg) if g.get("data-cell-blank-map") == "true"]
    return maps


def test_exactly_one_map_cell_is_the_first_blank():
    svg = _doc(render(FIXTURE))
    maps = _map_group(svg)
    assert len(maps) == 1
    blank_idx = {int(g.get("data-cell-index")) for g in _blank_groups(svg)}
    map_idx = int(maps[0].get("data-cell-index"))
    assert map_idx == min(blank_idx)


def test_non_map_blanks_have_no_markers():
    """Only the map cell carries the min/max markers; other blanks are just
    the outline rect (no dot circle, no plus path)."""
    svg = _doc(render("0123456789abcdef" * 16))  # large input → several blanks
    maps = {int(g.get("data-cell-index")) for g in _map_group(svg)}
    for g in _blank_groups(svg):
        if int(g.get("data-cell-index")) in maps:
            continue
        assert _circles(g) == [], "non-map blank should have no dot"
        assert _paths(g) == [], "non-map blank should have no plus"


# ---- Map dots: colors, positions, fill ----------------------------------


def test_map_has_blue_dot_and_red_plus():
    """v8 (PSY-F1): minftok = exactly one blue <circle> (dot); maxftok = exactly
    one red <path> (plus). Shape, not just colour, distinguishes them.
    Uses a multi-blank input so the map blank is the v9 white/gold anchor with
    red/blue markers (the sole-blank hybrid is in test_v10_casual_avalanche)."""
    svg = _doc(render(MULTI))
    g = _map_group(svg)[0]
    dots = [c for c in _circles(g) if c.get("fill") == BLUE]
    plusses = [p for p in _paths(g) if p.get("stroke") == RED]
    assert len(dots) == 1, "exactly one blue dot (minftok)"
    assert len(plusses) == 1, "exactly one red plus (maxftok)"
    # The blue dot carries data-blank-map-min; the red plus carries -max.
    assert dots[0].get("data-blank-map-min") is not None
    assert plusses[0].get("data-blank-map-max") is not None
    # The plus path is a crossed pair of strokes through its centre.
    d = plusses[0].get("d")
    assert d.count("M") == 2 and "H" in d and "V" in d


def test_dot_radius_is_fixed_regardless_of_grid():
    """The blue minftok dot has a fixed radius (nucleus_height / 8 +
    font_size_px / 16 = 3.5 at 12pt), independent of grid dimensions — so
    marker size is consistent across entvizes rather than shrinking on denser
    grids."""
    for inp in [FIXTURE, "deadbeef", "0123456789abcdef" * 16]:
        svg = _doc(render(inp))
        maps = _map_group(svg)
        if not maps:
            continue
        for c in _circles(maps[0]):
            if c.get("fill") == BLUE:
                assert float(c.get("r")) == 3.5, (
                    f"{inp!r}: dot r={c.get('r')} (expected fixed 3.5)"
                )


def test_map_fill_contrasts_with_entviz_background():
    """Map rect fill = gold when the entviz background is white, else white."""
    saw_white_bg = saw_nonwhite_bg = False
    for n in range(40):
        # v10: use MULTI-blank inputs (128 hex → 22 tokens → 2 blanks) so the
        # map blank is the white/gold anchor; vary the leading bytes to span both
        # white and non-white backgrounds. (A sole-blank map is fingerprint-filled
        # in v10, which test_v10_casual_avalanche covers.)
        svg = _doc(render((f"{n:08x}" + "0123456789abcdef" * 8)[:128]))
        maps = _map_group(svg)
        if not maps:
            continue
        cols = int(svg.get("data-cols"))
        rows = int(svg.get("data-rows"))
        # The entviz background is the rect filling grid_rect (top-left 28,27
        # after the MARGIN quiet ring, issue #31).
        bg = None
        bg_candidates = {WHITE, GOLD, "#ff3f2f", "#2f3fbf"}
        for r in svg.xpath('//*[local-name()="rect"]'):
            if (float(r.get("x", -1)) == 28 and float(r.get("y", -1)) == 27
                    and float(r.get("width", 0)) == cols * 60
                    and r.get("fill") in bg_candidates):
                bg = r.get("fill")
                break
        assert bg is not None
        map_rect = _children(maps[0], "rect")[0]
        expected = GOLD if bg == WHITE else WHITE
        assert map_rect.get("fill") == expected, (
            f"bg={bg} → map fill should be {expected}, got {map_rect.get('fill')}"
        )
        saw_white_bg |= bg == WHITE
        saw_nonwhite_bg |= bg != WHITE
    assert saw_white_bg and saw_nonwhite_bg, "fixtures didn't cover both bg cases"


def _recompute_min_max_cells(input_):
    parsed = parse(input_)
    core = parsed.core if parsed else base64.urlsafe_b64encode(
        input_.encode()).decode().rstrip('=')
    alphabet = parsed.alphabet if parsed else BASE64URL
    tokens, _ = tokenize_entropy(core, alphabet)
    used_ftoks = tokenize_fingerprint(compute_fingerprint(core))[:len(tokens)]
    grid = choose_grid(len(tokens), 1.0)
    median = get_median_ftok(used_ftoks)
    ci = assign_cell_indices(tokens, grid, median_token=median, sort_keys=used_ftoks)
    pairs = [(used_ftoks[t.index], ci[t.index]) for t in tokens]
    max_cell = max(pairs, key=lambda fc: (fc[0].quant, fc[1]))[1]
    min_cell = min(pairs, key=lambda fc: (fc[0].quant, -fc[1]))[1]
    return grid, min_cell, max_cell


def test_markers_carry_rowcol_attrs_at_minftok_and_maxftok():
    """SPEC-F2: data-blank-map-min/max carry the cell's literal "row,col", so
    the position is recoverable from the named attribute (not pixel geometry).
    PSY-F1: the blue dot marks minftok, the red plus marks maxftok."""
    svg = _doc(render(MULTI))
    grid, min_cell, max_cell = _recompute_min_max_cells(MULTI)
    assert min_cell != max_cell, "fixture should have distinct min/max cells"

    g = _map_group(svg)[0]
    blue = next(c for c in _circles(g) if c.get("fill") == BLUE)
    red = next(p for p in _paths(g) if p.get("stroke") == RED)

    # The attribute carries the literal row,col.
    assert blue.get("data-blank-map-min") == \
        f"{min_cell // grid.cols},{min_cell % grid.cols}"
    assert red.get("data-blank-map-max") == \
        f"{max_cell // grid.cols},{max_cell % grid.cols}"

    # And the rendered geometry still agrees: the blue dot's centre lands in the
    # minftok sub-cell of the scale-model rect.
    rect = _children(g, "rect")[0]
    rx0, ry0 = float(rect.get("x")), float(rect.get("y"))
    sub_w, sub_h = 48 / grid.cols, 20 / grid.rows
    bx, by = float(blue.get("cx")), float(blue.get("cy"))
    assert (int((by - ry0) / sub_h), int((bx - rx0) / sub_w)) == \
        (min_cell // grid.cols, min_cell % grid.cols)
