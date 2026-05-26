"""
Full entviz rendering pipeline: entropy string → SVG string.
Follows the algorithm in docs/index.md (v2; the original v1 spec is
preserved at docs/v1/index.md for historical reference).

Terminology: v1 used "bounding rect" for the rectangle containing the
grid of cells. v2 reuses that name for the outer canvas (which also
holds the color bar, shape count summary, and white margin + black
border). The cells-only rectangle is now grid_rect.
"""
import colorsys
import math

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

    tokens, is_truncated = tokenize_entropy(core, type_name)
    if not tokens:
        raise ValueError("No tokens produced from input entropy.")

    # is_truncated means the input was > 512 bits. Spec requires a blank
    # separator cell between the first 11 tokens (head) and the last 11
    # tokens (tail), "in addition to" the up-to-3 median/quartile blanks.
    # Reserve 4 extra cells for truncated input so all 4 possible blanks
    # (3 normal + 1 separator) deterministically fit. For non-truncated
    # input the existing assign_cell_indices logic gracefully scales the
    # blank count to whatever the chosen grid allows.
    token_count = len(tokens)
    extra_cells_needed = 4 if is_truncated else 0

    # --- Compute the fingerprint and derive used ftoks ---
    # The fingerprint avalanche means single-bit input changes propagate
    # to every ftok-derived channel.
    used_ftoks = tokenize_fingerprint(compute_fingerprint(core))[:token_count]

    # --- Choose grid ---
    # Pass token_count + separator-cell budget so the grid is large
    # enough for the separator plus the up-to-3 median/quartile blanks.
    grid = choose_grid(token_count + extra_cells_needed, target_ar)

    # --- Median, quartiles, visual style — all from ftoks ---
    median_ftok = get_median_ftok(used_ftoks)
    quartile_ftoks = get_quartile_ftoks(used_ftoks)
    second_quartile_ftok = quartile_ftoks[1] if len(quartile_ftoks) > 1 else None
    style = select_visual_style(median_ftok, second_quartile_ftok)

    # --- Blank cell placement keyed off ftok ASCII sort ---
    cell_indices = assign_cell_indices(
        tokens, grid, median_token=median_ftok, sort_keys=used_ftoks
    )

    # Large-input separator: shift the second half (tokens 11..21) by one
    # cell to leave a blank between cells 10 and 11. The shift runs AFTER
    # the median/quartile insertions so the head/tail split is preserved
    # exactly. Per spec: "the blank cell separating the first and last
    # 256-bit groups is in addition to" the other blanks.
    if is_truncated:
        for t_idx in list(cell_indices):
            if t_idx >= 11:
                cell_indices[t_idx] += 1

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

    # Bounding rect dimensions per v3 spec:
    #   width  = 1 + edge_size + 1 + GM + grid_width + GM + 1
    #   height = 1 + GM + grid_height + GM + nucleus_height + GM + 1
    # Layout left→right: left border (1) | color bar (edge_size) |
    #                    interior separator (1) | L margin (GM) | grid |
    #                    R margin (GM) | right border (1).
    # Layout top→bottom unchanged from v2: top border (1) | margin (GM) |
    #                    grid | margin (GM) | SCS line (nucleus_height)
    #                    | margin (GM) | bottom border (1).
    bounding_w = 1 + edge_size + 1 + gm + grid_w + gm + 1
    bounding_h = 1 + gm + grid_h + gm + nucleus_height + gm + 1
    bounding_rect = Rect(Point(0, 0), Size(bounding_w, bounding_h))

    # grid_rect sits at (1 + edge_size + 1 + GM, 1 + GM) inside the
    # bounding rect.
    grid_rect = Rect(Point(1 + edge_size + 1 + gm, 1 + gm), Size(grid_w, grid_h))

    # Color bar drawing region: x=1, width=edge_size; y starts at 1
    # (just below the top border) and ends at bounding_h - 1 (just
    # above the bottom border), so its drawable height is bounding_h - 2.
    color_bar_rect = Rect(
        Point(1, 1), Size(edge_size, bounding_h - 2),
    )

    renderer = Renderer(style, grid)

    svg = canvas(bounding_rect.size)
    # <defs> first so gradients, clipPath, and future symbols appear at
    # the top of the SVG. Order of definitions inside <defs> doesn't
    # matter for SVG rendering, but consolidating them early keeps the
    # document scannable.
    defs = etree.SubElement(svg, 'defs')

    # V3-5: clipPath spans the grid_rect (not the bounding rect).
    # The ellipse overlay clips to the cells-only area; the bounding-rect
    # margins, color bar, and SCS row stay overlay-free.
    clip_id = "grid-clip"
    cp = etree.SubElement(defs, 'clipPath', id=clip_id)
    etree.SubElement(
        cp, 'rect',
        x=str(grid_rect.left), y=str(grid_rect.top),
        width=str(grid_rect.size.width), height=str(grid_rect.size.height),
    )

    draw_rect(svg, bounding_rect, '#ffffff')
    # Entviz background color (from median ftok) fills the grid_rect so
    # blank cells show that color rather than the white bounding-rect fill.
    draw_rect(svg, grid_rect, style.bg_color)

    # Build the token→cell map once so both render passes can reuse it.
    # nucleus_bg is precomputed here so the edges pass can use it for the
    # gradient inner color without needing the token.
    from .colors import get_nucleus_colors
    cell_index_to_cell = {}
    token_cells = []  # parallel to tokens: (token, ftok, cell, ci, nucleus_bg)
    for token in tokens:
        ci = cell_indices[token.index]
        col = ci % grid.cols
        row = ci // grid.cols
        cell = Cell(
            Point(grid_rect.left + col * cell_width, grid_rect.top + row * cell_height),
            Size(cell_width, cell_height),
        )
        cell_index_to_cell[ci] = cell
        nucleus_bg, _ = get_nucleus_colors(token.quant)
        token_cells.append((token, used_ftoks[token.index], cell, ci, nucleus_bg))

    # Layer 1: every cell's edge shapes, all drawn before any nucleus or
    # overlay element. This is required because the ellipse overlay
    # (Phase 12) must sit on top of all edges but below all nuclei across
    # the whole grid.
    for token, ftok, cell, ci, nucleus_bg in token_cells:
        renderer.render_edges(svg, defs, ftok, cell, cell_index=ci, nucleus_bg=nucleus_bg)

    # Layer 2: ellipse overlay derived from raw digest bytes 60-63,
    # clipped to the bounding rect.
    digest = compute_fingerprint(core)
    _draw_ellipse_overlay(
        svg, defs, digest, bounding_rect, grid_rect,
        cell_w=cell_width, cell_h=cell_height,
        bg_color=style.bg_color, clip_id=clip_id,
    )

    # V3-4: per-token cell-text rendered size. Reference drives all
    # geometry; rendered size shrinks for hex (6-char tokens) so the
    # text fits inside the 3×nucleus_height-wide nucleus.
    cell_text_pt = (
        round(font_size_pt * 0.75)
        if "hex" in type_name.lower() else font_size_pt
    )
    cell_text_px = cell_text_pt * _DPI / 72

    # Layer 3: every cell's nucleus rect + text, drawn on top of edges
    # (and on top of the future ellipse overlay).
    for token, ftok, cell, ci, _nucleus_bg in token_cells:
        renderer.render_nucleus(svg, token, cell, text_size_px=cell_text_px)

    # Layer 4: quartile marks at the cells of the four quartile ftoks
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

    # Layer 5a: color bar inside its inset rect (x=1, width=edge_size).
    # Bands proportional to count^4 of each edge color (V3-1); empty
    # cells excluded since their render_edges is never called; sorted
    # descending by count with edge_colors order as the tiebreak.
    _draw_color_bar(
        svg, color_bar_rect, gm,
        renderer.color_usage, style.edge_colors,
    )

    # Layer 5b: shape count summary right-justified to grid_rect's right
    # edge, on the nucleus-height line below the grid. Rendered at
    # min(round(0.9 × reference), cell_text_pt) with #444 fill. For hex
    # inputs, cell_text_pt = round(0.75 × reference), so the min picks
    # cell_text_pt and the SCS matches the cell text size.
    _draw_shape_count_summary(
        svg, grid_rect, gm, nucleus_height,
        reference_pt=font_size_pt,
        cell_text_pt=cell_text_pt,
        dpi=_DPI,
        shape_usage=renderer.shape_usage,
    )

    # Black border lines on all four sides of the bounding rect, plus an
    # interior vertical separator at x = 1 + edge_size (the color bar's
    # right edge). The top, right, bottom, and left borders frame the
    # whole entviz; the interior separator divides the color bar from
    # the grid-margin column. All five lines are 1 px stroke #000000.
    _draw_border_line(svg, 0, 0, bounding_w - 1, 0)                                  # top
    _draw_border_line(svg, bounding_w - 1, 0, bounding_w - 1, bounding_h - 1)        # right
    _draw_border_line(svg, 0, bounding_h - 1, bounding_w - 1, bounding_h - 1)        # bottom
    _draw_border_line(svg, 0, 0, 0, bounding_h - 1)                                  # left
    _draw_border_line(svg, 1 + edge_size, 0, 1 + edge_size, bounding_h - 1)          # interior separator

    return etree.tostring(svg, encoding='unicode', xml_declaration=False)


