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
        # v4 cell aspect ratio is 3:2 (= cell_width / cell_height = 60/40 at 12pt).
        # Width = nucleus_width + 2·box_width = 10·box_width; height = nucleus_height
        # + 2·box_height = 4·box_height; nucleus_width:nucleus_height = 48:20 = 12:5.
        # Tolerance covers float drift.
        assert abs(size.width * 2 - size.height * 3) < (0.01 * size.width)
        self._invalidate_cache()
    def _invalidate_cache(self):
        super()._invalidate_cache()
        self._nucleus = None
    @property
    def box_width(self):
        """Width of every surround box. Equals cell_width/10 = nucleus_width/8.
        Derived from the horizontal tiling: 10 top-row boxes span
        nucleus_width + 2·box_width."""
        return self.size.width / 10
    @property
    def box_height(self):
        """Height of every surround box. Equals cell_height/4 = nucleus_height/2.
        Derived from the vertical tiling: 2 side-column boxes stack to
        nucleus_height."""
        return self.size.height / 4
    @property
    def nucleus(self):
        if self._nucleus is None:
            # nucleus_width = 8·box_width = cell_width × 4/5; the top row of
            # 10 boxes spans nucleus_width + 2·box_width = 10·box_width = cell_width.
            # nucleus_height = 2·box_height = cell_height / 2.
            self._nucleus = Rect(
                Point(self.left + self.box_width, self.top + self.box_height),
                Size(self.box_width * 8, self.box_height * 2),
            )
        return self._nucleus
    def box_origin(self, i: int) -> Point:
        """Top-left of surround box i (0..23), numbered clockwise from the
        top-left of the top row. Top/bottom rows have 10 boxes each;
        left/right columns have 2 boxes each. Every box is box_width ×
        box_height."""
        n = self.nucleus
        bw = self.box_width
        bh = self.box_height
        if i < 10:                                  # top row, left → right
            return Point(n.left - bw + i * bw, n.top - bh)
        if i < 12:                                  # right column, top → bottom
            return Point(n.right, n.top + (i - 10) * bh)
        if i < 22:                                  # bottom row, right → left
            return Point(n.left - bw + (21 - i) * bw, n.bottom)
        return Point(n.left - bw, n.top + (23 - i) * bh)  # left column, bottom → top


import math

Grid = namedtuple('Grid', ['cols', 'rows', 'token_count'])

def choose_grid(token_count: int, target_ar: float = 1.0) -> Grid:
    """
    Select the grid layout with at least 2 columns and 2 rows whose overall
    aspect ratio is closest to target_ar without being less than it. Each
    v4 cell has an aspect ratio of 3:2 (cell_width:cell_height = 60:40 at
    12pt), so grid AR = (cols * 3) / (rows * 2).

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
        (cols, rows, (cols * 3) / (rows * 2))
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

def assign_cell_indices(tokens: list, grid: Grid, median_token=None, sort_keys=None):
    """
    Insert up to 3 blank cells and assign final cell indices to tokens.
    Returns a mapping of token_index → cell_index.

    median_token: the item whose .index marks the first blank insertion
        point. In v2 this is the median *ftok*; in v1 it was the median
        token. Both share the (text, index, quant) shape; only .index is
        used here.
    sort_keys: optional sequence used for the "last" and "first" blank
        insertions. In v2 this is the list of used ftoks (so blanks land
        based on ftok ASCII sort, not token ASCII sort). If omitted, the
        tokens themselves are sorted (v1 behavior).
    """
    cell_indices = {t.index: t.index for t in tokens}
    cell_count = grid.cols * grid.rows
    token_count = len(tokens)

    if token_count >= cell_count or not tokens:
        return cell_indices

    def shift_from(start_token_idx):
        for t_idx in cell_indices:
            if t_idx >= start_token_idx:
                cell_indices[t_idx] += 1

    if median_token:
        shift_from(median_token.index)

    sort_source = sort_keys if sort_keys is not None else tokens
    sorted_items = sorted(sort_source, key=lambda x: (x.text, x.index))

    if token_count + 1 < cell_count:
        shift_from(sorted_items[-1].index)

    if token_count + 2 < cell_count:
        first_token = sorted_items[0]
        # Shift tokens with token_index >= first_token's index
        shift_from(first_token.index)

    return cell_indices
