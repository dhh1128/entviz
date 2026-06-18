"""
Generate the figures for the academic paper (docs/entviz-paper.md).

All shared infrastructure — house style, SVG primitives, entviz/gallery
embedding, CVD maths, the build runner — lives in scripts/figlib.py; this file
only defines the paper's figures. Outputs (SVG, checked in) land in
docs/assets/paper/, each also rasterised to a 2x PNG for the PDF build. The
figures are NOT hand-drawn: each wraps a real render() call or a gallery SVG.
tests/test_figures.py fails CI if a committed figure drifts from this generator
or from the current SPEC_VERSION; never edit the SVGs by hand — re-run this:

    PYTHONPATH=src .venv/bin/python scripts/paper_figures.py
"""
import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import segno  # noqa: E402

import figlib  # noqa: E402
from figlib import *  # noqa: E402,F401,F403  (house style + helpers)
from figlib import _inner  # noqa: E402  (underscore helper not covered by *)

GEN = "scripts/paper_figures.py"
figlib.GENERATOR = GEN

OUT = os.path.join(figlib.REPO_ROOT, "docs", "assets", "paper")


# ===========================================================================
#  FIGURES
# ===========================================================================

def fig_cell_anatomy():
    """Figure 4a — labelled anatomy of one cell."""
    art = render("0123456789abcdef0123456789abcdef", font_size_pt=24)
    root = parse(art)
    c0 = cells(root)[0]
    nuc = nucleus(c0)
    nx, ny, nw, nh = rect_box(nuc)
    txt_el = next(c0.iter(SVGNS + "text"))
    tx, ty = float(txt_el.get("x")), float(txt_el.get("y"))
    poly = next(c0.iter(SVGNS + "polygon"))
    pts = [tuple(map(float, p.split(","))) for p in poly.get("points").split()]
    pcx = sum(p[0] for p in pts) / 3
    pcy = sum(p[1] for p in pts) / 3
    # crop tightly to cell 0's exact extent (cell = 10x4 boxes)
    cx0, cy0, cw, ch = 52.0, 51.0, 120.0, 80.0
    boxes = [b for b in surround_boxes(root)
             if cx0 <= float(b.get("x")) < cx0 + cw and cy0 <= float(b.get("y")) < cy0 + ch
             and b.get("fill") != "#e7be00"]
    boxes = boxes or surround_boxes(root)
    topbox = min(boxes, key=lambda b: float(b.get("y")))
    bx, by = float(topbox.get("x")), float(topbox.get("y"))
    bw, bh = float(topbox.get("width")), float(topbox.get("height"))

    art_x, art_y, art_w = 40, 48, 300
    nested, art_h, mp = place(art, art_x, art_y, art_w, crop=(cx0, cy0, cw, ch))

    lx = art_x + art_w + 70
    W, H = lx + 360, art_y + art_h + 24
    s = [svg_open(W, H), nested]
    s.append(rect(art_x, art_y, art_w, art_h, stroke=HAIR, sw=1))
    s.append(text(art_x, art_y - 12, "one cell, enlarged", size=T_SMALL, fill=INK2, italic=True))

    # Overlay the 24-box surround grid so the reader can see where the boxes
    # live. The 24 boxes tile the perimeter ring of a 10x4 box grid; the
    # interior 8x2 is the nucleus. Each boundary is a black dashed line over a
    # white underlay (an "ants" line), so it reads on any box color.
    bw_, bh_ = cw / 10.0, ch / 4.0

    def gridline(ax1, ay1, ax2, ay2):
        (gx1, gy1), (gx2, gy2) = mp(ax1, ay1), mp(ax2, ay2)
        return (line(gx1, gy1, gx2, gy2, stroke="#ffffff", w=1.3)
                + line(gx1, gy1, gx2, gy2, stroke="#000000", w=0.6, dash="2 2"))

    # full-height verticals at the nucleus side edges (box boundaries throughout)
    for ax in (cx0 + bw_, cx0 + 9 * bw_):
        s.append(gridline(ax, cy0, ax, cy0 + ch))
    # top- and bottom-row internal verticals (skip the nucleus middle band)
    for k in range(2, 9):
        ax = cx0 + k * bw_
        s.append(gridline(ax, cy0, ax, cy0 + bh_))
        s.append(gridline(ax, cy0 + 3 * bh_, ax, cy0 + ch))
    # horizontals dividing the top and bottom rows from the middle band
    for ay in (cy0 + bh_, cy0 + 3 * bh_):
        s.append(gridline(cx0, ay, cx0 + cw, ay))
    # dividers splitting the two stacked boxes in each side column
    s.append(gridline(cx0, cy0 + 2 * bh_, cx0 + bw_, cy0 + 2 * bh_))
    s.append(gridline(cx0 + 9 * bw_, cy0 + 2 * bh_, cx0 + 10 * bw_, cy0 + 2 * bh_))

    items = [
        (mp(nx + nw / 2, ny + 3), "nucleus background", "24-bit token read as an RGB color"),
        (mp(tx, ty - 4), "cell text", "the token in monospace; white/black by Oklab L*"),
        (mp(bx + bw / 2, by + bh / 2), "surround box (1 of 24)", "fingerprint bit i fills box i, or leaves it empty"),
        (mp(bx + bw / 2, by + bh / 2), "per-cell edge color", "the palette entry nearest the nucleus color"),
        (mp(pcx, pcy), "quartile mark", "corner orientation encodes the token's rank"),
    ]
    # Sort by target y so the leader lines to the stacked labels never cross.
    items = order_by_target_y(items, lambda it: it[0][1])
    ys = [70, 120, 168, 212, 256]
    for (target, head, sub), ry in zip(items, ys):
        tgt_x, tgt_y = target
        knee = (lx - 18, ry - 4)
        s.append(leader(tgt_x, tgt_y, lx, ry, head, size=T_LABEL, weight="bold", knee=knee))
        s.append(text(lx, ry + 15, sub, size=T_SMALL, fill=INK2))
    s.append(svg_close())
    return "fig-4a-cell-anatomy", "".join(s)


