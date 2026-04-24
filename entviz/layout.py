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
    Select the grid layout that produces an overall rectangle with an aspect 
    ratio closest to the target, without being less than the target.
    Each cell has an aspect ratio of 2:1.
    """
    best_grid = None
    min_diff = float('inf')

    # Possible column counts range from 1 to token_count.
    for cols in range(1, token_count + 1):
        rows = math.ceil(token_count / cols)
        
        # Grid AR = (cols * cell_width) / (rows * cell_height)
        # Since cell_width = 2 * cell_height:
        # Grid AR = (cols * 2) / rows
        current_ar = (cols * 2) / rows
        
        if current_ar >= target_ar:
            diff = current_ar - target_ar
            # We want the one closest to target_ar (smallest diff)
            # The spec says "closest ... without being less than".
            if diff <= min_diff:
                min_diff = diff
                best_grid = Grid(cols, rows, token_count)
                
    return best_grid
