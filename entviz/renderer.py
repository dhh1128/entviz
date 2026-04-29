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

    def render_cell(self, svg: etree.Element, token, cell: Cell):
        """
        Implementation of the Cell Rendering Algorithm.
        """
        # 1. Nucleus Colors
        bg_color, fg_color = get_nucleus_colors(token.quant)

        # 2. Draw Nucleus Rect
        n = cell.nucleus
        etree.SubElement(svg, 'rect', 
                         x=str(n.left), y=str(n.top), 
                         width=str(n.size.width), height=str(n.size.height),
                         fill=bg_color)

        # 3. Draw Text (Simplified for now, assumes center alignment)
        text_el = etree.SubElement(svg, 'text',
                                   x=str(n.center.x), y=str(n.center.y),
                                   fill=fg_color,
                                   style=f"font-family: monospace; font-size: {cell.size.height/2}px;",
                                   **{"text-anchor": "middle", "dominant-baseline": "central"})
        text_el.text = token.text

        # 4. Edge Rendering (Step 5-9)
        # Convert quant to 6 4-bit edge_nums
        edge_nums = [(token.quant >> (i * 4)) & 0x0F for i in range(6)]

        for i in range(6):
            edge_num = edge_nums[i]
            
            # Color selection with XOR shift
            color_base = edge_num & 0x03
            color_idx = color_base ^ (self.color_shift & 0x03)
            edge_color = self.style.edge_colors[color_idx]
            
            # Shape selection with XOR shift
            shape_base = (edge_num >> 2) & 0x03
            shape_idx = shape_base ^ (self.shape_shift & 0x03)
            edge_shape = self.style.edge_shapes[shape_idx]

            # Draw the edge shape
            draw_edge_shape(svg, cell, i, edge_shape, edge_color)

            # Update shifts
            self.color_shift = (self.color_shift + 1) & 0xFF
            
            # If not the last column, increment shape_shift
            is_last_col = (token.index % self.grid.cols) == self.grid.cols - 1
            if not is_last_col:
                self.shape_shift = (self.shape_shift + 1) & 0xFF

        # After all 6 edges, if it was the last column, add shape_shift to color_shift
        is_last_col = (token.index % self.grid.cols) == self.grid.cols - 1
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
