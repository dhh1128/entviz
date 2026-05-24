"""
Phase 8 acceptance: the pipeline renders in a layered global order rather
than cell-by-cell. The critical structural property is that ALL edge
shapes appear in the SVG document before ANY nucleus rect, so a future
ellipse overlay (Phase 12) can sit between the two layers across the
whole grid simultaneously.
"""
from lxml import etree

from entviz.pipeline import render


def _doc(svg_str):
    return etree.fromstring(svg_str.encode())


def _is_nucleus(rect):
    # Nucleus rects are nucleus_width × nucleus_height (48 × 16 at 12pt/96).
    return float(rect.get("width", 0)) == 48 and float(rect.get("height", 0)) == 16


def _is_color_bar_band(rect):
    # Color bar bands are at x=0 with width=GM=4. Phase 10 added these
    # after the nucleus layer — that's intentional (the color bar is a
    # gestalt summary, drawn over the bounding rect's left strip).
    return float(rect.get("x", -1)) == 0 and float(rect.get("width", -1)) == 4


def _is_grid_bg(rect):
    # The single rect filling grid_rect with the entviz bg color.
    # Its size matches grid_w × grid_h; for a UUID 2x4 grid that's 128 × 128.
    w, h = float(rect.get("width", 0)), float(rect.get("height", 0))
    return w in (128, 192) and h in (64, 128)  # short or uuid


def test_all_edges_before_any_nucleus():
    svg = _doc(render("550e8400-e29b-41d4-a716-446655440000"))
    # Walk all rects + polygons in document order; the index of the first
    # nucleus must be greater than the index of every edge element.
    elements = svg.xpath('//*[local-name()="rect" or local-name()="polygon"]')

    first_nucleus_idx = None
    for i, el in enumerate(elements):
        if el.tag.endswith("}rect") and _is_nucleus(el):
            first_nucleus_idx = i
            break
    assert first_nucleus_idx is not None, "no nucleus rect found"

    # Every edge element (polygon, or non-nucleus non-bounding/grid rect)
    # after the first nucleus would mean the layering is wrong.
    for i, el in enumerate(elements[first_nucleus_idx + 1:], start=first_nucleus_idx + 1):
        if el.tag.endswith("}rect"):
            # Allow trailing nucleus rects and color-bar bands; reject
            # anything that looks like an edge shape.
            if _is_nucleus(el) or _is_color_bar_band(el):
                continue
            assert False, f"non-nucleus rect at index {i} (after nucleus layer began)"
        else:
            # polygon = edge shape (triangle drawer uses polygon)
            assert False, f"polygon at index {i} (after nucleus layer began)"


def test_text_appears_after_nucleus_rects():
    # Text is part of the nucleus layer and follows each nucleus rect.
    # Specifically, no text element should appear before the first nucleus.
    svg = _doc(render("550e8400-e29b-41d4-a716-446655440000"))
    elements = svg.xpath('//*')
    first_text_idx = next(
        (i for i, el in enumerate(elements) if el.tag.endswith("}text")), None
    )
    first_nucleus_idx = next(
        (i for i, el in enumerate(elements)
         if el.tag.endswith("}rect") and _is_nucleus(el)),
        None,
    )
    assert first_text_idx is not None and first_nucleus_idx is not None
    assert first_text_idx > first_nucleus_idx


def test_quartile_marks_after_nuclei():
    svg = _doc(render("550e8400-e29b-41d4-a716-446655440000"))
    elements = svg.xpath('//*')
    last_text_idx = next(
        (i for i, el in reversed(list(enumerate(elements))) if el.tag.endswith("}text")),
        None,
    )
    first_circle_idx = next(
        (i for i, el in enumerate(elements) if el.tag.endswith("}circle")), None
    )
    if first_circle_idx is None:
        return  # input may not produce circles
    assert first_circle_idx > last_text_idx, (
        "quartile circle appeared before/within the nucleus+text layer"
    )


def test_borders_last_in_document_order():
    svg = _doc(render("550e8400-e29b-41d4-a716-446655440000"))
    elements = svg.xpath('//*')
    last_three = elements[-3:]
    # Last three elements should be the 3 black border lines.
    for el in last_three:
        assert el.tag.endswith("}line"), f"expected trailing line, got {el.tag}"
        assert el.get("stroke") == "#000000"
