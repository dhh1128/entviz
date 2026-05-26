"""
V3-6a: structural tests for the new cubist + polygon shape sets.

This phase only adds the shape data structures; nothing in the
pipeline uses them yet (that's V3-6b). These tests pin the canonical
path d-strings, the window and hinge metadata, and the empty-as-
member contract.
"""
import re

from entviz.v3_shapes import (
    C1, C2, C3, C4,
    P1, P2, P3, P4,
    CUBIST_SHAPES,
    POLYGON_SHAPES,
    V3_FILL_RULE,
    V3EdgeShape,
)


# ----- Shape sets ----------------------------------------------------------


def test_cubist_set_has_4_members_in_canonical_order():
    assert CUBIST_SHAPES == [C1, C2, C3, C4]
    assert [s.name for s in CUBIST_SHAPES] == ["C1", "C2", "C3", "C4"]
    assert [s.slot for s in CUBIST_SHAPES] == [1, 2, 3, 4]


def test_polygon_set_has_4_members_in_canonical_order():
    assert POLYGON_SHAPES == [P1, P2, P3, P4]
    assert [s.name for s in POLYGON_SHAPES] == ["P1", "P2", "P3", "P4"]
    assert [s.slot for s in POLYGON_SHAPES] == [1, 2, 3, 4]


def test_slot_4_in_both_sets_is_empty():
    assert C4.is_empty is True
    assert P4.is_empty is True
    assert C4.path_d is None
    assert P4.path_d is None


def test_slots_1_through_3_are_not_empty():
    for s in (C1, C2, C3, P1, P2, P3):
        assert s.is_empty is False
        assert s.path_d is not None and len(s.path_d) > 0


def test_fill_rule_constant_is_evenodd():
    # All v3 shapes require evenodd to resolve holes / pieces / self-
    # touching correctly. The renderer in V3-6b will apply this.
    assert V3_FILL_RULE == "evenodd"


# ----- Path content -------------------------------------------------------


def _parse_d_string(d):
    """
    Return a list of subpaths; each subpath is a list of (x, y) vertices.
    Supports only the absolute M/L/Z commands used in v3 shapes.
    """
    subpaths = []
    current = None
    tokens = re.findall(r"[MLZ]|-?\d+(?:\.\d+)?", d)
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok == "M":
            if current is not None:
                subpaths.append(current)
            current = []
            x, y = float(tokens[i + 1]), float(tokens[i + 2])
            current.append((x, y))
            i += 3
        elif tok == "L":
            x, y = float(tokens[i + 1]), float(tokens[i + 2])
            current.append((x, y))
            i += 3
        elif tok == "Z":
            i += 1
        else:
            i += 1
    if current is not None:
        subpaths.append(current)
    return subpaths


def test_C1_path_matches_handoff_vertices():
    subs = _parse_d_string(C1.path_d)
    assert len(subs) == 3
    assert subs[0] == [(0, 8), (0, 6), (2, 6), (2, 0), (8, 0), (8, 8),
                       (6, 8), (6, 4), (4, 4), (4, 8)]
    assert subs[1] == [(12, 4), (14, 4), (14, 8), (12, 8)]
    assert subs[2] == [(22, 4), (24, 4), (24, 8), (22, 8)]


def test_C2_path_matches_handoff_vertices():
    subs = _parse_d_string(C2.path_d)
    assert len(subs) == 3
    assert subs[0] == [(0, 8), (0, 2), (4, 2), (4, 4), (6, 4), (6, 8),
                       (10, 8), (10, 2), (10, 0), (24, 0), (24, 8)]
    assert subs[1] == [(18, 0), (20, 0), (20, 4), (18, 4)]
    assert subs[2] == [(14, 0), (16, 0), (16, 2), (14, 2)]


def test_C3_path_matches_handoff_vertices():
    subs = _parse_d_string(C3.path_d)
    assert len(subs) == 2
    assert subs[0] == [(16, 0), (20, 0), (20, 8), (16, 8), (16, 6),
                       (12, 6), (12, 4), (16, 4)]
    assert subs[1] == [(0, 6), (2, 6), (2, 8), (0, 8)]


def test_P1_path_matches_handoff_vertices():
    subs = _parse_d_string(P1.path_d)
    assert len(subs) == 1
    assert subs[0] == [(0, 8), (0, 4), (3, 3), (4, 0), (12, 0), (16, 8)]


def test_P2_path_matches_handoff_vertices():
    subs = _parse_d_string(P2.path_d)
    assert len(subs) == 1
    assert subs[0] == [(16, 0), (12, 4), (8, 8), (14, 8), (18, 0),
                       (22, 8), (24, 8), (24, 4), (20, 0)]


def test_P3_path_matches_handoff_vertices():
    subs = _parse_d_string(P3.path_d)
    assert len(subs) == 2
    assert subs[0] == [(0, 2), (4, 0), (6, 4), (10, 8), (0, 8)]
    assert subs[1] == [(20, 8), (24, 4), (24, 8)]


# ----- Window and hinge metadata -----------------------------------------


def test_C1_window_and_hinge():
    assert C1.window == (2, 18)
    assert C1.hinge == (2, 0)


def test_C2_window_and_hinge():
    assert C2.window == (6, 22)
    assert C2.hinge == (6, 0)


def test_C3_window_and_hinge():
    assert C3.window == (4, 20)
    assert C3.hinge == (4, 0)


def test_P1_window_is_full_no_truncation_needed():
    # P1's content is entirely within x∈[0,16], so the full path IS the
    # tab — no clipping needed on 90°/270° rotation.
    assert P1.window == (0, 16)
    assert P1.hinge == (0, 0)


def test_P2_window_is_full_no_truncation_needed():
    # P2's body sits in x∈[8,24]; the window equals the body extent.
    assert P2.window == (8, 24)
    assert P2.hinge == (8, 0)


def test_P3_window_truncates_right_piece():
    # P3's right triangle piece at x∈[20,24] is outside the window
    # and gets discarded on rotation.
    assert P3.window == (0, 16)
    assert P3.hinge == (0, 0)


def test_window_width_is_16_for_every_nonempty_shape():
    # The tab window is always 16 wide (the V3-6 design constraint).
    for s in (C1, C2, C3, P1, P2, P3):
        left, right = s.window
        assert right - left == 16, f"{s.name} window width is {right - left}, expected 16"


def test_hinge_is_at_window_left_and_outer_y():
    # The hinge is always at the tab's outer-left corner: x = window_left,
    # y = 0 (outer / cell boundary in canonical coords).
    for s in (C1, C2, C3, P1, P2, P3):
        assert s.hinge == (s.window[0], 0), f"{s.name} hinge {s.hinge}"


# ----- Identity / equality ------------------------------------------------


def test_v3_edgeshape_equality_by_name():
    other_c1 = V3EdgeShape("C1", slot=99, is_empty=True, path_d=None,
                           window=None, hinge=None)
    assert C1 == other_c1  # equality is by name (allows lookup / dedup)


def test_v3_edgeshape_distinct_names_unequal():
    assert C1 != C2
    assert C1 != P1
