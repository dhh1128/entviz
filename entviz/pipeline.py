"""
Full entviz rendering pipeline: entropy string → SVG string.
Follows the algorithm in docs/index.md steps 1-16.
"""
from lxml import etree

from .entropy import parse, tokenize, get_median_token, get_quartile_tokens
from .layout import choose_grid, assign_cell_indices, Cell, Point, Size
from .colors import select_visual_style
from .renderer import Renderer
from .shapes import canvas, rect as draw_rect

_DPI = 96


def render(entropy_text: str, target_ar: float = 1.0, font_size_pt: int = 12) -> str:
    """
    Render entropy as an SVG entviz and return the SVG as a UTF-8 string.
    """
    # --- Steps 1-2: Normalize and tokenize ---
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

    # --- Step 3: Choose grid ---
    grid = choose_grid(token_count, target_ar)

    # --- Steps 4-7: Number cells and insert blank cells ---
    median_token = get_median_token(tokens)
    cell_indices = assign_cell_indices(tokens, grid, median_token)

    # --- Steps 5-6: Quartile tokens ---
    quartile_tokens = get_quartile_tokens(tokens)

    # --- Steps 8-11: Compute pixel dimensions ---
    nucleus_height = (font_size_pt * _DPI) / 72
    edge_size = nucleus_height / 2
    cell_width = nucleus_height * 4
    cell_height = nucleus_height * 2
    grid_width = cell_width * grid.cols
    grid_height = cell_height * grid.rows

    # --- Steps 12-13: Visual style ---
    second_quartile_token = quartile_tokens[1] if len(quartile_tokens) > 1 else None
    style = select_visual_style(median_token, second_quartile_token)

    # --- Step 14: Renderer ---
    renderer = Renderer(style, grid)

    # --- Step 11: Create SVG canvas and background rect ---
    svg = canvas(Size(grid_width, grid_height))
    draw_rect(svg, _rect(0, 0, grid_width, grid_height), style.bg_color)

    # Build a map from cell_index to Cell for quick lookup when drawing quartile marks
    cell_index_to_cell = {}

    # --- Step 15: Render each token into its cell ---
    for token in tokens:
        ci = cell_indices[token.index]
        col = ci % grid.cols
        row = ci // grid.cols
        x = col * cell_width
        y = row * cell_height
        cell = Cell(Point(x, y), Size(cell_width, cell_height))
        cell_index_to_cell[ci] = cell
        renderer.render_cell(svg, token, cell)

    # --- Step 16: Draw quartile marks ---
    for q_idx, q_token in enumerate(quartile_tokens):
        if q_token is None:
            continue
        ci = cell_indices.get(q_token.index)
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