def _avalanche(name, left_file, right_file, left_cap, right_cap, note):
    al = gallery(left_file)
    ar = gallery(right_file)
    gap = 70
    art_w = 240
    margin = 30
    top = 40
    nl, hl, _ = place(al, margin, top, art_w)
    nr, hr, _ = place(ar, margin + art_w + gap, top, art_w)
    art_h = max(hl, hr)
    W = margin * 2 + art_w * 2 + gap
    H = top + art_h + 70
    cy = top + art_h / 2
    s = [svg_open(W, H), nl, nr]
    mx = margin + art_w + gap / 2
    s.append(text(mx, cy - 6, "≠", size=34, anchor="middle", fill=ACCENT, weight="bold"))
    s.append(text(margin + art_w / 2, top + art_h + 24, left_cap, size=T_LABEL, anchor="middle", weight="bold"))
    s.append(text(margin + art_w + gap + art_w / 2, top + art_h + 24, right_cap, size=T_LABEL, anchor="middle", weight="bold"))
    s.append(caption(W, H - 16, note))
    s.append(svg_close())
    return name, "".join(s)


def fig_hero():
    return _avalanche(
        "fig-hero",
        "05-UUID-A.svg", "06-UUID-A-with-last-char-flipped.svg",
        "a value", "the same value, last character changed",
        "A single changed character flips ~256 fingerprint bits, so most channels visibly change at once.")


def fig_surround_avalanche():
    return _avalanche(
        "fig-4b-surround-avalanche",
        "05-UUID-A.svg", "07-UUID-A-with-mid-char-flipped.svg",
        "input", "input, one middle character changed",
        "The surround texture changes across most cells while the readable text barely moves.")


