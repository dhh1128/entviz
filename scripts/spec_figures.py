"""
Generate the figures for the algorithm spec (docs/spec.md).

Like the paper figures, these are built from scripts/figlib.py and from the live
renderer — the channel illustrations wrap a real render(), and the geometry /
schematic diagrams are computed from the spec constants in figlib.geometry().
Nothing here is hand-drawn, so tests/test_figures.py keeps them honest. Output
is SVG-only (the spec is a web page, not a PDF), written into docs/assets/.

    PYTHONPATH=src .venv/bin/python scripts/spec_figures.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import figlib  # noqa: E402
from figlib import *  # noqa: E402,F401,F403
from figlib import _inner  # noqa: E402

GEN = "scripts/spec_figures.py"
figlib.GENERATOR = GEN

OUT = os.path.join(figlib.REPO_ROOT, "docs", "assets")

# A render with one data cell whose features we annotate for the channel figures.
_ZOOM_INPUT = "0123456789abcdef0123456789abcdef"
_ZOOM_CROP = (52.0, 51.0, 120.0, 80.0)  # cell 0's exact extent at 24pt


def _cell0(art):
    """Locate cell 0's nucleus / text / a surround box / quartile in `art`."""
    root = parse(art)
    c0 = cells(root)[0]
    nx, ny, nw, nh = rect_box(nucleus(c0))
    t = next(c0.iter(SVGNS + "text"))
    tx, ty = float(t.get("x")), float(t.get("y"))
    poly = next(c0.iter(SVGNS + "polygon"))
    pts = [tuple(map(float, p.split(","))) for p in poly.get("points").split()]
    cx0, cy0, cw, ch = _ZOOM_CROP
    boxes = [b for b in surround_boxes(root)
             if cx0 <= float(b.get("x")) < cx0 + cw and cy0 <= float(b.get("y")) < cy0 + ch
             and b.get("fill") != "#e7be00"] or surround_boxes(root)
    tb = min(boxes, key=lambda b: float(b.get("y")))
    return {
        "nucleus": (nx + nw / 2, ny + 3),
        "text": (tx, ty - 4),
        "box": (float(tb.get("x")) + float(tb.get("width")) / 2,
                float(tb.get("y")) + float(tb.get("height")) / 2),
        "quartile": (sum(p[0] for p in pts) / 3, sum(p[1] for p in pts) / 3),
    }


def _annotated_cell(rows, italic_note="one cell, enlarged"):
    """Single-cell zoom on the left, labelled rows on the right (shared layout)."""
    art = render(_ZOOM_INPUT, font_size_pt=24)
    feat = _cell0(art)
    art_x, art_y, art_w = 40, 48, 300
    nested, art_h, mp = place(art, art_x, art_y, art_w, crop=_ZOOM_CROP)
    lx = art_x + art_w + 70
    W = lx + 380
    H = max(art_y + art_h + 24, 60 + 64 * len(rows))
    s = [svg_open(W, H), nested]
    s.append(rect(art_x, art_y, art_w, art_h, stroke=HAIR, sw=1))
    s.append(text(art_x, art_y - 12, italic_note, size=T_SMALL, fill=INK2, italic=True))
    ys = [70 + 62 * i for i in range(len(rows))]
    for (key, head, sub), ry in zip(rows, ys):
        tx, ty = mp(*feat[key])
        s.append(leader(tx, ty, lx, ry, head, size=T_LABEL, weight="bold", knee=(lx - 18, ry - 4)))
        s.append(text(lx, ry + 15, sub, size=T_SMALL, fill=INK2))
    s.append(svg_close())
    return W, H, s


# ===========================================================================
#  CHANNEL ILLUSTRATIONS (from real renders)
# ===========================================================================

def fig_example():
    """A clean, representative v6 entviz — the spec's opening illustration."""
    art = gallery("11-256-bit-hex.svg")
    margin, top = 40, 40
    art_w = 340
    cap = ("A v6 entviz of a 256-bit input: text grid, colour bar, surround texture, "
           "ellipse overlay, and CRC landmarks.")
    _, aw0, ah0, _ = _inner(art)
    art_h = art_w * ah0 / aw0
    W = max(margin * 2 + art_w, approx_w(cap, T_SMALL) + 2 * margin)
    H = top + art_h + 44
    art_x = (W - art_w) / 2
    nested, art_h, _ = place(art, art_x, top, art_w)
    s = [svg_open(W, H), nested]
    s.append(rect(art_x, top, art_w, art_h, stroke=HAIR, sw=1))
    s.append(caption(W, H - 16, cap))
    s.append(svg_close())
    return "example", "".join(s)


