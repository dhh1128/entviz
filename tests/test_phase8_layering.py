"""
Layered rendering — pipeline renders in a global order (not per-cell), so
the ellipse overlay can sit between the edge layer and the nucleus layer
across the whole grid. v4 layer order:

  1. white bounding bg
  2. grid_rect bg
  3. surround boxes (per cell)       — edge layer
  4. ellipse overlay (clipped)
  5. nuclei + text (per cell)        — nucleus layer
  6. blank-cell rings + pointer markers
  7. quartile triangles (polygons)
  8. color bar bands
  9. gray border lines
"""
from lxml import etree

from entviz.pipeline import render


def _doc(svg_str):
    return etree.fromstring(svg_str.encode())


def _is_nucleus_rect(rect):
    # nucleus is 48 × 20 at 12pt; blank-cell rects are also 48 × 20 but carry
    # rounded corners (rx), so exclude those.
    return (float(rect.get("width", 0)) == 48 and float(rect.get("height", 0)) == 20
            and rect.get("rx") is None)


def _is_color_bar_band(rect):
    # v6: color bar bands at x=1 with width=bar_width=20.
    return float(rect.get("x", -1)) == 1 and float(rect.get("width", -1)) == 20


def _is_grid_bg(rect):
    # The single rect filling grid_rect with the entviz bg color sits
    # at (grid_rect.left, grid_rect.top). For UUID (6 hex tokens, 2x3
    # grid) in v6: grid_rect = (27, 31) of size 120 × 120.
    return (float(rect.get("x", 0)) == 27 and float(rect.get("y", 0)) == 31
            and float(rect.get("width", 0)) == 120
            and float(rect.get("height", 0)) == 120)


def test_all_edges_before_any_nucleus():
    """All surround boxes are emitted before the first nucleus rect."""
    svg = _doc(render("550e8400-e29b-41d4-a716-446655440000"))
    rects = svg.xpath('//*[local-name()="rect" and not(ancestor::*[local-name()="defs"])]')

    first_nucleus_idx = None
    for i, el in enumerate(rects):
        if _is_nucleus_rect(el):
            first_nucleus_idx = i
            break
    assert first_nucleus_idx is not None, "no nucleus rect found"

    # Every rect before the first nucleus is either bg or surround box;
    # rects after are nuclei or color-bar bands.
    for i, el in enumerate(rects[first_nucleus_idx + 1:], start=first_nucleus_idx + 1):
        if _is_nucleus_rect(el) or _is_color_bar_band(el):
            continue
        # Otherwise should not be an edge box (which is 6 × 10 at 12pt)
        w, h = float(el.get("width", 0)), float(el.get("height", 0))
        assert not (w == 6 and h == 10), (
            f"surround box at doc-order index {i} appeared after first nucleus"
        )


def test_text_appears_after_nucleus_rects():
    """Cell text is emitted after each nucleus rect."""
    svg = _doc(render("550e8400-e29b-41d4-a716-446655440000"))
    elements = svg.xpath('//*')
    first_text_idx = next(
        (i for i, el in enumerate(elements) if el.tag.endswith("}text")), None
    )
    first_nucleus_idx = next(
        (i for i, el in enumerate(elements)
         if el.tag.endswith("}rect") and _is_nucleus_rect(el)),
        None,
    )
    assert first_text_idx is not None and first_nucleus_idx is not None
    assert first_text_idx > first_nucleus_idx


def test_overlay_between_edges_and_nuclei():
    """The ellipse overlay sits between the edge layer and the nucleus layer."""
    # Use an input large enough to qualify for an overlay (>= 256 bits).
    svg = _doc(render("0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"))
    elements = svg.xpath('//*')
    # Find ellipse position and first nucleus position
    ellipse_idx = next(
        (i for i, el in enumerate(elements) if el.tag.endswith("}ellipse")), None
    )
    first_nucleus_idx = next(
        (i for i, el in enumerate(elements)
         if el.tag.endswith("}rect") and _is_nucleus_rect(el)),
        None,
    )
    assert ellipse_idx is not None, "no ellipse found for ≥256-bit input"
    assert first_nucleus_idx is not None
    assert ellipse_idx < first_nucleus_idx, (
        "ellipse overlay must precede the nucleus layer"
    )


def test_borders_last_in_document_order():
    """Gray border lines are the final elements in the SVG."""
    svg = _doc(render("550e8400-e29b-41d4-a716-446655440000"))
    elements = svg.xpath('//*')
    # Last 5 elements should be the 5 gray border lines (top/right/bottom/left
    # + interior separator).
    last_five = elements[-5:]
    for el in last_five:
        assert el.tag.endswith("}line"), f"expected trailing line, got {el.tag}"
        assert el.get("stroke") == "#808080"
