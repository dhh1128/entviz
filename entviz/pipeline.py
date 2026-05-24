"""
Full entviz rendering pipeline: entropy string → SVG string.
Follows the v2 algorithm in docs/index2.md.

v2 changes from v1:
- Compute fingerprint (SHA-512 of normalized core) once per render.
- Tokenize fingerprint into 22 ftoks; the first token_count are the
  "used ftoks" that drive every fingerprint-derived channel.
- Median, quartiles, visual style, and blank-cell placement now derive
  from ftoks. Token-derived channels (text, nucleus bg) come later in
  Phase 5 when the renderer is repointed.
"""
from lxml import etree

from .entropy import parse, tokenize
from .layout import choose_grid, assign_cell_indices, Cell, Point, Size
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

    tokens = tokenize(core, type_name)
    if not tokens:
        raise ValueError("No tokens produced from input entropy.")

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
    nucleus_height = (font_size_pt * _DPI) / 72
    cell_width = nucleus_height * 4
    cell_height = nucleus_height * 2
    grid_width = cell_width * grid.cols
    grid_height = cell_height * grid.rows

    renderer = Renderer(style, grid)

    svg = canvas(Size(grid_width, grid_height))
    draw_rect(svg, _rect(0, 0, grid_width, grid_height), style.bg_color)

    cell_index_to_cell = {}

    for token in tokens:
        ci = cell_indices[token.index]
        col = ci % grid.cols
        row = ci // grid.cols
        x = col * cell_width
        y = row * cell_height
        cell = Cell(Point(x, y), Size(cell_width, cell_height))
        cell_index_to_cell[ci] = cell
        renderer.render_cell(svg, token, cell)

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


def _rect(x, y, w, h):
    from .layout import Rect, Point, Size
    return Rect(Point(x, y), Size(w, h))
