import pytest
from entviz.colors import select_visual_style, POSSIBLE_EDGE_COLORS, SHAPE_ARRAY_0, SHAPE_ARRAY_1
from entviz.entropy import Token

def test_select_visual_style_colors():
    # Median quant ends in ...01 (1) -> Gold background
    median = Token("med", 0, 0x01)
    q2 = Token("q2", 1, 0x00)
    style = select_visual_style(median, q2)
    
    assert style.bg_color == POSSIBLE_EDGE_COLORS[1] # gold
    assert len(style.edge_colors) == 4
    assert POSSIBLE_EDGE_COLORS[1] not in style.edge_colors

def test_select_visual_style_shapes_all_array0():
    # Q2 quant ends in ...0000 (0) -> All shapes from Array 0
    median = Token("med", 0, 0x00)
    q2 = Token("q2", 1, 0x00)
    style = select_visual_style(median, q2)
    
    assert style.edge_shapes == SHAPE_ARRAY_0

def test_select_visual_style_shapes_all_array1():
    # Q2 quant ends in ...1111 (15) -> All shapes from Array 1
    median = Token("med", 0, 0x00)
    q2 = Token("q2", 1, 0x0F)
    style = select_visual_style(median, q2)
    
    assert style.edge_shapes == SHAPE_ARRAY_1

def test_select_visual_style_shapes_mixed():
    # Q2 quant ends in ...1010 (10) 
    # Bit 0: 0 -> Array 0[0] (triangle)
    # Bit 1: 1 -> Array 1[1] (hammer)
    # Bit 2: 0 -> Array 0[2] (rect)
    # Bit 3: 1 -> Array 1[3] (double bars)
    median = Token("med", 0, 0x00)
    q2 = Token("q2", 1, 0x0A)
    style = select_visual_style(median, q2)
    
    expected = [
        SHAPE_ARRAY_0[0],
        SHAPE_ARRAY_1[1],
        SHAPE_ARRAY_0[2],
        SHAPE_ARRAY_1[3]
    ]
    assert style.edge_shapes == expected
