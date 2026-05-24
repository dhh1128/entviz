"""
Phase 5 acceptance tests: the renderer's edge logic switches from
token.quant to ftok.quant. The nucleus background, foreground, and text
still come from token (preserving losslessness for ≤512-bit inputs);
edges, edge colors, and the XOR shifts now derive from the ftok.

Also pins the long-standing v1 latency: the last-column check for the
shape_shift→color_shift adjustment must use the *cell* index, not the
token index, since blank-cell insertion can put a token at a column
that doesn't match its token_index.
"""
from lxml import etree
import pytest

from entviz.colors import VisualStyle
from entviz.entropy import Token
from entviz.fingerprint import Ftok
from entviz.layout import Cell, Grid, Point, Size
from entviz.renderer import Renderer


@pytest.fixture
def basic_setup():
    style = VisualStyle(
        bg_color='#ffffff',
        edge_colors=['#ffd966', '#ff3f2f', '#2f3fbf', '#000000'],
        edge_shapes=['triangle', 'hook', 'rect', 'box'],
        shape_shift=0,
        color_shift=0,
    )
    grid = Grid(cols=2, rows=2, token_count=4)
    return Renderer(style, grid), style, grid


def test_nucleus_color_uses_token_quant_not_ftok_quant(basic_setup):
    renderer, _, _ = basic_setup
    svg = etree.Element('svg')
    # Distinctive token.quant produces a known nucleus color.
    token = Token("ABCD", 0, 0x123456)
    # Ftok with a totally different quant shouldn't influence the nucleus.
    ftok = Ftok("xxxx", 0, 0xFFFFFF)
    cell = Cell(Point(0, 0), Size(64, 32))
    renderer.render_cell(svg, token, ftok, cell, cell_index=0)
    nucleus = svg.xpath('//rect')[0]
    assert nucleus.get('fill') == '#563412'  # 0x123456 → R=0x56, G=0x34, B=0x12


def test_text_uses_token_text_not_ftok_text(basic_setup):
    renderer, _, _ = basic_setup
    svg = etree.Element('svg')
    token = Token("ABCD", 0, 0)
    ftok = Ftok("ZZZZ", 0, 0)
    cell = Cell(Point(0, 0), Size(64, 32))
    renderer.render_cell(svg, token, ftok, cell, cell_index=0)
    text = svg.xpath('//text')[0]
    assert text.text == "ABCD"


def test_edge_nums_derive_from_ftok_quant():
    # Render the same token with two different ftoks. With ftok-driven edge
    # extraction, the edge layer (shapes, colors) must differ. With v1
    # behavior (token.quant drives edges) the two outputs would be identical
    # because token.quant is the same.
    style = VisualStyle(
        bg_color='#ffffff',
        edge_colors=['#ffd966', '#ff3f2f', '#2f3fbf', '#000000'],
        edge_shapes=['triangle', 'hook', 'rect', 'box'],
        shape_shift=0,
        color_shift=0,
    )
    grid = Grid(cols=2, rows=2, token_count=4)
    cell = Cell(Point(0, 0), Size(64, 32))
    token = Token("Z", 0, 0)

    svg1 = etree.Element('svg')
    Renderer(style, grid).render_cell(
        svg1, token, Ftok("A", 0, 0x000000), cell, cell_index=0
    )
    svg2 = etree.Element('svg')
    Renderer(style, grid).render_cell(
        svg2, token, Ftok("B", 0, 0xFFFFFF), cell, cell_index=0
    )

    # Compare child element counts and any non-nucleus element attributes.
    # Different ftoks must produce different shape/color choices.
    s1 = etree.tostring(svg1).decode()
    s2 = etree.tostring(svg2).decode()
    assert s1 != s2, "ftok.quant did not affect edge rendering"


def test_token_quant_does_not_drive_edges():
    # Inverse check: holding ftok.quant constant while varying token.quant
    # must not change edge colors/shapes. Build two fresh renderers so the
    # XOR-shift state starts identical for both calls.
    style = VisualStyle(
        bg_color='#ffffff',
        edge_colors=['#ffd966', '#ff3f2f', '#2f3fbf', '#000000'],
        edge_shapes=['triangle', 'hook', 'rect', 'box'],
        shape_shift=0,
        color_shift=0,
    )
    grid = Grid(cols=2, rows=2, token_count=4)
    cell = Cell(Point(0, 0), Size(64, 32))
    ftok = Ftok("F", 0, 0xABCDEF)

    svg_a = etree.Element('svg')
    Renderer(style, grid).render_cell(
        svg_a, Token("A", 0, 0x000000), ftok, cell, cell_index=0
    )
    svg_b = etree.Element('svg')
    Renderer(style, grid).render_cell(
        svg_b, Token("B", 0, 0xFFFFFF), ftok, cell, cell_index=0
    )

    edges_a = [r.get('fill') for r in svg_a.xpath('//rect')[1:]]
    edges_b = [r.get('fill') for r in svg_b.xpath('//rect')[1:]]
    assert edges_a == edges_b


def test_last_column_uses_cell_index_not_token_index(basic_setup):
    # Token at token_index 0 but rendered at cell_index 1 (last column in a
    # 2-col grid because a blank shifted it). The end-of-cell adjustment
    # "color_shift += shape_shift" must fire because the *cell* is in the
    # last column, even though the token thinks it isn't.
    renderer, _, _ = basic_setup
    svg = etree.Element('svg')
    token = Token("X", 0, 0)
    ftok = Ftok("X", 0, 0)
    cell = Cell(Point(0, 0), Size(64, 32))
    renderer.render_cell(svg, token, ftok, cell, cell_index=1)

    # In a last-column cell with both shifts starting at 0:
    # - color_shift increments 6 times → 6
    # - shape_shift does NOT increment (last col) → 0
    # - After all 6 edges, color_shift += shape_shift → 6 + 0 = 6.
    # The key check: shape_shift stayed at 0 (not incremented because last col).
    assert renderer.shape_shift == 0
    assert renderer.color_shift == 6


def test_non_last_column_increments_shape_shift(basic_setup):
    # Token at cell_index 0 (col 0 of 2, not last). shape_shift should
    # increment 6 times.
    renderer, _, _ = basic_setup
    svg = etree.Element('svg')
    token = Token("X", 0, 0)
    ftok = Ftok("X", 0, 0)
    cell = Cell(Point(0, 0), Size(64, 32))
    renderer.render_cell(svg, token, ftok, cell, cell_index=0)
    assert renderer.color_shift == 6
    assert renderer.shape_shift == 6