def fig_palette():
    """Figure 4c — palette swatch (by L*) above the CVD grid."""
    # Type sizes are bumped above the shared house-style minimum and the graphic
    # is kept compact (≤ ~780 px) so the figure renders at/above 1:1 in the page
    # column, keeping every label ≥ 9 pt instead of shrinking below it.
    T_H, T_L, T_B = 17, 15, 13   # sub-heading / labels / body
    sw_w, sw_h, gap, mx, top = 96, 66, 20, 28, 28
    n = len(NAMES)
    sw_block_h = top + sw_h + 70
    label_w, cell_w, cell_h, annot_w = 128, 84, 50, 168
    grid_x = mx + label_w
    cvd_top = sw_block_h + 44
    cvd_h = len(VISION_ROWS) * cell_h
    W = max(mx * 2 + n * sw_w + (n - 1) * gap, grid_x + n * cell_w + annot_w + mx)
    H = cvd_top + cvd_h + 60

    s = [svg_open(W, H)]
    s.append(text(mx, top - 6, "Palette, spaced by CIELAB lightness (L*)", size=T_H, weight="bold"))
    sw_total = n * sw_w + (n - 1) * gap
    sw_x0 = (W - sw_total) / 2
    for i, nm in enumerate(NAMES):
        x = sw_x0 + i * (sw_w + gap)
        hexv = PALETTE[nm]
        s.append(rect(x, top + 6, sw_w, sw_h, fill=hexv, stroke=HAIR, sw=1))
        cx = x + sw_w / 2
        s.append(text(cx, top + 6 + sw_h + 22, nm, size=T_L, anchor="middle", weight="bold"))
        s.append(text(cx, top + 6 + sw_h + 40, hexv, size=T_B, anchor="middle", family=MONO, fill=INK2))
        s.append(text(cx, top + 6 + sw_h + 57, f"L* = {lstar(hexv):.0f}", size=T_B, anchor="middle", fill=INK2))

    s.append(text(mx, cvd_top - 16, "Same palette under color-vision deficiency "
                  "(Machado et al. 2009)", size=T_H, weight="bold"))
    for j, nm in enumerate(NAMES):
        s.append(text(grid_x + j * cell_w + cell_w / 2, cvd_top - 2, nm, size=T_B, anchor="middle", weight="bold"))
    s.append(text(grid_x + n * cell_w + annot_w / 2, cvd_top - 2, "closest pair (ΔL*)", size=T_B, anchor="middle", weight="bold", fill=INK2))
    for r, (vision, vlabel) in enumerate(VISION_ROWS):
        y = cvd_top + r * cell_h
        s.append(text(mx, y + cell_h / 2 + 5, vlabel, size=T_L, weight="bold"))
        for j, nm in enumerate(NAMES):
            s.append(rect(grid_x + j * cell_w, y, cell_w, cell_h, fill=sim_hex(PALETTE[nm], vision), stroke=HAIR, sw=0.5))
        a, b, d = min_pair(vision)
        warn = d < 20
        s.append(text(grid_x + n * cell_w + 14, y + cell_h / 2 + 5, f"{a}/{b} ΔL* = {d:.0f}",
                      size=T_L, weight="bold" if warn else "normal", fill=WARN if warn else OK))
    s.append(text(mx, H - 32, "All normal-vision pairs clear the ΔL* ≥ 20 design floor;", size=T_B, fill=INK2))
    s.append(text(mx, H - 14, "the unavoidable protan red/blue collapse falls back to the color-bar letters.",
                  size=T_B, fill=INK2))
    s.append(svg_close())
    return "fig-4c-palette", "".join(s)


