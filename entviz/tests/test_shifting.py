import pytest
from entviz.layout import assign_cell_indices, Grid
from entviz.entropy import Token

def test_shifting_no_blanks():
    # 4 tokens, 2x2 grid (4 cells). No shifts.
    tokens = [Token(str(i), i, 0) for i in range(4)]
    grid = Grid(2, 2, 4)
    indices = assign_cell_indices(tokens, grid)
    for i in range(4):
        assert indices[i] == i

def test_shifting_one_blank():
    # 3 tokens, 2x2 grid (4 cells). 1 blank.
    # Tokens: T0, T1, T2. Median is T1.
    # Shift 1 at T1: T0 -> 0, T1 -> 2, T2 -> 3. (Cell 1 is blank)
    tokens = [Token(str(i), i, 0) for i in range(3)]
    median = tokens[1]
    grid = Grid(2, 2, 3)
    indices = assign_cell_indices(tokens, grid, median_token=median)
    assert indices[0] == 0
    assert indices[1] == 2
    assert indices[2] == 3

def test_shifting_three_blanks():
    # 3 tokens, 3x2 grid (6 cells). 3 blanks.
    # Tokens: T0, T1, T2. 
    # Sorted: T0, T1, T2.
    # Median: T1.
    # Shift 1 (Median T1): T0=0, T1=2, T2=3
    # Shift 2 (Final T2): T0=0, T1=2, T2=4 (Cell 3 is blank)
    # Shift 3 (First T0): T0=1, T1=3, T2=5 (Cell 0 is blank)
    tokens = [Token(str(i), i, 0) for i in range(3)]
    median = tokens[1]
    grid = Grid(3, 2, 3)
    indices = assign_cell_indices(tokens, grid, median_token=median)
    # Final cell indices:
    # Cell 0: Blank (Shift 3)
    # Cell 1: T0
    # Cell 2: Blank (Shift 1)
    # Cell 3: T1
    # Cell 4: Blank (Shift 2)
    # Cell 5: T2
    assert indices[0] == 1
    assert indices[1] == 3
    assert indices[2] == 5
