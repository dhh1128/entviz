"""
Generate the palette figures used by the spec and the academic paper:

  docs/assets/palette-swatch.svg   the five palette colours with name/hex/L*
  docs/assets/palette-cvd.svg      the palette under normal vision + the three
                                   dichromacies + achromatopsia (lightness only)

Both are hand-written SVG (no rasteriser, no numpy) so they stay diffable and
regenerate in milliseconds. All label text is sized so it renders at >= 10 pt
at the SVG's nominal (1:1) size (>= 14 px at 96 dpi).

Run from the repo root:
    uv run python scripts/palette_figures.py        (or: PYTHONPATH=src python ...)

CVD simulation: Machado, Oliveira & Fernandes (2009), severity 1.0.
"""
import itertools
import os

from entviz.colors import POSSIBLE_EDGE_COLORS
from entviz.renderer import MONOSPACE_FONT_FAMILY

REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
ASSETS = os.path.join(REPO_ROOT, "docs", "assets")

# Cross-platform sans stack for labels; monospace (shared with the renderer)
# for hex codes so digits line up.
SANS = "'Helvetica Neue', Arial, 'Segoe UI', Roboto, 'DejaVu Sans', sans-serif"
MONO = MONOSPACE_FONT_FAMILY

NAMES = ["white", "gold", "red", "blue", "black"]
PALETTE = dict(zip(NAMES, POSSIBLE_EDGE_COLORS))

CVD_MATRICES = {  # Machado et al. 2009, severity 1.0
    "protan": [[0.152286, 1.052583, -0.204868],
               [0.114503, 0.786281, 0.099216],
               [-0.003882, -0.048116, 1.051998]],
    "deutan": [[0.367322, 0.860646, -0.227968],
               [0.280085, 0.672501, 0.047413],
               [-0.011820, 0.042940, 0.968881]],
    "tritan": [[1.255528, -0.076749, -0.178779],
               [-0.078411, 0.930809, 0.147602],
               [0.004733, 0.691367, 0.303900]],
}
VISION_ROWS = [
    ("normal", "Normal vision"),
    ("protan", "Protanopia"),
    ("deutan", "Deuteranopia"),
    ("tritan", "Tritanopia"),
    ("achromat", "Achromatopsia"),
]


# ---- colour math (pure Python) ----
def _ungamma(c):
    c /= 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _gamma(c):
    c = max(0.0, min(1.0, c))
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def _linear(hex_color):
    return [_ungamma(int(hex_color[i:i + 2], 16)) for i in (1, 3, 5)]


def _Y(lin):
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def lstar(hex_color):
    Y = _Y(_linear(hex_color))
    return 116 * (Y ** (1 / 3)) - 16 if Y > 0.008856 else 903.3 * Y


def sim_hex(hex_color, vision):
    """Return the hex a viewer with `vision` perceives for `hex_color`."""
    if vision == "normal":
        return hex_color
    lin = _linear(hex_color)
    if vision == "achromat":
        # Lightness-only: collapse to the grey of equal luminance.
        g = round(_gamma(_Y(lin)) * 255)
        return f"#{g:02x}{g:02x}{g:02x}"
    m = CVD_MATRICES[vision]
    v = [max(0.0, min(1.0, sum(m[i][j] * lin[j] for j in range(3)))) for i in range(3)]
    return "#" + "".join(f"{round(_gamma(c) * 255):02x}" for c in v)


def sim_lstar(hex_color, vision):
    return lstar(sim_hex(hex_color, vision)) if vision != "normal" else lstar(hex_color)


def min_pair(vision):
    L = {n: sim_lstar(PALETTE[n], vision) for n in NAMES}
    a, b = min(itertools.combinations(NAMES, 2), key=lambda p: abs(L[p[0]] - L[p[1]]))
    return a, b, abs(L[a] - L[b])


# ---- SVG helpers ----
def _esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _text(x, y, s, size, family=SANS, anchor="middle", weight="normal", fill="#111"):
    family = family.replace('"', "&quot;")  # safe inside a double-quoted attribute
    return (f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}px" '
            f'font-weight="{weight}" text-anchor="{anchor}" fill="{fill}">{_esc(s)}</text>')