def _draw_border_line(svg, x1, y1, x2, y2):
    etree.SubElement(
        svg, 'line',
        x1=str(x1), y1=str(y1), x2=str(x2), y2=str(y2),
        stroke='#000000', **{'stroke-width': '1'},
    )


def enumerate_perimeter_points(cols, rows, cell_w, cell_h, origin: Point) -> list:
    """
    v2 spec line 156: walk perimeter cells in cell-index order; for each,
    visit corners in TL, TR, BL, BR order; emit each unique point the
    first time it is seen.

    Returns a list of Point objects in deterministic order; duplicates
    suppressed. Points are in user space (offset by `origin`).
    """
    seen = {}
    points = []

    def emit(x, y):
        key = (x, y)
        if key in seen:
            return
        seen[key] = True
        points.append(Point(x, y))

    for ci in range(cols * rows):
        col = ci % cols
        row = ci // cols
        is_perimeter = (row == 0 or row == rows - 1 or col == 0 or col == cols - 1)
        if not is_perimeter:
            continue
        x = origin.x + col * cell_w
        y = origin.y + row * cell_h
        emit(x, y)                                       # TL
        emit(x + cell_w, y)                              # TR
        emit(x, y + cell_h)                              # BL
        emit(x + cell_w, y + cell_h)                     # BR
    return points


