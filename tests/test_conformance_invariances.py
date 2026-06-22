"""Metamorphic conformance tests: prove the checker tolerates exactly the
serialization-level variations the spec's *equivalence relation* permits, and
that each such variation is genuinely INVISIBLE (pixel-identical raster).

Each test takes a known-good entviz, applies one class of legitimate variation,
and asserts:

  (A) Tier-A: ``extract_model`` is UNCHANGED  (``diff_models == []``), so the
      checker tolerates the variation; and
  (B) Tier-B: the cairosvg raster is pixel-identical, so the variation is truly
      invisible — not merely "tolerated".

The two NEGATIVE tests at the end document where Tier-A is deliberately blind
(paint order, added visible elements): the model is unchanged but the raster
DIFFERS, which is why those properties are normative *only* under Tier B.

Raster (B) assertions are skipped when cairosvg/Pillow/numpy are absent; the
model (A) assertions always run.
"""
import io
import re

import pytest
from lxml import etree

from compliance import diff_models, extract_model
from entviz.pipeline import render

SVGNS = "http://www.w3.org/2000/svg"
Q = "{%s}" % SVGNS

# A rich input: 3x4 grid with dense surround, a colour bar, an ellipse overlay,
# quartile marks, and a blank-map cell — every channel is exercised.
BASE_INPUT = "0123456789abcdef" * 4  # 256-bit hex


@pytest.fixture(scope="module")
def base():
    return render(BASE_INPUT)


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def _tag(e):
    t = e.tag
    return t.split("}", 1)[1] if isinstance(t, str) and "}" in t else t


def _raster(svg, scale=2.0):
    cairosvg = pytest.importorskip("cairosvg")
    np = pytest.importorskip("numpy")
    Image = pytest.importorskip("PIL.Image")
    png = cairosvg.svg2png(bytestring=svg.encode(), scale=scale)
    return np.asarray(Image.open(io.BytesIO(png)).convert("RGB")).astype(int)


def assert_model_unchanged(original, variant):
    diffs = diff_models(extract_model(original), extract_model(variant))
    assert diffs == [], f"checker did NOT tolerate the variation: {diffs[:6]}"


def assert_raster_identical(original, variant, tol=0):
    np = pytest.importorskip("numpy")
    a, b = _raster(original), _raster(variant)
    assert a.shape == b.shape, f"canvas size changed {a.shape} != {b.shape}"
    maxdiff = int(np.abs(a - b).max())
    assert maxdiff <= tol, f"raster differs (max per-channel diff {maxdiff} > {tol})"
    return maxdiff


def _parse(svg):
    return etree.fromstring(svg.encode())


def _ser(root):
    return etree.tostring(root, encoding="unicode")


# Sanity: a pure parse->serialize round-trip must itself be invisible, so any
# raster difference in a later test is attributable to the transform alone.
def test_roundtrip_is_invisible(base):
    rt = _ser(_parse(base))
    assert_model_unchanged(base, rt)
    assert_raster_identical(base, rt)


# --------------------------------------------------------------------------
# Equivalence-relation bullet 1: XML prolog / DOCTYPE / encoding / namespaces
# --------------------------------------------------------------------------
def test_xml_prolog_and_extra_namespace(base):
    root = _parse(base)
    root.set("data-ignored-ns-probe", "x")  # forces re-serialization with attrs
    variant = '<?xml version="1.0" encoding="UTF-8"?>\n' + _ser(root)
    # strip the probe so the model surfaces are identical
    variant = variant.replace(' data-ignored-ns-probe="x"', "")
    assert_model_unchanged(base, variant)
    assert_raster_identical(base, variant)


# --------------------------------------------------------------------------
# Bullet 2a: attribute ordering
# --------------------------------------------------------------------------
def test_attribute_order(base):
    root = _parse(base)
    for el in root.iter():
        items = list(el.attrib.items())
        for k, _ in items:
            del el.attrib[k]
        for k, v in reversed(items):  # reverse every element's attribute order
            el.set(k, v)
    assert_model_unchanged(base, _ser(root))
    assert_raster_identical(base, _ser(root))


# --------------------------------------------------------------------------
# Bullet 3a: numeric formatting that denotes the SAME value
# --------------------------------------------------------------------------
_COORD_ATTRS = {"x", "y", "width", "height", "cx", "cy", "r", "rx", "ry",
                "x1", "y1", "x2", "y2", "stroke-width", "fill-opacity",
                "stroke-opacity", "data-ellipse-anchor-x", "data-ellipse-anchor-y",
                "data-ellipse-rx", "data-ellipse-ry", "data-ellipse-rotation-deg"}
