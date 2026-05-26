import math
import pytest
from entviz.layout import choose_grid, Grid


def test_choose_grid_11_tokens_1to1():
    # Spec example unchanged in v2: 11 tokens, 1:1 target → 3x4 (6:4 ratio).
    grid = choose_grid(11, 1.0)
    assert grid.cols == 3
    assert grid.rows == 4
    assert grid.token_count == 11


def test_choose_grid_exact_match():
    # 8 tokens, 1:1 target. v4 cells are 3:2 (not 2:1), so candidates are:
    #   2x4 → 6:8 = 0.75 (below 1.0, rejected)
    #   3x3 → 9:6 = 1.5  (above 1.0 → picked: closest from above)
    #   4x2 → 12:4 = 3.0
    grid = choose_grid(8, 1.0)
    assert grid.cols == 3
    assert grid.rows == 3


def test_choose_grid_never_picks_taller_than_target():
    """Spec: chosen grid AR must NOT be less than the target (unless no
    above-target candidate exists, in which case the widest is picked).
    With v4 cell AR 3:2, grid AR = (cols * 3) / (rows * 2)."""
    for n in range(3, 23):
        for target in [0.5, 1.0, 1.5, 2.0]:
            grid = choose_grid(n, target)
            grid_ar = (grid.cols * 3) / (grid.rows * 2)
            # Build the set of all valid 2x2+ candidate ratios for n.
            candidate_ars = []
            for rows in range(2, n + 1):
                cols = math.ceil(n / rows)
                if cols >= 2:
                    candidate_ars.append((cols * 3) / (rows * 2))
            if any(ar >= target for ar in candidate_ars):
                assert grid_ar >= target, (
                    f"n={n} target={target} → {grid} (AR {grid_ar:.3f}) "
                    f"is below target but an above-target candidate exists"
                )


def test_choose_grid_high_ar_falls_back_to_widest():
    # 11 tokens, 20:1 target. With 2x2 minimum, the widest valid layout is
    # 6x2 (6:1); none reach 20:1. v2 falls back to the widest available
    # rather than returning a 1-row grid as v1 did.
    grid = choose_grid(11, 20.0)
    assert grid.cols == 6
    assert grid.rows == 2


def test_choose_grid_low_ar_uses_tallest_valid_layout():
    # 11 tokens, 0.1:1 target. Among 2x2-min layouts the tallest is 2x6
    # (0.67:1), which is the closest valid ratio above the target.
    grid = choose_grid(11, 0.1)
    assert grid.cols == 2
    assert grid.rows == 6


def test_grid_never_has_single_row():
    for n in range(1, 23):
        for target in [0.1, 0.5, 1.0, 2.0, 5.0, 20.0]:
            grid = choose_grid(n, target)
            assert grid.rows >= 2, f"token_count={n} target={target} → rows={grid.rows}"


def test_grid_never_has_single_column():
    for n in range(1, 23):
        for target in [0.1, 0.5, 1.0, 2.0, 5.0, 20.0]:
            grid = choose_grid(n, target)
            assert grid.cols >= 2, f"token_count={n} target={target} → cols={grid.cols}"


def test_single_token_forces_2x2_grid():
    # 1 token alone has no natural multi-cell layout; v2 forces 2x2
    # (which will end up with blank cells).
    grid = choose_grid(1, 1.0)
    assert grid.cols == 2
    assert grid.rows == 2


def test_two_tokens_forces_2x2_grid():
    # 2 tokens could naively map to 2x1 or 1x2 (both invalid in v2).
    grid = choose_grid(2, 1.0)
    assert grid.cols == 2
    assert grid.rows == 2


def test_three_tokens_uses_2x2_grid():
    # 3 tokens fit in a 2x2 grid with 1 blank cell. The only other 2x2-min
    # layout would be 3x2 (6 cells, half empty) which is much further from 1:1.
    grid = choose_grid(3, 1.0)
    assert grid.cols == 2
    assert grid.rows == 2


def test_22_tokens_at_target_1():
    # Boundary: token_count at the v2 cap. Valid layouts include 2x11, 3x8,
    # 4x6, 5x5, 6x4, 7x4, 8x3, 11x2 — pick the one closest to 1:1 not below.
    grid = choose_grid(22, 1.0)
    # Ratios: 11x2 = 11/1 wait let me recompute. cell_w = 2*cell_h, so grid AR = (cols*2)/rows.
    # cols=5, rows=ceil(22/5)=5 → ar=10/5=2.0
    # cols=4, rows=ceil(22/4)=6 → ar=8/6=1.33
    # cols=3, rows=ceil(22/3)=8 → ar=6/8=0.75
    # 1.33 is closest to 1.0 from above → 4x6.
    assert (grid.cols, grid.rows) == (4, 6)
