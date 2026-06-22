"""
Shared library for the entviz documentation figures.

Both the academic paper (scripts/paper_figures.py → docs/assets/paper/) and the
algorithm spec (scripts/spec_figures.py → docs/assets/) build their figures from
this one module, so every figure shares a single house style and — crucially —
is generated from the live renderer rather than hand-drawn. That is what lets a
single drift test (tests/test_figures.py) prove the figures still match the
algorithm and the current SPEC_VERSION.

House style — "entviz-fig":
  * Clean page: white background, no figure border (the figure merges into the
    typeset page; the surrounding document supplies the numbered caption).
  * Desaturated chrome ink, NOT pure black; one muted slate-blue accent for
    leader lines and callouts. The entviz artwork itself keeps the full,
    saturated palette — color appears only where it carries meaning.
  * Labels/captions in DejaVu Sans (a humanist sans reliably installed here that
    cairosvg + fontconfig resolve natively). Literal entropy / hex / band-letter
    text reuses the renderer's own MONOSPACE_FONT_FAMILY so glyph metrics match
    a real entviz.

cairosvg is imported lazily inside build() so the SVG-building functions (and the
drift test that calls them) need only entviz + lxml (+ segno for the comparison
figure), not a system libcairo — cairosvg lives in the opt-in `render` group.
"""
import os
import re
import sys

from lxml import etree

REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(REPO_ROOT, "src"))

from entviz import SPEC_VERSION  # noqa: E402
from entviz.pipeline import render  # noqa: E402
from entviz.renderer import MONOSPACE_FONT_FAMILY  # noqa: E402
from entviz.colors import POSSIBLE_EDGE_COLORS  # noqa: E402

GALLERY = os.path.join(REPO_ROOT, "docs", "assets", "gallery")
SVGNS = "{http://www.w3.org/2000/svg}"

# Set by each generator before it builds, so the figure's data-generator stamp
# names the script that produced it.
GENERATOR = "scripts/figlib.py"

# ---- house style ----------------------------------------------------------
SANS = "'DejaVu Sans', 'Bitstream Vera Sans', Verdana, sans-serif"
MONO = MONOSPACE_FONT_FAMILY
INK = "#2b2b33"      # primary ink (titles, key strokes) — slate, not black
INK2 = "#5a5f6a"     # secondary text
HAIR = "#c9cdd4"     # hairlines / faint grids
ACCENT = "#3f5b73"   # the one muted accent: leader lines, callout dots
WARN = "#b00020"     # sub-threshold / failure flag
OK = "#0a7d3f"       # meets-floor flag
BLUE = "#1d4ed8"     # the renderer's blank-map "smallest" dot color
PAGE = "#ffffff"

T_TITLE = 16
T_PANEL = 14         # (a)/(b) panel labels, bold
T_LABEL = 13         # feature labels
T_SMALL = 12         # secondary notes (>= 10pt at 1:1)

_DPI = 96


def geometry(font_size_pt=12):
    """The v6 cell/grid geometry, mirroring docs/spec.md and entviz.pipeline.

    Returned in pixels for the given point size. tests/test_figures.py asserts
    these match the dimensions a real render() actually emits, so the geometry
    figure (cell-layout) cannot drift from the renderer.
    """
    fs = font_size_pt * _DPI / 72
    return {
        "font_size_px": fs,
        "nucleus_width": 3 * fs,
        "nucleus_height": 1.25 * fs,
        "box_width": 0.375 * fs,
        "box_height": 0.625 * fs,
        "cell_width": 3.75 * fs,
        "cell_height": 2.5 * fs,
        "bar_width": 1.25 * fs,
        "gm": 0.625 * fs / 2,
    }


