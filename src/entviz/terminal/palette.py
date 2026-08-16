"""256-color rendering for the terminal pill. See docs/terminal-pill.md §4.

Two rules, both about determinism rather than fidelity:

* **Indices 0-15 are never used.** They are the user's terminal theme and get
  remapped, so a pill that used them would render differently per terminal.
  Everything here comes from the 6x6x6 cube (16-231) or the grays (232-255).

* **The spec palette is a pinned table, not a quantization.** Nearest-by-RGB
  picks index 178 (``#d7af00``) for gold, which darkens gold while the same
  quantizer lightens red, collapsing the gold/red Oklab lightness gap to 0.080 —
  half the spec palette's own worst adjacent gap of 0.157. Lightness spacing is
  the entire rationale for that palette (spec.md:411), so it is the one property
  the quantization must not damage. Index 184 (``#d7d700``) instead holds the
  worst adjacent gap at 0.149, level with the spec palette, and makes gold a
  more yellow gold, which strengthens rather than weakens the hue cue vs. red.

There is deliberately no truecolor mode. The pill's colors are already lossy
projections of text printed alongside them, so the extra precision buys nothing,
and a single rendering that is byte-identical on every terminal is worth more
than one that varies with the terminal's capabilities.
"""
from ..colors import weighted_rgb_distance

#: The spec's five palette colors, pinned by hand. See the module docstring.
PALETTE_256 = {
    "#ffffff": 231,
    "#e7be00": 184,
    "#ff3f2f": 202,
    "#2f3fbf": 25,
    "#000000": 16,
}

#: The six intensity levels of the xterm 6x6x6 color cube.
_CUBE_LEVELS = (0, 95, 135, 175, 215, 255)

COLOR_MODES = ("256", "none")


def _build_table():
    """Every usable index (16-255) with the sRGB color it renders as."""
    table = {}
    for r, rv in enumerate(_CUBE_LEVELS):
        for g, gv in enumerate(_CUBE_LEVELS):
            for b, bv in enumerate(_CUBE_LEVELS):
                table[16 + 36 * r + 6 * g + b] = f"#{rv:02x}{gv:02x}{bv:02x}"
    for i in range(24):
        v = 8 + 10 * i
        table[232 + i] = f"#{v:02x}{v:02x}{v:02x}"
    return table


_TABLE = _build_table()
_CACHE = dict(PALETTE_256)


def rgb_of(index: int) -> str:
    """The sRGB color an index renders as, as a ``#rrggbb`` string."""
    return _TABLE[index]


def quantize(color: str) -> int:
    """An sRGB ``#rrggbb`` color → the 256-palette index to paint it with.

    Spec palette colors route through the pinned table; everything else (cell
    nucleus colors, which are arbitrary 24-bit values) takes the nearest entry
    by the spec's own weighted RGB metric (spec.md:441), so the snapping rule is
    one the spec already defines rather than a new one invented here.
    """
    if color not in _CACHE:
        _CACHE[color] = min(
            _TABLE, key=lambda i: weighted_rgb_distance(color, _TABLE[i]))
    return _CACHE[color]


def sgr(fg: str | None, bg: str | None, mode: str) -> str:
    """The SGR introducer painting ``fg``/``bg``, or ``""`` in ``none`` mode.

    Background is emitted first so a reader of the escape sees the field before
    the mark drawn on it, matching how the glyphs are described everywhere else.
    """
    if mode == "none":
        return ""
    if mode != "256":
        raise ValueError(
            f"color mode must be one of {COLOR_MODES!r} (got {mode!r}); "
            "there is no truecolor mode, see docs/terminal-pill.md §2")
    parts = []
    if bg is not None:
        parts.append(f"48;5;{quantize(bg)}")
    if fg is not None:
        parts.append(f"38;5;{quantize(fg)}")
    return f"\x1b[{';'.join(parts)}m" if parts else ""


RESET = "\x1b[0m"
