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

def test_select_visual_style_uses_lsb_only():
    # v3: only the LSB of the second quartile ftok's quant matters for
    # shape selection. Bits 1-3 are unused (reserved). Both q2 quants
    # below have LSB=0, so the result is always the cubist set (array 0),
    # regardless of the upper bits.
    median = Token("med", 0, 0x00)
    for q2_quant in (0x00, 0x02, 0x04, 0x0E, 0xFFFFFE):
        style = select_visual_style(median, Token("q2", 1, q2_quant))
        assert style.edge_shapes == SHAPE_ARRAY_0, (
            f"q2.quant=0x{q2_quant:x} (LSB=0) should pick cubist, "
            f"got {[s.name for s in style.edge_shapes]}"
        )

    # Mirror: any LSB=1 quant should pick the polygon set entirely.
    for q2_quant in (0x01, 0x03, 0x05, 0x0F, 0xFFFFFF):
        style = select_visual_style(median, Token("q2", 1, q2_quant))
        assert style.edge_shapes == SHAPE_ARRAY_1, (
            f"q2.quant=0x{q2_quant:x} (LSB=1) should pick polygon, "
            f"got {[s.name for s in style.edge_shapes]}"
        )


def test_select_visual_style_never_mixes_cubist_and_polygon():
    # No selection bits should ever produce a mix of cubist + polygon
    # shapes in a single entviz.
    median = Token("med", 0, 0x00)
    cubist_names = {s.name for s in SHAPE_ARRAY_0}
    polygon_names = {s.name for s in SHAPE_ARRAY_1}
    for q in range(256):
        style = select_visual_style(median, Token("q2", 1, q))
        names = {s.name for s in style.edge_shapes}
        is_cubist = names <= cubist_names
        is_polygon = names <= polygon_names
        assert is_cubist or is_polygon, (
            f"q2.quant=0x{q:02x} produced a mixed set: {names}"
        )
