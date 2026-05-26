"""
v4 blank-cell marker: bicolor ring at nucleus_width/4 radius, plus
two pointer markers indicating minftok and maxftok cells.
"""
import math
from lxml import etree

from entviz.pipeline import render
from entviz.layout import choose_grid, assign_cell_indices
from entviz.entropy import parse, tokenize_entropy, BASE64URL
from entviz.fingerprint import compute_fingerprint, tokenize_fingerprint, get_median_ftok
import base64


def _doc(svg_str):
    return etree.fromstring(svg_str.encode())


def _circles(svg, r):
    """All circles with the given r attribute."""
    return [
        c for c in svg.xpath('//*[local-name()="circle"]')
        if float(c.get("r", -1)) == r
    ]


# ---- Bicolor ring -------------------------------------------------------


def test_blank_ring_consists_of_two_adjacent_circles():
    """Each blank cell has one circle at r=12.5 (white outer) and one at
    r=11.5 (black inner) — both centered at the same point."""
    # "Lorem ipsum..." → 16 tokens → 4x4 fit but choose_grid may pick 4x5 or
    # similar → at least one blank cell.
    svg = _doc(render("Lorem ipsum dolor sit amet, consectetur adipiscing elit."))
    white_outers = [
        c for c in svg.xpath('//*[local-name()="circle"]')
        if float(c.get("r", -1)) == 12.5 and c.get("stroke") == "#ffffff"
    ]
    black_inners = [
        c for c in svg.xpath('//*[local-name()="circle"]')
        if float(c.get("r", -1)) == 11.5 and c.get("stroke") == "#000000"
    ]
    assert white_outers, "no white-outer ring strokes"
    assert len(white_outers) == len(black_inners), (
        f"ring pair mismatch: {len(white_outers)} outer vs {len(black_inners)} inner"
    )
    # Each pair must share a center.
    outer_centers = {(float(c.get("cx")), float(c.get("cy"))) for c in white_outers}
    inner_centers = {(float(c.get("cx")), float(c.get("cy"))) for c in black_inners}
    assert outer_centers == inner_centers


def test_blank_ring_radius_is_nucleus_width_over_4():
    """At 12pt, nucleus_width = 48, so nominal_radius = 12, white outer
    at r=12.5, black inner at r=11.5."""
    svg = _doc(render("Lorem ipsum dolor sit amet, consectetur adipiscing elit."))
    outers = [c for c in svg.xpath('//*[local-name()="circle"]')
              if c.get("stroke") == "#ffffff" and float(c.get("r", -1)) > 5]
    for c in outers:
        assert float(c.get("r")) == 12.5
        assert c.get("stroke-width") == "1"


def test_blank_ring_count_matches_blank_cell_count():
    """For an input with a known blank-cell count, the SVG should
    contain that many ring pairs."""
    # "Lorem ipsum..." → choose_grid for 16 tokens at 1.0 AR → 4x5 = 20 cells,
    # 4 blanks (using the actual v4 cell aspect ratio).
    # Wait — choose_grid's stale 2:1 formula picks differently. Just count
    # nuclei vs total grid cells: blank rings = (grid cells) − (nuclei).
    svg = _doc(render("Lorem ipsum dolor sit amet, consectetur adipiscing elit."))
    nuclei = [
        r for r in svg.xpath('//*[local-name()="rect"]')
        if float(r.get("width", 0)) == 48 and float(r.get("height", 0)) == 20
    ]
    rings = [c for c in svg.xpath('//*[local-name()="circle"]')
             if float(c.get("r", -1)) == 12.5 and c.get("stroke") == "#ffffff"]
    # Compute the grid dimensions from canvas
    bw = float(svg.get("width"))
    bh = float(svg.get("height"))
    GM, box_height = 5, 10
    cell_w, cell_h = 60, 40
    grid_w = bw - 3 - box_height - 2 * GM
    grid_h = bh - 2 - 2 * GM
    cells = int(grid_w / cell_w) * int(grid_h / cell_h)
    assert len(rings) == cells - len(nuclei), (
        f"{len(rings)} rings vs expected {cells - len(nuclei)} "
        f"(cells={cells}, nuclei={len(nuclei)})"
    )


# ---- Pointer markers ----------------------------------------------------


