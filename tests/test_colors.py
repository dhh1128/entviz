from entviz.colors import *
import math

def test_relative_luminance():
    def assert_rlum(r, g, b, expected):
        assert math.isclose(relative_luminance((r, g, b)), expected, rel_tol=1e-2)
        
    # Test case 1: Check luminance for black color
    assert_rlum(0, 0, 0, 0.0)

    # Test case 2: Check luminance for white color
    assert_rlum(255, 255, 255, 1.0)

    # Test case 3: Check luminance for gray color
    assert_rlum(128, 128, 128, 0.2158)

    # Test case 4: Check luminance for red color
    assert_rlum(255, 0, 0, 0.2126)

    # Test case 5: Check luminance for green color
    assert_rlum(0, 255, 0, 0.7152)

    # Test case 6: Check luminance for blue color
    assert_rlum(0, 0, 255, 0.0722)
    
    # Test case 7: Check luminance for custom color
    assert_rlum(100, 200, 50, 0.4424)

    # Test case 8: Check luminance for another custom color
    assert_rlum(150, 100, 75, 0.1611)