def fig_text_channel():
    """The text channel: tokenized, lossless input."""
    art = gallery("01-Random-UUID-v4.svg")
    root = parse(art)
    # a data cell's text element
    tcell = next(c for c in cells(root) if c.get("data-cell-blank") != "true")
    t = next(tcell.iter(SVGNS + "text"))
    tx, ty = float(t.get("x")), float(t.get("y"))
    margin, top = 40, 40
    art_w = 300
    nested, art_h, mp = place(art, margin, top, art_w)
    lx = margin + art_w + 60
    W, H = lx + 380, max(top + art_h + 30, 260)
    s = [svg_open(W, H), nested]
    s.append(rect(margin, top, art_w, art_h, stroke=HAIR, sw=1))
    mtx, mty = mp(tx, ty - 4)
    s.append(leader(mtx, mty, lx, 110, "text channel", size=T_LABEL, weight="bold", knee=(lx - 18, 106)))
    s.append(text(lx, 125, "the normalized input, tokenized into cells and", size=T_SMALL, fill=INK2))
    s.append(text(lx, 141, "read left-to-right, top-to-bottom. Lossless for", size=T_SMALL, fill=INK2))
    s.append(text(lx, 157, "inputs ≤ 512 bits: read aloud (with case), it", size=T_SMALL, fill=INK2))
    s.append(text(lx, 173, "transmits every bit. It does not, by itself,", size=T_SMALL, fill=INK2))
    s.append(text(lx, 189, "amplify difference — that is the other channels.", size=T_SMALL, fill=INK2))
    s.append(svg_close())
    return "text-channel", "".join(s)


def fig_surround_channel():
    rows = [
        ("box", "surround — 24 boxes", "10 above, 10 below, 2 each side"),
        ("box", "each box = one fingerprint bit", "filled or empty, by the cell's ftok quant"),
        ("box", "edge colour", "filled boxes use the palette entry nearest the nucleus"),
        ("nucleus", "the colour leaks outward", "binding the ring to the nucleus by Similarity"),
    ]
    W, H, s = _annotated_cell(rows)
    return "surround-channel", "".join(s)


def fig_nucleus_channel():
    rows = [
        ("nucleus", "nucleus background", "the 24-bit token read as a 24-bit RGB colour"),
        ("nucleus", "lossless ≤ 512 bits", "derived from the entropy, not the fingerprint"),
        ("text", "a redundant hint, not primary", "fine gradations fall below the JND / vanish < 16M colours"),
    ]
    W, H, s = _annotated_cell(rows)
    return "nucleus-channel", "".join(s)


def fig_crc():
    """Blank-cell map dots and quartile-mark orientations."""
    art = gallery("09-64-bit-hex.svg")
    root = parse(art)
    mins = [e for e in root.iter() if e.get("data-blank-map-min")]
    maxs = [e for e in root.iter() if e.get("data-blank-map-max")]
    polys = [e for e in root.iter(SVGNS + "polygon")]
    margin, top, art_w = 40, 50, 300
    nested, art_h, mp = place(art, margin, top, art_w)
    W, H = 760, max(top + art_h + 50, 320)
    s = [svg_open(W, H), nested]
    s.append(rect(margin, top, art_w, art_h, stroke=HAIR, sw=1))
    lx = margin + art_w + 60
    rows = []
    if maxs:
        c = maxs[0]
        rows.append((mp(float(c.get("cx")), float(c.get("cy"))),
                     "blank-cell map — red dot", "the cell holding the largest fingerprint token", WARN))
    if mins:
        c = mins[0]
        rows.append((mp(float(c.get("cx")), float(c.get("cy"))),
                     "blank-cell map — blue dot", "the cell holding the smallest token", BLUE))
    if polys:
        p = polys[0]
        pts = [tuple(map(float, q.split(","))) for q in p.get("points").split()]
        rows.append((mp(sum(q[0] for q in pts) / 3, sum(q[1] for q in pts) / 3),
                     "quartile mark", "corner orientation encodes the token's rank quartile", ACCENT))
    for (target, head, sub, col), ry in zip(rows, [70, 150, 230]):
        tx, ty = target
        s.append(leader(tx, ty, lx, ry, head, size=T_LABEL, weight="bold", knee=(lx - 18, ry - 4), fill=INK))
        s.append(text(lx, ry + 15, sub, size=T_SMALL, fill=INK2))
        s.append(dot(tx, ty, 3.0, fill=col))
    s.append(text(margin + art_w / 2, top + art_h + 22, "blank positions and quartile marks act as a",
                  size=T_SMALL, anchor="middle", fill=INK2))
    s.append(text(margin + art_w / 2, top + art_h + 38, "visual CRC — easily checked, derived from the fingerprint",
                  size=T_SMALL, anchor="middle", fill=INK2))
    s.append(svg_close())
    return "crc", "".join(s)


