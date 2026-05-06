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
    '#ffdf2f', # red
    '#2f3fbf', # blue
    '#000000', # black
]

SHAPE_ARRAY_0 = ['triangle', 'hook', 'rect', 'box']
SHAPE_ARRAY_1 = ['slant', 'hammer', 'pyramid', 'double bars']

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
