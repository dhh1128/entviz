import pytest
from lxml import etree
from entviz.cell_shapes import draw_edge_shape, SHAPE_DRAWERS
from entviz.layout import Cell, Point, Size
from entviz.shapes import canvas

CELL_SIZE = Size(64, 32)  # standard 2:1 cell at nucleus_height=16

def make_cell():
    return Cell(Point(0, 0), CELL_SIZE)

def make_svg():
    return canvas(Size(200, 100))

def count_elements(svg, tag):
    return len(svg.xpath(f'//{tag}'))

def test_all_shapes_known():
    assert set(SHAPE_DRAWERS.keys()) == {
        'fin', 'axe', 'brick', 'inf', 'wave', 'hole', 'keel', 'mound'
    }

def test_unknown_shape_raises():
    cell = make_cell()
    svg = make_svg()
    with pytest.raises(ValueError):
        draw_edge_shape(svg, cell, 0, 'unknown', '#ff0000')

@pytest.mark.parametrize("shape,edge", [
    (shape, edge)
    for shape in ['fin', 'axe', 'brick', 'inf', 'wave', 'hole', 'keel', 'mound']
    for edge in range(6)
])
def test_shape_produces_elements(shape, edge):
    """Every shape/edge combination should produce at least one SVG element."""
    cell = make_cell()
    svg = make_svg()
    draw_edge_shape(svg, cell, edge, shape, '#aabbcc')
    total = count_elements(svg, 'rect') + count_elements(svg, 'polygon') + count_elements(svg, 'circle')
    assert total >= 1, f"{shape} edge {edge} produced no elements"

@pytest.mark.parametrize("edge", range(6))
def test_triangle_is_polygon(edge):
    cell = make_cell()
    svg = make_svg()
    draw_edge_shape(svg, cell, edge, 'fin', '#ff0000')
    assert count_elements(svg, 'polygon') == 1

@pytest.mark.parametrize("edge", range(6))
def test_brick_is_single_rect(edge):
    cell = make_cell()
    svg = make_svg()
    draw_edge_shape(svg, cell, edge, 'brick', '#ff0000')
    assert count_elements(svg, 'rect') == 1

@pytest.mark.parametrize("edge", range(6))
def test_box_is_single_rect(edge):
    cell = make_cell()
    svg = make_svg()
    draw_edge_shape(svg, cell, edge, 'inf', '#ff0000')
    assert count_elements(svg, 'rect') == 1

@pytest.mark.parametrize("edge", range(6))
def test_hook_is_two_rects(edge):
    cell = make_cell()
    svg = make_svg()
    draw_edge_shape(svg, cell, edge, 'axe', '#ff0000')
    assert count_elements(svg, 'rect') == 2

@pytest.mark.parametrize("edge", range(6))
def test_slant_is_two_polygons(edge):
    cell = make_cell()
    svg = make_svg()
    draw_edge_shape(svg, cell, edge, 'wave', '#ff0000')
    assert count_elements(svg, 'polygon') == 2

@pytest.mark.parametrize("edge", range(6))
def test_hammer_is_two_rects(edge):
    cell = make_cell()
    svg = make_svg()
    draw_edge_shape(svg, cell, edge, 'hole', '#ff0000')
    assert count_elements(svg, 'rect') == 2

@pytest.mark.parametrize("edge", range(6))
def test_double_bars_is_two_rects(edge):
    cell = make_cell()
    svg = make_svg()
    draw_edge_shape(svg, cell, edge, 'mound', '#ff0000')
    assert count_elements(svg, 'rect') == 2

@pytest.mark.parametrize("edge", [0, 1, 3, 4])
def test_pyramid_horiz_has_two_polygons_and_one_rect(edge):
    cell = make_cell()
    svg = make_svg()
    draw_edge_shape(svg, cell, edge, 'keel', '#ff0000')
    assert count_elements(svg, 'polygon') == 2
    assert count_elements(svg, 'rect') == 1

@pytest.mark.parametrize("edge", [2, 5])
def test_pyramid_vert_has_two_polygons(edge):
    cell = make_cell()
    svg = make_svg()
    draw_edge_shape(svg, cell, edge, 'keel', '#ff0000')
    assert count_elements(svg, 'polygon') == 2

def test_box_is_centered():
    """The box should be centered within the edge rect."""
    cell = make_cell()
    svg = make_svg()
    draw_edge_shape(svg, cell, 0, 'inf', '#ff0000')
    rect_el = svg.xpath('//rect')[0]
    e = cell.edge_height
    er = cell.edge_rect(0)
    # x of box should be centered in edge rect
    expected_x = er.left + (er.size.width - e) / 2
    expected_y = er.top + (er.size.height - e) / 2
    assert float(rect_el.get('x')) == pytest.approx(expected_x)
    assert float(rect_el.get('y')) == pytest.approx(expected_y)
    assert float(rect_el.get('width')) == pytest.approx(e)
    assert float(rect_el.get('height')) == pytest.approx(e)

def test_fill_color_applied():
    """Shapes should use the provided fill color."""
    cell = make_cell()
    for shape in SHAPE_DRAWERS:
        svg = make_svg()
        draw_edge_shape(svg, cell, 0, shape, '#123456')
        fills = [el.get('fill') for el in svg.iter() if el.get('fill')]
        assert all(f == '#123456' for f in fills), f"{shape} has wrong fill"
