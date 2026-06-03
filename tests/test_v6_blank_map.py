"""
v6 blank-cell marker: every blank cell carries a black-outlined rounded
rectangle coincident with the nucleus rect. The FIRST blank cell (lowest
cell index) additionally becomes a "map" — a miniature scale model of the
grid, filled (white, or gold on a white-background entviz), with a red dot
at the maxftok cell's grid position and a blue dot at the minftok cell's.

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


def test_non_map_blanks_have_no_dots():
    """Only the map cell carries the red/blue dots; other blanks are just
    the outline rect (no circles)."""
    svg = _doc(render("0123456789abcdef" * 16))  # large input → several blanks
    maps = {int(g.get("data-cell-index")) for g in _map_group(svg)}
    for g in _blank_groups(svg):
        if int(g.get("data-cell-index")) in maps:
            continue
        assert _circles(g) == [], "non-map blank should have no circles"


# ---- Map dots: colors, positions, fill ----------------------------------


def test_map_has_one_red_and_one_blue_dot():
    svg = _doc(render(FIXTURE))
    g = _map_group(svg)[0]
    fills = [c.get("fill") for c in _circles(g)]
    assert fills.count(RED) == 1
    assert fills.count(BLUE) == 1


def test_dot_radius_is_fixed_regardless_of_grid():
    """The red/blue dots have a fixed radius (nucleus_height / 8 + font_size_px
    / 16 = 3.5 at 12pt), independent of grid dimensions — so dot size is
    consistent across entvizes rather than shrinking on denser grids."""
    # Two inputs with different grids (and thus different sub-cell sizes):
    # a small 2x3-ish grid vs a dense large-input grid.
    for inp in [FIXTURE, "deadbeef", "0123456789abcdef" * 16]:
        svg = _doc(render(inp))
        maps = _map_group(svg)
        if not maps:
            continue
        for c in _circles(maps[0]):
            if c.get("fill") in (RED, BLUE):
                assert float(c.get("r")) == 3.5, (
                    f"{inp!r}: dot r={c.get('r')} (expected fixed 3.5)"
                )


def test_map_fill_contrasts_with_entviz_background():
    """Map rect fill = gold when the entviz background is white, else white."""
    saw_white_bg = saw_nonwhite_bg = False
    for n in range(40):
        svg = _doc(render(f"deadbeef{n:02d}" * 3))
        maps = _map_group(svg)
        if not maps:
            continue
        cols = int(svg.get("data-cols"))
        rows = int(svg.get("data-rows"))
        # The entviz background is the rect filling grid_rect (top-left 27,26).
        bg = None
        bg_candidates = {WHITE, GOLD, "#ff3f2f", "#2f3fbf"}
        for r in svg.xpath('//*[local-name()="rect"]'):
            if (float(r.get("x", -1)) == 27 and float(r.get("y", -1)) == 26
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


def test_red_dot_at_maxftok_blue_dot_at_minftok():
    """The red dot sits in the sub-cell matching the maxftok cell's
    (row, col); the blue dot matches the minftok cell's."""
    svg = _doc(render(FIXTURE))
    grid, min_cell, max_cell = _recompute_min_max_cells(FIXTURE)
    assert min_cell != max_cell, "fixture should have distinct min/max cells"

    g = _map_group(svg)[0]
    rect = _children(g, "rect")[0]
    rx0, ry0 = float(rect.get("x")), float(rect.get("y"))
    sub_w = 48 / grid.cols
    sub_h = 20 / grid.rows

    def sub_of(circle):
        cx, cy = float(circle.get("cx")), float(circle.get("cy"))
        return (int((cy - ry0) / sub_h), int((cx - rx0) / sub_w))  # (row, col)

    red = next(c for c in _circles(g) if c.get("fill") == RED)
    blue = next(c for c in _circles(g) if c.get("fill") == BLUE)
    assert sub_of(red) == (max_cell // grid.cols, max_cell % grid.cols)
    assert sub_of(blue) == (min_cell // grid.cols, min_cell % grid.cols)