def enumerate_interior_corners(cols, rows, cell_w, cell_h, origin: Point) -> list:
    """
    V3-5: enumerate strictly-interior corners of an N-cols × M-rows grid.
    These are the cell-corner points that lie inside the grid_rect — not
    on its outer boundary. There are exactly (cols - 1) × (rows - 1) such
    points. Returned in row-major order (left to right, top to bottom),
    offset by `origin`.
    """
    return [
        Point(origin.x + c * cell_w, origin.y + r * cell_h)
        for r in range(1, rows)
        for c in range(1, cols)
    ]


def ellipse_params_from_digest(digest: bytes) -> dict:
    """
    v2 mapping (kept for backwards-compatible test imports). v3 uses
    v3_ellipse_params_from_digest below.
    """
    return {
        "anchor_index": digest[60],
        "axis_ratio": 1.0 + (digest[61] / 255.0) * 1.5,
        "rotation_deg": (digest[62] / 255.0) * 180.0,
        "opacity": 0.10 + (digest[63] / 255.0) * 0.20,
    }


def v3_ellipse_params_from_digest(digest: bytes) -> dict:
    """
    V3-5: map raw digest bytes 60-63 to the v3 ellipse parameters.

    - anchor_index: digest[60] (full byte; caller mods by pool size)
    - rx_step, ry_step, rotation_step: each digest byte mod 16 → 0..15
      discretization. Caller maps to ranges:
        rx       = r_min + rx_step/15 × (r_max − r_min)
        ry       = r_min + ry_step/15 × (r_max − r_min)
        rotation = rotation_step/15 × 180°
      with r_min = cell_h and r_max = d_far(anchor) − cell_w.
    - opacity is fixed at 0.20 (no digest byte consumed for it).
    """
    return {
        "anchor_index": digest[60],
        "rx_step": digest[61] % 16,
        "ry_step": digest[62] % 16,
        "rotation_step": digest[63] % 16,
    }


