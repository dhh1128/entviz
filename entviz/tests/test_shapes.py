from ..shapes import *
from ..layout import Size, Point, Rect

SIZE_300x200 = Size(300, 200)

def std_canvas():
    return canvas(SIZE_300x200)

def std_square():
    return Rect(Point(100, 100), Size(50, 50))

def assert_xml(el, *expected):
    xml = etree.tostring(el, encoding='utf-8').decode('utf-8')
    for item in expected:
        assert item in xml

def test_canvas():
    assert_xml(std_canvas(),
        "<svg", 'width="300', 'height="200', 'xmlns="http://')

def test_circle():
    assert_xml(circle(std_canvas(), std_square(), "blue"), 
        "<circle", 'cx="125', 'cy="125', 'r="25', 'fill="blue')

def test_rect():
    assert_xml(rect(std_canvas(), std_square(), "red"), 
        "<rect", 'x="100', 'y="100', 'width="50', 'height="50', 'fill="red')

# right_triangle was retired in v4 (no longer needed once v3 edge shapes
# went away). Test removed.