_NUMTOK = re.compile(r"-?\d+(?:\.\d+)?")


def _reformat_same_value(svg, fmt):
    root = _parse(svg)
    for el in root.iter():
        for k, v in list(el.attrib.items()):
            if k in _COORD_ATTRS:
                el.set(k, fmt(float(v)))
            elif k in ("viewBox", "transform", "points", "d"):
                el.set(k, _NUMTOK.sub(lambda m: fmt(float(m.group())), v))
    return _ser(root)


def test_numeric_same_value_more_decimals(base):
    # 27 -> 27.0000, 0.5 -> 0.5000 : identical value, fatter formatting.
    variant = _reformat_same_value(base, lambda x: f"{x:.4f}")
    assert_model_unchanged(base, variant)
    assert_raster_identical(base, variant)


# --------------------------------------------------------------------------
# Bullet 3b: coordinates that DIFFER within the 0.05px tolerance
# --------------------------------------------------------------------------
def test_within_tolerance_shift_stays_inside_tier_b(base):
    # Tier A ⊆ Tier B: a coordinate shift AT the Tier-A tolerance edge (0.01px)
    # keeps the model equal AND keeps the raster within the Tier-B per-channel
    # tolerance (channel_tol=16) — so no difference can be model-equivalent yet
    # pixel-rejected. (A larger shift, e.g. 0.04px, is correctly REJECTED by the
    # model comparison now — see test_diff_models_tolerates_subpixel_* and the
    # tolerance sweep in the analysis.)
    variant = _reformat_same_value(base, lambda x: f"{x + 0.008:.3f}")  # within 0.01px
    assert_model_unchanged(base, variant)
    maxdiff = assert_raster_identical(base, variant, tol=16)
    print(f"\n[+0.008px shift] max per-channel raster diff = {maxdiff} (Tier-B channel_tol=16)")


# --------------------------------------------------------------------------
# Bullet 4: the salted clip-path id value (renamed consistently)
# --------------------------------------------------------------------------
def test_salted_clip_id_rename(base):
    variant = base.replace("grid-clip-", "anything-unique-")
    assert "anything-unique-" in variant
    assert_model_unchanged(base, variant)
    assert_raster_identical(base, variant)


# --------------------------------------------------------------------------
# Bullet 5: element grouping that preserves paint order + geometry
# --------------------------------------------------------------------------
def test_regroup_preserving_paint_order(base):
    root = _parse(base)
    grid = next(g for g in root.iter(Q + "g") if g.get("data-channel") == "grid")
    wrapper = etree.SubElement(grid, Q + "g")  # a new, transform-less group
    for child in list(grid):
        if child is wrapper:
            continue
        grid.remove(child)
        wrapper.append(child)  # same order, now one level deeper
    assert_model_unchanged(base, _ser(root))
    assert_raster_identical(base, _ser(root))


# --------------------------------------------------------------------------
# Bullet 6: additional advisory metadata that does not render
# --------------------------------------------------------------------------
def test_advisory_metadata(base):
    root = _parse(base)
    root.set("data-vendor-note", "produced-by-fuzzer")          # extra attr
    desc = etree.Element(Q + "desc")
    desc.text = "an entviz"
    root.insert(0, desc)                                         # <desc> (non-rendering)
    root.insert(0, etree.Comment(" advisory comment "))         # XML comment
    assert_model_unchanged(base, _ser(root))
    assert_raster_identical(base, _ser(root))


# --------------------------------------------------------------------------
# Required-but-not-model-compared attribute: the library-version stamp
# --------------------------------------------------------------------------
def test_library_version_stamp_varies(base):
    root = _parse(base)
    root.set("data-entviz-lib", "99.99.99")  # each impl stamps its own version
    assert_model_unchanged(base, _ser(root))
    assert_raster_identical(base, _ser(root))


# --------------------------------------------------------------------------
# v10 MAY: surround as a <path> (default now) OR as individual rects
# (an older impl). Convert path->rects AND drop the declared attributes so the
# checker must fall back to recovering the channel from geometry.
# --------------------------------------------------------------------------
_BOX = re.compile(r"M(-?[\d.]+) (-?[\d.]+)h(-?[\d.]+)v(-?[\d.]+)h-?[\d.]+z?")