def _ellipse_fill_for_bg(bg_color: str) -> str:
    # Hex → RGB → HLS; if L > 0.5 fill black, else fill white.
    r = int(bg_color[1:3], 16) / 255.0
    g = int(bg_color[3:5], 16) / 255.0
    b = int(bg_color[5:7], 16) / 255.0
    _, l, _ = colorsys.rgb_to_hls(r, g, b)
    return '#000000' if l > 0.5 else '#ffffff'


_V3_OVERLAY_MIN_INTERIOR_CORNERS = 6  # 3x4 / 4x3 and larger
_V3_OVERLAY_OPACITY = 0.20


def _draw_ellipse_overlay(svg, defs, digest, bounding_rect, grid_rect,
                          cell_w, cell_h, bg_color, clip_id):
    """
    V3-5 ellipse overlay:
      - skip if grid has < 6 interior corners (~< 256 bits of input)
      - anchor: strictly-interior corner of the grid
      - rx, ry: independent, each in [cell_h, d_far − cell_w] with
        16-level discretization
      - rotation: [0°, 180°), 16-level
      - opacity: fixed 20%
      - clip target: grid_rect (passed in via clip_id)
    """
    cols = int(round(grid_rect.size.width / cell_w))
    rows = int(round(grid_rect.size.height / cell_h))
    if (cols - 1) * (rows - 1) < _V3_OVERLAY_MIN_INTERIOR_CORNERS:
        return  # grid too small for the overlay to read

    points = enumerate_interior_corners(
        cols=cols, rows=rows, cell_w=cell_w, cell_h=cell_h,
        origin=Point(grid_rect.left, grid_rect.top),
    )
    if not points:
        return

    p = v3_ellipse_params_from_digest(digest)
    anchor = points[p["anchor_index"] % len(points)]

    # d_far = distance from anchor to the farthest of the grid_rect's
    # four outer corners.
    corners = [
        (grid_rect.left, grid_rect.top),
        (grid_rect.right, grid_rect.top),
        (grid_rect.left, grid_rect.bottom),
        (grid_rect.right, grid_rect.bottom),
    ]
    d_far = max(math.hypot(c[0] - anchor.x, c[1] - anchor.y) for c in corners)
    r_min = cell_h
    r_max = d_far - cell_w
    if r_max <= r_min:
        return  # degenerate radius range — shouldn't trigger past the >=6
                # interior-corners gate, but defensive

    rx = r_min + (p["rx_step"] / 15.0) * (r_max - r_min)
    ry = r_min + (p["ry_step"] / 15.0) * (r_max - r_min)
    rotation_deg = (p["rotation_step"] / 15.0) * 180.0
    fill = _ellipse_fill_for_bg(bg_color)
    # SVG quirk: when clip-path and transform live on the same element,
    # the clip rectangle rotates along with the element (clip-path is
    # resolved in post-transform user space). Wrap the ellipse in a
    # non-rotated <g> that carries the clip-path; keep the rotate
    # transform on the <ellipse> inside. The clip then stays in
    # screen space while the ellipse rotates within it.
    clipped = etree.SubElement(svg, 'g', **{"clip-path": f"url(#{clip_id})"})
    etree.SubElement(
        clipped, 'ellipse',
        cx=str(anchor.x), cy=str(anchor.y),
        rx=str(rx), ry=str(ry),
        transform=f"rotate({rotation_deg} {anchor.x} {anchor.y})",
        fill=fill,
        **{"fill-opacity": f"{_V3_OVERLAY_OPACITY}"},
    )


