#!/usr/bin/env python
"""Visual prototype for the ellipse overlay coverage band (entviz v6 work).

Renders a matrix of representative grids x coverage percentiles, using the REAL
geometry helpers from entviz so what you see is what the algorithm would draw.
For each grid it enumerates the reachable parameter space (anchor x rx_step x
ry_step x rotation) and shows the draws at the smallest / ~40th / ~75th /
largest reachable coverage — so you can judge both ends: is the smallest still
noticeable, does the largest swamp the grid? Overlay uses the white-bg rule
(#000 @ 0.2).

Use this to eyeball the v6 coverage clamp. The clamp is d_far-relative:
rx, ry in [max(R_MIN, alpha*d_far), beta*d_far]. Pass alpha/beta (and an output
name) on the command line; with no args it shows current v5 behaviour.

Run (needs the opt-in render group: cairosvg + numpy):
    uv run --group render python scripts/ellipse_prototype.py             # v5
    uv run --group render python scripts/ellipse_prototype.py 0.22 0.58 cand_a
Then open the PNG (WSL):
    wslview .cache/ellipse_view.png       # default Windows image viewer
    code .cache/ellipse_view.png          # VS Code

Outputs (gitignored .cache/): ellipse_view[_<name>].svg and .png.

See reviews/ellipse-audit-2026-06-02.md for the findings this supports.
"""
import math
import sys
from pathlib import Path

import numpy as np
import cairosvg

from entviz.layout import Point
from entviz.pipeline import (enumerate_interior_corners,
    enumerate_external_corners, _HYBRID_INTERIOR_THRESHOLD)

FPX = 16.0                      # 12pt @ 96dpi
CELL_W = 3.75 * FPX             # 60
CELL_H = 2.5 * FPX              # 40
R_MIN = CELL_H / 2              # 20
N = 90                          # coverage sample resolution per axis

GRIDS = [(2, 2), (3, 3), (4, 4), (4, 6), (11, 2)]
PCTILES = [0, 40, 75, 100]      # which reachable-coverage percentiles to show

# d_far-relative clamp (alpha, beta); None => v5 behaviour [R_MIN, d_far-CELL_W].
# v6 adopted (0.22, 0.58) — see reviews/ellipse-audit-2026-06-02.md. Override on
# the command line to preview alternatives.
CLAMP = (0.22, 0.58)


def pool(cols, rows):
    if (cols - 1) * (rows - 1) >= _HYBRID_INTERIOR_THRESHOLD:
        return enumerate_interior_corners(cols, rows, CELL_W, CELL_H, Point(0, 0))
    return enumerate_external_corners(cols, rows, CELL_W, CELL_H, Point(0, 0))


def d_far(a, W, H):
    return max(math.hypot(c[0] - a.x, c[1] - a.y)
               for c in [(0, 0), (W, 0), (0, H), (W, H)])


def radius_bounds(a, W, H):
    """(lo, hi) isotropic radius bounds for this anchor."""
    if CLAMP is None:
        return R_MIN, d_far(a, W, H) - CELL_W
    alpha, beta = CLAMP
    return max(R_MIN, alpha * d_far(a, W, H)), beta * d_far(a, W, H)


def coverage(a, rx, ry, th, W, H):
    xs = (np.arange(N) + 0.5) / N * W
    ys = (np.arange(N) + 0.5) / N * H
    GX, GY = np.meshgrid(xs, ys)
    dx, dy = GX - a.x, GY - a.y
    ct, st = math.cos(-th), math.sin(-th)
    xr, yr = dx * ct - dy * st, dx * st + dy * ct
    return ((xr / rx) ** 2 + (yr / ry) ** 2 <= 1.0).mean()


def reachable_draws(cols, rows):
    W, H = cols * CELL_W, rows * CELL_H
    out = []
    for a in pool(cols, rows):
        lo, hi = radius_bounds(a, W, H)
        if hi <= lo:
            continue
        for rxs in range(0, 16, 2):
            for rys in range(0, 16, 2):
                rx = lo + (rxs / 15) * (hi - lo)
                ry = lo + (rys / 15) * (hi - lo)
                for rts in range(0, 16, 3):
                    th = math.radians((rts / 15) * 180)
                    out.append((coverage(a, rx, ry, th, W, H), a, rx, ry,
                                (rts / 15) * 180))
    return out, W, H


