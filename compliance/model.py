"""Tier A: the entviz render model.

``extract_model(svg)`` recovers the abstract render model (docs/spec.md →
Conformance → "The render model") from a rendered entviz SVG, using only the
**normative** surface: the required ``data-*`` attributes and the normative
geometry (which is identical for every conformant implementation). It does not
depend on any reference-implementation internals, so it can be pointed at the
SVG of any implementation under test.

The model is a plain JSON-serializable ``dict``; two models are compared with
:func:`models_equal` / :func:`diff_models`. Continuous ellipse parameters are
rounded to :data:`ELLIPSE_NDIGITS` so that float-formatting differences between
implementations are not spurious failures (per the equivalence relation).
"""
from __future__ import annotations

from typing import Optional

from lxml import etree

SVG_NS = "http://www.w3.org/2000/svg"

# Continuous ellipse params (rx, ry, rotation, anchor) are compared at this
# precision. The equivalence relation ignores numeric formatting that denotes
# the same value; rounding here makes that concrete and cross-implementation.
ELLIPSE_NDIGITS = 3

# Coordinate/length/angle fields are compared BY VALUE within this absolute
# tolerance (docs/spec.md → Equivalence relation → numeric formatting), never by
# exact equality: two conformant implementations may round an unspecified-
# precision coordinate differently (e.g. 12.345 vs 12.346), and that ≤0.001 px
# disagreement must not be a spurious failure. The tolerance is deliberately
# kept SMALL ENOUGH that any Tier-A-equivalent coordinate difference is also
# within the Tier-B raster tolerance (channel_tol — see raster.py): empirically
# a shift ≤0.02 px stays under the per-channel/fraction allowance while ≥0.03 px
# fails Tier B, so 0.01 px keeps the two tiers consistent (Tier-A ⊆ Tier-B) with
# ~10× headroom over the largest legitimate rounding difference (0.001 px).
_NUM_TOL = 0.01

# Geometry constants from docs/spec.md (all multiples of font_size_px = fs).
_BOX_W = 0.375      # box_width  = 0.375 * fs
_BOX_H = 0.625      # box_height = 0.625 * fs
_NUC_W = 3.0        # nucleus_width  = 3 * fs
# (nucleus_height = 1.25*fs = 2*box_height; not needed directly below.)

_COORD_NDIGITS = 3  # rounding for surround-box position lookup


def _tag(el) -> str:
    """Local tag name without namespace."""
    t = el.tag
    if isinstance(t, str) and "}" in t:
        return t.split("}", 1)[1]
    return t


def _findall(root, tag: str):
    """All descendants with the given local tag, namespace-agnostic."""
    out = []
    for el in root.iter():
        if _tag(el) == tag:
            out.append(el)
    return out


def _num(s: str) -> float:
    return float(s)


def _box_origins(cell_x: float, cell_y: float, fs: float):
    """The 24 surround-box origin points for a cell, per the spec's surround
    layout. Index order is clockwise from the top-left of the top row.
    Returns a list of (x, y) tuples indexed 0..23."""
    bw = _BOX_W * fs
    bh = _BOX_H * fs
    origins = [None] * 24
    # Top row 0..9
    for i in range(10):
        origins[i] = (cell_x + i * bw, cell_y)
    # Right column 10, 11 (x = nucleus.right = cell_x + 9*bw)
    origins[10] = (cell_x + 9 * bw, cell_y + bh)
    origins[11] = (cell_x + 9 * bw, cell_y + 2 * bh)
    # Bottom row 12..21 (y = nucleus.bottom = cell_y + 3*bh), stepping left
    for i in range(12, 22):
        origins[i] = (cell_x + (21 - i) * bw, cell_y + 3 * bh)
    # Left column 22, 23 (x = cell_x)
    origins[22] = (cell_x, cell_y + 2 * bh)
    origins[23] = (cell_x, cell_y + bh)
    return origins


def _round(v: float, nd: int = _COORD_NDIGITS) -> float:
    return round(v, nd)


