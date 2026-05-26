from collections import namedtuple


def relative_luminance(rgb):
    """
    Gamma-corrected luminance of an RGB triple (0..255 per channel),
    matching the W3C definition used for accessibility contrast. Returns
    a value in [0, 1]. Used to pick a readable foreground (black/white)
    against an arbitrary nucleus background color.
    """
    rs = rgb[0] / 255
    gs = rgb[1] / 255
    bs = rgb[2] / 255

    def gamma_correction(c):
        if c <= 0.04045:
            return c / 12.92
        return ((c + 0.055) / 1.055) ** 2.4

    return (0.2126 * gamma_correction(rs)
            + 0.7152 * gamma_correction(gs)
            + 0.0722 * gamma_correction(bs))


VisualStyle = namedtuple('VisualStyle', [
    'bg_color',     # entviz background; one of POSSIBLE_EDGE_COLORS[0..3]
    'edge_colors',  # the 4 non-bg colors, used as the quartile-mark palette
])

POSSIBLE_EDGE_COLORS = [
    '#ffffff',  # white
    '#ffd966',  # gold
    '#ff3f2f',  # red
    '#2f3fbf',  # blue
    '#000000',  # black — always present, never the background
]


def select_visual_style(median_token, second_quartile_token=None) -> VisualStyle:
    """
    v4: pick the entviz background from the 4 background candidates using
    the median ftok's low 2 bits (unchanged from v3). The remaining 4 of
    [white, gold, red, blue, black] are the quartile-mark palette. v4 has
    no entviz-wide edge color — filled surround boxes use the per-cell
    nucleus background color instead. `second_quartile_token` is kept in
    the signature for call-site compatibility and ignored.
    """
    color_idx = median_token.quant & 0x03
    bg_color = POSSIBLE_EDGE_COLORS[color_idx]
    edge_colors = [c for i, c in enumerate(POSSIBLE_EDGE_COLORS) if i != color_idx]
    return VisualStyle(bg_color=bg_color, edge_colors=edge_colors)


def _hex_to_rgb(hex_color: str):
    return (int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16))


def weighted_rgb_distance(c1: str, c2: str) -> float:
    """
    Cheap stand-in for CIELAB ΔE. Weights green highest (cone-peak
    sensitivity) and blue lowest:
        sqrt(2·(Δr)² + 4·(Δg)² + 3·(Δb)²)
    Inputs are #rrggbb hex strings.
    """
    r1, g1, b1 = _hex_to_rgb(c1)
    r2, g2, b2 = _hex_to_rgb(c2)
    return (2 * (r1 - r2) ** 2 + 4 * (g1 - g2) ** 2 + 3 * (b1 - b2) ** 2) ** 0.5


def closest_palette_color(target: str, palette) -> str:
    """Return the palette entry with minimum weighted_rgb_distance to target."""
    return min(palette, key=lambda c: weighted_rgb_distance(c, target))


def get_nucleus_colors(quant: int):
    """Convert a 24-bit quant to its (bg_color, fg_color) pair. Red is the
    low-order byte, then green, then blue (CSS order). Foreground is white
    or black, picked to maximize WCAG-style luminance contrast against the
    bg. The crossover (where black contrast equals white contrast) sits at
    Y ≈ 0.179, NOT 0.5:

        (1 + 0.05) / (Y + 0.05) = (Y + 0.05) / (0 + 0.05)
      → (Y + 0.05)² = 0.0525
      → Y = √0.0525 − 0.05 ≈ 0.1791

    A naive 0.5 threshold mis-paired medium-luminance backgrounds with
    white, producing WCAG contrast ratios of 2-3:1 (fails AA) where
    black would have given 6-12:1.
    """
    r = quant & 0xFF
    g = (quant >> 8) & 0xFF
    b = (quant >> 16) & 0xFF
    bg_color = f"#{r:02x}{g:02x}{b:02x}"
    lum = relative_luminance((r, g, b))
    fg_color = "#ffffff" if lum < _WCAG_BLACK_WHITE_CROSSOVER else "#000000"
    return bg_color, fg_color


# sqrt(1.05 * 0.05) - 0.05 — luminance at which white-on-bg has equal
# WCAG contrast to bg-on-black. Below: prefer white. Above: prefer black.
_WCAG_BLACK_WHITE_CROSSOVER = (0.0525) ** 0.5 - 0.05
