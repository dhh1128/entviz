import pytest
from entviz.layout import choose_grid, Grid

def test_choose_grid_11_tokens_1to1():
    # Spec example: 11 tokens, 1:1 target.
    # Options: 
    # 11x1 (22:1)
    # 6x2 (12:2 = 6:1)
    # 4x3 (8:3 = 2.66:1)
    # 3x4 (6:4 = 1.5:1) <--- Closest >= 1:1
    # 2x6 (4:6 = 0.66:1)
    # 1x11 (2:11 = 0.18:1)
    grid = choose_grid(11, 1.0)
    assert grid.cols == 3
    assert grid.rows == 4
    assert grid.token_count == 11

def test_choose_grid_exact_match():
    # 8 tokens, 1:1 target.
    # 4x2 grid = 8:2 = 4:1
    # 3x3 grid (9 cells) = 6:3 = 2:1
    # 2x4 grid = 4:4 = 1:1 <--- Exact match
    grid = choose_grid(8, 1.0)
    assert grid.cols == 2
    assert grid.rows == 4

def test_choose_grid_high_ar():
    # 11 tokens, 20:1 target.
    # 11x1 is 22:1, which is >= 20.
    grid = choose_grid(11, 20.0)
    assert grid.cols == 11
    assert grid.rows == 1

def test_choose_grid_low_ar():
    # 11 tokens, 0.1:1 target.
    # 1x11 is 0.18:1, which is >= 0.1.
    grid = choose_grid(11, 0.1)
    assert grid.cols == 1
    assert grid.rows == 11