def extract_model(svg: str | bytes) -> dict:
    """Recover the render model from an entviz SVG string/bytes."""
    if isinstance(svg, str):
        svg = svg.encode("utf-8")
    root = etree.fromstring(svg)

    model: dict = {
        "spec_version": root.get("data-entviz-version"),
        "input_bytes": _opt_int(root.get("data-input-bytes")),
        "truncated": root.get("data-truncated") == "true",
        "cols": int(root.get("data-cols")),
        "rows": int(root.get("data-rows")),
    }
    cols = model["cols"]
    rows = model["rows"]

    # --- font size from any nucleus rect (nucleus_width = 3*fs) ---
    fs = _derive_fs(root)
    bw = _BOX_W * fs
    bh = _BOX_H * fs

    # --- entviz background color: first <rect> of the grid channel group ---
    model["bg_color"] = _grid_bg_color(root)

    # --- surround boxes: all rects sized box_width x box_height ---
    surround = {}
    for r in _findall(root, "rect"):
        w = r.get("width")
        h = r.get("height")
        if w is None or h is None:
            continue
        if _close(_num(w), bw) and _close(_num(h), bh):
            key = (_round(_num(r.get("x"))), _round(_num(r.get("y"))))
            surround[key] = r.get("fill")

    # --- cells ---
    cells: dict = {}
    map_rect_by_cell = {}
    for g in _findall(root, "g"):
        if g.get("data-channel") != "cell":
            continue
        ci = int(g.get("data-cell-index"))
        cell = {
            "row": int(g.get("data-cell-row")),
            "col": int(g.get("data-cell-col")),
            "blank": g.get("data-cell-blank") == "true",
            "fingerprint": g.get("data-cell-fingerprint") == "true",
            "quartile": _opt_int(g.get("data-cell-quartile")),
            "blank_map": g.get("data-cell-blank-map") == "true",
        }
        rects = [c for c in g if _tag(c) == "rect"]
        texts = [c for c in g if _tag(c) == "text"]
        if cell["blank"]:
            # The blank's outlined (rounded) rect locates the map sub-grid.
            if rects:
                mr = rects[0]
                map_rect_by_cell[ci] = mr
            if cell["blank_map"]:
                cell["map_min"] = _dot_rowcol(g, "data-blank-map-min")
                cell["map_max"] = _dot_rowcol(g, "data-blank-map-max")
        else:
            # Filled cell: nucleus rect (first rect) + text.
            nuc = rects[0]
            nx, ny = _num(nuc.get("x")), _num(nuc.get("y"))
            cell["nucleus_bg"] = nuc.get("fill")
            if texts:
                cell["text"] = texts[0].text or ""
                cell["fg"] = texts[0].get("fill")
                cell["text_size_px"] = _text_size_px(texts[0])
            # Surround bits + edge color. v10 SVG profile: the cell group
            # DECLARES them (data-surround-bits is the hex bit pattern,
            # data-edge-color the edge color), so recovery is a direct read.
            # Fall back to recovering them from the box geometry for SVGs that
            # predate the declaration.
            bits_attr = g.get("data-surround-bits")
            if bits_attr is not None:
                cell["surround_bits"] = int(bits_attr, 16)
                cell["edge_color"] = g.get("data-edge-color")
            else:
                cell_x = nx - bw
                cell_y = ny - bh
                bits = 0
                edge = None
                for i, (ox, oy) in enumerate(_box_origins(cell_x, cell_y, fs)):
                    fill = surround.get((_round(ox), _round(oy)))
                    if fill is not None:
                        bits |= (1 << i)
                        edge = fill
                cell["surround_bits"] = bits
                cell["edge_color"] = edge
        cells[str(ci)] = cell
    model["cells"] = cells

    # --- ellipse ---
    model["ellipse"] = _ellipse(root)

    # --- color bar ---
    model["color_bar"] = _color_bar(root)
    model["color_bar_markers"] = _color_bar_markers(root)

    # --- labels ---
    model["labels"] = _labels(root)
    model["user_note"] = _user_note(root)

    return model


def _opt_int(s) -> Optional[int]:
    return int(s) if s is not None else None


def _close(a: float, b: float, tol: float = 0.01) -> bool:
    return abs(a - b) <= tol


def _first_rect(el):
    """The first <rect> DESCENDANT of `el` (excluding `el` itself), in document
    order. Searching descendants — not just direct children — keeps recovery
    robust to the `<g>` regrouping the equivalence relation permits (a checker
    must tolerate extra nesting that changes neither paint order nor geometry)."""
    for c in el.iter():
        if c is not el and _tag(c) == "rect":
            return c
    return None


