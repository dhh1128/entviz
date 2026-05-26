"""
V3-7: defs+use SVG encoding.

The 6 non-empty v3 shapes are defined once each as <path> elements
inside <defs>. Each drawn edge becomes a single <use> element that
references the relevant shape by id. The cloned shape inherits the
<use>'s fill (a per-edge gradient) and is transformed into position.

The expected savings vs V3-6b: each `<path d="..." transform=...
fill=... fill-rule=evenodd/>` (~120-220 bytes depending on shape)
becomes a `<use href="#cN" transform=... fill=.../>` (~80 bytes).
For a typical 22-cell hex input that's ~5-10 KB shaved per render.
"""
from lxml import etree

from entviz.pipeline import render


LARGE_INPUT = "deadbeefdeadbeef" * 8  # 22 hex tokens, 4x6 grid


def _doc(svg_str):
    return etree.fromstring(svg_str.encode())


def test_v3_shape_paths_defined_in_defs():
    svg = _doc(render(LARGE_INPUT))
    defs = svg.xpath('//*[local-name()="defs"]')[0]
    path_ids = {
        p.get("id") for p in defs.xpath('./*[local-name()="path"]')
        if p.get("id")
    }
    # The 6 non-empty shapes should be defined (lowercase ids).
    expected = {"c1", "c2", "c3", "p1", "p2", "p3"}
    assert expected.issubset(path_ids), (
        f"missing shape defs: {expected - path_ids}"
    )


def test_v3_shape_def_paths_have_fill_rule_evenodd():
    svg = _doc(render(LARGE_INPUT))
    defs = svg.xpath('//*[local-name()="defs"]')[0]
    for sid in ("c1", "c2", "c3", "p1", "p2", "p3"):
        path = defs.xpath(f'./*[local-name()="path"][@id="{sid}"]')[0]
        assert path.get("fill-rule") == "evenodd", (
            f"shape def {sid} missing fill-rule=evenodd"
        )


def test_v3_shape_defs_have_no_inline_fill_or_transform():
    # Defs should be plain geometry only; per-edge fill and transform
    # come from the <use> element.
    svg = _doc(render(LARGE_INPUT))
    defs = svg.xpath('//*[local-name()="defs"]')[0]
    for sid in ("c1", "c2", "c3", "p1", "p2", "p3"):
        path = defs.xpath(f'./*[local-name()="path"][@id="{sid}"]')[0]
        assert path.get("fill") is None, f"def {sid} should not have fill"
        assert path.get("transform") is None, f"def {sid} should not have transform"


def test_edges_are_use_elements_not_inline_paths():
    # After V3-7, the rendered SVG should contain `<use>` elements for
    # every drawn edge and NO inline edge-shape `<path>` elements.
    svg = _doc(render(LARGE_INPUT))
    # Edge-shape paths inside <defs> are fine; that's where they live now.
    inline_paths = svg.xpath(
        '//*[local-name()="path"][not(ancestor::*[local-name()="defs"])]'
    )
    assert len(inline_paths) == 0, (
        f"found {len(inline_paths)} inline edge paths; expected 0"
    )

    uses = svg.xpath('//*[local-name()="use"]')
    assert len(uses) > 0, "no <use> elements found"
    for u in uses:
        href = u.get("href") or u.get("{http://www.w3.org/1999/xlink}href") or ""
        assert href.startswith("#"), f"<use> href {href!r} not local"


def test_use_elements_reference_v3_shape_ids():
    svg = _doc(render(LARGE_INPUT))
    valid_ids = {"#c1", "#c2", "#c3", "#p1", "#p2", "#p3"}
    uses = svg.xpath('//*[local-name()="use"]')
    for u in uses:
        href = u.get("href") or u.get("{http://www.w3.org/1999/xlink}href") or ""
        assert href in valid_ids, f"<use href={href!r}> not a v3 shape"


def test_use_elements_carry_fill_and_transform():
    svg = _doc(render(LARGE_INPUT))
    uses = svg.xpath('//*[local-name()="use"]')
    for u in uses:
        # Each <use> should set fill (the per-edge gradient) and transform
        # (the placement). The shape's fill-rule comes from the def.
        assert u.get("fill") is not None and u.get("fill").startswith("url(#"), (
            f"<use> missing gradient fill: {etree.tostring(u)}"
        )
        assert u.get("transform") is not None, (
            f"<use> missing transform: {etree.tostring(u)}"
        )


def test_v3_7_svg_size_smaller_than_v3_6b():
    # Concrete size-reduction expectation.
    new_svg = render(LARGE_INPUT)
    # The V3-6b reference for this input was committed at refs/v3-6b/.
    import os
    v3_6b = open("refs/v3-6b/exact-512.svg").read()
    assert len(new_svg) < len(v3_6b), (
        f"V3-7 size {len(new_svg)} not smaller than V3-6b size {len(v3_6b)}"
    )
