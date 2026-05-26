"""
Phase 9 acceptance tests: shape rename (triangle→fin etc.), letter
attribute on each shape (for the Phase 11 shape count summary), and
linear-gradient edge fill (nucleus_bg at the inner boundary, edge_color
at the outer boundary, perpendicular to the shared edge).
"""
from lxml import etree

from entviz.cell_shapes import SHAPE_DRAWERS
from entviz.colors import SHAPE_ARRAY_0, SHAPE_ARRAY_1, EdgeShape
from entviz.pipeline import render


def _doc(svg_str):
    return etree.fromstring(svg_str.encode())


def test_shape_names_are_v3():
    # V3-6b: SHAPE_ARRAY_0/1 now point at the cubist and polygon sets.
    names0 = [s.name for s in SHAPE_ARRAY_0]
    names1 = [s.name for s in SHAPE_ARRAY_1]
    assert names0 == ['C1', 'C2', 'C3', 'C4']
    assert names1 == ['P1', 'P2', 'P3', 'P4']


def test_v1_v2_shape_names_are_gone():
    names0 = [s.name for s in SHAPE_ARRAY_0]
    names1 = [s.name for s in SHAPE_ARRAY_1]
    for old in ['triangle', 'hook', 'rect', 'box', 'slant', 'hammer', 'pyramid',
                'double bars', 'fin', 'axe', 'brick', 'inf', 'wave', 'hole',
                'keel', 'mound']:
        assert old not in names0 + names1


def test_each_v3_edgeshape_has_slot():
    # V3 shapes are identified by slot (1-4) rather than letter; slot 4
    # is the empty member.
    for s in SHAPE_ARRAY_0 + SHAPE_ARRAY_1:
        assert s.slot in (1, 2, 3, 4)


def test_v2_procedural_drawer_registry_still_exists():
    # The v2 SHAPE_DRAWERS dict is dead code post-V3-6b but kept in
    # cell_shapes.py for now. V3-6/V3-7 cleanup may remove it.
    expected = {'fin', 'axe', 'brick', 'inf', 'wave', 'hole', 'keel', 'mound'}
    assert set(SHAPE_DRAWERS.keys()) == expected


def test_rendered_svg_contains_gradient_defs():
    svg = _doc(render("550e8400-e29b-41d4-a716-446655440000"))
    gradients = svg.xpath('//*[local-name()="linearGradient"]')
    assert len(gradients) > 0


def test_gradient_stops_carry_two_colors():
    svg = _doc(render("550e8400-e29b-41d4-a716-446655440000"))
    gradients = svg.xpath('//*[local-name()="linearGradient"]')
    g = gradients[0]
    stops = g.xpath('./*[local-name()="stop"]')
    assert len(stops) == 2
    # Stops have a color attribute (stop-color) — both should be hex.
    for s in stops:
        c = s.get('stop-color') or s.get('style', '')
        assert c, f"stop missing color: {etree.tostring(s)}"


def test_edge_shape_fill_references_gradient():
    # V3-7: edges render as <use> elements (referencing shape paths
    # in <defs>). The gradient fill lives on the <use>.
    svg = _doc(render("550e8400-e29b-41d4-a716-446655440000"))
    uses = svg.xpath('//*[local-name()="use"]')
    has_gradient_fill = any(
        (el.get("fill") or "").startswith("url(#") for el in uses
    )
    assert has_gradient_fill, "no edge <use> uses a gradient fill"


def test_edgeshape_class_basics():
    fn = lambda svg, cell, edge, fill: None
    s = EdgeShape(name="test", letter="T", draw=fn)
    assert s.name == "test"
    assert s.letter == "T"
    assert s.draw is fn