def _rect(x, y, w, h, fill, stroke="#888", sw=1):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="{sw}"/>')


# ---- figure 1: swatch ----
def build_swatch_svg():
    sw_w, sw_h, gap, mx, top = 120, 96, 22, 28, 56
    n = len(NAMES)
    width = mx * 2 + n * sw_w + (n - 1) * gap
    height = top + sw_h + 106
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
           f'viewBox="0 0 {width} {height}" font-family="{SANS}">',
           _rect(0, 0, width, height, "#ffffff", stroke="none"),
           _text(width / 2, 32, "entviz palette — spaced by CIELAB lightness (L*)",
                 18, weight="bold")]
    for i, name in enumerate(NAMES):
        x = mx + i * (sw_w + gap)
        hexv = PALETTE[name]
        out.append(_rect(x, top, sw_w, sw_h, hexv))
        cx = x + sw_w / 2
        out.append(_text(cx, top + sw_h + 26, name, 16, weight="bold"))
        out.append(_text(cx, top + sw_h + 48, hexv, 14, family=MONO, fill="#333"))
        out.append(_text(cx, top + sw_h + 68, f"L*={lstar(hexv):.0f}", 14, fill="#333"))
    out.append(_text(width / 2, height - 12,
                     "indices 0–3 are background candidates; black (index 4) is "
                     "always an edge colour, never the background",
                     14, fill="#555"))
    out.append("</svg>")
    return "\n".join(out)


# ---- figure 2: CVD grid ----
def build_cvd_svg():
    label_w, cell_w, cell_h, mx, top, annot_w = 170, 96, 64, 24, 64, 232
    n = len(NAMES)
    grid_x = mx + label_w
    width = grid_x + n * cell_w + annot_w + mx
    height = top + len(VISION_ROWS) * cell_h + 40
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
           f'viewBox="0 0 {width} {height}" font-family="{SANS}">',
           _rect(0, 0, width, height, "#ffffff", stroke="none"),
           _text(mx, 32, "entviz palette under colour-vision deficiency "
                         "(Machado et al. 2009, severity 1.0)", 18, anchor="start", weight="bold")]
    # column headers
    for j, name in enumerate(NAMES):
        out.append(_text(grid_x + j * cell_w + cell_w / 2, top - 14, name, 14, weight="bold"))
    out.append(_text(grid_x + n * cell_w + annot_w / 2, top - 14,
                     "closest pair (ΔL*)", 14, weight="bold", fill="#555"))
    for r, (vision, vlabel) in enumerate(VISION_ROWS):
        y = top + r * cell_h
        out.append(_text(mx, y + cell_h / 2 + 5, vlabel, 15, anchor="start", weight="bold"))
        for j, name in enumerate(NAMES):
            out.append(_rect(grid_x + j * cell_w, y, cell_w, cell_h, sim_hex(PALETTE[name], vision)))
        a, b, d = min_pair(vision)
        warn = d < 20
        txt = f"{a}/{b}  ΔL*={d:.0f}" + ("  ⚠" if warn else "  ✓")
        out.append(_text(grid_x + n * cell_w + 14, y + cell_h / 2 + 5, txt, 15,
                         anchor="start", weight="bold" if warn else "normal",
                         fill="#b00" if warn else "#070"))
    out.append(_text(mx, height - 12,
                     "✓ = all pairs ≥ 20 ΔL* (design floor)   "
                     "⚠ = an unavoidable sub-floor pair; falls back to the "
                     "blue–yellow axis + color-bar letters",
                     14, anchor="start", fill="#555"))
    out.append("</svg>")
    return "\n".join(out)


def main():
    os.makedirs(ASSETS, exist_ok=True)
    for fname, svg in (("palette-swatch.svg", build_swatch_svg()),
                       ("palette-cvd.svg", build_cvd_svg())):
        path = os.path.join(ASSETS, fname)
        with open(path, "w") as fh:
            fh.write(svg + "\n")
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