def loc(e):
    return etree.QName(e).localname


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ---- primitive SVG emitters ----------------------------------------------
def text(x, y, s, size=T_LABEL, family=SANS, anchor="start", weight="normal",
         fill=INK, italic=False, preserve=False):
    fam = family.replace('"', "&quot;")
    style = "" if not italic else ' font-style="italic"'
    # xml:space="preserve" stops SVG renderers from collapsing runs of interior
    # whitespace (and trimming leading/trailing spaces). Needed for monospace
    # ASCII art (e.g. the randomart panel), where every space is load-bearing
    # and a collapsed run misaligns the |...| frame.
    sp = ' xml:space="preserve"' if preserve else ""
    return (f'<text x="{x:.2f}" y="{y:.2f}" font-family="{fam}" '
            f'font-size="{size}px" font-weight="{weight}" text-anchor="{anchor}"'
            f'{style} fill="{fill}"{sp}>{esc(s)}</text>')


def line(x1, y1, x2, y2, stroke=ACCENT, w=1.0, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
            f'stroke="{stroke}" stroke-width="{w}"{d}/>')


def rect(x, y, w, h, fill="none", stroke="none", sw=1.0, rx=0, dash=None):
    r = f' rx="{rx}" ry="{rx}"' if rx else ""
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{r}{d}/>')


def dot(x, y, r=3.0, fill=ACCENT):
    return f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{r}" fill="{fill}"/>'


def leader(tx, ty, lx, ly, label, anchor="start", size=T_LABEL, weight="normal",
           fill=INK, knee=None):
    """Leader line from a target point (tx,ty) to a label at (lx,ly)."""
    out = []
    if knee is not None:
        out.append(line(tx, ty, knee[0], knee[1]))
        out.append(line(knee[0], knee[1], lx, ly))
    else:
        out.append(line(tx, ty, lx, ly))
    out.append(dot(tx, ty, 2.6))
    ty_off = ly - 4 if anchor != "middle" else ly
    out.append(text(lx, ty_off, label, size=size, anchor=anchor, weight=weight, fill=fill))
    return "".join(out)


def order_by_target_y(rows, ykey):
    """Reorder annotation rows so their leader lines don't cross.

    Leaders run from a target point to a label stacked top-to-bottom on the
    right. Two leaders cross whenever a lower target is wired to a higher label.
    Stable-sorting the rows by target y (so the topmost target gets the topmost
    label slot) makes the target order match the slot order and removes every
    crossing. `ykey(row)` returns the row's target y.
    """
    return sorted(rows, key=ykey)


def dim(x1, y1, x2, y2, label, fill=INK2, size=T_SMALL, place=None):
    """A dimension line with end ticks and a label.

    `place` controls label side: horizontal lines accept "above"/"below"
    (default "above"); vertical lines accept "left"/"right" (default "left").
    """
    out = [line(x1, y1, x2, y2, stroke=fill, w=1.0)]
    if y1 == y2:  # horizontal: vertical ticks
        out += [line(x1, y1 - 4, x1, y1 + 4, stroke=fill), line(x2, y2 - 4, x2, y2 + 4, stroke=fill)]
        ly = y1 - 6 if (place or "above") == "above" else y1 + 6 + size
        out.append(text((x1 + x2) / 2, ly, label, size=size, anchor="middle", fill=fill))
    else:  # vertical: horizontal ticks
        out += [line(x1 - 4, y1, x1 + 4, y1, stroke=fill), line(x2 - 4, y2, x2 + 4, y2, stroke=fill)]
        if (place or "left") == "left":
            out.append(text(x1 - 8, (y1 + y2) / 2 + 4, label, size=size, anchor="end", fill=fill))
        else:
            out.append(text(x1 + 8, (y1 + y2) / 2 + 4, label, size=size, anchor="start", fill=fill))
    return "".join(out)


def hbrace(x0, x1, y, label, depth=8, fill=INK2, size=T_SMALL):
    """A simple downward square bracket spanning [x0,x1] at height y, labelled below."""
    xm = (x0 + x1) / 2
    out = [
        line(x0, y, x0, y + depth, stroke=fill, w=1.0),
        line(x0, y + depth, x1, y + depth, stroke=fill, w=1.0),
        line(x1, y, x1, y + depth, stroke=fill, w=1.0),
        line(xm, y + depth, xm, y + depth + 4, stroke=fill, w=1.0),
        text(xm, y + depth + 4 + size, label, size=size, anchor="middle", fill=fill, weight="bold"),
    ]
    return "".join(out)


