"""
V3 edge shape data: cubist and polygon shape sets.

Each shape is authored in a 24×8 canonical edge space:
  - x runs along the edge (0..24)
  - y=0 is the OUTER boundary (cell perimeter), y=8 is INNER (nucleus side)

The full path applies to upright slots (edges 0/1 and, via 180° rotation,
edges 3/4). Rotated slots (edges 2/5) use a tab — the part of the shape
within a 16-wide window — pivoted around the hinge. Tab path emission is
implemented in V3-6b; this module captures the canonical full-path data
plus the window/hinge metadata that V3-6b needs.

Empty members (C4, P4) are valid renderable members of their sets:
selecting them means render nothing in that slot. They still participate
in shape-count bookkeeping (color/SCS tallies).

The fill is always a `nucleus_bg → edge_color` linear gradient (the
locked v2 color model; see spec-improvement-notes.md item 4 Q1). All
paths require `fill-rule="evenodd"` to correctly resolve holes (C2),
detached pieces (C1, C3, P3), and self-touching outlines (P2).
"""


class V3EdgeShape:
    """
    v3 edge shape: canonical SVG path data + tab/hinge metadata.

    Distinct from v2's `EdgeShape` (which carries a `draw` callable for
    procedural primitive emission). v3 emits a single `<path>` per drawn
    edge with the path_d below, transformed appropriately for the edge.
    """
    __slots__ = ('name', 'slot', 'is_empty', 'path_d', 'window', 'hinge')

    def __init__(self, name, slot, is_empty, path_d, window, hinge):
        self.name = name
        self.slot = slot
        self.is_empty = is_empty
        self.path_d = path_d  # None for empty members
        self.window = window  # (left, right) in canonical coords; used for tab
        self.hinge = hinge    # (x, y) pivot for 90°/270° rotation

    def __repr__(self):
        return f"V3EdgeShape({self.name!r}, slot={self.slot}, is_empty={self.is_empty})"

    def __eq__(self, other):
        return isinstance(other, V3EdgeShape) and self.name == other.name

    def __hash__(self):
        return hash(self.name)


# All v3 shapes use fill-rule="evenodd" so holes, pieces, and self-
# touching paths resolve in a single <path>.
V3_FILL_RULE = "evenodd"


# ----- Cubist set -----------------------------------------------------------

# C1: main polygon (forked posts on left) + two detached square pieces.
# No holes; all three subpaths are "additive" under evenodd.
_C1_D = (
    "M0,8 L0,6 L2,6 L2,0 L8,0 L8,8 L6,8 L6,4 L4,4 L4,8 Z "
    "M12,4 L14,4 L14,8 L12,8 Z "
    "M22,4 L24,4 L24,8 L22,8 Z"
)

# C2: main polygon (heavy outer block on right) + two rectangular holes.
# Holes use evenodd-subtractive subpaths.
_C2_D = (
    "M0,8 L0,2 L4,2 L4,4 L6,4 L6,8 L10,8 L10,2 L10,0 L24,0 L24,8 Z "
    "M18,0 L20,0 L20,4 L18,4 Z "
    "M14,0 L16,0 L16,2 L14,2 Z"
)

# C3: post + mid strip (right side) + detached square (top-left).
_C3_D = (
    "M16,0 L20,0 L20,8 L16,8 L16,6 L12,6 L12,4 L16,4 Z "
    "M0,6 L2,6 L2,8 L0,8 Z"
)

C1 = V3EdgeShape("C1", slot=1, is_empty=False, path_d=_C1_D, window=(2, 18),  hinge=(2, 0))
C2 = V3EdgeShape("C2", slot=2, is_empty=False, path_d=_C2_D, window=(6, 22),  hinge=(6, 0))
C3 = V3EdgeShape("C3", slot=3, is_empty=False, path_d=_C3_D, window=(4, 20),  hinge=(4, 0))
C4 = V3EdgeShape("C4", slot=4, is_empty=True,  path_d=None,  window=None,    hinge=None)

CUBIST_SHAPES = [C1, C2, C3, C4]


# ----- Polygon set ----------------------------------------------------------

# P1: closed pentagon-ish polygon; entirely within x∈[0,16] so the full
# path IS the tab — no truncation needed on rotation.
_P1_D = "M0,8 L0,4 L3,3 L4,0 L12,0 L16,8 Z"

# P2: self-touching nine-vertex polygon (M-shape / mountain-with-notch).
# Window is x∈[8,24]; the body fits entirely inside it, so full = tab.
# The polygon visits two points that lie on the outline boundary; evenodd
# resolves the resulting self-touching correctly.
_P2_D = "M16,0 L12,4 L8,8 L14,8 L18,0 L22,8 L24,8 L24,4 L20,0 Z"

# P3: triangular-ish main shape (left) + small triangle piece (right).
# Window x∈[0,16]; right piece at x≥20 is discarded on rotation.
_P3_D = "M0,2 L4,0 L6,4 L10,8 L0,8 Z M20,8 L24,4 L24,8 Z"

P1 = V3EdgeShape("P1", slot=1, is_empty=False, path_d=_P1_D, window=(0, 16),  hinge=(0, 0))
P2 = V3EdgeShape("P2", slot=2, is_empty=False, path_d=_P2_D, window=(8, 24),  hinge=(8, 0))
P3 = V3EdgeShape("P3", slot=3, is_empty=False, path_d=_P3_D, window=(0, 16),  hinge=(0, 0))
P4 = V3EdgeShape("P4", slot=4, is_empty=True,  path_d=None,  window=None,    hinge=None)

POLYGON_SHAPES = [P1, P2, P3, P4]