def fig_color_bar():
    """Figure 4d — the color bar, normal vs simulated protanopia, letters surviving."""
    art = render("0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef", font_size_pt=24)
    root = parse(art)
    cbar = [g for g in root.iter(SVGNS + "g") if g.get("data-channel") == "color-bar"][0]
    bands = []
    rects = [r for r in cbar.iter(SVGNS + "rect")]
    txts = [t for t in cbar.iter(SVGNS + "text")]
    total_h = sum(float(r.get("height")) for r in rects)
    for r, t in zip(rects, txts):
        bands.append((r.get("fill"), (t.text or "").strip(), t.get("fill"),
                      float(r.get("height")) / total_h))

    # Bigger labels + a two-line caption keep the figure narrow (≈640 px) so it
    # renders near 1:1 and every label stays ≥ 9 pt.
    T_L, T_B = 15, 13
    bar_w, bar_h = 64, 300
    gap = 170
    mx, top = 60, 30
    cap1 = "Band heights are the fingerprint's 2-bit pattern counts, 4th-power skewed;"
    cap2 = "the letter names the color for CVD and monochrome viewers."
    W = max(mx * 2 + bar_w * 2 + gap, approx_w(cap1, T_B) + 2 * mx)
    H = top + bar_h + 84

    def draw_bar(x, vision):
        out = []
        y = top
        for fill, letter, lfill, frac in bands:
            h = frac * bar_h
            f = sim_hex(fill, vision) if vision != "normal" else fill
            out.append(rect(x, y, bar_w, h, fill=f, stroke=HAIR, sw=0.5))
            if letter:
                out.append(text(x + bar_w / 2, y + h / 2 + 7, letter.lower(), size=20,
                                anchor="middle", family=MONO, fill=lfill, weight="bold"))
            y += h
        return "".join(out)

    s = [svg_open(W, H)]
    span = bar_w * 2 + gap
    x1 = (W - span) / 2
    x2 = x1 + bar_w + gap
    s.append(draw_bar(x1, "normal"))
    s.append(draw_bar(x2, "protan"))
    s.append(text(x1 + bar_w / 2, top + bar_h + 26, "normal vision", size=T_L, anchor="middle", weight="bold"))
    s.append(text(x2 + bar_w / 2, top + bar_h + 26, "protanopia (simulated)", size=T_L, anchor="middle", weight="bold"))
    mxx = (x1 + bar_w + x2) / 2
    s.append(text(mxx, top + bar_h / 2 - 9, "the letters", size=T_B, anchor="middle", fill=INK2))
    s.append(text(mxx, top + bar_h / 2 + 9, "w / g / r / b / k", size=T_B, anchor="middle", family=MONO, fill=INK))
    s.append(text(mxx, top + bar_h / 2 + 27, "survive", size=T_B, anchor="middle", fill=INK2))
    s.append(caption(W, H - 32, cap1, size=T_B))
    s.append(caption(W, H - 14, cap2, size=T_B))
    s.append(svg_close())
    return "fig-4d-color-bar", "".join(s)


def fig_ellipse():
    """Figure 4e — clamped ellipse on two grids, silhouette traced in accent."""
    files = [("11-256-bit-hex.svg", "256-bit input (interior anchor)"),
             ("12-512-bit-hex.svg", "512-bit input")]
    art_w = 250
    gap = 60
    mx, top = 30, 30
    arts = [gallery(fn) for fn, _ in files]
    heights = [art_w * _inner(a)[2] / _inner(a)[1] for a in arts]
    maxh = max(heights)
    block_w = art_w * len(arts) + gap * (len(arts) - 1)
    ell_cap = ("The translucent overlay (dashed silhouette) is clamped to cover ~8–70% of the "
               "grid — noticeable but never swamping it.")
    W = max(block_w + 2 * mx, approx_w(ell_cap, T_SMALL) + 2 * mx)
    H = top + maxh + 56
    x0 = (W - block_w) / 2
    nests = []
    placements = []
    for i, (art, (fn, cap)) in enumerate(zip(arts, files)):
        x = x0 + i * (art_w + gap)
        nested, h, mp = place(art, x, top, art_w)
        root = parse(art)
        ell = [g for g in root.iter(SVGNS + "g") if g.get("data-channel") == "ellipse"]
        nests.append((nested, cap, x))
        placements.append((mp, ell[0] if ell else None))
    s = [svg_open(W, H)]
    for (nested, cap, xx) in nests:
        s.append(nested)
    for (mp, ell), (nested, cap, xx) in zip(placements, nests):
        if ell is not None:
            el = ell.find(SVGNS + "ellipse")
            cx, cy = float(el.get("cx")), float(el.get("cy"))
            rx, ry = float(el.get("rx")), float(el.get("ry"))
            rot = ell.get("data-ellipse-rotation-deg") or "0"
            mcx, mcy = mp(cx, cy)
            sx0, _ = mp(0, 0)
            sx1, _ = mp(1, 0)
            sc = sx1 - sx0
            s.append(f'<ellipse cx="{mcx:.2f}" cy="{mcy:.2f}" rx="{rx*sc:.2f}" ry="{ry*sc:.2f}" '
                     f'transform="rotate({rot} {mcx:.2f} {mcy:.2f})" fill="none" stroke="{ACCENT}" '
                     f'stroke-width="1.6" stroke-dasharray="4 3"/>')
        s.append(text(xx + art_w / 2, top + maxh + 24, cap, size=T_LABEL, anchor="middle", weight="bold"))
    s.append(caption(W, H - 14, ell_cap))
    s.append(svg_close())
    return "fig-4e-ellipse", "".join(s)


