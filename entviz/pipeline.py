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
    # nucleus_height drives all geometry. cell is 4×nucleus_height wide and
    # 2×nucleus_height tall. The grid_rect is the rectangle of cells only;
    # in Phase 7 it sits inside a larger bounding_rect that also holds the
    # color bar, the shape count summary, and the white margin + black
    # border. The v1 spec called this rect the "bounding rect" — that name
    # is now reserved for the outer canvas, so we use grid_rect here.
    nucleus_height = (font_size_pt * _DPI) / 72
    cell_width = nucleus_height * 4
    cell_height = nucleus_height * 2
    grid_rect = Rect(Point(0, 0), Size(cell_width * grid.cols, cell_height * grid.rows))

    renderer = Renderer(style, grid)

    svg = canvas(grid_rect.size)
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

    return etree.tostring(svg, encoding='unicode', xml_declaration=False)
