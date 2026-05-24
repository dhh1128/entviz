from lxml import etree
from .layout import Cell, Rect, Point, Size
from .colors import get_nucleus_colors, VisualStyle
from .shapes import circle

# Quartile mark corner: (x_fn, y_fn) as lambdas of (cell, r)
# 1st=top-left, 2nd=top-right, 3rd=bottom-right, 4th=bottom-left
_QUARTILE_CORNERS = [
    lambda cell, r: Point(cell.left + r, cell.top + r),
    lambda cell, r: Point(cell.right - r, cell.top + r),
    lambda cell, r: Point(cell.right - r, cell.bottom - r),
    lambda cell, r: Point(cell.left + r, cell.bottom - r),
]


def _gradient_endpoints(edge_index: int, er: Rect):
    """
    Return (x1, y1, x2, y2) for a gradient that runs from the inner
    boundary (touching the nucleus) to the outer boundary of edge_rect
    `er`, perpendicular to the shared edge. Coordinates are in user
    space (i.e., the same coordinate system as the edge_rect itself).

    Edge layout:
      0,1: top horizontal — inner = bottom of edge_rect, outer = top.
      2:   right vertical — inner = left edge_rect, outer = right.
      3,4: bottom horizontal — inner = top, outer = bottom.
      5:   left vertical — inner = right, outer = left.
    """
    cx = (er.left + er.right) / 2
    cy = (er.top + er.bottom) / 2
    if edge_index in (0, 1):
        return cx, er.bottom, cx, er.top
    if edge_index in (3, 4):
        return cx, er.top, cx, er.bottom
    if edge_index == 2:
        return er.left, cy, er.right, cy
    if edge_index == 5:
        return er.right, cy, er.left, cy
    raise ValueError(f"bad edge index {edge_index}")


class Renderer:
    def __init__(self, style: VisualStyle, grid):
        self.style = style
        self.grid = grid
        self.shape_shift = 0
        self.color_shift = 0
        self._gradient_seq = 0
        # Phase 10/11: tally edge color and shape usage across all
        # render_edges calls so the color bar and SCS can summarise them.
        # Blank cells (whose render_edges is never called) are excluded.
        self.color_usage = {c: 0 for c in style.edge_colors}
        self.shape_usage = {s: 0 for s in style.edge_shapes}

    def render_edges(self, svg: etree.Element, defs: etree.Element,
                     ftok, cell: Cell, cell_index: int, nucleus_bg: str):
        """
        v2 layered draw, pass 1: this cell's 6 edge shapes. Ftok.quant
        drives edge_num extraction; the XOR shift state on the renderer
        accumulates across cells. Each edge gets its own linear gradient
        (inner = nucleus_bg, outer = edge_color, perpendicular to the
        shared edge) appended to the supplied defs element. The shape
        is filled via url(#g-N) referencing that gradient.

        Last-column XOR adjustment keys off cell_index, not token.index.
        """
        edge_nums = [(ftok.quant >> (i * 4)) & 0x0F for i in range(6)]
        is_last_col = (cell_index % self.grid.cols) == self.grid.cols - 1

        for i in range(6):
            edge_num = edge_nums[i]

            color_idx = (edge_num & 0x03) ^ (self.color_shift & 0x03)
            edge_color = self.style.edge_colors[color_idx]

            shape_idx = ((edge_num >> 2) & 0x03) ^ (self.shape_shift & 0x03)
            edge_shape = self.style.edge_shapes[shape_idx]

            gradient_id = f"g{self._gradient_seq}"
            self._gradient_seq += 1
            self._add_gradient(defs, gradient_id, i, cell.edge_rect(i),
                               nucleus_bg, edge_color)
            edge_shape.draw(svg, cell, i, f"url(#{gradient_id})")
            self.color_usage[edge_color] = self.color_usage.get(edge_color, 0) + 1
            self.shape_usage[edge_shape] = self.shape_usage.get(edge_shape, 0) + 1

            self.color_shift = (self.color_shift + 1) & 0xFF
            if not is_last_col:
                self.shape_shift = (self.shape_shift + 1) & 0xFF

        if is_last_col:
            self.color_shift = (self.color_shift + self.shape_shift) & 0xFF

    @staticmethod
    def _add_gradient(defs, gid, edge_index, edge_rect, inner_color, outer_color):
        x1, y1, x2, y2 = _gradient_endpoints(edge_index, edge_rect)
        g = etree.SubElement(
            defs, 'linearGradient',
            id=gid, gradientUnits='userSpaceOnUse',
            x1=str(x1), y1=str(y1), x2=str(x2), y2=str(y2),
        )
        etree.SubElement(g, 'stop', offset='0%', **{'stop-color': inner_color})
        etree.SubElement(g, 'stop', offset='100%', **{'stop-color': outer_color})

    def render_nucleus(self, svg: etree.Element, token, cell: Cell):
        """
        v2 layered draw, pass 3: this cell's nucleus rect + centered text.
        Token.quant drives the nucleus background color (which determines
        foreground contrast); token.text supplies the displayed string.
        No state change.
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

    def draw_quartile_mark(self, svg: etree.Element, cell: Cell, quartile_index: int):
        """Draw a small filled circle in the corner of a quartile token's cell (spec step 16)."""
        e = cell.edge_height  # edge_size
        r = e / 4             # diameter = edge_size/2, so radius = edge_size/4
        fill_color = self.style.edge_colors[quartile_index]
        center = _QUARTILE_CORNERS[quartile_index](cell, r)
        mark_rect = Rect(Point(center.x - r, center.y - r), Size(r * 2, r * 2))
        circle(svg, mark_rect, fill_color)
