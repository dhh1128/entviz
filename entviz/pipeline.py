"""
Full entviz rendering pipeline: entropy string → SVG string.
Follows the v2 algorithm in docs/index2.md.

Terminology: v1 used "bounding rect" for the rectangle containing the
grid of cells. v2 reuses that name for the outer canvas (which also
holds the color bar, shape count summary, and white margin + black
border). The cells-only rectangle is now grid_rect. The bounding_rect
and its geometry land in Phase 7.
"""
from lxml import etree

from .entropy import parse, tokenize_entropy
from .layout import choose_grid, assign_cell_indices, Cell, Point, Rect, Size
from .colors import select_visual_style
from .fingerprint import (
    compute_fingerprint,
    get_median_ftok,
    get_quartile_ftoks,
    tokenize_fingerprint,
)
from .renderer import Renderer
from .shapes import canvas, rect as draw_rect

_DPI = 96


def render(entropy_text: str, target_ar: float = 1.0, font_size_pt: int = 12) -> str:
    """
    Render entropy as an SVG entviz and return the SVG as a UTF-8 string.
    """
    # --- Normalize and tokenize the entropy ---
    parsed = parse(entropy_text.strip())
    if parsed is None:
        import base64
        core = base64.urlsafe_b64encode(entropy_text.encode()).decode().rstrip('=')
        type_name = 'base64'
    else:
        core = parsed.core
        type_name = parsed.type

    tokens, _is_truncated = tokenize_entropy(core, type_name)
    if not tokens:
        raise ValueError("No tokens produced from input entropy.")

    # _is_truncated indicates the input was > 512 bits and a blank separator
    # cell must be inserted between tokens 10 and 11. That separator-cell
    # wiring lands in a later phase; for now the truncated tokens render
    # contiguously, which is enough to keep large inputs from crashing.
    token_count = len(tokens)

    # --- Compute the fingerprint and derive used ftoks ---
    # The fingerprint avalanche means single-bit input changes propagate
    # to every ftok-derived channel.
    used_ftoks = tokenize_fingerprint(compute_fingerprint(core))[:token_count]

    # --- Choose grid ---
    grid = choose_grid(token_count, target_ar)

    # --- Median, quartiles, visual style — all from ftoks ---
    median_ftok = get_median_ftok(used_ftoks)
    quartile_ftoks = get_quartile_ftoks(used_ftoks)
    second_quartile_ftok = quartile_ftoks[1] if len(quartile_ftoks) > 1 else None
    style = select_visual_style(median_ftok, second_quartile_ftok)

    # --- Blank cell placement keyed off ftok ASCII sort ---
    cell_indices = assign_cell_indices(
        tokens, grid, median_token=median_ftok, sort_keys=used_ftoks
    )

    # --- Pixel dimensions ---
    # Geometry is anchored on nucleus_height. cell is 4×nucleus_height wide
    # and 2×nucleus_height tall; edge_size = nucleus_height/2 = half the
    # height of a top/bottom edge rect; GM (grid margin) = edge_size/2 is
    # the white margin between the grid_rect and the bounding_rect edges.
    nucleus_height = (font_size_pt * _DPI) / 72
    cell_width = nucleus_height * 4
    cell_height = nucleus_height * 2
    edge_size = nucleus_height / 2
    gm = edge_size / 2

    grid_w = cell_width * grid.cols
    grid_h = cell_height * grid.rows

    # Bounding rect dimensions per v2 spec step 13:
    #   width  = GM + GM + grid_width + GM + 1
    #   height = 1 + GM + grid_height + GM + nucleus_height + GM + 1
    # Layout left→right: color-bar (GM) | margin (GM) | grid | margin (GM)
    #                    | right border (1).
    # Layout top→bottom: top border (1) | margin (GM) | grid | margin (GM)
    #                    | SCS line (nucleus_height) | margin (GM)
    #                    | bottom border (1).
    bounding_w = gm + gm + grid_w + gm + 1
    bounding_h = 1 + gm + grid_h + gm + nucleus_height + gm + 1
    bounding_rect = Rect(Point(0, 0), Size(bounding_w, bounding_h))

    # grid_rect sits at (2*GM, 1+GM) inside the bounding rect.
    grid_rect = Rect(Point(gm + gm, 1 + gm), Size(grid_w, grid_h))

    renderer = Renderer(style, grid)

    svg = canvas(bounding_rect.size)
    draw_rect(svg, bounding_rect, '#ffffff')
    # Entviz background color (from median ftok) fills the grid_rect so
    # blank cells show that color rather than the white bounding-rect fill.
    draw_rect(svg, grid_rect, style.bg_color)

    cell_index_to_cell = {}

    for token in tokens:
        ci = cell_indices[token.index]
        col = ci % grid.cols
        row = ci // grid.cols
        cell = Cell(
            Point(grid_rect.left + col * cell_width, grid_rect.top + row * cell_height),
            Size(cell_width, cell_height),
        )
        cell_index_to_cell[ci] = cell
        renderer.render_cell(svg, token, used_ftoks[token.index], cell, cell_index=ci)

    # Quartile marks placed at the cells of the four quartile ftoks
    # (mapped through the 1:1 ftok→token→cell correspondence).
    for q_idx, q_ftok in enumerate(quartile_ftoks):
        if q_ftok is None:
            continue
        ci = cell_indices.get(q_ftok.index)
        if ci is None:
            continue
        cell = cell_index_to_cell.get(ci)
        if cell is None:
            continue
        renderer.draw_quartile_mark(svg, cell, q_idx)

    # Black border lines on top, right, bottom of the bounding rect.
    # The left edge is reserved for the color bar and gets no border.
    # The top and bottom lines start at x=GM (color bar's right edge).
    _draw_border_line(svg, gm, 0, bounding_w - 1, 0)                              # top
    _draw_border_line(svg, bounding_w - 1, 0, bounding_w - 1, bounding_h - 1)     # right
    _draw_border_line(svg, gm, bounding_h - 1, bounding_w - 1, bounding_h - 1)    # bottom

    return etree.tostring(svg, encoding='unicode', xml_declaration=False)


def _draw_border_line(svg, x1, y1, x2, y2):
    etree.SubElement(
        svg, 'line',
        x1=str(x1), y1=str(y1), x2=str(x2), y2=str(y2),
        stroke='#000000', **{'stroke-width': '1'},
    )