# ===========================================================================
#  SCHEMATIC / GEOMETRY DIAGRAMS (computed from the spec constants)
# ===========================================================================

def fig_tokens():
    """Splitting a string into 24-bit tokens (hex example: 6 chars/token)."""
    src = "0123456789abcdef0123456789abcdef0123"  # 36 hex = 6 tokens
    toks = [src[i:i + 6] for i in range(0, len(src), 6)]
    bw, bh, gap, mx, top = 110, 46, 16, 30, 64
    W = mx * 2 + len(toks) * bw + (len(toks) - 1) * gap
    H = top + bh + 84
    s = [svg_open(W, H)]
    s.append(text(mx, 30, "Tokens — 24 bits each (6 hex characters)", size=T_TITLE, weight="bold"))
    s.append(text(mx, 52, "normalized input:", size=T_SMALL, fill=INK2))
    s.append(text(mx + 130, 52, src, size=T_SMALL, family=MONO, fill=INK))
    for i, tk in enumerate(toks):
        x = mx + i * (bw + gap)
        s.append(rect(x, top, bw, bh, fill="#f4f4f1", stroke=ACCENT, sw=1.2, rx=4))
        s.append(text(x + bw / 2, top + bh / 2 + 8, tk, size=22, family=MONO, anchor="middle", fill=INK))
        s.append(text(x + bw / 2, top + bh + 20, f"token {i}", size=T_SMALL, anchor="middle", fill=INK2))
    s.append(caption(W, H - 14, "Each token carries 24 bits (or as close as whole characters allow); "
             "the per-alphabet token length is floor(24 / bits_per_char)."))
    s.append(svg_close())
    return "tokens", "".join(s)


def _mini_grid(x, y, cols, rows, unit, stroke=INK2, sw=1.0, fill="none"):
    cw, ch = unit * 1.5, unit  # cell aspect 3:2
    out = [rect(x, y, cols * cw, rows * ch, fill=fill, stroke=stroke, sw=sw)]
    for c in range(1, cols):
        out.append(line(x + c * cw, y, x + c * cw, y + rows * ch, stroke=stroke, w=0.6))
    for r in range(1, rows):
        out.append(line(x, y + r * ch, x + cols * cw, y + r * ch, stroke=stroke, w=0.6))
    return "".join(out), cols * cw, rows * ch


def fig_grid_options():
    """The four candidate layouts for 11 tokens; 3x4 chosen at target 1:1."""
    options = [(6, 2), (4, 3), (3, 4), (2, 6)]
    chosen = (3, 4)
    unit = 18
    mx, top, gap = 36, 70, 56
    # precompute widths
    widths = [c * unit * 1.5 for c, r in options]
    W = mx * 2 + sum(widths) + gap * (len(options) - 1)
    H = top + max(r * unit for c, r in options) + 76
    s = [svg_open(W, H)]
    s.append(text(mx, 32, "Grid options for 11 tokens (target aspect 1:1)", size=T_TITLE, weight="bold"))
    s.append(text(mx, 52, "choose the layout whose aspect is closest to 1:1 without going below it",
                  size=T_SMALL, fill=INK2))
    x = mx
    for (c, r), w in zip(options, widths):
        is_ch = (c, r) == chosen
        grid, gw, gh = _mini_grid(x, top, c, r, unit,
                                  stroke=ACCENT if is_ch else INK2,
                                  sw=2.0 if is_ch else 1.0,
                                  fill="#eef2f6" if is_ch else "none")
        s.append(grid)
        ar = (c * 3) / (r * 2)
        s.append(text(x + gw / 2, top + gh + 20, f"{c}×{r}", size=T_LABEL, anchor="middle",
                      weight="bold", fill=INK if is_ch else INK2))
        s.append(text(x + gw / 2, top + gh + 36, f"AR {ar:.2f}" + ("  ✓ chosen" if is_ch else ""),
                      size=T_SMALL, anchor="middle", fill=ACCENT if is_ch else INK2))
        x += w + gap
    s.append(svg_close())
    return "grid-options", "".join(s)