def approx_w(s, size, mono=False):
    """Rough rendered width of a label, for sizing canvases so captions fit."""
    return len(s) * size * (0.62 if mono else 0.55)


def caption(W, y, s, size=T_SMALL, fill=INK2):
    return text(W / 2, y, s, size=size, anchor="middle", fill=fill)


def svg_open(w, h):
    # data-spec-version stamps the algorithm/spec revision the figure was built
    # against; the drift test asserts it equals the current SPEC_VERSION, so a
    # version bump forces regeneration even if the pixels happen not to change.
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.2f}" '
            f'height="{h:.2f}" viewBox="0 0 {w:.2f} {h:.2f}" font-family="{SANS}" '
            f'data-spec-version="{SPEC_VERSION}" data-generator="{GENERATOR}">'
            + rect(0, 0, w, h, fill=PAGE))


def svg_close():
    return "</svg>"


# ---- embed entviz / gallery artwork --------------------------------------
def _inner(svg_text):
    root = etree.fromstring(svg_text.encode())
    w = float(root.get("width"))
    h = float(root.get("height"))
    vb = root.get("viewBox") or f"0 0 {w} {h}"
    inner = b"".join(etree.tostring(c) for c in root).decode()
    return inner, w, h, [float(t) for t in vb.split()]


def place(svg_text, x, y, dest_w, crop=None):
    """Embed artwork as a nested <svg>, optionally cropped to `crop`=(sx,sy,sw,sh).

    Returns (nested_svg, dest_h, mapper) where mapper(ex,ey) -> figure coords.
    """
    inner, w, h, vb = _inner(svg_text)
    sx, sy, sw, sh = crop if crop else vb
    scale = dest_w / sw
    dest_h = sh * scale
    nested = (f'<svg x="{x:.2f}" y="{y:.2f}" width="{dest_w:.2f}" height="{dest_h:.2f}" '
              f'viewBox="{sx:.3f} {sy:.3f} {sw:.3f} {sh:.3f}">{inner}</svg>')

    def mp(ex, ey):
        return (x + (ex - sx) * scale, y + (ey - sy) * scale)
    return nested, dest_h, mp


def gallery(name):
    with open(os.path.join(GALLERY, name)) as fh:
        return fh.read()


# ---- parsing helpers -------------------------------------------------------
def parse(svg_text):
    return etree.fromstring(svg_text.encode())


def marker_center(el):
    """(cx, cy) of a blank-cell-map marker. The minftok marker is a <circle>
    (cx/cy attributes); the maxftok marker is the v8 plus <path>, whose centre
    is parsed from its `d` ("M cx-arm,cy H cx+arm M cx,cy-arm V cy+arm").

    Fails loudly (ValueError) rather than with a bare IndexError/ValueError if
    handed anything but those two shapes — so a future change to the plus
    geometry surfaces a clear message here instead of a cryptic crash mid-figure
    (this annotation code is exactly what broke when the marker shape changed)."""
    cx, cy = el.get("cx"), el.get("cy")
    if cx is not None and cy is not None:
        return float(cx), float(cy)
    # Expected plus path: "M cx-arm,cy H cx+arm M cx,cy-arm V cy+arm" → 8 tokens.
    d = el.get("d", "")
    parts = d.split()
    if len(parts) != 8 or parts[0] != "M" or parts[4] != "M":
        raise ValueError(
            f"marker_center: element is neither a <circle> (cx/cy) nor the "
            f"expected plus <path>; got tag={el.tag!r} d={d!r}")
    try:
        return float(parts[5].split(",")[0]), float(parts[1].split(",")[1])
    except (IndexError, ValueError) as e:
        raise ValueError(f"marker_center: cannot parse plus centre from d={d!r}") from e


def cells(root):
    return [g for g in root.iter(SVGNS + "g") if g.get("data-channel") == "cell"]


def nucleus(cell):
    """First rect of a cell group (the nucleus / blank outline)."""
    for r in cell.iter(SVGNS + "rect"):
        return r
    return None


def rect_box(r):
    return (float(r.get("x")), float(r.get("y")),
            float(r.get("width")), float(r.get("height")))


