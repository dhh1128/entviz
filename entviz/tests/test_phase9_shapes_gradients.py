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


def test_shape_names_are_v2():
    names0 = [s.name for s in SHAPE_ARRAY_0]
    names1 = [s.name for s in SHAPE_ARRAY_1]
    assert names0 == ['fin', 'axe', 'brick', 'inf']
    assert names1 == ['wave', 'hole', 'keel', 'mound']


def test_v1_shape_names_are_gone():
    names0 = [s.name for s in SHAPE_ARRAY_0]
    names1 = [s.name for s in SHAPE_ARRAY_1]
    for old in ['triangle', 'hook', 'rect', 'box', 'slant', 'hammer', 'pyramid', 'double bars']:
        assert old not in names0 + names1


def test_shape_letters_unique_and_distinct():
    letters = [s.letter for s in SHAPE_ARRAY_0 + SHAPE_ARRAY_1]
    assert letters == ['F', 'A', 'B', 'I', 'W', 'H', 'K', 'M']
    assert len(set(letters)) == 8


def test_each_edgeshape_has_drawer():
    for s in SHAPE_ARRAY_0 + SHAPE_ARRAY_1:
        assert callable(s.draw)


def test_shape_drawers_registry_has_v2_keys():
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
    # At least one rect or polygon in the rendered SVG should have a fill
    # of the form url(#...) — i.e., a gradient reference.
    svg = _doc(render("550e8400-e29b-41d4-a716-446655440000"))
    all_shapes = svg.xpath('//*[local-name()="rect" or local-name()="polygon"]')
    has_gradient_fill = any(
        (el.get("fill") or "").startswith("url(#") for el in all_shapes
    )
    assert has_gradient_fill, "no shape uses a gradient fill"


def test_edgeshape_class_basics():
    fn = lambda svg, cell, edge, fill: None
    s = EdgeShape(name="test", letter="T", draw=fn)
    assert s.name == "test"
    assert s.letter == "T"
    assert s.draw is fn
