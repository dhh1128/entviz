"""v10 casual-avalanche colour levers (spec.md "Casual avalanche (v10)").

Locks the three rendering changes:
  1. fingerprint-sourced surround edge colour on the top-left cell and the
     1st/2nd quartile cells (2 ftok-quant bits -> edge palette);
  2. hybrid fingerprint blank fill (colour the map blank iff it is the sole
     blank, with markers recoloured to luminance contrast; otherwise white/gold
     anchor + coloured siblings);
  3. nucleus colours unchanged.
"""
from lxml import etree

from entviz.colors import (
    select_visual_style, closest_palette_color, get_nucleus_colors,
)
from entviz.entropy import parse, tokenize_entropy
from entviz.fingerprint import (
    compute_fingerprint, tokenize_fingerprint, get_median_ftok,
    get_quartile_ftoks,
)
from entviz.layout import Cell, Point, Size
from entviz.pipeline import render
from entviz.renderer import Renderer

SVG = "{http://www.w3.org/2000/svg}"

UUID_A = "550e8400-e29b-41d4-a716-446655440000"


def _model(inp):
    """Re-derive the pieces the levers depend on, the same way the pipeline
    does (UUID has no blanks, so token index == cell index)."""
    p = parse(inp)
    toks, _ = tokenize_entropy(p.core, p.alphabet)
    used = tokenize_fingerprint(compute_fingerprint(p.core))[:len(toks)]
    style = select_visual_style(get_median_ftok(used))
    quart = get_quartile_ftoks(used)
    return toks, used, style, quart


def _root(inp):
    return etree.fromstring(render(inp).encode())


def _cell_group(root, idx):
    return next(g for g in root.iter(SVG + "g")
               if g.get("data-cell-index") == str(idx))


def _edge_fills_of_cell(root, idx):
    """The set of fill colours on cell `idx`'s surround boxes, located by
    geometry (edges live in a flat layer, not the cell group)."""
    cg = _cell_group(root, idx)
    nuc = next(r for r in cg.findall(SVG + "rect")
               if r.get("rx") is None and r.get("fill", "").startswith("#"))
    nl, nt = float(nuc.get("x")), float(nuc.get("y"))
    nw, nh = float(nuc.get("width")), float(nuc.get("height"))
    bw, bh = nw / 8, nh / 2
    cl, ct, cw, ch = nl - bw, nt - bh, nw + 2 * bw, nh + 2 * bh
    fills = set()
    for r in root.iter(SVG + "rect"):
        if abs(float(r.get("width")) - bw) > 0.01:
            continue
        cx, cy = float(r.get("x")) + bw / 2, float(r.get("y")) + bh / 2
        if cl <= cx <= cl + cw and ct <= cy <= ct + ch:
            fills.add(r.get("fill"))
    return fills


def _dummy_cell():
    return Cell(Point(0, 0), Size(60, 40))   # box dims derived (6 × 10)


# --- Change 1: fingerprint edge colour ---------------------------------------

def test_render_edges_override_forces_fill():
    style = select_visual_style(get_median_ftok(
        tokenize_fingerprint(compute_fingerprint("x"))[:1]))
    r = Renderer(style, grid=None)

    class F:  # all 24 bits set so every box renders
        quant = (1 << 24) - 1
    # render_edges adds plain `rect` tags (the SVG namespace is only applied
    # when the whole tree is serialized), so query without a namespace here.
    g = etree.Element("g")
    r.render_edges(g, F(), _dummy_cell(), nucleus_bg="#840e55",
                   edge_override="#2f3fbf")
    fills = {rect.get("fill") for rect in g.findall("rect")}
    assert fills == {"#2f3fbf"}, "override must force the edge colour"
    # without override, falls back to nearest palette to the nucleus
    g2 = etree.Element("g")
    r.render_edges(g2, F(), _dummy_cell(), nucleus_bg="#840e55")
    fills2 = {rect.get("fill") for rect in g2.findall("rect")}
    assert fills2 == {closest_palette_color("#840e55", style.edge_colors)}


def test_topleft_cell_edge_is_fingerprint_sourced():
    toks, used, style, _ = _model(UUID_A)
    expected = style.edge_colors[used[0].quant & 0b11]
    assert _edge_fills_of_cell(_root(UUID_A), 0) == {expected}


