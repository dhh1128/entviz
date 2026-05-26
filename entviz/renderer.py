from lxml import etree
from .layout import Cell, Point
from .colors import get_nucleus_colors, closest_palette_color, VisualStyle


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

    def draw_quartile_mark(self, svg: etree.Element, cell: Cell,
                           quartile_index: int, fg_color: str):
        """
        v4 quartile mark: small right triangle in one corner of the nucleus.
        Both legs = nucleus_height / 2; the right-angle vertex sits at the
        nucleus corner matching the quartile (1st=TL, 2nd=TR, 3rd=BR,
        4th=BL); each leg runs along one of the nucleus's two edges meeting
        at that corner. Filled in the cell's text foreground color so the
        mark sits on top of the nucleus_bg in the same color as the cell
        text (black on light nuclei, white on dark) — small enough not to
        intrude on text readability, but unambiguous as a corner marker.
        Quartile identity comes from triangle orientation alone.
        """
        n = cell.nucleus
        leg = n.size.height / 2
        if quartile_index == 0:        # 1st: TL corner
            pts = [n.top_left,
                   Point(n.left + leg, n.top),
                   Point(n.left, n.top + leg)]
        elif quartile_index == 1:      # 2nd: TR corner
            pts = [n.top_right,
                   Point(n.right - leg, n.top),
                   Point(n.right, n.top + leg)]
        elif quartile_index == 2:      # 3rd: BR corner
            pts = [n.bottom_right,
                   Point(n.right, n.bottom - leg),
                   Point(n.right - leg, n.bottom)]
        else:                          # 4th: BL corner
            pts = [n.bottom_left,
                   Point(n.left, n.bottom - leg),
                   Point(n.left + leg, n.bottom)]
        etree.SubElement(
            svg, 'polygon',
            points=" ".join(f"{p.x},{p.y}" for p in pts),
            fill=fg_color,
        )