def _derive_fs(root) -> float:
    """font_size_px from the first nucleus rect (nucleus_width = 3*fs)."""
    for g in _findall(root, "g"):
        if g.get("data-channel") != "cell" or g.get("data-cell-blank") == "true":
            continue
        rect = _first_rect(g)
        if rect is not None:
            return _num(rect.get("width")) / _NUC_W
    # Fallback: derive from grid bg width = cols * 3.75 * fs.
    cols = int(root.get("data-cols"))
    bg = _grid_bg_rect(root)
    if bg is not None:
        return _num(bg.get("width")) / (cols * 3.75)
    raise ValueError("cannot derive font size from SVG")


def _grid_bg_rect(root):
    for g in _findall(root, "g"):
        if g.get("data-channel") == "grid":
            return _first_rect(g)
    return None


def _grid_bg_color(root) -> Optional[str]:
    r = _grid_bg_rect(root)
    return r.get("fill") if r is not None else None


def _ellipse(root):
    for g in _findall(root, "g"):
        if g.get("data-channel") == "ellipse":
            ax = g.get("data-ellipse-anchor-x")
            if ax is None:
                continue
            return {
                "anchor": [round(_num(ax), ELLIPSE_NDIGITS),
                           round(_num(g.get("data-ellipse-anchor-y")), ELLIPSE_NDIGITS)],
                "rx": round(_num(g.get("data-ellipse-rx")), ELLIPSE_NDIGITS),
                "ry": round(_num(g.get("data-ellipse-ry")), ELLIPSE_NDIGITS),
                "rotation": round(_num(g.get("data-ellipse-rotation-deg")), ELLIPSE_NDIGITS),
            }
    return None


def _color_bar(root):
    bands = []
    for g in _findall(root, "g"):
        rank = g.get("data-color-bar-rank")
        if rank is None:
            continue
        letter = None
        for t in _findall(g, "text"):
            if t.get("data-color-bar-letter") == "true":
                letter = t.text
                break
        bands.append({
            "rank": int(rank),
            "band": g.get("data-color-bar-band"),
            "letter": letter,
        })
    bands.sort(key=lambda b: b["rank"])
    return bands


def _color_bar_markers(root):
    """v9: the two fixed-slot color-bar markers, recovered from the color-bar
    group's attributes (`data-bar-slots`, `data-bar-marker-square`,
    `data-bar-marker-triangle`). Returns None on a malformed/absent bar."""
    for g in _findall(root, "g"):
        if g.get("data-channel") == "color-bar":
            slots = _opt_int(g.get("data-bar-slots"))
            if slots is None:
                return None
            return {
                "slots": slots,
                "left": _opt_int(g.get("data-bar-marker-left")),
                "right": _opt_int(g.get("data-bar-marker-right")),
            }
    return None


def _labels(root):
    top = None
    bottom = None
    marker = False
    for g in _findall(root, "g"):
        ch = g.get("data-channel")
        if ch == "label-top":
            top = _text_content(g)
            # truncation marker = a bold dark-red tspan
            for t in _findall(g, "tspan"):
                fill = (t.get("fill") or "").lower()
                if fill in ("#a00000",) or t.get("font-weight") == "bold":
                    marker = True
        elif ch == "label-bottom":
            bottom = _text_content(g)
    return {"top": top, "bottom": bottom, "truncation_marker": marker}


def _user_note(root):
    for el in root.iter():
        n = el.get("data-user-note")
        if n is not None:
            return n
    return None


def _text_content(g) -> Optional[str]:
    """Concatenate text + tspans of the (first) <text> in a group."""
    for t in _findall(g, "text"):
        parts = []
        if t.text:
            parts.append(t.text)
        for child in t:
            if child.text:
                parts.append(child.text)
            if child.tail:
                parts.append(child.tail)
        return "".join(parts)
    return None