def test_pointer_markers_pair_per_blank():
    """Each blank ring has 2 pointer markers (inside + outside), both r=1.5."""
    svg = _doc(render("Lorem ipsum dolor sit amet, consectetur adipiscing elit."))
    rings = [c for c in svg.xpath('//*[local-name()="circle"]')
             if float(c.get("r", -1)) == 12.5 and c.get("stroke") == "#ffffff"]
    markers = _circles(svg, 1.5)
    assert len(markers) == 2 * len(rings)


def test_pointer_markers_at_tangent_distance():
    """Outside markers at distance 15 from ring center; inside at distance 9."""
    svg = _doc(render("Lorem ipsum dolor sit amet, consectetur adipiscing elit."))
    rings = [c for c in svg.xpath('//*[local-name()="circle"]')
             if float(c.get("r", -1)) == 12.5 and c.get("stroke") == "#ffffff"]
    markers = _circles(svg, 1.5)
    for r in rings:
        rcx, rcy = float(r.get("cx")), float(r.get("cy"))
        # Find the 2 markers belonging to this ring (nearest 2 by distance)
        dists = sorted(
            math.hypot(float(m.get("cx")) - rcx, float(m.get("cy")) - rcy)
            for m in markers
        )
        # Two closest distances should be 9 (inside) and 15 (outside).
        assert dists[0] == 9.0 or abs(dists[0] - 9) < 0.01
        assert dists[1] == 15.0 or abs(dists[1] - 15) < 0.01


def test_pointer_marker_design():
    """Each pointer is a white-filled disc with a 1-px black stroke."""
    svg = _doc(render("Lorem ipsum dolor sit amet, consectetur adipiscing elit."))
    markers = _circles(svg, 1.5)
    assert markers
    for m in markers:
        assert m.get("fill") == "#ffffff"
        assert m.get("stroke") == "#000000"
        assert m.get("stroke-width") == "1"


def test_all_max_pointers_point_at_same_cell():
    """All outside markers in an entviz target the same maxftok cell."""
    input_ = "Lorem ipsum dolor sit amet, consectetur adipiscing elit."
    svg = _doc(render(input_))
    rings = [c for c in svg.xpath('//*[local-name()="circle"]')
             if float(c.get("r", -1)) == 12.5 and c.get("stroke") == "#ffffff"]
    markers = _circles(svg, 1.5)

    # Compute target cell from the actual algorithm
    parsed = parse(input_)
    core = parsed.core if parsed else base64.urlsafe_b64encode(input_.encode()).decode().rstrip('=')
    alphabet = parsed.alphabet if parsed else BASE64URL
    tokens, _ = tokenize_entropy(core, alphabet)
    used_ftoks = tokenize_fingerprint(compute_fingerprint(core))[:len(tokens)]
    grid = choose_grid(len(tokens), 1.0)
    median = get_median_ftok(used_ftoks)
    ci = assign_cell_indices(tokens, grid, median_token=median, sort_keys=used_ftoks)
    used_ftok_cells = [(used_ftoks[t.index], ci[t.index]) for t in tokens]
    max_cell_idx = max(used_ftok_cells, key=lambda fc: (fc[0].quant, fc[1]))[1]
    # Compute max target center
    col = max_cell_idx % grid.cols
    row = max_cell_idx // grid.cols
    grid_left, grid_top = 17, 6
    max_target = (grid_left + col * 60 + 30, grid_top + row * 40 + 20)

    # For each ring, the outside marker (distance 15) should lie on the line
    # toward max_target.
    for r in rings:
        rcx, rcy = float(r.get("cx")), float(r.get("cy"))
        # Find outside marker (the one at distance 15)
        outsides = [
            m for m in markers
            if abs(math.hypot(float(m.get("cx")) - rcx, float(m.get("cy")) - rcy) - 15) < 0.01
        ]
        assert outsides
        m = outsides[0]
        mx, my = float(m.get("cx")), float(m.get("cy"))
        # Expected angle from ring to target
        expected_angle = math.atan2(max_target[1] - rcy, max_target[0] - rcx)
        actual_angle = math.atan2(my - rcy, mx - rcx)
        assert abs(expected_angle - actual_angle) < 0.01, (
            f"ring at ({rcx},{rcy}): expected angle {expected_angle:.3f}, "
            f"got {actual_angle:.3f}"
        )
