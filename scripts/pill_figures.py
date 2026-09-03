"""
Generate the figures for the terminal pill design record (docs/terminal-pill.md).

Like the paper and spec suites, these are built from scripts/figlib.py and from
live code — every painted pill here comes from a real entviz.terminal.pill()
call, never from hand-transcribed glyphs. tests/test_figures.py keeps them
honest. Output is SVG-only, written into docs/assets/pill/.

    PYTHONPATH=src .venv/bin/python scripts/pill_figures.py

Why these figures exist at all: the pill's whole argument is that a cell's color
and its characters are the same 24 bits in two notations, and that the color bar
and separators are the only channels that see the elided region. A monochrome
code block cannot make either point — §5's avalanche pair is two values whose
displayed characters are *identical* and which differ only in color. The doc said
"colors omitted here" everywhere it mattered most.

Glyphs are drawn as GEOMETRY, not as text. A block element is a filled rect over
the bottom n/8 of the cell and a braille pattern is up to eight dots on a 2x4
grid — which is what a terminal actually paints, and is immune to whether the
reader's browser has a font covering U+2580-U+259F and U+2800-U+28FF. Only the
token text (ASCII) is set as real monospace type.

The SPEC_VERSION stamp figlib.svg_open() applies is about the *algorithm*, not
about conformance: the pill is non-normative and carries no obligations (see the
doc's header), but its nucleus colors, edge palette, and color-bar bands are all
derived from the spec'd algorithm, so a spec bump genuinely can change these
figures and should force their regeneration.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import figlib  # noqa: E402
from figlib import *  # noqa: E402,F401,F403

from entviz.colors import _hex_to_rgb, oklab_lightness  # noqa: E402
from entviz.terminal import palette, pill, whois  # noqa: E402
from entviz.terminal.pill import (BAR, CELL, EIGHTHS, GAP,  # noqa: E402
                                  SEPARATOR, _read, _separator_span,
                                  _shown_indices)

GEN = "scripts/pill_figures.py"
figlib.GENERATOR = GEN

OUT = os.path.join(figlib.REPO_ROOT, "docs", "assets", "pill")

#: The gallery's Ed25519 verification key — the doc's running example (§1).
AID = "DKxy2sgzfplyr_tgwIxS19f2OchFHtLwPWD3v4oYimBx"

#: The avalanche quartet (§5): one UUID and its three single-character
#: neighbours. A and "mid" display the same characters and differ only in color.
UUID_A = "550e8400-e29b-41d4-a716-446655440000"
UUID_MID = "550e8400-e29b-41d5-a716-446655440000"
UUID_FIRST = "450e8400-e29b-41d4-a716-446655440000"
UUID_LAST = "550e8400-e29b-41d4-a716-446655440001"

#: Terminal cell metrics. A real terminal cell is about half as wide as it is
#: tall; the mono advance width of most fonts is ~0.6em, so the type size falls
#: out of the column width rather than being chosen independently.
CW = 13.0
CH = 26.0
TYPE = CW / 0.6

#: Braille dot -> (column, row) on the standard 2x4 cell. Dots 1-3 run down the
#: left column, 4-6 down the right, and 7/8 are the bottom row added for
#: 8-dot computer braille.
_DOT_GRID = {0x01: (0, 0), 0x02: (0, 1), 0x04: (0, 2), 0x40: (0, 3),
             0x08: (1, 0), 0x10: (1, 1), 0x20: (1, 2), 0x80: (1, 3)}


# ---- terminal-cell drawing -------------------------------------------------
def _block(x, y, level, fg, bg, scale=1.0):
    """One lower-block glyph: the bottom `level`/8 of the cell in `fg`."""
    cw, ch = CW * scale, CH * scale
    out = [rect(x, y, cw, ch, fill=bg)] if bg else []
    if level:
        h = ch * level / 8.0
        out.append(rect(x, y + ch - h, cw, h, fill=fg))
    return "".join(out)


def _braille(x, y, bits, fg, bg, scale=1.0):
    """One braille pattern, drawn as dots rather than set as type."""
    cw, ch = CW * scale, CH * scale
    out = [rect(x, y, cw, ch, fill=bg)] if bg else []
    for bit, (col, row) in _DOT_GRID.items():
        if bits & bit:
            out.append(dot(x + cw * (0.3 + 0.4 * col),
                           y + ch * (0.17 + 0.22 * row), cw * 0.15, fill=fg))
    return "".join(out)


def _glyph(x, y, char, fg, bg, scale=1.0):
    """Dispatch one character to the way a terminal would paint it."""
    if char in EIGHTHS:
        return _block(x, y, EIGHTHS.index(char), fg or figlib.INK, bg, scale)
    if 0x2800 <= ord(char) <= 0x28FF:
        return _braille(x, y, ord(char) - 0x2800, fg or figlib.INK, bg, scale)
    cw, ch = CW * scale, CH * scale
    out = [rect(x, y, cw, ch, fill=bg)] if bg else []
    out.append(text(x + cw / 2, y + ch * 0.72, char, size=TYPE * scale,
                    family=MONO, anchor="middle", fill=fg or figlib.INK))
    return "".join(out)


def line_spans(spans, x, y, color=True):
    """Paint a Pill's spans as a row of terminal cells. Returns (svg, width).

    `color=False` is the `none` rung: mono glyphs, no paint, so the figure shows
    exactly what a reader of a color-stripped pill sees.
    """
    out, cx = [], x
    for span in spans:
        chars = span.text if color else (span.mono or span.text)
        for char in chars:
            out.append(_glyph(cx, y, char,
                              span.fg if color else None,
                              span.bg if color else None))
            cx += CW
    return "".join(out), cx - x



def swatch(x, y, w, h, fill, label=None, size=T_SMALL, lfill=INK2):
    """A color chip with a hairline, so white reads as a chip and not as page."""
    out = [rect(x, y, w, h, fill=fill, stroke=HAIR, sw=1.0)]
    if label:
        out.append(text(x + w + 7, y + h / 2 + size * 0.36, label, size=size,
                        fill=lfill))
    return "".join(out)


class Fig:
    """A figure that sizes its own canvas.

    Every figure here is a stack of rows whose width depends on text that only
    the font knows the true width of, so hardcoding a canvas clips captions on
    one figure and leaves a band of dead page on the next. Tracking the extent
    as elements go in costs nothing and makes the canvas a consequence of the
    content instead of a number to keep in sync by hand.
    """

    def __init__(self, pad=30):
        self.body, self.pad = [], pad
        self.right = self.bottom = 0.0

    def add(self, svg, right=None, bottom=None):
        self.body.append(svg)
        self.right = max(self.right, right or 0.0)
        self.bottom = max(self.bottom, bottom or 0.0)
        return self

    def label(self, x, y, s, size=T_SMALL, fill=INK2, **kw):
        """Sans text, extent included."""
        return self.add(text(x, y, s, size=size, fill=fill, **kw),
                        x + approx_w(s, size), y + 6)

    def mono(self, x, y, s, size=T_SMALL, fill=INK2, **kw):
        """Monospace text. Never put an arrow or any other non-ASCII glyph in
        here — the mono chain leads with web fonts that no build box installs,
        so anything outside the base ASCII coverage of the fallback renders as
        tofu in the PNG path."""
        return self.add(text(x, y, s, size=size, family=MONO, fill=fill, **kw),
                        x + approx_w(s, size, mono=True), y + 6)

    def chip(self, x, y, w, h, fill, text_=None, size=T_SMALL, lfill=INK2):
        return self.add(swatch(x, y, w, h, fill, text_, size, lfill),
                        x + w + (approx_w(text_, size) + 12 if text_ else 0),
                        y + h)

    def pill(self, value, x, y, color=True, fn=pill):
        p = fn(value)
        art, w = line_spans(p.spans, x, y, color=color)
        self.add(art, x + w, y + CH)
        return p, w

    def close(self, name, note=None):
        w, h = self.right + self.pad, self.bottom + self.pad
        body = list(self.body)
        if note:
            w = max(w, approx_w(note, T_SMALL) + 2 * self.pad)
            h += 22
            body.append(caption(w, h - 12, note))
        return name, svg_open(w, h) + "".join(body) + svg_close()


# ---- figures ---------------------------------------------------------------
def fig_pill_and_whois():
    """(1) The running example, painted: the pill and its whois line."""
    f = Fig()
    x, y = 30, 30
    for i, (label, fn) in enumerate([("the pill", pill),
                                     ("the whois line", whois)]):
        ry = y + i * (CH + 18)
        _, w = f.pill(AID, x, ry, fn=fn)
        f.label(x + w + 20, ry + CH * 0.7, label)
    f.label(x, f.bottom + 26, "value: " + AID, fill=INK)
    return f.close("pill-and-whois",
                   "Both open with the same four-cell prefix, so a pill and its "
                   "whois line can be tied together by eye.")


def fig_pill_anatomy():
    """(2) The pill spread out, with the three kinds of cell called out."""
    f = Fig()
    p = pill(AID)
    x, y = 30, 30
    # The four bar spans are one visual unit (flush in the real pill too); every
    # other span becomes its own group so a leader can point at it.
    units = ([[s for s in p.spans if s.channel == BAR]]
             + [[s] for s in p.spans if s.channel not in (BAR, GAP)])
    labels = {
        BAR: "color bar: one cell per band, filled to its share of the tallest",
        SEPARATOR: "separator: a summary of the cells this pill is not showing",
        CELL: "cell: the token's own text, on the token's own color",
    }
    groups, cx = [], x
    for unit in units:
        art, w = line_spans(unit, cx, y)
        f.add(art, cx + w, y + CH)
        groups.append((unit[0].channel, cx + w / 2))
        cx += w + 26

    seen, rows = set(), []
    for channel, mid in groups:
        if channel not in seen:
            seen.add(channel)
            rows.append((mid, labels[channel]))
    # Rightmost target takes the TOP label slot. Each label then runs rightward
    # from its own leader, and every other leader terminates in a row above it,
    # so no leader line ever crosses label text. (Left-to-right ordering does
    # the opposite: the first, longest label is struck through twice.)
    rows.sort(reverse=True)
    ly = y + CH + 30
    for i, (mid, label) in enumerate(rows):
        ty = ly + i * 24
        f.add(line(mid, y + CH + 3, mid, ty - 9, stroke=ACCENT))
        f.add(dot(mid, y + CH + 3, 2.6))
        f.label(mid + 9, ty, label)
    return f.close("pill-anatomy",
                   "Spread out to be labelled; the real string has one space "
                   "after the bar and nothing between a cell and its separator.")


def fig_pill_color_bar():
    """(3) Why the bar normalizes to the tallest band, not to the sum."""
    f = Fig()
    read = _read(AID)
    weights = [b.weight for b in read.bands]
    tallest, total = max(weights), sum(weights)
    x, y, col = 30, 46, 320
    panels = [("max-normalized (what the pill draws)",
               [round(8 * w / tallest) for w in weights]),
              ("sum-normalized (the rejected alternative)",
               [round(8 * w / total) for w in weights])]
    for i, (title, heights) in enumerate(panels):
        px = x + i * col
        f.label(px, y - 14, title, weight="bold", fill=INK)
        for j, (band, h) in enumerate(zip(read.bands, heights)):
            f.add(_block(px + j * CW, y, h, band.color, read.background),
                  px + (j + 1) * CW, y + CH)
        f.mono(px, y + CH + 22, "fills  " + "  ".join(f"{h}/8" for h in heights))

    ny = y + CH + 52
    f.label(x, ny, "band weights (count to the 4th), in first-appearance order:",
            fill=INK)
    for j, band in enumerate(read.bands):
        f.chip(x + j * 160, ny + 12, 16, 16, band.color,
               f"{band.weight / tallest:.2f} of the tallest")
    f.chip(x, ny + 46, 16, 16, read.background,
           "the entviz background, which every bar cell is painted on")
    f.label(x, ny + 84, "It is removed from the edge palette, so no band is "
            "ever painted over itself.")
    return f.close("pill-color-bar",
                   "Four bars adding to 8 spend nearly the whole range on the "
                   "constraint; normalizing to the tallest preserves the ratios "
                   "and uses the full range.")


def fig_pill_separator():
    """(4) How one block glyph summarizes the cells an ellipsis hides."""
    f = Fig()
    read = _read(AID)
    shown = _shown_indices(read)
    run = read.cells[shown[0] + 1:shown[1]]
    sep = _separator_span(run)
    tally = {}
    for cell in run:
        tally[cell.edge] = tally.get(cell.edge, 0) + cell.boxes
    least, greatest = min(tally.values()), max(tally.values())

    x, y = 30, 44
    f.label(x, y - 14, "the cells the first ellipsis hides", weight="bold",
            fill=INK)
    step = CW * len(run[0].text) + 22
    for i, cell in enumerate(run):
        cx = x + i * step
        art, w = line_spans([type(sep)(cell.text, CELL, cell.ink, cell.nucleus,
                                       None)], cx, y)
        f.add(art, cx + w, y + CH)
        f.chip(cx, y + CH + 8, w, 9, cell.edge)
        f.mono(cx, y + CH + 32, f"{cell.boxes} boxes")
    f.label(x, y + CH + 58, "each hidden cell, the surround edge color it takes "
            "from its nucleus, and how many of its 24 boxes the fingerprint fills")

    ty = y + CH + 92
    f.label(x, ty + 12, "tallied by edge color:", fill=INK)
    for i, (color, n) in enumerate(sorted(tally.items(), key=lambda kv: -kv[1])):
        f.chip(x + 160 + i * 110, ty, 16, 16, color, f"{n} boxes")

    # Drawn oversize: at one column wide the 2/8 foreground sliver that carries
    # the ratio is a hairline, and the ratio is the whole point of the glyph.
    ry = ty + 46
    scale = 2.4
    f.label(x, ry + CH * scale / 2, "the one block that stands for all of them:",
            fill=INK)
    bx = x + 250
    # Hairline: this glyph's foreground is often white, and white fill on a white
    # page reads as the glyph having stopped early rather than as its rarest
    # color. The outline restores the cell's true extent.
    f.add(_glyph(bx, ry, sep.text, sep.fg, sep.bg, scale)
          + rect(bx, ry, CW * scale, CH * scale, stroke=HAIR, sw=1.0),
          bx + CW * scale, ry + CH * scale)
    f.label(bx + CW * scale + 18, ry + CH * scale / 2 - 8,
            "background = the largest tally, foreground = the smallest")
    f.mono(bx + CW * scale + 18, ry + CH * scale / 2 + 12,
           f"fill = {least}/{greatest} rounds to {EIGHTHS.index(sep.text)}/8")
    return f.close("pill-separator",
                   "It costs zero columns, and is the pill's only look at a "
                   "region the displayed cells cannot see.")


def fig_pill_palette_256():
    """(5) The five spec colors and the 256 entries pinned to stand for them."""
    f = Fig()
    names = [("white", "#ffffff"), ("gold", "#e7be00"), ("red", "#ff3f2f"),
             ("blue", "#2f3fbf"), ("black", "#000000")]
    x, y, rh = 30, 52, 34
    for col, head in ((x, "spec"), (x + 230, "256"), (x + 460, "Oklab L")):
        f.label(col, y - 14, head, weight="bold", fill=INK)
    for i, (name, spec_hex) in enumerate(names):
        ry = y + i * rh
        idx = palette.PALETTE_256[spec_hex]
        approx = palette.rgb_of(idx)
        f.chip(x, ry, 26, 22, spec_hex, f"{name}  {spec_hex}")
        f.label(x + 205, ry + 15, "→", fill=HAIR)
        f.chip(x + 230, ry, 26, 22, approx, f"{idx}  {approx}")
        f.mono(x + 460, ry + 15, f"{oklab_lightness(_hex_to_rgb(spec_hex)):.3f}")
        f.label(x + 505, ry + 15, "→", fill=HAIR)
        f.mono(x + 525, ry + 15, f"{oklab_lightness(_hex_to_rgb(approx)):.3f}")

    ny = y + len(names) * rh + 24
    red = oklab_lightness(_hex_to_rgb(palette.rgb_of(palette.PALETTE_256["#ff3f2f"])))
    f.label(x, ny, "Gold is pinned, not quantized — nearest-by-RGB would pick "
            "178:", weight="bold", fill=INK)
    for hexv, idx, verdict, tone in (("#d7af00", 178, "gold/red gap collapses to",
                                      WARN),
                                     ("#d7d700", 184, "gap held at", OK)):
        ny += 32
        light = oklab_lightness(_hex_to_rgb(hexv))
        f.chip(x, ny, 26, 22, hexv,
               f"{idx}  {hexv}   L {light:.3f}   {verdict} {light - red:.3f}",
               lfill=tone)
    return f.close("pill-palette-256",
                   "Lightness spacing is the whole rationale for the palette, so "
                   "it is the one property the quantization must not damage.")


def fig_pill_none_rung():
    """(6) What braille recovers when the color is stripped."""
    f = Fig()
    x, y = 30, 44
    for i, (color, head, note) in enumerate(
            [(True, "the 256 rung", "cells and bars carry their own color"),
             (False, "the none rung", "the same widths, in braille and blocks")]):
        ry = y + i * (CH + 52)
        f.label(x, ry - 12, head, weight="bold", fill=INK)
        f.pill(AID, x, ry, color=color)
        f.label(x, ry + CH + 18, note)

    ny = f.bottom + 30
    f.label(x, ny, "A braille cell is 256 code points where a block glyph is 9. "
            "Dots fill 7, 8, 3, 6, 2, 5, 1, 4, so a glyph's dot COUNT is its "
            "fill height —")
    f.label(x, ny + 18, "the bar's ordinal reading survives as density, and "
            "which arrangement of that many dots gets drawn is free. That is "
            "where the color assignment goes.")
    ry = ny + 34
    for level, glyph in enumerate(_ramp()):
        gx = x + level * (CW + 12)
        f.add(_glyph(gx, ry, glyph, INK, None), gx + CW, ry + CH)
        f.mono(gx + CW / 2, ry + CH + 15, f"{level}/8", anchor="middle")
    return f.close("pill-none-rung",
                   "Both rungs are the same printable width, which is the only "
                   "thing a host laying pills out in columns requires.")


def fig_pill_avalanche():
    """(7) The case the colored channels exist for."""
    f = Fig()
    x, y = 30, 34
    rows = [(UUID_A, "UUID A", INK2),
            (UUID_MID, "A, one character flipped inside an elided cell", WARN),
            (UUID_FIRST, "A, first character flipped", INK2),
            (UUID_LAST, "A, last character flipped", INK2)]
    for i, (value, label, tone) in enumerate(rows):
        ry = y + i * (CH + 14)
        _, w = f.pill(value, x, ry)
        f.label(x + w + 20, ry + CH * 0.7, label, fill=tone)
    f.label(x, f.bottom + 26, "Rows 1 and 2 display the same characters. Only "
            "the color bar and the separator tell them apart.", fill=INK)
    return f.close("pill-avalanche",
                   "A pill without the fingerprint-derived channels would show "
                   "two different values as the same string.")


FIGURES = [
    fig_pill_and_whois,
    fig_pill_anatomy,
    fig_pill_color_bar,
    fig_pill_separator,
    fig_pill_palette_256,
    fig_pill_none_rung,
    fig_pill_avalanche,
]


def _ramp():
    """The `none` rung's density ramp: each fill height's first (bottom-heaviest)
    arrangement, 0/8 through 8/8."""
    from entviz.terminal.pill import BAR_ALPHABET
    return [alphabet[0] for alphabet in BAR_ALPHABET]


def main():
    figlib.build(FIGURES, OUT, png=False)


if __name__ == "__main__":
    main()