def _surround_path_to_rects(svg):
    root = _parse(svg)
    grid = next(g for g in root.iter(Q + "g") if g.get("data-channel") == "grid")
    layer = None
    for g in grid:
        if _tag(g) == "g" and any(_tag(c) == "path" and c.get("fill", "").startswith("#")
                                  and c.get("data-blank-map-max") is None for c in g):
            layer = g
            break
    assert layer is not None, "surround layer not found"
    for p in list(layer):
        if _tag(p) != "path" or p.get("data-blank-map-max") is not None:
            continue
        fill = p.get("fill")
        for m in _BOX.finditer(p.get("d", "")):
            x, y, w, h = map(float, m.groups())
            r = etree.SubElement(layer, Q + "rect")
            r.set("x", f"{x:g}"); r.set("y", f"{y:g}")
            r.set("width", f"{w:g}"); r.set("height", f"{h:g}")
            r.set("fill", fill)
        layer.remove(p)
    # drop the declarations so the checker MUST use the geometry fallback
    for g in root.iter(Q + "g"):
        if g.get("data-channel") == "cell":
            for a in ("data-surround-bits", "data-edge-color"):
                if g.get(a) is not None:
                    del g.attrib[a]
    return _ser(root)


def test_surround_rects_form_is_equivalent_to_path_form(base):
    variant = _surround_path_to_rects(base)
    assert "data-surround-bits" not in variant  # old-style: no declaration
    assert_model_unchanged(base, variant)        # geometry fallback recovers it
    assert_raster_identical(base, variant)        # same boxes, same pixels


# --------------------------------------------------------------------------
# v10 MAY: font-size carried as a presentation attribute OR inside style;
# font-family on the root OR per-text.
# --------------------------------------------------------------------------
def test_font_size_in_style_instead_of_attribute(base):
    root = _parse(base)
    ff = root.get("font-family")
    for t in root.iter(Q + "text"):
        fs = t.get("font-size")
        if fs is not None:
            del t.attrib["font-size"]
            style = t.get("style", "")
            t.set("style", (style + ";" if style else "") + f"font-family: {ff}; font-size: {fs}px;")
    assert_model_unchanged(base, _ser(root))
    assert_raster_identical(base, _ser(root))


# ==========================================================================
# NEGATIVE controls — Tier-A is deliberately blind here; only Tier-B catches.
# These document the boundary, and motivate the spec recommendations.
# ==========================================================================
def test_paint_order_violation_is_invisible_to_tier_a_but_changes_raster(base):
    """Moving the surround paths INTO their cell groups keeps every declared
    attribute (so the model is unchanged — Tier A passes) but paints the boxes
    OVER the ellipse overlay instead of under it, so the raster changes. This is
    why paint order is normative only under Tier B."""
    root = _parse(base)
    grid = next(g for g in root.iter(Q + "g") if g.get("data-channel") == "grid")
    # collect surround paths (anonymous fill+d, in a sub-group of grid)
    paths = [p for p in grid.iter(Q + "path")
             if p.get("data-blank-map-max") is None and p.get("fill", "").startswith("#")]
    cells = {g.get("data-cell-index"): g for g in root.iter(Q + "g")
             if g.get("data-channel") == "cell"}
    moved = 0
    # crude: append each surround path to *a* cell group (any) to change order
    for p in paths:
        p.getparent().remove(p)
        next(iter(cells.values())).append(p)
        moved += 1
    assert moved > 0
    variant = _ser(root)
    assert_model_unchanged(base, variant)  # Tier A: BLIND to the move
    # Tier B: the raster DOES change (ellipse no longer tints the boxes).
    np = pytest.importorskip("numpy")
    a, b = _raster(base), _raster(variant)
    assert int(np.abs(a - b).max()) > 0, "expected a visible raster difference"


def test_added_visible_element_is_invisible_to_the_model_but_caught_elsewhere(base):
    """An extra visible <rect> is 'additional content' the render MODEL ignores
    (extract_model only reads declared channels) — yet it paints pixels. It is
    caught two ways: by Tier B (the raster differs) AND, now, by the Tier-A
    closed-profile check (validate_closed_profile), which has no golden-raster
    dependency. See test_closed_profile.py."""
    from compliance import validate_closed_profile
    root = _parse(base)
    bad = etree.SubElement(root, Q + "rect")
    bad.set("x", "0"); bad.set("y", "0")
    bad.set("width", "10"); bad.set("height", "10"); bad.set("fill", "#ff00ff")
    variant = _ser(root)
    assert_model_unchanged(base, variant)            # the model comparison is blind
    assert validate_closed_profile(variant) != []    # the closed-profile check is not
    np = pytest.importorskip("numpy")
    a, b = _raster(base), _raster(variant)
    assert int(np.abs(a - b).max()) > 0               # and Tier B sees the pixels
