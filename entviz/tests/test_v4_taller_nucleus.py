"""
v4 nucleus geometry: nucleus_width = 3·font_size_px (unchanged from v3),
nucleus_height = 1.25·font_size_px (was 1.0·font_size_px). The 25%
vertical extra makes room for glyph descenders on typical monospace
fonts whose bounding boxes extend below the em-box.
"""
from lxml import etree

from entviz.pipeline import render


def _doc(svg_str):
    return etree.fromstring(svg_str.encode())


def test_nucleus_dimensions_at_12pt():
    """At 12pt / 96 DPI: nucleus is 48 × 20, NOT v3's 48 × 16."""
    svg = _doc(render("550e8400-e29b-41d4-a716-446655440000"))
    nuclei = [
        r for r in svg.xpath('//*[local-name()="rect"]')
        if float(r.get("width", 0)) == 48 and float(r.get("height", 0)) == 20
    ]
    assert nuclei, "no v4 nucleus rects found (48 × 20)"
    # No v3-sized nuclei (48 × 16) should remain.
    v3_nuclei = [
        r for r in svg.xpath('//*[local-name()="rect"]')
        if float(r.get("width", 0)) == 48 and float(r.get("height", 0)) == 16
    ]
    assert not v3_nuclei, "found v3-sized nuclei (48 × 16) — should be 48 × 20 in v4"


def test_nucleus_dimensions_at_16pt():
    """At 16pt: font_size_px ≈ 21.33; nucleus_width ≈ 64; nucleus_height ≈ 26.67."""
    svg = _doc(render("550e8400-e29b-41d4-a716-446655440000", font_size_pt=16))
    rects = svg.xpath('//*[local-name()="rect"]')
    # Find a nucleus by aspect ratio (12:5) regardless of exact pixel values.
    nuclei = []
    for r in rects:
        w = float(r.get("width", 0))
        h = float(r.get("height", 0))
        if w > 0 and h > 0:
            ratio = w / h
            # nucleus aspect = 12:5 = 2.4
            if abs(ratio - 2.4) < 0.01 and w > 50:  # filter out small surround boxes
                nuclei.append((w, h))
    assert nuclei, f"no v4-aspect nuclei found; sample rects: {[(r.get('width'), r.get('height')) for r in rects[:5]]}"


def test_cell_height_is_25x_font_size_px():
    """v4 cell_height = 2.5 · font_size_px = 40 at 12pt (was 32 in v3)."""
    svg = _doc(render("deadbeef"))
    # Bounding height for a 2x2 grid: 1 + GM + 2·40 + GM + 1 = 92 (GM=5).
    # v3 was: 1 + 4 + 64 + 4 + 16 + 4 + 1 = 94.
    bh = float(svg.get("height"))
    assert bh == 92, f"v4 bounding height should be 92, got {bh}"


def test_text_baseline_inside_nucleus():
    """Cell text's y attribute should be inside the nucleus vertical span.
    At 12pt, nucleus is 20 px tall; with central baseline at nucleus center,
    descenders (~25% of em) fit inside the nucleus."""
    svg = _doc(render("550e8400-e29b-41d4-a716-446655440000"))
    texts = [t for t in svg.xpath('//*[local-name()="text"]')
             if t.get("text-anchor") == "middle"]
    nuclei = [
        r for r in svg.xpath('//*[local-name()="rect"]')
        if float(r.get("width", 0)) == 48 and float(r.get("height", 0)) == 20
    ]
    assert texts and nuclei
    # Text y should be at nucleus center: nucleus.top + 10
    for t in texts:
        ty = float(t.get("y"))
        # Find the nucleus whose vertical span contains ty
        match = next(
            (n for n in nuclei
             if float(n.get("y")) <= ty <= float(n.get("y")) + 20),
            None,
        )
        # lxml Elements default to falsy when they have no children, so
        # use 'is not None' for the existence check.
        assert match is not None, f"text at y={ty} not inside any nucleus"
