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
    '#e7be00',  # gold
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


def _srgb_to_linear(c):
    """sRGB component (0..1) → linear-light component."""
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def oklab_lightness(rgb):
    """
    Perceptual lightness L from Oklab (Björn Ottosson, 2020) — a modern
    perceptually-uniform color space that handles saturated colors
    (especially greens) better than CIELAB L*. Returns L in [0, 1] where
    0 = pure black and 1 = pure white. Inputs are an (R, G, B) triple
    with components in 0..255.
    """
    r = _srgb_to_linear(rgb[0] / 255)
    g = _srgb_to_linear(rgb[1] / 255)
    b = _srgb_to_linear(rgb[2] / 255)
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    lp = l ** (1 / 3)
    mp = m ** (1 / 3)
    sp = s ** (1 / 3)
    return 0.2104542553 * lp + 0.7936177850 * mp - 0.0040720468 * sp


# Threshold above the rigorous Oklab midpoint (0.5). Past 0.5, the math
# nominally favors black text by perceptual lightness gap; the +0.1 bias
# accounts for the eye's better acuity with small light marks on
# darker-than-mid fields. Bgs with Oklab L in roughly 0.5–0.6 (mostly
# saturated dark colors like dark green, plus mid-grays) get white text;
# above 0.6 (everything from medium tones up) gets black.
_OKLAB_BLACK_WHITE_THRESHOLD = 0.6


def get_nucleus_colors(quant: int):
    """Convert a 24-bit quant to its (bg_color, fg_color) pair. Red is
    the low-order byte, then green, then blue (CSS order). Foreground is
    white or black, picked by Oklab perceptual lightness against a
    threshold of 0.6 — see _OKLAB_BLACK_WHITE_THRESHOLD for the rationale.
    """
    r = quant & 0xFF
    g = (quant >> 8) & 0xFF
    b = (quant >> 16) & 0xFF
    bg_color = f"#{r:02x}{g:02x}{b:02x}"
    L = oklab_lightness((r, g, b))
    fg_color = "#ffffff" if L < _OKLAB_BLACK_WHITE_THRESHOLD else "#000000"
    return bg_color, fg_color
