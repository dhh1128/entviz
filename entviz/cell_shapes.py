from lxml import etree
from .layout import Cell, Rect, Point, Size
from .shapes import rect as draw_rect, right_triangle

def _sub(parent: Rect, dx: float, dy: float, w: float, h: float) -> Rect:
    return Rect(Point(parent.left + dx, parent.top + dy), Size(w, h))

def _centered(parent: Rect, w: float, h: float) -> Rect:
    return _sub(parent, (parent.size.width - w) / 2, (parent.size.height - h) / 2, w, h)

# Triangle rotations per edge index (0-5), standard = 0°, then +90°/+180°/+270°.
# The right angle of the triangle faces toward the outer corner of the edge;
# the 45° tip points toward the nucleus side.
_TRIANGLE_ROTATIONS = [0, 0, 90, 180, 180, 270]

def draw_triangle(svg, cell: Cell, edge: int, fill_color: str):
    er = cell.edge_rect(edge)
    right_triangle(svg, er, _TRIANGLE_ROTATIONS[edge], fill_color)

def draw_hook(svg, cell: Cell, edge: int, fill_color: str):
    """L-shaped hook: thin bar along outer edge + full-depth piece at one end."""
    er = cell.edge_rect(edge)
    e = cell.edge_height  # edge_size

    if edge in [0, 1, 3, 4]:
        # Horizontal edge rect: width=3e, height=e
        # bar: (3e - e/2) × (e/4) along outer edge
        # piece: (e/2) × e at the end toward nucleus-center
        bar_w = er.size.width - e / 2
        bar_h = e / 4
        piece_w = e / 2
        piece_h = e
        if edge in [0, 1]:
            draw_rect(svg, _sub(er, 0, 0, bar_w, bar_h), fill_color)
            draw_rect(svg, _sub(er, bar_w, 0, piece_w, piece_h), fill_color)
        else:  # 3, 4: +180°, bar at bottom, piece at left
            draw_rect(svg, _sub(er, piece_w, er.size.height - bar_h, bar_w, bar_h), fill_color)
            draw_rect(svg, _sub(er, 0, 0, piece_w, piece_h), fill_color)
    else:
        # Vertical edge rect: width=e, height=2e
        # bar: (e/4) × (3e/2) along nucleus side
        # piece: e × (e/2) at top or bottom
        bar_w = e / 4
        bar_h = e * 3 / 2
        piece_w = e
        piece_h = e / 2
        if edge == 2:  # right side of cell, +90°: bar on left (nucleus side), piece at bottom
            draw_rect(svg, _sub(er, 0, 0, bar_w, bar_h), fill_color)
            draw_rect(svg, _sub(er, 0, bar_h, piece_w, piece_h), fill_color)
        else:  # edge 5, left side, +270°: bar on right, piece at top
            draw_rect(svg, _sub(er, er.size.width - bar_w, piece_h, bar_w, bar_h), fill_color)
            draw_rect(svg, _sub(er, 0, 0, piece_w, piece_h), fill_color)

def draw_rect_shape(svg, cell: Cell, edge: int, fill_color: str):
    """Full rectangle filling the entire edge rect."""
    draw_rect(svg, cell.edge_rect(edge), fill_color)

def draw_box(svg, cell: Cell, edge: int, fill_color: str):
    """Centered e×e square within the edge rect."""
    er = cell.edge_rect(edge)
    e = cell.edge_height
    draw_rect(svg, _centered(er, e, e), fill_color)

def draw_slant(svg, cell: Cell, edge: int, fill_color: str):
    """Paired e×e triangles at opposite ends of the edge rect, rotated 180° from each other."""
    er = cell.edge_rect(edge)
    e = cell.edge_height

    if edge in [0, 1, 3, 4]:
        left = Rect(er.top_left, Size(e, e))
        right = Rect(Point(er.right - e, er.top), Size(e, e))
        if edge in [0, 1]:
            right_triangle(svg, left, 270, fill_color)
            right_triangle(svg, right, 90, fill_color)
        else:  # +180°
            right_triangle(svg, left, 90, fill_color)
            right_triangle(svg, right, 270, fill_color)
    else:
        top = Rect(er.top_left, Size(e, e))
        bot = Rect(Point(er.left, er.bottom - e), Size(e, e))
        if edge == 2:  # +90°
            right_triangle(svg, top, 0, fill_color)
            right_triangle(svg, bot, 180, fill_color)
        else:  # edge 5, +270°
            right_triangle(svg, top, 180, fill_color)
            right_triangle(svg, bot, 0, fill_color)