def fig_crc():
    """Figure 4f — blank-cell map dots and quartile-mark orientations, annotated."""
    art = gallery("09-64-bit-hex.svg")
    root = parse(art)
    mins = [e for e in root.iter() if e.get("data-blank-map-min")]
    maxs = [e for e in root.iter() if e.get("data-blank-map-max")]
    polys = [e for e in root.iter(SVGNS + "polygon")]

    art_w = 300
    margin = 40
    top = 50
    nested, art_h, mp = place(art, margin, top, art_w)
    W, H = 760, max(top + art_h + 50, 320)
    s = [svg_open(W, H), nested]
    s.append(rect(margin, top, art_w, art_h, stroke=HAIR, sw=1))

    lx = margin + art_w + 60
    rows = []
    if maxs:
        c = maxs[0]
        rows.append((mp(*marker_center(c)),
                     "blank-cell map — red plus", "marks the cell holding the largest fingerprint token", WARN))
    if mins:
        c = mins[0]
        rows.append((mp(*marker_center(c)),
                     "blank-cell map — blue dot", "marks the cell holding the smallest token", BLUE))
    if polys:
        p = polys[0]
        pts = [tuple(map(float, q.split(","))) for q in p.get("points").split()]
        rows.append((mp(sum(q[0] for q in pts) / 3, sum(q[1] for q in pts) / 3),
                     "quartile mark", "corner orientation encodes the token's rank quartile", ACCENT))
    # Sort by target y so the red/blue/quartile leaders never cross.
    rows = order_by_target_y(rows, lambda r: r[0][1])
    ys = [70, 150, 230]
    for (target, head, sub, col), ry in zip(rows, ys[:len(rows)]):
        tx, ty = target
        knee = (lx - 18, ry - 4)
        s.append(leader(tx, ty, lx, ry, head, size=T_LABEL, weight="bold", knee=knee, fill=INK))
        s.append(text(lx, ry + 15, sub, size=T_SMALL, fill=INK2))
        s.append(dot(tx, ty, 3.0, fill=col))
    s.append(text(margin + art_w / 2, top + art_h + 22, "blanks sit at fingerprint-derived positions —",
                  size=T_SMALL, anchor="middle", fill=INK2))
    s.append(text(margin + art_w / 2, top + art_h + 38, "their layout is itself a CRC",
                  size=T_SMALL, anchor="middle", fill=INK2))
    s.append(svg_close())
    return "fig-4f-crc", "".join(s)


def fig_large_input():
    """Figure 4g — head / fingerprint-middle / tail layout for a >512-bit input."""
    art = render(
        hashlib.sha512(b"entviz large-input figure").hexdigest()
        + hashlib.sha512(b"entviz v9 large-input demo").hexdigest(),
        font_size_pt=14)
    root = parse(art)
    data = []
    for c in cells(root):
        idx = int(c.get("data-cell-index"))
        x, y, w, h = rect_box(nucleus(c))
        blank = c.get("data-cell-blank") == "true"
        framed = c.get("data-cell-fingerprint") == "true"
        data.append((idx, x, y, w, h, blank, framed))
    data.sort()
    framed = [d for d in data if d[6]]
    heads = [d for d in data if (not d[5]) and not d[6]]
    first_m = min((d[0] for d in framed), default=10**9)
    last_m = max((d[0] for d in framed), default=-1)
    head_cells = [d for d in heads if d[0] < first_m]
    tail_cells = [d for d in heads if d[0] > last_m]

    art_w = 380
    margin = 60
    top = 64
    nested, art_h, mp = place(art, margin, top, art_w)
    lx = margin + art_w + 60
    cap = ("Head and tail show real input; the four framed middle cells show a domain-separated "
           "digest (Crockford base32) that avalanches on any change.")
    W = max(lx + 300, approx_w(cap, T_SMALL) + 2 * 30)
    H = top + art_h + 56
    s = [svg_open(W, H), nested]

    def center(d):
        _, x, y, w, h, _, _ = d
        return mp(x + w / 2, y + h / 2)

    rows = []
    if head_cells:
        rows.append((center(head_cells[0]), "head", "first tokens of the real input", INK))
    if framed:
        rows.append((center(framed[0]), "fingerprint-middle", "a digest in Crockford base32, framed — not the user's data", WARN))
    if tail_cells:
        rows.append((center(tail_cells[-1]), "tail", "last tokens of the real input", INK))
    ys = [96, 168, 240]
    for (target, head, sub, col), ry in zip(rows, ys):
        tx, ty = target
        knee = (lx - 18, ry - 4)
        s.append(leader(tx, ty, lx, ry, head, size=T_LABEL, weight="bold", knee=knee, fill=col))
        s.append(text(lx, ry + 15, sub, size=T_SMALL, fill=INK2))
    s.append(caption(W, H - 14, cap))
    s.append(svg_close())
    return "fig-4g-large-input", "".join(s)


