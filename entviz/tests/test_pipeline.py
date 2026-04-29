import pytest
from lxml import etree
from entviz.pipeline import render

# A 256-bit hex string (32 bytes = 11 base64 tokens)
HEX_256 = "deadbeef" * 8

# A UUID
UUID = "550e8400-e29b-41d4-a716-446655440000"

# A short base64-ish string (unknown type → generic base64 encoding path)
UNKNOWN = "notrecognized12345"


def parse_svg(svg_str: str) -> etree.Element:
    return etree.fromstring(svg_str.encode())


def test_render_returns_svg_string():
    result = render(HEX_256)
    assert isinstance(result, str)
    assert result.startswith('<svg')


def test_render_svg_has_width_and_height():
    result = render(HEX_256)
    svg = parse_svg(result)
    assert float(svg.get('width')) > 0
    assert float(svg.get('height')) > 0


def test_render_contains_text_tokens():
    result = render(HEX_256)
    svg = parse_svg(result)
    texts = svg.xpath('//*[local-name()="text"]')
    assert len(texts) > 0


def test_render_contains_nucleus_rects():
    result = render(HEX_256)
    svg = parse_svg(result)
    rects = svg.xpath('//*[local-name()="rect"]')
    # background rect + nucleus rects at minimum
    assert len(rects) >= 2


def test_render_contains_quartile_circles():
    result = render(HEX_256)
    svg = parse_svg(result)
    circles = svg.xpath('//*[local-name()="circle"]')
    # At most 4 quartile marks (some tokens may share quartile slots)
    assert 1 <= len(circles) <= 4


def test_render_uuid():
    result = render(UUID)
    svg = parse_svg(result)
    texts = svg.xpath('//*[local-name()="text"]')
    assert len(texts) > 0


def test_render_unknown_type():
    result = render(UNKNOWN)
    assert isinstance(result, str)
    svg = parse_svg(result)
    assert float(svg.get('width')) > 0


def test_render_aspect_ratio_landscape():
    result_square = render(HEX_256, target_ar=1.0)
    result_wide = render(HEX_256, target_ar=3.0)
    sq = parse_svg(result_square)
    wd = parse_svg(result_wide)
    sq_ar = float(sq.get('width')) / float(sq.get('height'))
    wd_ar = float(wd.get('width')) / float(wd.get('height'))
    assert wd_ar >= sq_ar


def test_render_font_size_affects_dimensions():
    small = parse_svg(render(HEX_256, font_size_pt=8))
    large = parse_svg(render(HEX_256, font_size_pt=16))
    assert float(large.get('width')) > float(small.get('width'))
    assert float(large.get('height')) > float(small.get('height'))


def test_different_entropy_produces_different_output():
    a = render("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    b = render("bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb")
    assert a != b


def test_background_rect_uses_style_color():
    result = render(HEX_256)
    svg = parse_svg(result)
    # First rect should be the background
    first_rect = svg.xpath('//*[local-name()="rect"]')[0]
    fill = first_rect.get('fill')
    from entviz.colors import POSSIBLE_EDGE_COLORS
    assert fill in POSSIBLE_EDGE_COLORS
