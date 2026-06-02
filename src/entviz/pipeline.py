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

from . import SPEC_VERSION, __version__
from .entropy import parse, tokenize_entropy
from .layout import choose_grid, assign_cell_indices, Cell, Point, Rect, Size
from .colors import select_visual_style
from .fingerprint import (
    compute_fingerprint,
    get_median_ftok,
    get_quartile_ftoks,
    tokenize_fingerprint,
)
from .renderer import Renderer, MONOSPACE_FONT_FAMILY
from .shapes import canvas, rect as draw_rect

_DPI = 96


def render(entropy_text: str, target_ar: float = 1.0, font_size_pt: int = 12) -> str:
    """
    Render entropy as an SVG entviz and return the SVG as a UTF-8 string.
    """
    # --- Normalize and tokenize the entropy ---
    raw_input = entropy_text.strip()
    parsed = parse(raw_input)
    if parsed is None:
        import base64
        from .entropy import BASE64URL
        core = base64.urlsafe_b64encode(raw_input.encode()).decode().rstrip('=')
        # "txt(N)->b64url" surfaces in the per-entviz top label so the
        # viewer knows the input wasn't directly tokenizable in any
        # known alphabet and we re-encoded it as bytes. N = input chars.
        type_name = f"txt({len(raw_input)})->b64url"
        alphabet = BASE64URL  # fallback always produces urlsafe base64
        prefix = None
        suffix = None
    else:
        core = parsed.core
        type_name = parsed.type
        alphabet = parsed.alphabet
        prefix = parsed.prefix
        suffix = parsed.suffix
        # Length-bearing labels for the variable-length plain-alphabet
        # types (hex / b64 / b64url). Rename base64* → b64* for
        # consistency with the txt->b64url fallback shortening.
        if type_name == "hex":
            type_name = f"hex({len(core)})"
        elif type_name == "base64":
            type_name = f"b64({len(core)})"
        elif type_name == "base64url":
            type_name = f"b64url({len(core)})"

    tokens, is_truncated = tokenize_entropy(core, alphabet)
    if not tokens:
        raise ValueError("No tokens produced from input entropy.")

    # v5: when the input exceeds 512 bits, tokenize_entropy returns 20
    # tokens — 8 head + 4 middle slices + 8 tail. The label gets a loud
    # `part of` prefix rendered in bold dark-red; assembly is
    # done in _draw_label_strips where the styling lives. We carry the
    # byte count separately so the label rendering doesn't have to peek
    # at the raw input.
    truncated_bytes = len(raw_input.encode("utf-8")) if is_truncated else None

    # v5 large-input layout uses a fixed 22-cell budget: H=8 + 1 blank +
    # M=4 + 1 blank + T=8. The 20 returned tokens map to cell indices
    # 0..7 (head), 9..12 (middle), and 14..21 (tail); cell indices 8 and
    # 13 are the separator blanks. We bypass the median/quartile blank
    # insertion entirely in this path because the cell layout is fully
    # determined by the spec.
    token_count = len(tokens)

    # --- Compute the fingerprint and derive used ftoks ---
    # The fingerprint avalanche means single-bit input changes propagate
    # to every ftok-derived channel.
    used_ftoks = tokenize_fingerprint(compute_fingerprint(core))[:token_count]

    # --- Choose grid ---
    if is_truncated:
        # v5: fixed 22 cells (20 tokens + 2 separators).
        grid = choose_grid(22, target_ar)
    else:
        grid = choose_grid(token_count, target_ar)

    # --- Median, quartiles, visual style — all from ftoks ---
    median_ftok = get_median_ftok(used_ftoks)
    quartile_ftoks = get_quartile_ftoks(used_ftoks)
    second_quartile_ftok = quartile_ftoks[1] if len(quartile_ftoks) > 1 else None
    style = select_visual_style(median_ftok, second_quartile_ftok)

    # --- Blank cell placement keyed off ftok ASCII sort ---
    if is_truncated:
        # v5: deterministic mapping. tokens[0..7] → cells 0..7;
        # tokens[8..11] → cells 9..12 (skipping separator at cell 8);
        # tokens[12..19] → cells 14..21 (skipping separator at cell 13).
        # The median/quartile blank-insertion rule does NOT apply here:
        # the spec says >512-bit inputs always have token_count = 20 and
        # use a 22-cell grid with the two separators fixed at 8 and 13.
        cell_indices = {}
        for t_idx in range(token_count):
            if t_idx < 8:
                cell_indices[t_idx] = t_idx
            elif t_idx < 12:
                cell_indices[t_idx] = t_idx + 1  # skip cell 8
            else:
                cell_indices[t_idx] = t_idx + 2  # skip cells 8 and 13
    else:
        cell_indices = assign_cell_indices(
            tokens, grid, median_token=median_ftok, sort_keys=used_ftoks
        )

    # --- Pixel dimensions ---
    # font_size_px is the rendered text size for full-size cells (base64).
    # nucleus is enlarged vertically (1.25·font_size_px) so descenders fit;
    # nucleus width stays at 3·font_size_px. Surround box dimensions follow
    # from the tiling constraints: 10 top-row boxes span nucleus_width +
    # 2·box_width, so box_width = nucleus_width / 8 = font_size_px × 3/8;
    # 2 side-column boxes stack to nucleus_height, so box_height =
    # nucleus_height / 2 = font_size_px × 5/8. cell_width = 10·box_width
    # = font_size_px × 3.75; cell_height = 4·box_height = font_size_px × 2.5.
    # GM (grid margin) = box_height / 2.
    font_size_px = (font_size_pt * _DPI) / 72
    nucleus_width = font_size_px * 3
    nucleus_height = font_size_px * 1.25
    box_width = nucleus_width / 8
    box_height = nucleus_height / 2
    cell_width = nucleus_width + 2 * box_width
    cell_height = nucleus_height + 2 * box_height
    gm = box_height / 2
    # v6: the color bar is its own geometry term, twice box_height wide, so
    # its per-band color letters render legibly (v5 reused box_height = 10px,
    # too narrow for the letters). bar_width = 2·box_height = 1.25·font_size_px.
    bar_width = 2 * box_height

    grid_w = cell_width * grid.cols
    grid_h = cell_height * grid.rows

    # Bounding rect dimensions (v6):
    #   width  = 1 + bar_width + 1 + GM + grid_width + GM + 1
    #   height = 1 + GM + nucleus_height + GM + grid_height
    #              + [GM + nucleus_height +] GM + 1
    # The top "type label" strip is always present (the entviz declares
    # the detected type / alphabet). The bottom "suffix label" strip
    # appears only when the parsed result has a suffix.
    bounding_w = 1 + bar_width + 1 + gm + grid_w + gm + 1
    has_suffix_label = bool(suffix)
    suffix_strip_h = nucleus_height + gm if has_suffix_label else 0
    bounding_h = (
        1 + gm + nucleus_height + gm + grid_h + gm + suffix_strip_h + 1
    )
    bounding_rect = Rect(Point(0, 0), Size(bounding_w, bounding_h))

    # grid_rect sits below the top label strip.
    grid_rect = Rect(
        Point(1 + bar_width + 1 + gm, 1 + gm + nucleus_height + gm),
        Size(grid_w, grid_h),
    )

    # Color bar drawing region: x=1, width=bar_width; y starts at 1
    # (just below the top border) and ends at bounding_h - 1 (just
    # above the bottom border), so its drawable height is bounding_h - 2.
    color_bar_rect = Rect(
        Point(1, 1), Size(bar_width, bounding_h - 2),
    )

    renderer = Renderer(style, grid)

    svg = canvas(bounding_rect.size)
    # v5: data-* attributes on the root SVG let an overlay (e.g. the
    # Idea-2 React component) discover structure without re-deriving it
    # from raw geometry. data-truncated is OMITTED when false (not
    # rendered as ="false") so a missing attribute reads as the absence
    # of the property.
    # data-entviz-version = the spec/algorithm revision the output conforms
    # to; data-entviz-lib = the library build that produced it. Two axes,
    # both sourced from src/entviz/__init__.py (see that file).
    svg.set("data-entviz-version", SPEC_VERSION)
    svg.set("data-entviz-lib", __version__)
    svg.set("data-input-bytes", str(len(raw_input.encode("utf-8"))))
    svg.set("data-cols", str(grid.cols))
    svg.set("data-rows", str(grid.rows))
    if is_truncated:
        svg.set("data-truncated", "true")
    # <defs> first so gradients, clipPath, and future symbols appear at
    # the top of the SVG. Order of definitions inside <defs> doesn't
    # matter for SVG rendering, but consolidating them early keeps the
    # document scannable.
    defs = etree.SubElement(svg, 'defs')

    # clipPath spans the grid_rect (not the bounding rect). The ellipse
    # overlay clips to the cells-only area; the bounding-rect margins
    # and color bar stay overlay-free. The id is salted with the first
    # 16 hex chars (64 bits) of the fingerprint so that multiple SVGs
    # embedded in the same HTML document (e.g. the gallery page) don't
    # collide on `#grid-clip` — when two clipPaths share an id, the
    # browser resolves url(#…) to the FIRST one document-wide, silently
    # clipping every other entviz to the first one's rectangle. 64-bit
    # salt gives ~4 billion entvizes before birthday-bound collision;
    # the pre-fix 32-bit salt birthday-bounded at ~65k (review F-A3).
    digest_hex = compute_fingerprint(core).hex()
    clip_id = f"grid-clip-{digest_hex[:16]}-{grid.cols}x{grid.rows}"
    cp = etree.SubElement(defs, 'clipPath', id=clip_id)
    etree.SubElement(
        cp, 'rect',
        x=str(grid_rect.left), y=str(grid_rect.top),
        width=str(grid_rect.size.width), height=str(grid_rect.size.height),
    )

    draw_rect(svg, bounding_rect, '#ffffff')

    # v5: introduce channel groups so an overlay can find each visual
    # subsystem by name (data-channel="..."). The groups are pure
    # metadata — they have no transform, fill, or opacity, so they do
    # not affect rendering. The depth-first document order of leaf
    # elements is preserved exactly, which is what every existing
    # layering test relies on. The ellipse group is nested inside the
    # grid group (between edges and nuclei) so layering is preserved
    # while still being a queryable channel on its own.
    grid_g = etree.SubElement(svg, 'g', **{"data-channel": "grid"})

    # Entviz background color (from median ftok) fills the grid_rect so
    # blank cells show that color rather than the white bounding-rect fill.
    draw_rect(grid_g, grid_rect, style.bg_color)

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

    # v5: pre-allocate per-cell groups for the nucleus / blank-marker /
    # quartile layer (Layer 3+) keyed by cell-index. Cells are created
    # in reading order so the document-order traversal of "//*" still
    # walks them as 0,1,2,...; that order is required by overlays that
    # use cell-index as an iteration key. Edges remain a single flat
    # batch (Layer 1) so the "all edges before any nucleus" invariant
    # still holds after the ellipse layer.
    used_cell_indices = set(cell_indices.values())

    # Layer 1: every cell's edge shapes, all drawn before any nucleus or
    # overlay element. This is required because the ellipse overlay
    # (Phase 12) must sit on top of all edges but below all nuclei across
    # the whole grid. Wrapped in an internal group for tidiness; the
    # group itself is purely organizational (no data-channel attribute
    # so React queries don't see it as a separate channel).
    edges_g = etree.SubElement(grid_g, 'g')
    for token, ftok, cell, ci, nucleus_bg in token_cells:
        renderer.render_edges(edges_g, ftok, cell, nucleus_bg=nucleus_bg)

    # Layer 2: ellipse overlay derived from raw digest bytes 60-63,
    # clipped to the grid rect. Wrapped in its own data-channel group
    # carrying the ellipse parameters as data-* so an overlay can find
    # the silhouette without re-deriving it from the digest.
    digest = compute_fingerprint(core)
    _draw_ellipse_overlay(
        grid_g, defs, digest, bounding_rect, grid_rect,
        cell_w=cell_width, cell_h=cell_height,
        bg_color=style.bg_color, clip_id=clip_id,
    )

    # v5: per-cell groups inside the grid, in reading order. Each group
    # carries data-cell-index/row/col plus optional data-cell-blank,
    # data-cell-quartile, data-cell-blank-marker. The nucleus, text,
    # quartile-mark, and blank-marker children get attached to the
    # appropriate group below.
    nuclei_g = etree.SubElement(grid_g, 'g')  # holds all cell groups
    cell_groups = {}
    for ci in range(grid.cols * grid.rows):
        col = ci % grid.cols
        row = ci // grid.cols
        attrs = {
            "data-channel": "cell",
            "data-cell-index": str(ci),
            "data-cell-row": str(row),
            "data-cell-col": str(col),
        }
        if ci not in used_cell_indices:
            attrs["data-cell-blank"] = "true"
        cell_groups[ci] = etree.SubElement(nuclei_g, 'g', **attrs)

    # V3-4: per-token cell-text rendered size. Reference drives all
    # geometry; rendered size shrinks for 6-char tokens (4-bit alphabets:
    # hex, decimal) so the text fits inside the 3×nucleus_height-wide
    # nucleus. Per spec: 4-char tokens render at reference size; 6-char
    # tokens render at 0.75× reference.
    cell_text_pt = (
        round(font_size_pt * 0.75)
        if alphabet.bits_per_char == 4 else font_size_pt
    )
    cell_text_px = cell_text_pt * _DPI / 72
    label_text_px = round(font_size_pt * 0.75) * _DPI / 72

    # Layer 3: every cell's nucleus rect + text, drawn on top of edges
    # (and on top of the future ellipse overlay).
    for token, ftok, cell, ci, _nucleus_bg in token_cells:
        renderer.render_nucleus(
            cell_groups[ci], token, cell, text_size_px=cell_text_px
        )

    # Layer 3b: blank cells — every cell index in the grid that no token
    # was placed at. v6: each blank cell shows a black-outlined rounded
    # rectangle coincident with the nucleus rect. The FIRST blank cell (the
    # lowest cell index) additionally becomes a "map": a miniature scale
    # model of the grid, filled (white, or gold on a white-bg entviz), with
    # a red dot at the maxftok cell's grid position and a blue dot at the
    # minftok cell's. This replaces v5's white-disc + clock hands and its
    # mix-blend-mode dependence, closing adversarial finding F-A6 here.

    def _cell_nucleus_origin(ci):
        col = ci % grid.cols
        row = ci // grid.cols
        return (
            grid_rect.left + col * cell_width + box_width,
            grid_rect.top + row * cell_height + box_height,
        )

    # Identify minftok / maxftok cells. used_ftoks[i] corresponds to
    # tokens[i] by index. Build (ftok, cell_index) pairs, then min/max
    # by (quant, ±cell_index) for the tie-break.
    used_ftok_cells = [
        (used_ftoks[t.index], cell_indices[t.index]) for t in tokens
    ]
    # For min: smallest quant; tie-break = highest cell index
    min_ftok_cell_idx = min(
        used_ftok_cells, key=lambda fc: (fc[0].quant, -fc[1])
    )[1]
    # For max: largest quant; tie-break = highest cell index
    max_ftok_cell_idx = max(
        used_ftok_cells, key=lambda fc: (fc[0].quant, fc[1])
    )[1]

    blank_indices = [ci for ci in range(grid.cols * grid.rows)
                     if ci not in used_cell_indices]
    map_cell_idx = min(blank_indices) if blank_indices else None
    corner_radius = font_size_px / 8     # = 2 at 12pt
    # The map fill must contrast with whatever background shows behind it:
    # white on any non-white entviz background, gold on a white one.
    map_fill = '#ffd966' if style.bg_color == '#ffffff' else '#ffffff'

    for ci in blank_indices:
        cg = cell_groups[ci]
        nx, ny = _cell_nucleus_origin(ci)
        is_map = ci == map_cell_idx
        etree.SubElement(
            cg, 'rect',
            x=str(nx), y=str(ny),
            width=str(nucleus_width), height=str(nucleus_height),
            rx=str(corner_radius), ry=str(corner_radius),
            fill=(map_fill if is_map else 'none'), stroke='#000000',
            **{'stroke-width': '1'},
        )
        if not is_map:
            continue
        # Map: subdivide the nucleus rect into cols×rows logical sub-cells
        # mirroring the grid, then place a red dot (maxftok cell) and a blue
        # dot (minftok cell) at their matching (row, col) positions.
        cg.set("data-cell-blank-map", "true")
        sub_w = nucleus_width / grid.cols
        sub_h = nucleus_height / grid.rows
        dot_r = 0.35 * min(sub_w, sub_h)

        def _sub_center(cell_idx):
            return (nx + (cell_idx % grid.cols + 0.5) * sub_w,
                    ny + (cell_idx // grid.cols + 0.5) * sub_h)

        max_cx, max_cy = _sub_center(max_ftok_cell_idx)
        min_cx, min_cy = _sub_center(min_ftok_cell_idx)
        if max_ftok_cell_idx == min_ftok_cell_idx:
            # Degenerate (single used ftok): blue ring + concentric red dot
            # so both remain visible.
            etree.SubElement(
                cg, 'circle', cx=str(min_cx), cy=str(min_cy), r=str(dot_r),
                fill='none', stroke='#1d4ed8',
                **{'stroke-width': '1', 'data-blank-map-min': 'true'},
            )
            etree.SubElement(
                cg, 'circle', cx=str(max_cx), cy=str(max_cy), r=str(dot_r * 0.5),
                fill='#d62828', **{'data-blank-map-max': 'true'},
            )
        else:
            etree.SubElement(
                cg, 'circle', cx=str(max_cx), cy=str(max_cy), r=str(dot_r),
                fill='#d62828', **{'data-blank-map-max': 'true'},
            )
            etree.SubElement(
                cg, 'circle', cx=str(min_cx), cy=str(min_cy), r=str(dot_r),
                fill='#1d4ed8', **{'data-blank-map-min': 'true'},
            )

    # Layer 4: quartile marks at the cells of the four quartile ftoks
    # (mapped through the 1:1 ftok→token→cell correspondence). The mark
    # is drawn in the cell text's foreground color, so we look up the
    # token for each quartile cell to recover its quant.
    token_by_index = {t.index: t for t in tokens}
    for q_idx, q_ftok in enumerate(quartile_ftoks):
        if q_ftok is None:
            continue
        ci = cell_indices.get(q_ftok.index)
        if ci is None:
            continue
        cell = cell_index_to_cell.get(ci)
        if cell is None:
            continue
        token = token_by_index.get(q_ftok.index)
        if token is None:
            continue
        _bg, fg_color = get_nucleus_colors(token.quant)
        # v5: emit the mark into the cell's group, and tag the group
        # with the quartile index (1..4). Quartile index here is 0-based;
        # the data-* attribute is 1-based to match the human convention
        # "1st/2nd/3rd/4th quartile".
        cg = cell_groups[ci]
        cg.set("data-cell-quartile", str(q_idx + 1))
        renderer.draw_quartile_mark(cg, cell, q_idx, fg_color)

    # Layer 5a: color bar inside its inset rect (x=1, width=box_height).
    # Bands proportional to count^4 of each edge color (V3-1); empty
    # cells excluded since their render_edges is never called; sorted
    # descending by count with edge_colors order as the tiebreak.
    _draw_color_bar(
        svg, color_bar_rect, gm,
        _two_bit_color_usage(digest, style.edge_colors), style.edge_colors,
        box_height=box_height,
    )
    # (color bar width is bar_width = 2·box_height; the letter-size cap reads
    # bar_rect.size.width directly, so it picks up the wider bar automatically.)

    # Layer 5b: top / bottom label strips. The top strip is always drawn
    # ("<Type>:" or "<Type>: <prefix>..."). The bottom strip appears only
    # when the parsed result has a suffix ("...<suffix>"). Both use the
    # cell-text font family and rendered size, filled #666 so they read
    # as a quiet label, not competing with the cells.
    _draw_label_strips(
        svg, grid_rect, gm, nucleus_height,
        type_name=type_name, prefix=prefix, suffix=suffix,
        text_size_px=label_text_px,
        truncated_bytes=truncated_bytes,
    )

    # Gray border lines (#808080) on all four sides of the bounding rect,
    # plus an interior vertical separator at x = 1 + bar_width + 0.5 (the
    # color bar's right edge). Each line is centered on a half-pixel so a
    # 1-px stroke covers exactly one pixel column/row crisply; the four
    # outer lines extend the full canvas width/height so the corner
    # pixels are painted by both adjacent sides (no 1-px gap at corners).
    # shape-rendering="crispEdges" disables antialiasing so the lines
    # render as solid 1-px bands, not blurry 2-px halos.
    _draw_border_line(svg, 0, 0.5, bounding_w, 0.5)                                  # top
    _draw_border_line(svg, bounding_w - 0.5, 0, bounding_w - 0.5, bounding_h)        # right
    _draw_border_line(svg, 0, bounding_h - 0.5, bounding_w, bounding_h - 0.5)        # bottom
    _draw_border_line(svg, 0.5, 0, 0.5, bounding_h)                                  # left
    _draw_border_line(svg, 1 + bar_width + 0.5, 0,
                      1 + bar_width + 0.5, bounding_h)                                # interior separator

    return etree.tostring(svg, encoding='unicode', xml_declaration=False)


def _draw_label_strips(svg, grid_rect, gm, nucleus_height,
                       type_name, prefix, suffix, text_size_px,
                       truncated_bytes=None):
    """
    Render the top "<Type>: <prefix>..." label strip (always) and, when
    suffix is present, the bottom "...<suffix>" strip. Strips are
    `nucleus_height` tall, separated from the grid and from the border
    by GM. Both strips use monospace at `text_size_px`, filled #666.
    Top is left-aligned to grid_rect.left; bottom is right-aligned to
    grid_rect.right (so the ellipses on each point inward toward the
    cells).

    v5: each strip is wrapped in its own data-channel group
    ("label-top" / "label-bottom") so an overlay can highlight or
    suppress the labels independently.

    When `truncated_bytes` is not None, the top label is prefixed with a
    loud `part of ` marker rendered in bold dark-red (#a00000), with the
    rest of the label following in the standard #666 non-bold style. The
    marker and tail are emitted as two adjacent <text> elements inside
    the label-top group so the styling cleanly differs while the line
    still reads left-to-right. The byte count is omitted from the marker
    because it is already present in the type-label parenthetical (e.g.
    `hex(200)`, `b64(119)`).
    """
    style = f"font-family: {MONOSPACE_FONT_FAMILY}; font-size: {text_size_px}px;"
    # Top strip — always.
    top_g = etree.SubElement(svg, 'g', **{"data-channel": "label-top"})
    rest_text = f"{type_name}:"
    if prefix:
        rest_text += f" {prefix}..."
    # Vertical center of the top strip is at grid_rect.top - GM - nucleus_height/2.
    top_cy = grid_rect.top - gm - nucleus_height / 2
    if truncated_bytes is not None:
        # Loud marker in bold dark red, followed by the standard label
        # in #666. Use two adjacent <text> elements so each carries its
        # own styling unambiguously; the second is positioned with `dx`
        # equal to the rendered width of the marker text in monospace
        # ems. Monospace assumption: char width ≈ 0.6 · font_size_px is
        # a safe approximation across DejaVu Sans Mono / Menlo /
        # Consolas (all sit in 0.55–0.62). We pad with a single ascii
        # space between marker and tail to make the visual break crisp.
        marker_text = "part of "
        marker_el = etree.SubElement(
            top_g, 'text',
            x=str(grid_rect.left), y=str(top_cy),
            fill='#a00000', style=style,
            **{
                "dominant-baseline": "central",
                "font-weight": "bold",
            },
        )
        marker_el.text = marker_text
        # Approximate monospace advance per char. Slight overestimate is
        # fine — it just leaves a tiny visual gap; underestimate would
        # cause overlap, which is worse.
        char_advance = text_size_px * 0.6
        tail_x = grid_rect.left + len(marker_text) * char_advance
        tail_el = etree.SubElement(
            top_g, 'text',
            x=str(tail_x), y=str(top_cy),
            fill='#666666', style=style,
            **{"dominant-baseline": "central"},
        )
        tail_el.text = rest_text
    else:
        el = etree.SubElement(
            top_g, 'text',
            x=str(grid_rect.left), y=str(top_cy),
            fill='#666666', style=style,
            **{"dominant-baseline": "central"},
        )
        el.text = rest_text
    # Bottom strip — only when suffix exists.
    if suffix:
        bottom_g = etree.SubElement(svg, 'g', **{"data-channel": "label-bottom"})
        bottom_text = f"...{suffix}"
        bottom_cy = grid_rect.bottom + gm + nucleus_height / 2
        el = etree.SubElement(
            bottom_g, 'text',
            x=str(grid_rect.right), y=str(bottom_cy),
            fill='#666666', style=style,
            **{"text-anchor": "end", "dominant-baseline": "central"},
        )
        el.text = bottom_text


def _draw_border_line(svg, x1, y1, x2, y2):
    etree.SubElement(
        svg, 'line',
        x1=str(x1), y1=str(y1), x2=str(x2), y2=str(y2),
        stroke='#808080', **{'stroke-width': '1', 'shape-rendering': 'crispEdges'},
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


def enumerate_external_corners(cols, rows, cell_w, cell_h, origin: Point) -> list:
    """
    v4 hybrid: enumerate cell-corner points on the OUTER boundary of an
    N x M grid_rect. Used as ellipse anchors when the grid is too small
    to have ≥ 6 interior corners (i.e., smaller than 3x4 / 4x3).

    For an N-cols × M-rows grid there are 2(N+1) + 2(M-1) = 2(N + M)
    external corners — every cell-corner on the grid_rect's outer
    perimeter, including the four grid_rect vertices and the cell
    boundary midpoints on each edge.

    Enumeration order (row-major):
      - Top edge: (col, 0) for col in 0..N
      - For each interior row r in 1..M-1: (0, r) then (N, r)
      - Bottom edge: (col, M) for col in 0..N
    """
    points = []
    # Top edge — all N+1 corners.
    for c in range(cols + 1):
        points.append(Point(origin.x + c * cell_w, origin.y))
    # Interior rows — just the leftmost and rightmost corners.
    for r in range(1, rows):
        points.append(Point(origin.x, origin.y + r * cell_h))
        points.append(Point(origin.x + cols * cell_w, origin.y + r * cell_h))
    # Bottom edge — all N+1 corners.
    for c in range(cols + 1):
        points.append(Point(origin.x + c * cell_w, origin.y + rows * cell_h))
    return points


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
      with r_min = nucleus_height (= cell_h/2) and r_max = d_far(anchor) − cell_w.
    - opacity is fixed at 0.20 (no digest byte consumed for it).
    """
    return {
        "anchor_index": digest[60],
        "rx_step": digest[61] % 16,
        "ry_step": digest[62] % 16,
        "rotation_step": digest[63] % 16,
    }


# Per-bg overlay (fill, opacity). Saturated bgs need higher opacity to
# read against the surround boxes; white is least demanding because its
# darkened overlay is high luminance contrast already. The v4 values
# below were tuned against the hybrid-anchored small-grid overlays,
# where the visible silhouette is smaller and needs more pop.
_V3_OVERLAY_BY_BG = {
    '#ffffff': ('#000000', 0.20),  # white  → darken at 20%
    '#ffd966': ('#000000', 0.30),  # gold   → darken at 30%
    '#ff3f2f': ('#000000', 0.40),  # red    → darken at 40%
    '#2f3fbf': ('#ffffff', 0.40),  # blue   → lighten at 40%
}


def _ellipse_overlay_for_bg(bg_color: str):
    """Return (fill_color, opacity) for the ellipse overlay on bg_color."""
    if bg_color in _V3_OVERLAY_BY_BG:
        return _V3_OVERLAY_BY_BG[bg_color]
    # Fallback for any unexpected bg (e.g., test inputs): use the v3-5
    # luminosity rule with the old default 0.20 opacity.
    r = int(bg_color[1:3], 16) / 255.0
    g = int(bg_color[3:5], 16) / 255.0
    b = int(bg_color[5:7], 16) / 255.0
    _, l, _ = colorsys.rgb_to_hls(r, g, b)
    return ('#000000' if l > 0.5 else '#ffffff', 0.20)


# v4 hybrid anchor strategy threshold: grids with at least this many
# interior corners (3x4 / 4x3 and larger) anchor the ellipse at an
# interior corner — producing a centered curve mostly visible inside
# the grid. Smaller grids fall back to external (boundary) corners,
# producing a quarter-ellipse-in-a-corner or half-ellipse-along-an-
# edge silhouette. The math (r_min ≤ r_max) holds for both modes
# all the way down to a 2x2 grid.
_HYBRID_INTERIOR_THRESHOLD = 6


def _draw_ellipse_overlay(svg, defs, digest, bounding_rect, grid_rect,
                          cell_w, cell_h, bg_color, clip_id):
    """
    v4 hybrid ellipse overlay:
      - anchor: interior corner of the grid if (cols-1)·(rows-1) ≥ 6,
        otherwise an external (boundary) corner of the grid_rect
      - rx, ry: independent, each in [r_min, d_far − cell_w] with
        16-level discretization (r_min = nucleus_height = cell_h/2)
      - rotation: [0°, 180°), 16-level
      - fill and opacity: per entviz bg color
      - clip target: grid_rect (passed in via clip_id)
    """
    cols = int(round(grid_rect.size.width / cell_w))
    rows = int(round(grid_rect.size.height / cell_h))
    interior_count = (cols - 1) * (rows - 1)

    if interior_count >= _HYBRID_INTERIOR_THRESHOLD:
        points = enumerate_interior_corners(
            cols=cols, rows=rows, cell_w=cell_w, cell_h=cell_h,
            origin=Point(grid_rect.left, grid_rect.top),
        )
    else:
        points = enumerate_external_corners(
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
    # v6: clamp rx/ry to [0.22·d_far, 0.58·d_far] (was v5's
    # [nucleus_height, d_far − cell_w]). Both bounds scale with the grid via
    # d_far, holding overlay coverage in a noticeable-but-partial band
    # (~8–70%, median ~32%) on every grid size — no swamping, no slivers.
    # See reviews/ellipse-audit-2026-06-02.md. 0.58 > 0.22 always, so the
    # range is never degenerate; the guard below is purely defensive.
    r_min = 0.22 * d_far
    r_max = 0.58 * d_far
    if r_max <= r_min:
        return

    rx = r_min + (p["rx_step"] / 15.0) * (r_max - r_min)
    ry = r_min + (p["ry_step"] / 15.0) * (r_max - r_min)
    rotation_deg = (p["rotation_step"] / 15.0) * 180.0
    fill, opacity = _ellipse_overlay_for_bg(bg_color)
    # v3 structure restored: <g clip-path><ellipse transform=rotate>.
    # User confirms this rendered flawlessly in v3.
    # v5: hoist the ellipse parameters onto the wrapping clip-path group
    # AND add data-channel="ellipse" so an overlay can grab the anchor
    # + radii + rotation without parsing the transform string. The
    # rotation is normalized to [0, 180) degrees.
    clipped = etree.SubElement(
        svg, 'g',
        **{
            "clip-path": f"url(#{clip_id})",
            "data-channel": "ellipse",
            "data-ellipse-anchor-x": str(anchor.x),
            "data-ellipse-anchor-y": str(anchor.y),
            "data-ellipse-rx": str(rx),
            "data-ellipse-ry": str(ry),
            "data-ellipse-rotation-deg": str(rotation_deg),
        },
    )
    etree.SubElement(
        clipped, 'ellipse',
        cx=str(anchor.x), cy=str(anchor.y),
        rx=str(rx), ry=str(ry),
        transform=f"rotate({rotation_deg} {anchor.x} {anchor.y})",
        fill=fill,
        **{"fill-opacity": f"{opacity}"},
    )


def _two_bit_color_usage(digest: bytes, edge_colors) -> dict:
    """
    v4 color-bar source: tally each of the 4 two-bit patterns across all
    256 disjoint 2-bit slices of the digest. Pattern value i → edge_colors[i].
    """
    counts = [0, 0, 0, 0]
    for byte in digest:
        for shift in (0, 2, 4, 6):
            counts[(byte >> shift) & 0x03] += 1
    return {edge_colors[i]: counts[i] for i in range(4)}


# v5: palette → uppercase band letter mapping. Used by the color-bar
# letter rendering; an overlay component (Idea 2) can also consume the
# data-color-bar-band="<letter>" attribute without re-deriving this map.
_BAND_LETTER_BY_COLOR = {
    "#ffffff": "W",
    "#ffd966": "G",
    "#ff3f2f": "R",
    "#2f3fbf": "B",
    "#000000": "K",
}


def _draw_color_bar(svg, bar_rect, gm, color_usage, edge_colors,
                    box_height=None):
    """
    Draw color-bar bands inside bar_rect's drawing region.

    bar_rect is the color bar's *drawing region* (already accounting
    for the surrounding black borders that cover 1 px on each side in
    v3): bar_rect.left = 1, bar_rect.width = box_height, bar_rect.top = 1,
    bar_rect.height = bounding_h - 2.

    Band heights are weighted by `count^4` (V3-1). The `gm` parameter is
    accepted for backwards-compatible call signatures but unused.

    v5: each band group carries data-color-bar-band="<W|G|R|B|K>" plus
    data-color-bar-rank="<0..3>" (rank 0 = top / largest), and a
    centered uppercase letter is rendered inside each band.
    `box_height` lets callers pin the letter font-size minimum to
    0.5 · box_height; if omitted, the minimum is derived from the bar
    width instead (kept for backwards-compatible call signatures).
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
    bar_g = etree.SubElement(svg, 'g', **{"data-channel": "color-bar"})
    bar_cx = bar_rect.left + bar_rect.size.width / 2
    y = bar_rect.top
    for i, (color, n) in enumerate(used):
        is_last = i == len(used) - 1
        # Pin the last band to exactly cover the remaining height so any
        # floating-point drift doesn't leave a gap or overflow.
        h = (bar_rect.bottom - y) if is_last else bar_rect.size.height * (n ** 4) / total
        letter = _BAND_LETTER_BY_COLOR.get(color)
        band_attrs = {"data-color-bar-rank": str(i)}
        if letter is not None:
            band_attrs["data-color-bar-band"] = letter
        band_g = etree.SubElement(bar_g, 'g', **band_attrs)
        etree.SubElement(
            band_g, 'rect',
            x=str(bar_rect.left), y=str(y),
            width=str(bar_rect.size.width), height=str(h),
            fill=color,
        )
        # Centered uppercase letter. Font color follows the existing
        # Oklab L < 0.6 contrast rule used for cell text; this gives
        # black-on-{white,gold,red} and white-on-{blue,black} for the
        # five palette colors (red sits at L≈0.66, just above the
        # threshold, so the rule selects black text — if the maintainer
        # wants white-on-red, the threshold needs adjusting, not this
        # call site). Only emit a letter for palette colors; tests that
        # pass synthetic colors (e.g. "#a") skip the letter rendering.
        if letter is not None:
            from .colors import get_nucleus_colors
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)
            quant = r | (g << 8) | (b << 16)
            _bg, fg = get_nucleus_colors(quant)
            # Letter must fit both the band height and the bar width.
            # Lowercase glyphs sit largely at x-height, so this stays
            # visually compact. No minimum floor — a tiny band gets a
            # tiny letter, and bands too small for a legible glyph
            # simply skip the letter.
            font_size = min(h * 0.7, bar_rect.size.width * 0.85)
            if font_size >= 2:
                cy = y + h / 2
                text_el = etree.SubElement(
                    band_g, 'text',
                    x=str(bar_cx), y=str(cy),
                    fill=fg,
                    style=f"font-family: {MONOSPACE_FONT_FAMILY}; font-size: {font_size}px;",
                    **{
                        "text-anchor": "middle",
                        "dominant-baseline": "central",
                        "data-color-bar-letter": "true",
                    },
                )
                text_el.text = letter.lower()
        y += h
