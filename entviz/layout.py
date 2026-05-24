from collections import namedtuple

Point = namedtuple('Point', ['x', 'y'])
Size = namedtuple('Size', ['width', 'height'])

Point.__str__ = lambda self: f'{self.x},{self.y}'

class Rect:
    def __init__(self, top_left: Point, size: Size):
        self.top_left = top_left
        self.size = size
        self._invalidate_cache()
    def __eq__(self, other):
        if isinstance(other, Rect):
            return self.top_left == other.top_left and self.size == other.size
        return False
    def __ne__(self, value: object) -> bool:
        return not self.__eq__(value)
    @property
    def bottom_right(self):
        if self._br is None:
            self._br = Point(self.top_left.x + self.size.width, self.top_left.y + self.size.height)
        return self._br
    @property
    def top_right(self):
        if self._tr is None:
            self._tr = Point(self.top_left.x + self.size.width, self.top_left.y)
        return self._tr
    @property
    def bottom_left(self):
        if self._bl is None:
            self._bl = Point(self.top_left.x, self.top_left.y + self.size.height)
        return self._bl
    @property
    def left(self):
        return self.top_left.x
    @property
    def top(self):
        return self.top_left.y
    @property
    def right(self):
        return self.left + self.size.width
    @property
    def bottom(self):
        return self.top + self.size.height
    @property
    def center(self):
        if self._c is None:
            self._c = Point(self.top_left.x + self.size.width / 2, self.top_left.y + self.size.height / 2)
        return self._c
    def _invalidate_cache(self):
        self._br = None
        self._tr = None
        self._bl = None
        self._c = None
    def lhalign_to(self, other: 'Rect'):
        self.top_left = Point(other.left, self.top)
        self._invalidate_cache()
    def rhalign_to(self, other: 'Rect'):
        self.top_left = Point(other.right - self.size.width, self.top)
        self._invalidate_cache()
    def tvalign_to(self, other: 'Rect'):
        self.top_left = Point(self.left, other.top)
        self._invalidate_cache()
    def bvalign_to(self, other: 'Rect'):
        self.top_left = Point(self.left, other.bottom - self.size.height)
        self._invalidate_cache()
    
class Cell(Rect):
    def __init__(self, top_left: Point, size: Size):
        super().__init__(top_left, size)
        # We should have an aspect ratio of 2:1, but allow for some rounding error.
        assert size.width - (size.height * 2) < (0.01 * size.width)
        self._invalidate_cache()
    def _invalidate_cache(self):
        super()._invalidate_cache()
        self._nucleus = None
        self._e0134_size = None
        self._e25_size = None
        self._edge_rects = [None] * 6
    @property
    def edge_height(self):
        return self.size.height / 4
    @property
    def edge_width(self):
        return self.edge_height
    @property
    def edge_0134_size(self):
        if self._e0134_size is None:
            self._e0134_size = Size(self.nucleus.size.width / 2, self.edge_height)
        return self._e0134_size
    @property
    def edge_25_size(self):
        if self._e25_size is None:
            self._e25_size = Size(self.edge_width, self.nucleus.size.height)
        return self._e25_size
    @property
    def nucleus(self):
        if self._nucleus is None:
            height = self.edge_height * 2
            width = self.edge_width * 6
            self._nucleus = Rect(
                    Point(self.left + self.edge_width, 
                          self.top + self.edge_height), 
                    Size(width, height))
        return self._nucleus
    def edge_rect(self, edge: int):
        n = self.nucleus
        r = self._edge_rects[edge]
        if not r:
            if edge == 0:
                r = Rect(Point(n.left, self.top), self.edge_0134_size)
            elif edge == 1:
                r = Rect(Point(self.center.x, self.top), self.edge_0134_size)
            elif edge == 2:
                r = Rect(n.top_right, self.edge_25_size)
            elif edge == 3:
                r = Rect(Point(self.center.x, self.nucleus.bottom), self.edge_0134_size)
            elif edge == 4:
                r = Rect(Point(n.left, self.nucleus.bottom), self.edge_0134_size)
            elif edge == 5:
                r = Rect(Point(self.left, n.top), self.edge_25_size)
            else:
                raise ValueError("Edge must be 0 to 5")
            self._edge_rects[edge] = r
        return r


import math

Grid = namedtuple('Grid', ['cols', 'rows', 'token_count'])

def choose_grid(token_count: int, target_ar: float = 1.0) -> Grid:
    """
    Select the grid layout with at least 2 columns and 2 rows whose overall
    aspect ratio is closest to target_ar without being less than it. Each
    cell has an aspect ratio of 2:1, so grid AR = (cols * 2) / rows.

    If no 2x2+ layout achieves the target ratio (e.g., target_ar=20 with
    only 11 tokens), fall back to the widest available layout. If
    token_count is so small that no natural 2x2+ layout exists at all
    (1 or 2 tokens), force a 2x2 grid; the extra cells become blanks.
    """
    # For each row count, keep only the smallest cols that fits — i.e., the
    # "tight" layout. Without this, target ratios above all achievable values
    # would pick wasteful layouts like 10x2 for 11 tokens (9 blanks for an
    # ar of 10) instead of 6x2 (ar of 6, only 1 blank). The spec's worked
    # example for 11 tokens lists 6x2, 4x3, 3x4, 2x6 — the tight set.
    tightest_cols_for_rows = {}
    for cols in range(2, token_count + 1):
        rows = math.ceil(token_count / cols)
        if rows < 2:
            continue
        if rows not in tightest_cols_for_rows or cols < tightest_cols_for_rows[rows]:
            tightest_cols_for_rows[rows] = cols

    candidates = [
        (cols, rows, (cols * 2) / rows)
        for rows, cols in tightest_cols_for_rows.items()
    ]

    if not candidates:
        return Grid(2, 2, token_count)

    above = [c for c in candidates if c[2] >= target_ar]
    if above:
        cols, rows, _ = min(above, key=lambda c: c[2] - target_ar)
    else:
        cols, rows, _ = max(candidates, key=lambda c: c[2])
    return Grid(cols, rows, token_count)

def assign_cell_indices(tokens: list, grid: Grid, median_token=None):
    """
    Step 7: Insert blank cells and assign final cell indices to tokens.
    Returns a mapping of token_index to cell_index.
    """
    cell_indices = {t.index: t.index for t in tokens}
    cell_count = grid.cols * grid.rows
    token_count = len(tokens)
    
    if token_count >= cell_count or not tokens:
        return cell_indices

    # Helper to shift all tokens starting from a specific token_index
    def shift_from(start_token_idx):
        for t_idx in cell_indices:
            if t_idx >= start_token_idx:
                cell_indices[t_idx] += 1

    # Shift 1: Median token
    if median_token:
        shift_from(median_token.index)
    
    # Shift 2: Final token in sorted list
    if token_count + 1 < cell_count:
        sorted_tokens = sorted(tokens, key=lambda t: (t.text, t.index))
        final_token = sorted_tokens[-1]
        # Shift tokens with token_index >= final_token's index
        shift_from(final_token.index)

    # Shift 3: First token in sorted list
    if token_count + 2 < cell_count:
        sorted_tokens = sorted(tokens, key=lambda t: (t.text, t.index))
        first_token = sorted_tokens[0]
        # Shift tokens with token_index >= first_token's index
        shift_from(first_token.index)

    return cell_indices
