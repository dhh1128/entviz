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
                cell["map_min"] = _dot_rowcol(g, "data-blank-map-min",
                                              map_rect_by_cell.get(ci),
                                              cols, rows)
                cell["map_max"] = _dot_rowcol(g, "data-blank-map-max",
                                              map_rect_by_cell.get(ci),
                                              cols, rows)
        else:
            # Filled cell: nucleus rect (first rect) + text.
            nuc = rects[0]
            nx, ny = _num(nuc.get("x")), _num(nuc.get("y"))
            cell["nucleus_bg"] = nuc.get("fill")
            if texts:
                cell["text"] = texts[0].text or ""
                cell["fg"] = texts[0].get("fill")
                cell["text_size_px"] = _text_size_px(texts[0])
            # surround bits + edge color from geometry
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

    # --- labels ---
    model["labels"] = _labels(root)
    model["user_note"] = _user_note(root)

    return model


def _opt_int(s) -> Optional[int]:
    return int(s) if s is not None else None


def _close(a: float, b: float, tol: float = 0.01) -> bool:
    return abs(a - b) <= tol


def _derive_fs(root) -> float:
    """font_size_px from the first nucleus rect (nucleus_width = 3*fs)."""
    for g in _findall(root, "g"):
        if g.get("data-channel") != "cell" or g.get("data-cell-blank") == "true":
            continue
        for c in g:
            if _tag(c) == "rect":
                return _num(c.get("width")) / _NUC_W
    # Fallback: derive from grid bg width = cols * 3.75 * fs.
    cols = int(root.get("data-cols"))
    bg = _grid_bg_rect(root)
    if bg is not None:
        return _num(bg.get("width")) / (cols * 3.75)
    raise ValueError("cannot derive font size from SVG")


def _grid_bg_rect(root):
    for g in _findall(root, "g"):
        if g.get("data-channel") == "grid":
            for c in g:
                if _tag(c) == "rect":
                    return c
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


def _dot_rowcol(g, attr: str, map_rect, cols: int, rows: int):
    """Recover (row, col) of a blank-map dot from its center within the map
    sub-grid. The dot is centered at sub_cell (row+0.5, col+0.5)."""
    if map_rect is None:
        return None
    mx = _num(map_rect.get("x"))
    my = _num(map_rect.get("y"))
    mw = _num(map_rect.get("width"))
    mh = _num(map_rect.get("height"))
    sub_w = mw / cols
    sub_h = mh / rows
    for c in g:
        if c.get(attr) != "true":
            continue
        cx = c.get("cx")
        cy = c.get("cy")
        if cx is None or cy is None:
            continue
        col = int(round((_num(cx) - mx) / sub_w - 0.5))
        row = int(round((_num(cy) - my) / sub_h - 0.5))
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
    else:
        if a != b:
            diffs.append(f"{path}: golden={a!r} actual={b!r}")


def models_equal(golden: dict, actual: dict) -> bool:
    return not diff_models(golden, actual)