def _text_size_px(text_el) -> Optional[float]:
    # Prefer a font-size presentation attribute (compact form); fall back to
    # font-size inside the style attribute (legacy form). A checker MUST accept
    # either per the SVG profile.
    attr = text_el.get("font-size")
    if attr is not None:
        v = attr.strip()
        if v.endswith("px"):
            v = v[:-2]
        try:
            return round(float(v), 3)
        except ValueError:
            return None
    style = text_el.get("style") or ""
    for part in style.split(";"):
        part = part.strip()
        if part.startswith("font-size:"):
            v = part.split(":", 1)[1].strip()
            if v.endswith("px"):
                v = v[:-2]
            try:
                return round(float(v), 3)
            except ValueError:
                return None
    return None


def _dot_rowcol(g, attr: str):
    """Recover (row, col) of a blank-map marker from its data-blank-map-*
    attribute, which carries the literal "row,col" of the cell (v8, SPEC-F2).

    Reading the named attribute directly — rather than reverse-engineering the
    position from the marker's pixel geometry — is what the SVG profile (§173)
    requires, and it works regardless of the marker's element type (the minftok
    dot is a <circle>, the maxftok plus is a <path>)."""
    for c in g:
        v = c.get(attr)
        if v is None:
            continue
        try:
            row, col = (int(x) for x in v.split(","))
        except (ValueError, TypeError):
            return None
        return [row, col]
    return None


# --------------------------------------------------------------------------
# Comparison
# --------------------------------------------------------------------------

def diff_models(golden: dict, actual: dict, path: str = "") -> list[str]:
    """Return a list of human-readable difference descriptions (empty == equal)."""
    diffs: list[str] = []
    _diff(golden, actual, path or "<model>", diffs)
    return diffs


def _diff(a, b, path, diffs):
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a:
                diffs.append(f"{path}.{k}: unexpected (only in actual) = {b[k]!r}")
            elif k not in b:
                diffs.append(f"{path}.{k}: missing (only in golden) = {a[k]!r}")
            else:
                _diff(a[k], b[k], f"{path}.{k}", diffs)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            diffs.append(f"{path}: list length {len(a)} != {len(b)}")
        else:
            for i, (x, y) in enumerate(zip(a, b)):
                _diff(x, y, f"{path}[{i}]", diffs)
    elif isinstance(a, bool) or isinstance(b, bool):
        # bool is an int subclass; compare strictly (don't run it through the
        # numeric tolerance, where True/1 etc. would blur).
        if a != b:
            diffs.append(f"{path}: golden={a!r} actual={b!r}")
    elif isinstance(a, (int, float)) and isinstance(b, (int, float)):
        # Coordinates/lengths/angles: by-value comparison within the spec's
        # numeric tolerance, not exact (real differences are >= 1 px / structural
        # and remain caught; only sub-0.05 rounding noise is absorbed).
        if abs(a - b) > _NUM_TOL:
            diffs.append(f"{path}: golden={a!r} actual={b!r} (|delta| > {_NUM_TOL})")
    else:
        if a != b:
            diffs.append(f"{path}: golden={a!r} actual={b!r}")


def models_equal(golden: dict, actual: dict) -> bool:
    return not diff_models(golden, actual)


# --------------------------------------------------------------------------
# Closed-profile validation: an entviz contains ONLY the enumerated channels
# and nothing else. There is no slot for a brand/logo, a copyright mark, or any
# extra text or graphic overlaid on the diagram. (Purely non-rendering advisory
# metadata — <title>, <desc>, <metadata>, XML comments, extra data-* attributes
# — is allowed; it adds no ink.)
# --------------------------------------------------------------------------

