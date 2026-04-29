import pytest
from lxml import etree
from entviz.renderer import Renderer
from entviz.colors import VisualStyle
from entviz.layout import Grid, Cell, Point, Size
from entviz.entropy import Token

@pytest.fixture
def basic_setup():
    style = VisualStyle(
        bg_color='#ffffff',
        edge_colors=['#ffd966', '#ffdf2f', '#2f3fbf', '#000000'],
        edge_shapes=['triangle', 'hook', 'rect', 'box'],
        shape_shift=0,
        color_shift=0
    )
    grid = Grid(cols=2, rows=1, token_count=2)
    renderer = Renderer(style, grid)
    return renderer, style, grid

def test_render_cell_nucleus(basic_setup):
    renderer, style, grid = basic_setup
    svg = etree.Element('svg')
    token = Token("ABCD", 0, 0x123456)
    cell = Cell(Point(0, 0), Size(64, 32))
    
    renderer.render_cell(svg, token, cell)
    
    # Check nucleus rect
    rects = svg.xpath('//rect')
    # 1 nucleus + 6 edges = 7 rects
    assert len(rects) == 7
    
    # First rect is nucleus
    nucleus = rects[0]
    assert nucleus.get('fill') == '#563412' # 0x123456 -> R=56, G=34, B=12 in hex
    
    # Check text
    text = svg.xpath('//text')[0]
    assert text.text == "ABCD"

def test_quartile_mark_produces_circle(basic_setup):
    renderer, style, grid = basic_setup
    svg = etree.Element('svg')
    cell = Cell(Point(0, 0), Size(64, 32))
    for q in range(4):
        s = etree.Element('svg')
        renderer.draw_quartile_mark(s, cell, q)
        circles = s.xpath('//circle')
        assert len(circles) == 1, f"quartile {q} should produce exactly one circle"
        c = circles[0]
        r = float(c.get('r'))
        assert r == pytest.approx(cell.edge_height / 4)
        assert c.get('fill') == style.edge_colors[q]

def test_quartile_mark_corners(basic_setup):
    renderer, style, grid = basic_setup
    cell = Cell(Point(0, 0), Size(64, 32))
    e = cell.edge_height  # 8
    r = e / 4             # 2
    expected_centers = [
        (r, r),                             # top-left
        (cell.right - r, r),               # top-right
        (cell.right - r, cell.bottom - r), # bottom-right
        (r, cell.bottom - r),              # bottom-left
    ]
    for q, (ex, ey) in enumerate(expected_centers):
        s = etree.Element('svg')
        renderer.draw_quartile_mark(s, cell, q)
        c = s.xpath('//circle')[0]
        assert float(c.get('cx')) == pytest.approx(ex), f"q{q} cx"
        assert float(c.get('cy')) == pytest.approx(ey), f"q{q} cy"

def test_renderer_state_transitions(basic_setup):
    renderer, style, grid = basic_setup
    svg = etree.Element('svg')
    cell = Cell(Point(0, 0), Size(64, 32))
    
    # Token 0 (Col 0 of 2)
    token0 = Token("T0", 0, 0)
    renderer.render_cell(svg, token0, cell)
    
    # After 6 edges in Col 0:
    # color_shift increments 6 times -> 6
    # shape_shift increments 6 times -> 6 (since NOT last col)
    assert renderer.color_shift == 6
    assert renderer.shape_shift == 6
    
    # Token 1 (Col 1 of 2 - Last Col)
    token1 = Token("T1", 1, 0)
    renderer.render_cell(svg, token1, cell)
    
    # After 6 edges in Col 1:
    # color_shift starts at 6. Increments 6 times -> 12.
    # shape_shift starts at 6. Does NOT increment (since IS last col).
    # Finally, color_shift += shape_shift -> 12 + 6 = 18.
    assert renderer.color_shift == 18
    assert renderer.shape_shift == 6
