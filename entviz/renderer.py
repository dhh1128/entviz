from lxml import etree
from .layout import Cell, Rect, Point, Size
from .colors import get_nucleus_colors, VisualStyle
from .cell_shapes import draw_edge_shape
from .shapes import circle

# Quartile mark corner: (x_fn, y_fn) as lambdas of (cell, r)
# 1st=top-left, 2nd=top-right, 3rd=bottom-right, 4th=bottom-left
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
        self.shape_shift = 0
        self.color_shift = 0

    def render_cell(self, svg: etree.Element, token, ftok, cell: Cell, cell_index: int):
        """
        v2 cell rendering. Token supplies nucleus background, foreground,
        and text (preserving losslessness for ≤512-bit inputs). Ftok
        supplies the edge_nums that drive edge color and shape selection.
        The last-column XOR adjustment keys off cell_index, not
        token.index, because blank-cell insertion can put a token at a
        cell whose column differs from token.index % grid.cols.
        """
        bg_color, fg_color = get_nucleus_colors(token.quant)

        n = cell.nucleus
        etree.SubElement(svg, 'rect',
                         x=str(n.left), y=str(n.top),
                         width=str(n.size.width), height=str(n.size.height),
                         fill=bg_color)

        text_el = etree.SubElement(svg, 'text',
                                   x=str(n.center.x), y=str(n.center.y),
                                   fill=fg_color,
                                   style=f"font-family: monospace; font-size: {cell.size.height/2}px;",
                                   **{"text-anchor": "middle", "dominant-baseline": "central"})
        text_el.text = token.text

        edge_nums = [(ftok.quant >> (i * 4)) & 0x0F for i in range(6)]
        is_last_col = (cell_index % self.grid.cols) == self.grid.cols - 1

        for i in range(6):
            edge_num = edge_nums[i]

            color_base = edge_num & 0x03
            color_idx = color_base ^ (self.color_shift & 0x03)
            edge_color = self.style.edge_colors[color_idx]

            shape_base = (edge_num >> 2) & 0x03
            shape_idx = shape_base ^ (self.shape_shift & 0x03)
            edge_shape = self.style.edge_shapes[shape_idx]

            draw_edge_shape(svg, cell, i, edge_shape, edge_color)

            self.color_shift = (self.color_shift + 1) & 0xFF
            if not is_last_col:
                self.shape_shift = (self.shape_shift + 1) & 0xFF

        if is_last_col:
            self.color_shift = (self.color_shift + self.shape_shift) & 0xFF

    def draw_quartile_mark(self, svg: etree.Element, cell: Cell, quartile_index: int):
        """Draw a small filled circle in the corner of a quartile token's cell (spec step 16)."""
        e = cell.edge_height  # edge_size
        r = e / 4             # diameter = edge_size/2, so radius = edge_size/4
        fill_color = self.style.edge_colors[quartile_index]
        center = _QUARTILE_CORNERS[quartile_index](cell, r)
        mark_rect = Rect(Point(center.x - r, center.y - r), Size(r * 2, r * 2))
        circle(svg, mark_rect, fill_color)