def at_percentiles(ds):
    ds = sorted(ds, key=lambda d: d[0])
    return [ds[min(len(ds) - 1, round(p / 100 * (len(ds) - 1)))] for p in PCTILES]


def build_svg():
    PANW, PANH, PAD = 230, 180, 44
    sw = PAD + len(PCTILES) * PANW
    sh = PAD + len(GRIDS) * PANH
    title = (f"Ellipse coverage — smallest→largest reachable draw per grid  "
             f"(white-bg #000 @ 0.2; clamp(alpha,beta)·d_far = {CLAMP})")
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{sw}" height="{sh}" '
         f'viewBox="0 0 {sw} {sh}">',
         f'<rect width="{sw}" height="{sh}" fill="#fafafa"/>',
         f'<text x="10" y="22" font-family="sans-serif" font-size="15" '
         f'font-weight="bold">{title}</text>']
    labels = ["smallest", "~40th pct", "~75th pct", "largest"]
    for ti, lab in enumerate(labels):
        s.append(f'<text x="{PAD+ti*PANW+PANW/2}" y="40" text-anchor="middle" '
                 f'font-family="sans-serif" font-size="13" font-weight="bold">'
                 f'{lab}</text>')
    cid = 0
    for gi, (cols, rows) in enumerate(GRIDS):
        ds, W, H = reachable_draws(cols, rows)
        py = PAD + gi * PANH
        s.append(f'<text x="8" y="{py+PANH/2}" font-family="sans-serif" '
                 f'font-size="13" font-weight="bold">{cols}x{rows}</text>')
        for ti, (cov, a, rx, ry, rot) in enumerate(at_percentiles(ds)):
            px = PAD + ti * PANW
            sc = min((PANW - 24) / W, (PANH - 44) / H)
            ox, oy = px + (PANW - W * sc) / 2, py + 34
            cid += 1
            cp = f"cp{cid}"
            s.append(f'<g transform="translate({ox},{oy}) scale({sc})">')
            s.append(f'<defs><clipPath id="{cp}"><rect x="0" y="0" '
                     f'width="{W}" height="{H}"/></clipPath></defs>')
            s.append(f'<rect x="0" y="0" width="{W}" height="{H}" '
                     f'fill="#ffffff" stroke="#999" stroke-width="{1/sc}"/>')
            for r in range(rows):
                for c in range(cols):
                    s.append(f'<rect x="{c*CELL_W}" y="{r*CELL_H}" '
                             f'width="{CELL_W}" height="{CELL_H}" fill="none" '
                             f'stroke="#ddd" stroke-width="{1/sc}"/>')
            s.append(f'<g clip-path="url(#{cp})"><ellipse cx="{a.x}" cy="{a.y}" '
                     f'rx="{rx}" ry="{ry}" '
                     f'transform="rotate({rot} {a.x} {a.y})" '
                     f'fill="#000000" fill-opacity="0.2"/></g></g>')
            s.append(f'<text x="{px+PANW/2}" y="{py+PANH-6}" '
                     f'text-anchor="middle" font-family="sans-serif" '
                     f'font-size="12" fill="#444">{cov*100:.0f}%</text>')
    s.append('</svg>')
    return "\n".join(s)


def main():
    global CLAMP
    name = ""
    if len(sys.argv) >= 3:
        CLAMP = (float(sys.argv[1]), float(sys.argv[2]))
        name = "_" + (sys.argv[3] if len(sys.argv) >= 4 else
                      f"{sys.argv[1]}_{sys.argv[2]}")
    out_dir = Path(__file__).resolve().parent.parent / ".cache"
    out_dir.mkdir(exist_ok=True)
    svg_path = out_dir / f"ellipse_view{name}.svg"
    png_path = out_dir / f"ellipse_view{name}.png"
    svg_path.write_text(build_svg())
    cairosvg.svg2png(url=str(svg_path), write_to=str(png_path), output_width=1100)
    print(f"wrote {png_path}  (clamp={CLAMP})")
    print(f"open with:  wslview {png_path.relative_to(out_dir.parent)}")


if __name__ == "__main__":
    main()