def fig_grid_and_cells():
    """Cell indexing 0..N in reading order across a 3x4 grid."""
    cols, rows = 3, 4
    cw, ch = 96, 64
    mx, top = 40, 64
    cap = ("A token's cell index equals its token index unless blank cells shift it "
           "(see the blank-cell rule).")
    W = max(mx * 2 + cols * cw + 150, mx + approx_w(cap, T_SMALL) + mx)
    H = top + rows * ch + 40
    s = [svg_open(W, H)]
    s.append(text(mx, 32, "Cell index — left-to-right, top-to-bottom", size=T_TITLE, weight="bold"))
    idx = 0
    for r in range(rows):
        for c in range(cols):
            x, y = mx + c * cw, top + r * ch
            s.append(rect(x, y, cw, ch, fill="#f7f8fa", stroke=HAIR, sw=1))
            s.append(text(x + cw / 2, y + ch / 2 + 9, str(idx), size=26, anchor="middle", fill=INK))
            idx += 1
    # reading-order arrow
    ax = mx + cols * cw + 30
    s.append(text(ax, top + 20, "reading", size=T_SMALL, fill=INK2))
    s.append(text(ax, top + 36, "order", size=T_SMALL, fill=INK2))
    s.append(f'<path d="M {ax} {top+60} h 90 m -10 -6 l 10 6 l -10 6" fill="none" stroke="{ACCENT}" stroke-width="1.5"/>')
    s.append(text(mx, top + rows * ch + 28, cap, size=T_SMALL, fill=INK2))
    s.append(svg_close())
    return "grid-and-cells", "".join(s)


def fig_cell_layout():
    """Cell + 24-box surround geometry, dimensioned from figlib.geometry()."""
    g = geometry(12)  # reference: 12pt @ 96dpi -> fs 16; cell 60x40, box 6x10
    S = 7.0  # display scale (px per spec px)
    nw, nh = g["nucleus_width"], g["nucleus_height"]
    bw, bh = g["box_width"], g["box_height"]
    cw, ch = g["cell_width"], g["cell_height"]
    ox, oy = 210, 130  # origin of the cell on the canvas (room for left dim + top dim)

    def X(v):
        return ox + v * S

    def Y(v):
        return oy + v * S

    s = [svg_open(ox + cw * S + 250, oy + ch * S + 100)]
    s.append(text(40, 36, "Cell and 24-box surround geometry", size=T_TITLE, weight="bold"))
    s.append(text(40, 56, "all lengths derive from font_size_px (12 pt @ 96 dpi → 16 px)",
                  size=T_SMALL, fill=INK2))
    # surround boxes (local cell coords): top 10, bottom 10, sides 2+2
    box_fill, box_stroke = "#eef0f3", HAIR
    for i in range(10):
        s.append(rect(X(i * bw), Y(0), bw * S, bh * S, fill=box_fill, stroke=box_stroke, sw=0.8))
        s.append(rect(X(i * bw), Y(ch - bh), bw * S, bh * S, fill=box_fill, stroke=box_stroke, sw=0.8))
    for k in range(2):
        yy = bh + k * bh
        s.append(rect(X(0), Y(yy), bw * S, bh * S, fill=box_fill, stroke=box_stroke, sw=0.8))
        s.append(rect(X(cw - bw), Y(yy), bw * S, bh * S, fill=box_fill, stroke=box_stroke, sw=0.8))
    # nucleus
    s.append(rect(X(bw), Y(bh), nw * S, nh * S, fill="#cdeacd", stroke="#7bbf7b", sw=1))
    s.append(text(X(bw + nw / 2), Y(bh + nh / 2) + 6, "nucleus", size=T_LABEL, anchor="middle", fill=INK))
    s.append(text(X(bw + nw / 2), Y(bh / 2) + 5, "surround box ×24", size=T_SMALL, anchor="middle", fill=INK2))

    # dimensions, each on its own side so nothing collides
    s.append(dim(X(0), Y(-1.8), X(cw), Y(-1.8), f"cell width = 3.75·fs = {cw:.0f}", place="above"))
    s.append(dim(X(bw), Y(ch + 1.8), X(bw + nw), Y(ch + 1.8), f"nucleus width = 3·fs = {nw:.0f}", place="below"))
    s.append(dim(X(cw + 1.8), Y(0), X(cw + 1.8), Y(ch), f"cell height = 2.5·fs = {ch:.0f}", place="right"))
    s.append(dim(X(-1.8), Y(bh), X(-1.8), Y(bh + nh), f"nucleus h = 1.25·fs = {nh:.0f}", place="left"))
    # one box's dimensions (bottom-right note)
    s.append(text(X(cw) + 70, Y(ch) + 30, f"box = {bw:.0f}×{bh:.0f}  (0.375·fs × 0.625·fs)",
                  size=T_SMALL, anchor="middle", fill=INK2))
    s.append(svg_close())
    return "cell-layout", "".join(s)


