"""
Full entviz rendering pipeline: entropy string → SVG string.

Implements the v6 algorithm specified in docs/spec.md (the authoritative
spec); this.i records the "why" behind each decision referenced in the
inline comments below.

Terminology: "bounding rect" is the outer canvas — it holds the cell grid
plus the color bar, the label strips, the optional note caption, and the
white margin + black border. The cells-only rectangle is grid_rect. (v1
used "bounding rect" for the cells-only rectangle; that name moved to the
outer canvas and the inner rectangle became grid_rect.)
"""
import colorsys
import math
import re

from lxml import etree

from . import SPEC_VERSION, __version__
from .entropy import parse, tokenize_entropy, fingerprint_middle_digest
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


NOTE_MAX_LEN = 8
_NOTE_RE = re.compile(r'^[A-Za-z0-9]+$')

# Anti-DoS input cap (this.i:1nputcap). entviz visualizes identifiers; the
# largest plausible one (a long cert chain or JWT) is a few KB, so 64 KiB is
# ~16× headroom while bounding render()'s O(n) work (full-core SHA-512,
# .strip()/.encode() copies, the txt->b64url fallback) to a few milliseconds
# even worst-case (a 64 KiB input of 4-byte codepoints expands ~4× through the
# txt->b64url fallback before the SHA-512; measured ~14 ms). Past the cap the
# input is not an identifier and render() rejects it outright.
MAX_INPUT_CHARS = 65536


def sanitize_note(note):
    """Validate an optional out-of-band user note (see `this.i:usrn0te1`).

    Returns the note unchanged (case preserved — it is a caption, not
    entropy) when it is ASCII-alphanumeric and at most NOTE_MAX_LEN chars.
    `None` or an empty string mean "no note" and return None. Any other
    value raises ValueError: a trust-adjacent field is rejected outright
    rather than silently truncated or mangled.
    """
    if note is None or note == "":
        return None
    if not isinstance(note, str):
        raise ValueError("note must be a string")
    if len(note) > NOTE_MAX_LEN:
        raise ValueError(
            f"note must be at most {NOTE_MAX_LEN} characters (got {len(note)})")
    if not _NOTE_RE.match(note):
        raise ValueError(
            "note must be ASCII alphanumeric [A-Za-z0-9] with no spaces or punctuation")
    return note


def _cell_nucleus_origin(ci, grid, grid_rect, cell_width, cell_height,
                         box_width, box_height):
    """Top-left corner (canvas coords) of cell index `ci`'s nucleus rect.

    The nucleus is inset from the cell box by one surround-box on each side.
    Module-level (not nested in render) so it is greppable and reusable — see
    MNT-F3.
    """
    col = ci % grid.cols
    row = ci // grid.cols
    return (
        grid_rect.left + col * cell_width + box_width,
        grid_rect.top + row * cell_height + box_height,
    )