def test_quartile_1_and_2_cells_edge_is_fingerprint_sourced():
    toks, used, style, quart = _model(UUID_A)
    root = _root(UUID_A)
    for q in quart[:2]:
        if q is None:
            continue
        ci = q.index  # UUID: token index == cell index
        assert _edge_fills_of_cell(root, ci) == {style.edge_colors[q.quant & 0b11]}


def test_ordinary_cell_keeps_nearest_palette_edge():
    toks, used, style, quart = _model(UUID_A)
    fp_cells = {0} | {q.index for q in quart[:2] if q is not None}
    ordinary = next(i for i in range(len(toks)) if i not in fp_cells)
    nucleus_bg, _ = get_nucleus_colors(toks[ordinary].quant)
    expected = closest_palette_color(nucleus_bg, style.edge_colors)
    assert _edge_fills_of_cell(_root(UUID_A), ordinary) == {expected}


def test_nucleus_colours_unchanged():
    # Change 1 must not touch the nucleus fill (still entropy-derived).
    toks, used, style, _ = _model(UUID_A)
    cg = _cell_group(_root(UUID_A), 0)
    nuc = next(r for r in cg.findall(SVG + "rect")
               if r.get("rx") is None and r.get("fill", "").startswith("#"))
    expected_bg, _ = get_nucleus_colors(toks[0].quant)
    assert nuc.get("fill") == expected_bg


# --- Change 2: hybrid blank fill ---------------------------------------------

SOLE_BLANK_INPUT = "0011223344556677"   # 16 hex -> 3 tokens -> 1 (map) blank
MULTI_BLANK_INPUT = "ab" * 200          # >512 bit -> 4 blanks


def _blanks(root):
    return [g for g in root.iter(SVG + "g") if g.get("data-cell-blank") == "true"]


def _blank_rect(g):
    return g.findall(SVG + "rect")[0]


def test_sole_blank_is_the_map_blank():
    blanks = _blanks(_root(SOLE_BLANK_INPUT))
    assert len(blanks) == 1
    assert blanks[0].get("data-cell-blank-map") == "true"


def test_sole_blank_map_is_fingerprint_filled_and_markers_recoloured():
    root = _root(SOLE_BLANK_INPUT)
    p = parse(SOLE_BLANK_INPUT)
    toks, _ = tokenize_entropy(p.core, p.alphabet)
    used = tokenize_fingerprint(compute_fingerprint(p.core))[:len(toks)]
    style = select_visual_style(get_median_ftok(used))
    digest = compute_fingerprint(p.core)
    expected_fill = style.edge_colors[digest[32] & 0b11]   # j = 0
    mapg = _blanks(root)[0]
    assert _blank_rect(mapg).get("fill") == expected_fill, "map blank fp-filled"
    # markers recoloured to luminance contrast against the fill, by shape
    f = expected_fill
    _, contrast = get_nucleus_colors(
        int(f[1:3], 16) | (int(f[3:5], 16) << 8) | (int(f[5:7], 16) << 16))
    dot = mapg.find(SVG + "circle")
    plus = mapg.find(SVG + "path")
    assert dot.get("fill") == contrast
    assert plus.get("stroke") == contrast
    assert dot.get("fill") not in ("#1d4ed8", "#d62828")


def test_multi_blank_map_keeps_anchor_and_red_blue_markers():
    root = _root(MULTI_BLANK_INPUT)
    blanks = _blanks(root)
    assert len(blanks) >= 2
    style = select_visual_style(get_median_ftok(
        tokenize_fingerprint(compute_fingerprint(parse(MULTI_BLANK_INPUT).core))[:20]))
    anchor = "#e7be00" if style.bg_color == "#ffffff" else "#ffffff"
    mapg = next(g for g in blanks if g.get("data-cell-blank-map") == "true")
    assert _blank_rect(mapg).get("fill") == anchor
    assert mapg.find(SVG + "circle").get("fill") == "#1d4ed8"
    assert mapg.find(SVG + "path").get("stroke") == "#d62828"


def test_multi_blank_siblings_are_fingerprint_filled():
    root = _root(MULTI_BLANK_INPUT)
    style = select_visual_style(get_median_ftok(
        tokenize_fingerprint(compute_fingerprint(parse(MULTI_BLANK_INPUT).core))[:20]))
    siblings = [g for g in _blanks(root)
                if g.get("data-cell-blank-map") != "true"]
    assert siblings, "large input should have non-map blanks"
    for g in siblings:
        fill = _blank_rect(g).get("fill")
        assert fill in style.edge_colors, "sibling blank filled from edge palette"
        assert fill != "none"