# ===========================================================================
#  PALETTE (data-driven, house-styled)
# ===========================================================================

def fig_palette_swatch():
    sw_w, sw_h, gap, mx, top = 120, 96, 24, 30, 56
    n = len(NAMES)
    W = mx * 2 + n * sw_w + (n - 1) * gap
    H = top + sw_h + 90
    s = [svg_open(W, H)]
    s.append(text(W / 2, 34, "entviz palette — spaced by CIELAB lightness (L*)", size=T_TITLE,
                  anchor="middle", weight="bold"))
    for i, nm in enumerate(NAMES):
        x = mx + i * (sw_w + gap)
        hexv = PALETTE[nm]
        s.append(rect(x, top, sw_w, sw_h, fill=hexv, stroke=HAIR, sw=1))
        cx = x + sw_w / 2
        s.append(text(cx, top + sw_h + 24, nm, size=T_LABEL, anchor="middle", weight="bold"))
        s.append(text(cx, top + sw_h + 42, hexv, size=T_SMALL, anchor="middle", family=MONO, fill=INK2))
        s.append(text(cx, top + sw_h + 60, f"L* = {lstar(hexv):.0f}", size=T_SMALL, anchor="middle", fill=INK2))
    s.append(caption(W, H - 14, "indices 0–3 are background candidates; black (index 4) is always an "
             "edge colour, never the background."))
    s.append(svg_close())
    return "palette-swatch", "".join(s)


def fig_palette_cvd():
    label_w, cell_w, cell_h, mx, top, annot_w = 150, 110, 56, 30, 70, 210
    n = len(NAMES)
    grid_x = mx + label_w
    W = grid_x + n * cell_w + annot_w + mx
    H = top + len(VISION_ROWS) * cell_h + 44
    s = [svg_open(W, H)]
    s.append(text(mx, 34, "Palette under colour-vision deficiency (Machado et al. 2009, severity 1.0)",
                  size=T_TITLE, weight="bold"))
    for j, nm in enumerate(NAMES):
        s.append(text(grid_x + j * cell_w + cell_w / 2, top - 8, nm, size=T_SMALL, anchor="middle", weight="bold"))
    s.append(text(grid_x + n * cell_w + annot_w / 2, top - 8, "closest pair (ΔL*)", size=T_SMALL,
                  anchor="middle", weight="bold", fill=INK2))
    for r, (vision, vlabel) in enumerate(VISION_ROWS):
        y = top + r * cell_h
        s.append(text(mx, y + cell_h / 2 + 5, vlabel, size=T_LABEL, weight="bold"))
        for j, nm in enumerate(NAMES):
            s.append(rect(grid_x + j * cell_w, y, cell_w, cell_h, fill=sim_hex(PALETTE[nm], vision), stroke=HAIR, sw=0.5))
        a, b, d = min_pair(vision)
        warn = d < 20
        s.append(text(grid_x + n * cell_w + 14, y + cell_h / 2 + 5, f"{a}/{b} ΔL* = {d:.0f}",
                      size=T_LABEL, weight="bold" if warn else "normal", fill=WARN if warn else OK))
    s.append(caption(W, H - 14, "Every normal-vision pair clears the ΔL* ≥ 20 floor; the protan red/blue "
             "collapse is unavoidable and falls back to the colour-bar letters."))
    s.append(svg_close())
    return "palette-cvd", "".join(s)


# ===========================================================================
FIGURES = [
    fig_example,
    fig_text_channel,
    fig_surround_channel,
    fig_nucleus_channel,
    fig_crc,
    fig_tokens,
    fig_grid_options,
    fig_grid_and_cells,
    fig_cell_layout,
    fig_palette_swatch,
    fig_palette_cvd,
]


def main():
    figlib.build(FIGURES, OUT, png=False)


if __name__ == "__main__":
    main()
