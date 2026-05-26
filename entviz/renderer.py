from lxml import etree
from .layout import Cell, Rect, Point, Size
from .colors import get_nucleus_colors, closest_palette_color, VisualStyle
from .shapes import circle

# Quartile mark corner: (x_fn, y_fn) as lambdas of (cell, r).
# 1st=top-left, 2nd=top-right, 3rd=bottom-right, 4th=bottom-left.
_QUARTILE_CORNERS = [
    lambda cell, r: Point(cell.left + r, cell.top + r),
    lambda cell, r: Point(cell.right - r, cell.top + r),
    lambda cell, r: Point(cell.right - r, cell.bottom - r),
    lambda cell, r: Point(cell.left + r, cell.bottom - r),
]


class Renderer:
    def __init__(self, style: VisualStyle, grid):
        self.style = style
        self.grid = grid

    def render_edges(self, svg: etree.Element, ftok, cell: Cell, nucleus_bg: str):
        """
        v4 surround: 24 small boxes around the nucleus. Bit i of ftok.quant
        (LSB=bit 0) selects box i (clockwise from the top-left of the top
        row). A set bit emits a solid <rect> filled with this cell's edge
        color — the palette entry (one of the 4 non-bg colors) that is
        perceptually closest to the nucleus_bg under weighted RGB
        distance. A clear bit emits nothing.
        """
        edge_color = closest_palette_color(nucleus_bg, self.style.edge_colors)
        bw = cell.box_width
        bh = cell.box_height
        for i in range(24):
            if not (ftok.quant >> i) & 1:
                continue
            origin = cell.box_origin(i)
            etree.SubElement(
                svg, 'rect',
                x=str(origin.x), y=str(origin.y),
                width=str(bw), height=str(bh),
                fill=edge_color,
            )

    def render_nucleus(self, svg: etree.Element, token, cell: Cell,
                       text_size_px=None):
        """Nucleus rect + centered token text."""
        bg_color, fg_color = get_nucleus_colors(token.quant)
        n = cell.nucleus
        etree.SubElement(svg, 'rect',
                         x=str(n.left), y=str(n.top),
                         width=str(n.size.width), height=str(n.size.height),
                         fill=bg_color)
        if text_size_px is None:
            text_size_px = cell.size.height / 2
        text_el = etree.SubElement(svg, 'text',
                                   x=str(n.center.x), y=str(n.center.y),
                                   fill=fg_color,
                                   style=f"font-family: monospace; font-size: {text_size_px}px;",
                                   **{"text-anchor": "middle", "dominant-baseline": "central"})
        text_el.text = token.text

    def draw_quartile_mark(self, svg: etree.Element, cell: Cell, quartile_index: int):
        """Quartile mark: small filled circle in a cell corner. The 4-color
        non-bg palette (style.edge_colors) supplies the per-quartile color."""
        r = cell.box_height / 4
        fill_color = self.style.edge_colors[quartile_index]
        center = _QUARTILE_CORNERS[quartile_index](cell, r)
        mark_rect = Rect(Point(center.x - r, center.y - r), Size(r * 2, r * 2))
        circle(svg, mark_rect, fill_color)