def _draw_shape_count_summary(svg, grid_rect, gm, nucleus_height,
                              reference_pt, cell_text_pt, dpi, shape_usage):
    """
    V3-3a: SCS rendered font size = min(round(0.9 × reference_pt),
    cell_text_pt). Fill = #444. The min keeps the SCS from rendering
    larger than the cell text once V3-4 introduces per-token cell-text
    shrinking; pre-V3-4 the min is a no-op because cell_text_pt ==
    reference_pt.
    """
    # V3 SCS: format is `X##` where X is the shape's 1-digit slot index
    # (1, 2, 3) and ## is the zero-padded 2-digit count. Empty shapes
    # (slot 4) are tallied but NOT displayed — their count is derivable
    # as 6 × non_blank_cells − sum(displayed counts).
    used = [
        (s, n) for s, n in shape_usage.items()
        if n > 0 and not getattr(s, 'is_empty', False)
    ]
    if not used:
        return
    # Sort descending by count, tiebreak by slot number.
    used.sort(key=lambda x: (-x[1], x[0].slot))
    tokens = [f"{s.slot}{n:02d}" for s, n in used]
    text = " ".join(tokens)
    # Top of the SCS line is grid_rect.bottom + GM; vertical center for
    # dominant-baseline=central is half of nucleus_height down from that.
    y = grid_rect.bottom + gm + nucleus_height / 2
    # Compute rendered SCS font size in points, then convert to pixels.
    scs_pt = min(round(0.9 * reference_pt), cell_text_pt)
    scs_px = scs_pt * dpi / 72
    el = etree.SubElement(
        svg, 'text',
        x=str(grid_rect.right),
        y=str(y),
        fill='#444444',
        style=f"font-family: monospace; font-size: {scs_px}px;",
        **{"text-anchor": "end", "dominant-baseline": "central"},
    )
    el.text = text


def _draw_color_bar(svg, bar_rect, gm, color_usage, edge_colors):
    """
    Draw color-bar bands inside bar_rect's drawing region.

    bar_rect is the color bar's *drawing region* (already accounting
    for the surrounding black borders that cover 1 px on each side in
    v3): bar_rect.left = 1, bar_rect.width = edge_size, bar_rect.top = 1,
    bar_rect.height = bounding_h - 2.

    Band heights are weighted by `count^4` (V3-1). The `gm` parameter is
    accepted for backwards-compatible call signatures but unused.
    """
    used = [
        (c, color_usage.get(c, 0))
        for c in edge_colors if color_usage.get(c, 0) > 0
    ]
    if not used:
        return
    # Sort: descending by count, tiebreak by index in edge_colors. Since
    # x^4 is monotonic for non-negative x, sorting by count or by count^4
    # produces the same order; we sort by raw count for clarity.
    color_order = {c: i for i, c in enumerate(edge_colors)}
    used.sort(key=lambda x: (-x[1], color_order[x[0]]))
    total = sum(n ** 4 for _, n in used)
    y = bar_rect.top
    for i, (color, n) in enumerate(used):
        is_last = i == len(used) - 1
        # Pin the last band to exactly cover the remaining height so any
        # floating-point drift doesn't leave a gap or overflow.
        h = (bar_rect.bottom - y) if is_last else bar_rect.size.height * (n ** 4) / total
        etree.SubElement(
            svg, 'rect',
            x=str(bar_rect.left), y=str(y),
            width=str(bar_rect.size.width), height=str(h),
            fill=color,
        )
        y += h