def _blank_map_sub_center(cell_idx, nx, ny, grid, sub_w, sub_h):
    """Center of the blank-map's miniature sub-cell for grid cell `cell_idx`.

    The first blank cell renders a scale model of the whole grid inside its
    nucleus (origin nx, ny); this maps a real grid cell index to the center of
    its mirrored sub-cell so the min/max-ftok dots land in the right spot.
    """
    return (nx + (cell_idx % grid.cols + 0.5) * sub_w,
            ny + (cell_idx // grid.cols + 0.5) * sub_h)


# --- numeric serialization (docs/spec.md → Equivalence relation) -----------
# Coordinates are emitted as compact plain decimals: no exponential notation,
# at most 3 fractional digits, no trailing zeros, integers without a decimal
# point, -0 as 0. This mirrors entviz-rs / entviz-js `n()`. The rounding mode
# is unconstrained by the spec (this uses Python's round-half-to-even via
# `:.3f`); the checker's 0.05 px tolerance absorbs cross-impl rounding diffs.
# Normalizing once at serialization time keeps every call site free to build
# attributes with plain `str()`/f-strings.
def _compact(x: float) -> str:
    if not math.isfinite(x):
        return "0"  # coordinates are always finite; defensive
    s = f"{x:.3f}"
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


_NUM_RE = re.compile(r"-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?")
# Single-number coordinate/length/opacity attributes.
_COORD_ATTRS = frozenset({
    "x", "y", "width", "height", "cx", "cy", "r", "rx", "ry",
    "x1", "y1", "x2", "y2", "fx", "fy", "offset",
    "font-size",
    "stroke-width", "fill-opacity", "stroke-opacity", "stop-opacity",
    "data-ellipse-anchor-x", "data-ellipse-anchor-y", "data-ellipse-rx",
    "data-ellipse-ry", "data-ellipse-rotation-deg",
})
# Multi-number attributes (every numeric token is compacted; letters/commas,
# e.g. the `rotate(...)`/path commands, are left untouched).
_COMPOSITE_ATTRS = frozenset({"viewBox", "transform", "points", "d"})
_FONT_SIZE_RE = re.compile(r"(font-size:\s*)(-?\d+(?:\.\d+)?)(px)")


def _normalize_numbers(root) -> None:
    """Rewrite every numeric SVG attribute to the compact form in place."""
    for el in root.iter():
        for k, v in list(el.attrib.items()):
            if k in _COORD_ATTRS:
                el.set(k, _compact(float(v)))
            elif k in _COMPOSITE_ATTRS:
                el.set(k, _NUM_RE.sub(lambda m: _compact(float(m.group())), v))
            elif k == "style":
                el.set(k, _FONT_SIZE_RE.sub(
                    lambda m: m.group(1) + _compact(float(m.group(2))) + m.group(3), v))


def render(entropy_text: str, target_ar: float = 1.0, font_size_pt: int = 12,
           note: str = None) -> str:
    """
    Render entropy as an SVG entviz and return the SVG as a UTF-8 string.

    `note` is an optional out-of-band caption (max 8 ASCII-alphanumeric
    chars). It NEVER enters the entropy or the fingerprint and is outside
    the comparison surface; it renders as a quiet gray caption in the bottom
    strip. An invalid note raises ValueError. See `this.i:usrn0te1`.
    """
    note = sanitize_note(note)
    # Anti-DoS: reject oversized input before any O(n) work (parse, hashing,
    # the .strip()/.encode() copies). Measured on the raw input, pre-strip, so
    # whitespace padding can't smuggle a larger payload past the cap.
    # See this.i:1nputcap.
    if len(entropy_text) > MAX_INPUT_CHARS:
        raise ValueError(
            f"input must be at most {MAX_INPUT_CHARS} characters "
            f"(got {len(entropy_text)})")
    # Reject out-of-range render parameters at the render() boundary so the
    # library API matches the spec's Conformance error catalog (a Rust/TS port
    # validates here too, not only in its CLI). Ranges mirror the CLI: font size
    # [6, 30] pt; target aspect ratio [0.01, 100] (components 1..100). Only
    # already-invalid inputs are rejected; no valid render output changes.
    if not (6 <= font_size_pt <= 30):
        raise ValueError(
            f"font_size_pt must be in [6, 30] (got {font_size_pt})")
    if not (0.01 <= target_ar <= 100):
        raise ValueError(
            f"target_ar must be in [0.01, 100] (got {target_ar})")
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
        prefix_semantic = False
    else:
        core = parsed.core
        type_name = parsed.type
        alphabet = parsed.alphabet
        prefix = parsed.prefix
        suffix = parsed.suffix
        prefix_semantic = parsed.prefix_semantic
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

    # v6: when the input exceeds 512 bits, tokenize_entropy returns 20
    # tokens — 8 head (real entropy) + 4 middle (hex fingerprint readout) +
    # 8 tail (real entropy). The label gets a loud `fingerprint of` prefix
    # rendered in bold dark-red; assembly is done in _draw_label_strips where
    # the styling lives. We carry the byte count separately so the label
    # rendering doesn't have to peek at the raw input.
    truncated_bytes = len(raw_input.encode("utf-8")) if is_truncated else None

    # v6 large inputs do NOT use fixed separator blanks. The 20 tokens keep
    # logical order (head 0..7, middle 8..11, tail 12..19) but blank cells are
    # placed by the same median/quartile shift as short inputs (see the
    # assign_cell_indices call below), so a large input's blank layout varies
    # per input instead of being identical for every large input. The 4 middle
    # cells are identified by token index 8..11, not by a fixed cell position.
    token_count = len(tokens)

    # --- Compute the fingerprint and derive used ftoks ---
    # The fingerprint avalanche means single-bit input changes propagate
    # to every ftok-derived channel.
    #
    # A SEMANTIC prefix (an identity-bearing derivation/type code — every
    # CESR primitive; see the swap test in docs/spec.md and this.i:s3mpr3fx)
    # is folded into the fingerprint input so that two values differing ONLY
    # in their code (`B<body>` vs `D<body>` vs `E<body>`) avalanche apart
    # across every fingerprint-driven channel, including the 4 read-aloud
    # middle cells. The head/tail text cells still show `core` (the body)
    # alone — the code stays in the label, not the cell text. A SIGNAL prefix
    # (0x, swh:1:, …) is NOT folded: the fingerprint stays over the core, so
    # existing entvizes are unchanged. For a fixed-length self-framing CESR
    # code, prefix + core is exactly the original primitive string, so no
    # delimiter is needed (the split is unambiguous and injective).
    fingerprint_core = (prefix + core) if (prefix and prefix_semantic) else core
    used_ftoks = tokenize_fingerprint(
        compute_fingerprint(fingerprint_core))[:token_count]

    # --- Choose grid ---
    if is_truncated:
        # Large inputs have 20 tokens; pick a grid with a few spare cells so
        # the blank-shift below has slack to place fingerprint-derived blanks
        # (choose_grid(22) → 4x6 = 24 cells → 4 blanks, 3 of them shifted).
        grid = choose_grid(22, target_ar)
    else:
        grid = choose_grid(token_count, target_ar)

    # --- Median, quartiles, visual style — all from ftoks ---
    median_ftok = get_median_ftok(used_ftoks)
    quartile_ftoks = get_quartile_ftoks(used_ftoks)
    second_quartile_ftok = quartile_ftoks[1] if len(quartile_ftoks) > 1 else None
    style = select_visual_style(median_ftok, second_quartile_ftok)

    # --- Blank cell placement keyed off ftok ASCII sort ---
    # v6: large inputs use the SAME median/quartile blank-shift as short
    # inputs (no more fixed separator blanks at cells 8/13). Head/middle/tail
    # are a logical token ordering, not fixed cell positions, so blanks here
    # vary with the fingerprint and carry the same CRC-like signal they do for
    # short inputs. Token order is preserved, so reading order is unchanged;
    # the fingerprint-middle cells (token indices 8-11) stay identifiable by
    # their neutral bg + gold/white frame wherever they land.
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
    #   height = 1 + GM + nucleus_height + grid_height
    #              + [nucleus_height +] GM + 1
    # The top "type label" strip is always present (the entviz declares the
    # detected type / alphabet). The bottom "suffix label" strip appears only
    # when the parsed result has a suffix. v6: each label band ABUTS the grid
    # (no GM between band and grid) — the GM sits only on the border side — so
    # the label text is the same distance from the grid as nucleus text is
    # from a nucleus edge. (When there's no suffix, the GM below the grid is
    # just the bottom margin and is unchanged.)
    bounding_w = 1 + bar_width + 1 + gm + grid_w + gm + 1
    # The bottom strip appears when there is a suffix OR a user note.
    has_bottom_label = bool(suffix) or bool(note)
    bottom_region = (nucleus_height + gm) if has_bottom_label else gm
    bounding_h = 1 + gm + nucleus_height + grid_h + bottom_region + 1
    bounding_rect = Rect(Point(0, 0), Size(bounding_w, bounding_h))

    # grid_rect sits directly below the top label band (which abuts it).
    grid_rect = Rect(
        Point(1 + bar_width + 1 + gm, 1 + gm + nucleus_height),
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
    # font-family is an inherited SVG presentation property: set the monospace
    # chain ONCE on the root <svg> so every descendant <text> inherits it. Each
    # <text> then carries only a compact `font-size` attribute, not the full
    # `style="font-family:...; font-size:Npx;"` string (~21% of a dense SVG).
    # A conformant checker accepts the size from either an ancestor-inherited
    # font-family + a `font-size` attribute or the legacy per-text style.
    svg.set("font-family", MONOSPACE_FONT_FAMILY)
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
    digest_hex = compute_fingerprint(fingerprint_core).hex()
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
        # v6: the 4 fingerprint-middle cells (token indices 8-11 on a
        # >512-bit input) carry no entropy in their bg, so neutralize it to
        # the entviz background color — they read as "hollow" cells, distinct
        # from the entropy-colored head/tail nuclei. Their surround stays
        # ftok-driven (still avalanches). All other cells keep the entropy bg.
        if is_truncated and 8 <= token.index <= 11:
            nucleus_bg = style.bg_color
        else:
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
    # v10: fingerprint-edge cells — the top-left cell (grid position 0) and the
    # cells of the 1st & 2nd quartile ftoks take their surround edge colour from
    # the fingerprint (2 low-order ftok-quant bits → edge palette) instead of the
    # nearest-palette nucleus echo, so the surround colour avalanches to a casual
    # glance. Skipped where the target cell is blank or the quartile ftok is null.
    fp_edge_cells = set()
    if 0 in used_cell_indices:
        fp_edge_cells.add(0)
    for q_ftok in quartile_ftoks[:2]:
        if q_ftok is None:
            continue
        qci = cell_indices.get(q_ftok.index)
        if qci is not None:
            fp_edge_cells.add(qci)

    edges_g = etree.SubElement(grid_g, 'g')
    for token, ftok, cell, ci, nucleus_bg in token_cells:
        override = (style.edge_colors[ftok.quant & 0b11]
                    if ci in fp_edge_cells else None)
        renderer.render_edges(edges_g, ftok, cell, nucleus_bg=nucleus_bg,
                              edge_override=override)

    # Layer 2: ellipse overlay derived from raw digest bytes 60-63,
    # clipped to the grid rect. Wrapped in its own data-channel group
    # carrying the ellipse parameters as data-* so an overlay can find
    # the silhouette without re-deriving it from the digest.
    digest = compute_fingerprint(fingerprint_core)
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
    # Cells holding the fingerprint-middle tokens (token indices 8-11 on a
    # >512-bit input). Now that blanks shift, these no longer sit at fixed
    # cell indices, so tag them so overlays/tests can find them by position.
    fingerprint_cells = (
        {cell_indices[t] for t in range(8, 12)} if is_truncated else set()
    )
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
        if ci in fingerprint_cells:
            attrs["data-cell-fingerprint"] = "true"
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
    # The v9 fingerprint-middle cells always render 5 Crockford base32 chars
    # regardless of the input alphabet, so they use the 5-char (0.80×) rendered
    # size (per the generalized rule max(0.75, min(1.0, 4/token_chars)) = 0.80
    # for 5 chars) even when the input's own tokens are 4 chars. Bigger and
    # roomier than v6's 6-hex 0.75×. Without this the glyphs overflow the nucleus.
    fp_middle_text_px = round(font_size_pt * 0.80) * _DPI / 72

    # Layer 3: every cell's nucleus rect + text, drawn on top of edges
    # (and on top of the future ellipse overlay).
    # The fingerprint-middle cells (v6, token indices 8-11 on a >512-bit
    # input) get a 1-px inset border to frame them: gold on a white-bg
    # entviz, white otherwise — the same contrast rule as the blank-cell map
    # fill, and contrasting against their bg-colored (neutral) nucleus.
    fp_border = '#e7be00' if style.bg_color == '#ffffff' else '#ffffff'
    for token, ftok, cell, ci, nucleus_bg in token_cells:
        is_fp_middle = is_truncated and 8 <= token.index <= 11
        renderer.render_nucleus(
            cell_groups[ci], token, cell,
            text_size_px=(fp_middle_text_px if is_fp_middle else cell_text_px),
            bg_override=nucleus_bg,
            inner_border=(fp_border if is_fp_middle else None),
        )

    # Layer 3b: blank cells — every cell index in the grid that no token
    # was placed at. v6: each blank cell shows a black-outlined rounded
    # rectangle coincident with the nucleus rect. The FIRST blank cell (the
    # lowest cell index) additionally becomes a "map": a miniature scale
    # model of the grid, filled (white, or gold on a white-bg entviz), with
    # a red dot at the maxftok cell's grid position and a blue dot at the
    # minftok cell's. This replaces v5's white-disc + clock hands and its
    # mix-blend-mode dependence, closing adversarial finding F-A6 here.

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
    corner_radius = nucleus_height / 2   # = 10 at 12pt
    # The map fill must contrast with whatever background shows behind it:
    # white on any non-white entviz background, gold on a white one.
    map_fill = '#e7be00' if style.bg_color == '#ffffff' else '#ffffff'

    # v10: hybrid fingerprint blank fill. Every non-map blank is filled from the
    # fingerprint; the map blank is filled from the fingerprint ONLY when it is
    # the sole blank (the common small-input case — LEI, small hex — whose lone
    # blank IS the map blank, and where the casual-avalanche colour is needed),
    # otherwise it keeps the white/gold anchor so it stays findable while its
    # siblings carry the colour. Filled blanks are enumerated in cell-index
    # order; the j-th takes edge_palette[digest[32 + j] & 0b11].
    sole_blank = len(blank_indices) == 1
    blank_fill_color = {}
    for j, ci in enumerate(
            bi for bi in blank_indices if bi != map_cell_idx or sole_blank):
        blank_fill_color[ci] = style.edge_colors[digest[32 + j] & 0b11]

    for ci in blank_indices:
        cg = cell_groups[ci]
        nx, ny = _cell_nucleus_origin(
            ci, grid, grid_rect, cell_width, cell_height, box_width, box_height)
        is_map = ci == map_cell_idx
        blank_fill = map_fill if (is_map and not sole_blank) else blank_fill_color[ci]
        etree.SubElement(
            cg, 'rect',
            x=str(nx), y=str(ny),
            width=str(nucleus_width), height=str(nucleus_height),
            rx=str(corner_radius), ry=str(corner_radius),
            fill=blank_fill, stroke='#000000',
            **{'stroke-width': '1'},
        )
        if not is_map:
            continue
        # Map: subdivide the nucleus rect into cols×rows logical sub-cells
        # mirroring the grid, then mark the maxftok cell with a red PLUS and
        # the minftok cell with a blue DOT at their matching (row, col)
        # positions. The SHAPE (plus vs dot) — not the colour — carries the
        # max/min semantic, so it survives total colour blindness, under which
        # the red and blue collapse to near-equal grays (PSY-F1). Each marker's
        # data-blank-map-min / data-blank-map-max attribute carries the literal
        # "row,col" of its cell, so a conformance checker recovers the position
        # directly from the named attribute instead of reverse-engineering it
        # from pixel geometry (SPEC-F2).
        cg.set("data-cell-blank-map", "true")
        sub_w = nucleus_width / grid.cols
        sub_h = nucleus_height / grid.rows
        # Fixed marker radius (independent of grid dims) so markers are a
        # consistent size across entvizes; centered in the sub-cell, may
        # overflow it on dense grids (acceptable). The `+ font_size_px / 16`
        # term adds exactly 1 px at the 12 pt / 96 dpi nominal size.
        dot_r = nucleus_height / 8 + font_size_px / 16

        max_cx, max_cy = _blank_map_sub_center(
            max_ftok_cell_idx, nx, ny, grid, sub_w, sub_h)
        min_cx, min_cy = _blank_map_sub_center(
            min_ftok_cell_idx, nx, ny, grid, sub_w, sub_h)
        max_row, max_col = divmod(max_ftok_cell_idx, grid.cols)
        min_row, min_col = divmod(min_ftok_cell_idx, grid.cols)
        # Plus geometry: arms a touch longer than the dot radius, with a thinner
        # stroke, so the cross reads as a distinct shape rather than a blob.
        plus_arm = dot_r * 1.2
        plus_w = max(1.0, dot_r * 0.55)
        # v10: when the map blank is fingerprint-filled (sole-blank case) the
        # fixed red/blue would clash with the fill, so both markers take the
        # luminance-contrast colour against that fill (the cell-text foreground
        # rule). Max/min identity rides on SHAPE (plus vs dot), not hue, so this
        # costs only the redundant colour cue. Otherwise keep the v9 red/blue.
        if sole_blank:
            f = blank_fill_color[map_cell_idx]
            _, marker_color = get_nucleus_colors(
                int(f[1:3], 16) | (int(f[3:5], 16) << 8) | (int(f[5:7], 16) << 16))
            min_color = max_color = marker_color
        else:
            min_color, max_color = '#1d4ed8', '#d62828'
        # minftok = blue dot (drawn first); maxftok = red plus (drawn on top, so
        # it stays visible in the degenerate case where both land on one cell).
        etree.SubElement(
            cg, 'circle', cx=str(min_cx), cy=str(min_cy), r=str(dot_r),
            fill=min_color, **{'data-blank-map-min': f'{min_row},{min_col}'},
        )
        etree.SubElement(
            cg, 'path',
            d=f'M {max_cx - plus_arm},{max_cy} H {max_cx + plus_arm} '
              f'M {max_cx},{max_cy - plus_arm} V {max_cy + plus_arm}',
            fill='none', stroke=max_color,
            **{'stroke-width': str(plus_w), 'stroke-linecap': 'butt',
               'data-blank-map-max': f'{max_row},{max_col}'},
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
        box_height=box_height, cell_text_px=cell_text_px,
        band_order=_two_bit_first_appearance(digest, style.edge_colors),
        second_digest=fingerprint_middle_digest(core),
    )
    # (color bar width is bar_width = 2·box_height; v6 letters render at the
    # cell-text size, bottom-anchored within each band.)

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
        note=note,
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

    _normalize_numbers(svg)
    return etree.tostring(svg, encoding='unicode', xml_declaration=False)


def _draw_label_strips(svg, grid_rect, gm, nucleus_height,
                       type_name, prefix, suffix, text_size_px,
                       truncated_bytes=None, note=None):
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
    loud `fingerprint of ` marker rendered in bold dark-red (#a00000), with the
    rest of the label following in the standard #666 non-bold style. The
    marker and tail are emitted as two adjacent <text> elements inside
    the label-top group so the styling cleanly differs while the line
    still reads left-to-right. The byte count is omitted from the marker
    because it is already present in the type-label parenthetical (e.g.
    `hex(200)`, `b64(119)`).
    """
    # font-family is inherited from the root <svg>; each label <text> carries
    # only a compact font-size presentation attribute (compacted by
    # _normalize_numbers via _COORD_ATTRS).
    font_size_attr = {"font-size": str(text_size_px)}
    # Top strip — always.
    top_g = etree.SubElement(svg, 'g', **{"data-channel": "label-top"})
    if type_name:
        rest_text = f"{type_name}:"
        if prefix:
            rest_text += f" {prefix}..."
    else:
        # A self-describing prefix (e.g. swh:1:rev:, gitoid:blob:sha256:) is
        # the identifier on its own — show it alone, with no echoing type
        # segment in front of it. See `this.i:lbldedup`.
        rest_text = f"{prefix}..." if prefix else ""
    # v6: the top label band abuts the grid, so its text centers a
    # nucleus_height/2 above the grid — the same gap nucleus text has from the
    # nucleus's bottom edge. (The GM sits above the band, on the border side.)
    top_cy = grid_rect.top - nucleus_height / 2
    if truncated_bytes is not None:
        # Loud marker in bold dark red, then the standard label in #666 —
        # rendered as a bold-red <tspan> plus its tail inside ONE <text>, so
        # they flow with exactly one space between them. (v5/v6.0 used two
        # absolutely-positioned <text> elements with a guessed monospace
        # advance, which overshot and left a ~2-space gap.)
        label_el = etree.SubElement(
            top_g, 'text',
            x=str(grid_rect.left), y=str(top_cy),
            fill='#666666',
            **{**font_size_attr, "dominant-baseline": "central"},
        )
        marker_tspan = etree.SubElement(
            label_el, 'tspan',
            fill='#a00000', **{"font-weight": "bold"},
        )
        marker_tspan.text = "fingerprint of "
        marker_tspan.tail = rest_text   # flows right after the marker, in #666
    else:
        el = etree.SubElement(
            top_g, 'text',
            x=str(grid_rect.left), y=str(top_cy),
            fill='#666666',
            **{**font_size_attr, "dominant-baseline": "central"},
        )
        el.text = rest_text
    # Bottom strip — when a suffix exists and/or a user note is supplied.
    # Layout (right-aligned to grid_rect.right): "...<suffix> (<note>)". The
    # suffix (algorithm-derived) is #666; the note (out-of-band, unverified)
    # is quiet gray #808080 and carries data-user-note so it is structurally
    # distinct from derived content. See `this.i:usrn0te1`.
    if suffix or note:
        bottom_g = etree.SubElement(svg, 'g', **{"data-channel": "label-bottom"})
        # Bottom band abuts the grid; text centers nucleus_height/2 below it.
        bottom_cy = grid_rect.bottom + nucleus_height / 2
        el = etree.SubElement(
            bottom_g, 'text',
            x=str(grid_rect.right), y=str(bottom_cy),
            fill='#666666',
            **{**font_size_attr, "text-anchor": "end", "dominant-baseline": "central"},
        )
        if suffix and note:
            suffix_tspan = etree.SubElement(el, 'tspan')   # inherits #666
            suffix_tspan.text = f"...{suffix} "
            note_tspan = etree.SubElement(
                el, 'tspan', fill='#808080', **{"data-user-note": note})
            note_tspan.text = f"({note})"
        elif suffix:
            el.text = f"...{suffix}"
        else:  # note only
            note_tspan = etree.SubElement(
                el, 'tspan', fill='#808080', **{"data-user-note": note})
            note_tspan.text = f"({note})"


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
# (fill_color, fill_opacity, edge_opacity). The fill is dialed back so it
# obscures the underlying cells less; a 2px edge stroke at the higher
# edge_opacity keeps the silhouette crisp.
_V3_OVERLAY_BY_BG = {
    '#ffffff': ('#000000', 0.20, 0.30),  # white  → darken; fill 20 / edge 30
    '#e7be00': ('#000000', 0.20, 0.30),  # gold   → darken; fill 20 / edge 30
    '#ff3f2f': ('#000000', 0.25, 0.35),  # red    → darken; fill 25 / edge 35
    '#2f3fbf': ('#ffffff', 0.35, 0.45),  # blue   → lighten; fill 35 / edge 45
}


def _ellipse_overlay_for_bg(bg_color: str):
    """Return (fill_color, fill_opacity, edge_opacity) for the ellipse overlay
    on bg_color. The fill is the subtler interior wash; the edge_opacity is
    used for the 2px stroke that emphasizes the silhouette."""
    if bg_color in _V3_OVERLAY_BY_BG:
        return _V3_OVERLAY_BY_BG[bg_color]
    # Fallback for any unexpected bg (e.g., test inputs): use the v3-5
    # luminosity rule with the default fill 0.20 / edge 0.30.
    r = int(bg_color[1:3], 16) / 255.0
    g = int(bg_color[3:5], 16) / 255.0
    b = int(bg_color[5:7], 16) / 255.0
    _, l, _ = colorsys.rgb_to_hls(r, g, b)
    return ('#000000' if l > 0.5 else '#ffffff', 0.20, 0.30)


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
    fill, fill_opacity, edge_opacity = _ellipse_overlay_for_bg(bg_color)
    stroke_w = cell_h / 20.0   # = 2px at the 12pt nominal; scales with entviz
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
        stroke=fill,
        **{
            "fill-opacity": f"{fill_opacity}",
            "stroke-opacity": f"{edge_opacity}",
            "stroke-width": f"{stroke_w}",
        },
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


def _two_bit_first_appearance(digest: bytes, edge_colors) -> list:
    """
    v9: colors in each 2-bit pattern's FIRST-APPEARANCE order across the 256
    disjoint slices of the digest (tie-break by pattern value). This decouples
    the color-bar band *order* from the count^4 band *heights* — through v8 the
    order was descending count, carrying no information beyond the heights. See
    `this.i:b4rm4rks` / `d1scr3t3`.
    """
    first = {}
    idx = 0
    for byte in digest:
        for shift in (0, 2, 4, 6):
            pat = (byte >> shift) & 0x03
            if pat not in first:
                first[pat] = idx
            idx += 1
    order = sorted(range(4), key=lambda p: (first.get(p, 256 + p), p))
    return [edge_colors[p] for p in order]


# v5: palette → uppercase band letter mapping. Used by the color-bar
# letter rendering; an overlay component (Idea 2) can also consume the
# data-color-bar-band="<letter>" attribute without re-deriving this map.
_BAND_LETTER_BY_COLOR = {
    "#ffffff": "W",
    "#e7be00": "G",
    "#ff3f2f": "R",
    "#2f3fbf": "B",
    "#000000": "K",
}


def _draw_color_bar(svg, bar_rect, gm, color_usage, edge_colors,
                    box_height=None, cell_text_px=None,
                    band_order=None, second_digest=None):
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
    if band_order is not None:
        # v9: order bands by each pattern's first appearance in the digest scan
        # (decoupled from height), tie-break by edge-palette index.
        order_pos = {c: i for i, c in enumerate(band_order)}
        used.sort(key=lambda x: (order_pos.get(x[0], len(band_order)),
                                 color_order[x[0]]))
    else:
        # legacy (pre-v9): descending count, edge_colors index as tiebreak.
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
            # v6: the letter renders at exactly the cell-text size (uniformity
            # across the entviz), never scaled to the band. It is
            # bottom-anchored: the baseline sits a descender's height above the
            # band's bottom edge so the glyph bottom never bleeds below the
            # band; on a short band the top may bleed above. Bands are emitted
            # top-to-bottom, so a bleeding lower letter paints over the band
            # above it (deterministic layering).
            font_size = cell_text_px if cell_text_px is not None else bar_rect.size.width
            baseline_y = (y + h) - 0.22 * font_size
            text_el = etree.SubElement(
                band_g, 'text',
                x=str(bar_cx), y=str(baseline_y),
                fill=fg,
                **{
                    "font-size": str(font_size),
                    "text-anchor": "middle",
                    "data-color-bar-letter": "true",
                },
            )
            text_el.text = letter.lower()
        y += h

    # v9: two fixed-slot discrete CIRCLE markers ride the bar's gutters
    # (b4rm4rks). Identity is carried by SIDE — left = second[12], right =
    # second[13] — not by shape: a square-vs-triangle distinction proved
    # unreliable, because on a dark band (blue/red/black) the black halo
    # vanishes and only a too-small inner glyph reads. Circles need no shape
    # discrimination; you check each circle's slot (height) and gutter (side).
    # K = clamp(floor(bar_height/12px), 4, 16) equal slots, independent of the
    # bands. Drawn OPAQUE — white fill + ~0.75px black halo, NOT a blend mode —
    # so they render identically across rasterizers (F-A6) and stay visible
    # where a marker straddles two bands (white core on the dark side of the
    # cut, black halo on the light side). `second` is the domain-separated
    # digest, present on every input. The two never overlap (distinct gutters).
    if second_digest is not None:
        K = max(4, min(16, int(bar_rect.size.height // 12)))
        bar_g.set("data-bar-slots", str(K))
        slot_h = bar_rect.size.height / K
        radius = bar_rect.size.width * 0.17
        inset = bar_rect.size.width * 0.06
        for side, slot in (("left", second_digest[12] % K),
                           ("right", second_digest[13] % K)):
            bar_g.set(f"data-bar-marker-{side}", str(slot))
            cy = bar_rect.top + (slot + 0.5) * slot_h
            cx = (bar_rect.left + inset + radius) if side == "left" else \
                 (bar_rect.left + bar_rect.size.width - inset - radius)
            etree.SubElement(
                bar_g, 'circle',
                cx=str(cx), cy=str(cy), r=str(radius),
                fill="#ffffff", stroke="#000000",
                **{"stroke-width": "0.75", "data-bar-marker": side})