# Every element type an entviz may contain. Anything else (an <image>/<use>
# logo, an <a> wrapper, an injected <script>/<style>, <foreignObject>, …) is
# foreign and rejected outright.
_PROFILE_TAGS = frozenset({
    "svg", "defs", "clipPath", "g", "rect", "path", "text", "tspan",
    "polygon", "circle", "ellipse", "line", "desc", "title", "metadata",
})
_ADVISORY_TAGS = frozenset({"desc", "title", "metadata"})
# A rendering element may appear only in the channel(s) it belongs to.
_RENDER_OK = frozenset({
    ("rect", "grid"), ("rect", "cell"), ("rect", "color-bar"),
    ("path", "grid"), ("path", "cell"),
    ("circle", "cell"), ("circle", "color-bar"),
    ("polygon", "cell"),
    ("ellipse", "ellipse"),
    ("text", "cell"), ("text", "color-bar"), ("text", "label-top"), ("text", "label-bottom"),
    ("tspan", "cell"), ("tspan", "color-bar"), ("tspan", "label-top"), ("tspan", "label-bottom"),
})
# Allowed direct-child tags inside a single cell group (filled: nucleus rect
# [+ optional inner-border rect], text, optional quartile polygon; blank: pill
# rect, and for the map blank a min <circle> + a max <path>).
_CELL_CHILD_TAGS = frozenset({"rect", "text", "polygon", "circle", "path"})
# Allowed direct-child tags inside a single color-bar BAND group.
_BAND_CHILD_TAGS = frozenset({"rect", "text"})


def _resolve_channel(el):
    p = el
    while p is not None:
        c = p.get("data-channel") if hasattr(p, "get") else None
        if c:
            return c
        p = p.getparent()
    return None


def validate_closed_profile(svg) -> list[str]:
    """Return a list of profile violations (empty == a clean, closed entviz).

    Enforces that every element belongs to a known channel: foreign element
    types are rejected, rendering elements may appear only in their channel, the
    singletons (background, clip, ellipse overlay) are not duplicated, and a cell
    or color-bar group may not carry extra children. This is what makes it
    impossible to overlay a logo, a copyright, or stray text on a conformant
    entviz — extra ink has nowhere legal to live.
    """
    if isinstance(svg, (str, bytes)):
        root = etree.fromstring(svg.encode() if isinstance(svg, str) else svg)
    else:
        root = svg
    viol: list[str] = []
    n_rootbg = n_defs = n_clip = n_ellipse = 0

    for el in root.iter():
        if not isinstance(el.tag, str):
            continue  # XML comment / processing instruction — non-rendering, allowed
        t = _tag(el)
        if t == "svg":
            continue
        if t not in _PROFILE_TAGS:
            viol.append(f"foreign <{t}> element: not part of the entviz profile")
            continue
        if t in _ADVISORY_TAGS or t == "g":
            continue  # advisory metadata / organizational group
        parent = el.getparent()
        ptag = _tag(parent) if parent is not None else None
        ch = _resolve_channel(el)
        if t == "defs":
            n_defs += 1
            continue
        if t == "clipPath":
            n_clip += 1
            continue
        if t == "rect" and ptag == "clipPath":
            continue  # clip geometry
        if t == "rect" and ptag == "svg" and ch is None:
            n_rootbg += 1
            continue
        if t == "line" and ptag == "svg" and ch is None:
            continue  # canvas border
        if t == "ellipse" and ch == "ellipse":
            n_ellipse += 1
            continue
        if (t, ch) in _RENDER_OK:
            continue
        viol.append(f"unexpected <{t}> in channel {ch!r}: overlaid or extra content")

    if n_rootbg != 1:
        viol.append(f"expected exactly one background rect, found {n_rootbg}")
    if n_defs > 1:
        viol.append(f"expected at most one <defs>, found {n_defs}")
    if n_clip > 1:
        viol.append(f"expected at most one <clipPath>, found {n_clip}")
    if n_ellipse > 1:
        viol.append(f"expected at most one ellipse overlay, found {n_ellipse}")

    # Per-group child checks: extra ink can't hide inside a legitimate group.
    for g in _findall(root, "g"):
        ch = g.get("data-channel")
        if ch == "cell":
            kids = [_tag(c) for c in g if isinstance(c.tag, str)]
            bad = [k for k in kids if k not in _CELL_CHILD_TAGS]
            if bad:
                viol.append(f"cell {g.get('data-cell-index')} carries unexpected child(ren): {bad}")
            if kids.count("text") > 1 or kids.count("polygon") > 1 or kids.count("rect") > 2:
                viol.append(f"cell {g.get('data-cell-index')} has too many children: {kids}")
        elif g.get("data-color-bar-rank") is not None:
            kids = [_tag(c) for c in g if isinstance(c.tag, str)]
            bad = [k for k in kids if k not in _BAND_CHILD_TAGS]
            if bad:
                viol.append(f"color-bar band carries unexpected child(ren): {bad}")
    return viol
