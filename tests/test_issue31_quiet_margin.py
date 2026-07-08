"""
Regression test for issue #31: the gray frame must never sit on the canvas
edge, so fractional render scales (e.g. a non-default font size in a browser,
where the SVG is scaled to a non-integer pixel size and default overflow:hidden
shaves the outer half of an edge-hugging stroke) can never clip it. The frame
is the load-bearing anchor for raster localization, so it must always render as
a complete, solid, closed rectangle.

Invariant: every painted rect and line stays within [MARGIN, bounding-MARGIN]
on each axis — i.e. a MARGIN-unit quiet ring around the whole glyph carries no
ink and renders transparent. MARGIN = 1 user unit.
"""
from lxml import etree

from entviz.pipeline import render, MARGIN


def _doc(svg_str):
    return etree.fromstring(svg_str.encode())


# A spread of code paths: short hex, UUID, prefix+suffix (Bitcoin), text
# fallback, and a >512-bit input (head/fingerprint-middle/tail).
_INPUTS = [
    "deadbeef",
    "550e8400-e29b-41d4-a716-446655440000",
    "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
    "The quick brown fox jumps over the lazy dog",
    "ab" * 100,
]
# Font sizes including the exact repro (20pt) and the previously-fine 12pt.
_FONT_SIZES = [12, 20, 6, 24]


def _rects_and_lines(doc):
    for r in doc.xpath('//*[local-name()="rect"]'):
        x, y = float(r.get("x")), float(r.get("y"))
        yield x, y, x + float(r.get("width")), y + float(r.get("height"))
    for ln in doc.xpath('//*[local-name()="line"]'):
        x1, y1 = float(ln.get("x1")), float(ln.get("y1"))
        x2, y2 = float(ln.get("x2")), float(ln.get("y2"))
        # A 1-px stroke paints ±0.5 perpendicular to its centerline only
        # (default stroke-linecap="butt" gives no overshoot along the axis).
        if y1 == y2:      # horizontal
            yield (min(x1, x2), y1 - 0.5, max(x1, x2), y1 + 0.5)
        else:             # vertical
            yield (x1 - 0.5, min(y1, y2), x1 + 0.5, max(y1, y2))


def test_no_ink_in_quiet_margin_across_inputs_and_scales():
    for raw in _INPUTS:
        for fs in _FONT_SIZES:
            doc = _doc(render(raw, font_size_pt=fs))
            w, h = float(doc.get("width")), float(doc.get("height"))
            for x0, y0, x1, y1 in _rects_and_lines(doc):
                assert x0 >= MARGIN - 1e-6, f"{raw!r}@{fs}: ink at x={x0} < MARGIN"
                assert y0 >= MARGIN - 1e-6, f"{raw!r}@{fs}: ink at y={y0} < MARGIN"
                assert x1 <= w - MARGIN + 1e-6, f"{raw!r}@{fs}: ink at x={x1} > {w-MARGIN}"
                assert y1 <= h - MARGIN + 1e-6, f"{raw!r}@{fs}: ink at y={y1} > {h-MARGIN}"


def test_frame_lines_form_closed_rect_inset_by_margin():
    # The four gray lines must trace a closed rectangle whose outer edges sit
    # exactly MARGIN from the canvas edge (never on the boundary).
    doc = _doc(render("550e8400-e29b-41d4-a716-446655440000"))
    w, h = float(doc.get("width")), float(doc.get("height"))
    grays = [
        ln for ln in doc.xpath('//*[local-name()="line"]')
        if ln.get("stroke") == "#808080"
    ]
    # top, right, bottom, left + interior separator == 5 lines.
    assert len(grays) == 5

    def centerline(ln):
        return (float(ln.get("x1")), float(ln.get("y1")),
                float(ln.get("x2")), float(ln.get("y2")))

    horiz = [centerline(l) for l in grays if float(l.get("y1")) == float(l.get("y2"))]
    vert = [centerline(l) for l in grays if float(l.get("x1")) == float(l.get("x2"))]
    ys = sorted(c[1] for c in horiz)
    xs = sorted(c[0] for c in vert)
    # Outermost frame lines are centered half a unit inside the quiet ring, so
    # their outer stroke edge lands exactly on MARGIN / (bounding - MARGIN).
    assert ys[0] == MARGIN + 0.5           # top centerline
    assert ys[-1] == h - MARGIN - 0.5      # bottom centerline
    assert xs[0] == MARGIN + 0.5           # left centerline
    assert xs[-1] == w - MARGIN - 0.5      # right (outermost) centerline


def test_white_field_is_inset_leaving_transparent_ring():
    # The white fill must not reach the canvas edge — the ring outside it has
    # no fill element and therefore renders transparent.
    doc = _doc(render("deadbeef"))
    w, h = float(doc.get("width")), float(doc.get("height"))
    fields = [
        r for r in doc.xpath('//*[local-name()="rect"]')
        if r.get("fill") == "#ffffff" and float(r.get("x")) == MARGIN
    ]
    assert fields, "white field rect not found at x=MARGIN"
    f = fields[0]
    assert float(f.get("y")) == MARGIN
    assert float(f.get("width")) == w - 2 * MARGIN
    assert float(f.get("height")) == h - 2 * MARGIN