_BOX_SUBPATH_RE = re.compile(r"M(-?[\d.]+) (-?[\d.]+)h(-?[\d.]+)v(-?[\d.]+)")


def surround_boxes(root):
    """v10: surround boxes are subpaths of per-cell <path>s (one box per
    `M x y h w v h h-w z`), not individual rects. Recover each box as a dict
    with x/y/width/height/fill so a caller can locate a representative box."""
    grid = [g for g in root.iter(SVGNS + "g") if g.get("data-channel") == "grid"][0]
    out = []
    for p in grid.iter(SVGNS + "path"):
        # skip the blank-map plus marker (the only other <path> in the grid)
        if p.get("data-blank-map-max") is not None or p.get("data-blank-map-min") is not None:
            continue
        fill = p.get("fill")
        for m in _BOX_SUBPATH_RE.finditer(p.get("d", "")):
            x, y, w, h = map(float, m.groups())
            out.append({"x": x, "y": y, "width": w, "height": h, "fill": fill})
    return out


# ---- CVD color maths (Machado, Oliveira & Fernandes 2009, severity 1.0) --
NAMES = ["white", "gold", "red", "blue", "black"]
PALETTE = dict(zip(NAMES, POSSIBLE_EDGE_COLORS))

CVD_MATRICES = {
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
        g = round(_gamma(_Y(lin)) * 255)
        return f"#{g:02x}{g:02x}{g:02x}"
    m = CVD_MATRICES[vision]
    v = [max(0.0, min(1.0, sum(m[i][j] * lin[j] for j in range(3)))) for i in range(3)]
    return "#" + "".join(f"{round(_gamma(c) * 255):02x}" for c in v)


def sim_lstar(hex_color, vision):
    return lstar(sim_hex(hex_color, vision)) if vision != "normal" else lstar(hex_color)


def min_pair(vision):
    import itertools
    L = {n: sim_lstar(PALETTE[n], vision) for n in NAMES}
    a, b = min(itertools.combinations(NAMES, 2), key=lambda p: abs(L[p[0]] - L[p[1]]))
    return a, b, abs(L[a] - L[b])


# ---- SSH randomart (the "drunken bishop" walk) ----------------------------
def drunken_bishop(fp_bytes, cols=17, rows=9):
    field = [[0] * cols for _ in range(rows)]
    x, y = cols // 2, rows // 2
    for byte in fp_bytes:
        b = byte
        for _ in range(4):
            d = b & 0b11
            dx = -1 if (d & 1) == 0 else 1
            dy = -1 if (d & 2) == 0 else 1
            x = min(cols - 1, max(0, x + dx))
            y = min(rows - 1, max(0, y + dy))
            field[y][x] += 1
            b >>= 2
    chars = " .o+=*BOX@%&#/^SE"
    sx, sy = cols // 2, rows // 2
    out = []
    for r in range(rows):
        row_chars = []
        for c in range(cols):
            if (c, r) == (sx, sy):
                row_chars.append("S")
            elif (c, r) == (x, y):
                row_chars.append("E")
            else:
                row_chars.append(chars[min(field[r][c], 14)])
        out.append("".join(row_chars))
    return out


# ---- build runner ----------------------------------------------------------
def build(figures, out_dir, png=True):
    """Write each figure's SVG (and, if png, a 2x PNG) into out_dir.

    png=True for the paper (its PDF build wants bitmaps); png=False for the spec,
    which is web-only and references the SVGs directly. cairosvg is imported
    lazily, so a png=False build needs no libcairo.
    """
    os.makedirs(out_dir, exist_ok=True)
    cairosvg = None
    if png:
        import cairosvg as _c
        cairosvg = _c
    for fn in figures:
        name, svg = fn()
        svg_path = os.path.join(out_dir, name + ".svg")
        with open(svg_path, "w") as fh:
            fh.write(svg + "\n")
        if png:
            png_path = os.path.join(out_dir, name + ".png")
            cairosvg.svg2png(bytestring=svg.encode(), write_to=png_path, scale=2.0,
                             background_color="white")
            print(f"wrote {svg_path}  +  {os.path.basename(png_path)}")
        else:
            print(f"wrote {svg_path}")
