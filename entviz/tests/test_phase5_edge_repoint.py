"""
Phase 5 acceptance tests: the renderer's edge logic switches from
token.quant to ftok.quant. The nucleus background, foreground, and text
still come from token (preserving losslessness for ≤512-bit inputs);
edges, edge colors, and the XOR shifts now derive from the ftok.

Also pins the long-standing v1 latency: the last-column check for the
shape_shift→color_shift adjustment must use the *cell* index, not the
token index, since blank-cell insertion can put a token at a column
that doesn't match its token_index.

Phase 8 split render_cell into render_edges + render_nucleus. After
that split the type discipline is enforced by signature: render_edges
takes only ftok (no token), render_nucleus takes only token (no ftok).
The "token doesn't drive edges" property is now structural rather than
behavioral, but the per-method assertions below still verify each axis.
"""
from lxml import etree
import pytest

from entviz.colors import VisualStyle, SHAPE_ARRAY_0
from entviz.entropy import Token
from entviz.fingerprint import Ftok
from entviz.layout import Cell, Grid, Point, Size
from entviz.renderer import Renderer


@pytest.fixture
def basic_setup():
    style = VisualStyle(
        bg_color='#ffffff',
        edge_colors=['#ffd966', '#ff3f2f', '#2f3fbf', '#000000'],
        edge_shapes=list(SHAPE_ARRAY_0),
        shape_shift=0,
        color_shift=0,
    )
    grid = Grid(cols=2, rows=2, token_count=4)
    return Renderer(style, grid), style, grid


def test_nucleus_color_uses_token_quant(basic_setup):
    renderer, _, _ = basic_setup
    svg = etree.Element('svg')
    token = Token("ABCD", 0, 0x123456)
    cell = Cell(Point(0, 0), Size(64, 32))
    renderer.render_nucleus(svg, token, cell)
    nucleus = svg.xpath('//rect')[0]
    assert nucleus.get('fill') == '#563412'  # 0x123456 → R=0x56, G=0x34, B=0x12


def test_text_uses_token_text(basic_setup):
    renderer, _, _ = basic_setup
    svg = etree.Element('svg')
    token = Token("ABCD", 0, 0)
    cell = Cell(Point(0, 0), Size(64, 32))
    renderer.render_nucleus(svg, token, cell)
    text = svg.xpath('//text')[0]
    assert text.text == "ABCD"


def test_edge_nums_derive_from_ftok_quant():
    # Render edges with two different ftoks. The edge layer must differ.
    style = VisualStyle(
        bg_color='#ffffff',
        edge_colors=['#ffd966', '#ff3f2f', '#2f3fbf', '#000000'],
        edge_shapes=list(SHAPE_ARRAY_0),
        shape_shift=0,
        color_shift=0,
    )
    grid = Grid(cols=2, rows=2, token_count=4)
    cell = Cell(Point(0, 0), Size(64, 32))

    svg1 = etree.Element('svg')
    defs1 = etree.SubElement(svg1, 'defs')
    Renderer(style, grid).render_edges(
        svg1, defs1, Ftok("A", 0, 0x000000), cell, cell_index=0, nucleus_bg='#abcdef'
    )
    svg2 = etree.Element('svg')
    defs2 = etree.SubElement(svg2, 'defs')
    Renderer(style, grid).render_edges(
        svg2, defs2, Ftok("B", 0, 0xFFFFFF), cell, cell_index=0, nucleus_bg='#abcdef'
    )

    assert etree.tostring(svg1) != etree.tostring(svg2), (
        "ftok.quant did not affect edge rendering"
    )


def test_last_column_uses_cell_index_not_token_index(basic_setup):
    # cell_index=1 in a 2-column grid is the last column. The "if last col"
    # rules must fire based on cell_index (not the token whose .index is 0).
    renderer, _, _ = basic_setup
    svg = etree.Element('svg')
    defs = etree.SubElement(svg, 'defs')
    cell = Cell(Point(0, 0), Size(64, 32))
    renderer.render_edges(svg, defs, Ftok("X", 0, 0), cell, cell_index=1, nucleus_bg='#abcdef')
    # last col: shape_shift NEVER increments → stays 0
    # last col: color_shift += 1 per edge → 6, then += shape_shift (0) → 6
    assert renderer.shape_shift == 0
    assert renderer.color_shift == 6


def test_non_last_column_increments_shape_shift(basic_setup):
    renderer, _, _ = basic_setup
    svg = etree.Element('svg')
    defs = etree.SubElement(svg, 'defs')
    cell = Cell(Point(0, 0), Size(64, 32))
    renderer.render_edges(svg, defs, Ftok("X", 0, 0), cell, cell_index=0, nucleus_bg='#abcdef')
    assert renderer.color_shift == 6
    assert renderer.shape_shift == 6