def fig_comparison():
    """Figure 2 — SSH randomart, a QR code, and an entviz side by side."""
    fp = hashlib.sha256(b"entviz-comparison-figure").digest()
    art_lines = drunken_bishop(fp)
    margin = 30
    top = 40
    panel_w = 240
    gap = 44
    panel_h = 250
    W = margin * 2 + panel_w * 3 + gap * 2
    H = top + panel_h + 86

    s = [svg_open(W, H)]
    labels = ["(a) SSH randomart", "(b) QR code", "(c) entviz"]
    subs = ["emergent path; low perceptual entropy", "dense matrix; for machines", "designed; built for the eye"]
    xs = [margin, margin + panel_w + gap, margin + 2 * (panel_w + gap)]

    # (a) randomart
    ax = xs[0]
    s.append(rect(ax, top, panel_w, panel_h, fill="#fbfbfa", stroke=INK, sw=1.2))
    nlines = len(art_lines) + 2
    line_h = (panel_h - 24) / nlines
    fs = line_h / 1.18
    ry = top + line_h

    def mline(txt, yy):
        # preserve=True: the randomart's interior spaces are load-bearing (an
        # unvisited cell is a space, per OpenSSH); without it SVG collapses runs
        # of spaces and the |...| frame goes ragged.
        return text(ax + panel_w / 2, yy, txt, size=fs, family=MONO, anchor="middle",
                    fill=INK, preserve=True)
    s.append(mline("+--[ED25519 256]--+", ry))
    ry += line_h
    for ln in art_lines:
        s.append(mline("|" + ln + "|", ry))
        ry += line_h
    s.append(mline("+----[SHA256]-----+", ry))

    # (b) QR
    qx = xs[1]
    qr = segno.make("https://github.com/dhh1128/entviz", error="m")
    matrix = [row for row in qr.matrix]
    quiet = 2
    total = len(matrix) + 2 * quiet
    mod = panel_w / total
    qy = top + (panel_h - panel_w) / 2
    s.append(rect(qx, qy, panel_w, panel_w, fill="#ffffff", stroke=HAIR, sw=1))
    qg = [f'<g transform="translate({qx},{qy})">']
    for r, row in enumerate(matrix):
        for c, v in enumerate(row):
            if v:
                qg.append(rect((c + quiet) * mod, (r + quiet) * mod, mod + 0.3, mod + 0.3, fill=INK))
    qg.append("</g>")
    s.append("".join(qg))

    # (c) entviz
    ex = xs[2]
    art = gallery("10-128-bit-hex.svg")
    _, aw0, ah0, _ = _inner(art)
    disp_h = panel_w * ah0 / aw0
    nested, _, _ = place(art, ex, top + (panel_h - disp_h) / 2, panel_w)
    s.append(nested)

    for x, lab, sub in zip(xs, labels, subs):
        s.append(text(x + panel_w / 2, top + panel_h + 28, lab, size=T_LABEL, anchor="middle", weight="bold"))
        s.append(text(x + panel_w / 2, top + panel_h + 46, sub, size=T_SMALL, anchor="middle", fill=INK2))
    s.append(caption(W, H - 12, "Three answers to “show this value”: a machine baseline (QR), a naive "
             "human attempt (randomart), and a designed one (entviz)."))
    s.append(svg_close())
    return "fig-comparison", "".join(s)


# ===========================================================================
FIGURES = [
    fig_hero,
    fig_cell_anatomy,
    fig_surround_avalanche,
    fig_palette,
    fig_color_bar,
    fig_ellipse,
    fig_crc,
    fig_large_input,
    fig_comparison,
]


def main():
    figlib.build(FIGURES, OUT)


if __name__ == "__main__":
    main()