def draw_hammer(svg, cell: Cell, edge: int, fill_color: str):
    """T-shape: centered stem + crossbar near outer edge."""
    er = cell.edge_rect(edge)
    e = cell.edge_height

    if edge in [0, 1, 3, 4]:
        # stem: (e/2) × e, centered horizontally; crossbar: (3e*3/4) × (e/4), near outer edge
        stem_w = e / 2
        stem_h = e
        bar_w = er.size.width * 3 / 4
        bar_h = e / 4
        stem_x = (er.size.width - stem_w) / 2
        bar_x = (er.size.width - bar_w) / 2
        if edge in [0, 1]:
            draw_rect(svg, _sub(er, stem_x, 0, stem_w, stem_h), fill_color)
            draw_rect(svg, _sub(er, bar_x, e / 4, bar_w, bar_h), fill_color)
        else:  # +180°: crossbar near bottom
            draw_rect(svg, _sub(er, stem_x, 0, stem_w, stem_h), fill_color)
            draw_rect(svg, _sub(er, bar_x, e / 2, bar_w, bar_h), fill_color)
    else:
        # stem: e × (e/2), centered vertically; bar: (e/4) × (e*5/4), centered horizontally
        stem_w = e
        stem_h = e / 2
        bar_w = e / 4
        bar_h = e * 5 / 4
        stem_y = (er.size.height - stem_h) / 2
        bar_x = (er.size.width - bar_w) / 2
        bar_y = (er.size.height - bar_h) / 2
        if edge == 2:  # +90°: stem toward right (outer), bar extends inward
            draw_rect(svg, _sub(er, 0, stem_y, stem_w, stem_h), fill_color)
            draw_rect(svg, _sub(er, bar_x, bar_y, bar_w, bar_h), fill_color)
        else:  # +270°
            draw_rect(svg, _sub(er, 0, stem_y, stem_w, stem_h), fill_color)
            draw_rect(svg, _sub(er, bar_x, bar_y, bar_w, bar_h), fill_color)

def draw_pyramid(svg, cell: Cell, edge: int, fill_color: str):
    """Diamond/arrow: two e×e triangles pointing toward each other + center fill."""
    er = cell.edge_rect(edge)
    e = cell.edge_height

    if edge in [0, 1, 3, 4]:
        # Horizontal: left triangle + center rect + right triangle
        left_tri = Rect(er.top_left, Size(e, e))
        center = _sub(er, e, 0, e, e)
        right_tri = Rect(Point(er.right - e, er.top), Size(e, e))
        if edge in [0, 1]:
            right_triangle(svg, left_tri, 180, fill_color)
            draw_rect(svg, center, fill_color)
            right_triangle(svg, right_tri, 0, fill_color)
        else:  # +180°
            right_triangle(svg, left_tri, 0, fill_color)
            draw_rect(svg, center, fill_color)
            right_triangle(svg, right_tri, 180, fill_color)
    else:
        # Vertical: top triangle + bottom triangle
        top_tri = Rect(er.top_left, Size(e, e))
        bot_tri = Rect(Point(er.left, er.bottom - e), Size(e, e))
        if edge == 2:  # +90°
            right_triangle(svg, top_tri, 270, fill_color)
            right_triangle(svg, bot_tri, 90, fill_color)
        else:  # +270°
            right_triangle(svg, top_tri, 90, fill_color)
            right_triangle(svg, bot_tri, 270, fill_color)

def draw_double_bars(svg, cell: Cell, edge: int, fill_color: str):
    """Two parallel bars centered in the edge rect, separated by one bar-thickness gap."""
    er = cell.edge_rect(edge)
    e = cell.edge_height
    thickness = e / 4
    gap = e / 2

    if edge in [0, 1, 3, 4]:
        # Two vertical bars
        total_w = thickness * 2 + gap
        start_x = (er.size.width - total_w) / 2
        draw_rect(svg, _sub(er, start_x, 0, thickness, e), fill_color)
        draw_rect(svg, _sub(er, start_x + thickness + gap, 0, thickness, e), fill_color)
    else:
        # Two horizontal bars
        total_h = thickness * 2 + gap
        start_y = (er.size.height - total_h) / 2
        draw_rect(svg, _sub(er, 0, start_y, e, thickness), fill_color)
        draw_rect(svg, _sub(er, 0, start_y + thickness + gap, e, thickness), fill_color)


SHAPE_DRAWERS = {
    'triangle': draw_triangle,
    'hook': draw_hook,
    'rect': draw_rect_shape,
    'box': draw_box,
    'slant': draw_slant,
    'hammer': draw_hammer,
    'pyramid': draw_pyramid,
    'double bars': draw_double_bars,
}

def draw_edge_shape(svg, cell: Cell, edge: int, shape_name: str, fill_color: str):
    drawer = SHAPE_DRAWERS.get(shape_name)
    if drawer is None:
        raise ValueError(f"Unknown shape: {shape_name!r}")
    drawer(svg, cell, edge, fill_color)
