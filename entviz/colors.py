def relative_luminance(rgb):
    """
    Calculate the gamma-corrected luminance of an RGB color value. This is the luminance value
    used for accessibility purposes in web design, to ensure that text is readable against a
    background color. The luminance value is a number between 0 and 1, where 0 is black and 1 is
    white. See https://www.w3.org/WAI/GL/wiki/Relative_luminance.
    
    The simple method of getting luminance is just to assume that however much red, green, and blue
    we see, that's how much luminance we have. This does not account for the fact that the human eye
    perceives a fixed quantity of green light to be more luminous than that same quantity of red light
    (and red to be more luminous than blue), because of the sensitivity of the rods and cones in the
    eye to different light frequencies.
    
    This method fixes that problem and gives a more realistic idea of what the perceived luminance of
    a color is, for a typical human eye. 
    """
    rs = rgb[0] / 255
    gs = rgb[1] / 255
    bs = rgb[2] / 255

    def gamma_correction(c):
        if c <= 0.04045:
            return c / 12.92
        else:
            return ((c + 0.055) / 1.055) ** 2.4

    rs_gamma = gamma_correction(rs)
    gs_gamma = gamma_correction(gs)
    bs_gamma = gamma_correction(bs)

    Y = (0.2126 * rs_gamma) + (0.7152 * gs_gamma) + (0.0722 * bs_gamma)
    return Y

from collections import namedtuple

VisualStyle = namedtuple('VisualStyle', [
    'bg_color', 
    'edge_colors', 
    'edge_shapes',
    'shape_shift',
    'color_shift'
])

POSSIBLE_EDGE_COLORS = [
    '#ffffff', # white
    '#ffd966', # gold
    '#ff3f2f', # red (v1 had #ffdf2f, which was actually yellow ≈ gold)
    '#2f3fbf', # blue
    '#000000', # black
]

class EdgeShape:
    """
    A renderable edge shape. Owns its canonical v2 name, the identifying
    capital letter used by the shape count summary (Phase 11), and the
    drawer that paints the shape into a given cell's edge_rect.

    The drawer signature is (svg, cell, edge_index, fill). `fill` is a
    string accepted by the svg `fill` attribute — either a hex color (v1
    behavior, kept for tests) or a "url(#…)" gradient reference (v2
    pipeline default).

    Defining shapes as objects (rather than plain name strings) lets the
    upcoming shape-redesign effort swap a shape's geometry in one place
    without disturbing the renderer, the registry, or the SCS lookup.
    """
    __slots__ = ('name', 'letter', 'draw')

    def __init__(self, name: str, letter: str, draw):
        self.name = name
        self.letter = letter
        self.draw = draw

    def __repr__(self):
        return f"EdgeShape({self.name!r}, {self.letter!r})"

    def __eq__(self, other):
        if isinstance(other, EdgeShape):
            return self.name == other.name
        return False

    def __hash__(self):
        return hash(self.name)


def _make_shape(name, letter):
    # Late-imported drawer keeps the colors↔cell_shapes import order clean.
    # Used only by legacy v2 EdgeShape construction; v3 shape arrays
    # (below) use V3EdgeShape directly with no procedural drawer.
    from .cell_shapes import SHAPE_DRAWERS
    return EdgeShape(name, letter, SHAPE_DRAWERS[name])


# v3 shape arrays: the cubist and polygon sets. SHAPE_ARRAY_0 and
# SHAPE_ARRAY_1 retain their names for spec compatibility (array 0 is
# the "binary selector = 0" array), but their contents are now v3
# V3EdgeShape instances rather than v2 EdgeShape instances. Slot 4 of
# each array is the empty member.
from .v3_shapes import CUBIST_SHAPES, POLYGON_SHAPES
SHAPE_ARRAY_0 = CUBIST_SHAPES
SHAPE_ARRAY_1 = POLYGON_SHAPES

def select_visual_style(median_token, second_quartile_token) -> VisualStyle:
    """
    Steps 12 and 13: Select global background color, edge colors, and edge shapes.
    """
    # Step 12: Color Selection
    # Select index from low-order 2 bits of median token quant
    color_idx = median_token.quant & 0x03
    bg_color = POSSIBLE_EDGE_COLORS[color_idx]
    
    # edge_colors is the remaining 4 colors
    edge_colors = [c for i, c in enumerate(POSSIBLE_EDGE_COLORS) if i != color_idx]
    
    # Step 13: Shape Selection
    # Iterate over low-order 4 bits of second quartile token quant
    edge_shapes = []
    # If second_quartile_token is None (padding), we use a default (bits = 0)
    bits = second_quartile_token.quant & 0x0F if second_quartile_token else 0
    
    for i in range(4):
        selector = (bits >> i) & 0x01
        if selector == 0:
            edge_shapes.append(SHAPE_ARRAY_0[i])
        else:
            edge_shapes.append(SHAPE_ARRAY_1[i])
            
    return VisualStyle(
        bg_color=bg_color,
        edge_colors=edge_colors,
        edge_shapes=edge_shapes,
        shape_shift=0,
        color_shift=0
    )

def get_nucleus_colors(quant: int):
    """
    Step 2 of Cell Rendering: Convert quant to RGB and determine contrast foreground.
    """
    # red in low-order byte, then green, then blue
    r = quant & 0xFF
    g = (quant >> 8) & 0xFF
    b = (quant >> 16) & 0xFF
    
    bg_color = f"#{r:02x}{g:02x}{b:02x}"
    
    # Calculate luminance for contrast
    lum = relative_luminance((r, g, b))
    fg_color = "#ffffff" if lum < 0.5 else "#000000"
    
    return bg_color, fg_color
