"""
v4 blank-cell marker: white-disc ring with black outline at
(nucleus_width/4 + 5) radius, plus two clock-hand lines from ring
center indicating the maxftok and minftok cells:

  * Long hand → maxftok direction. Length = radius + 1 so the hand
    crosses the black rim by exactly 1 px. Stroked white with
    mix-blend-mode=difference: on the white disc interior the hand
    inverts to black; on the black rim it inverts to a single white
    pixel breaking the rim — that "notch" is the visual cue marking
    the angle.

  * Short hand → minftok direction. Length = radius/2, stroked
    black, with a small white-filled black-stroked tip circle at
    its end so the tip reads as a "circle with white dot inside"
    distinct from the long hand's notch.
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


RING_RADIUS = 17       # nucleus_width/4 + 5 at 12pt = 12 + 5
LONG_HAND_LEN = 18     # ring_radius + 1 (extends 1 px past rim)
SHORT_HAND_LEN = 8.5   # ring_radius / 2
TIP_RADIUS = 1.5       # radius of short-hand tip circle
LONG_HAND_STROKE = "#ffffff"   # rendered black via mix-blend-mode: difference
SHORT_HAND_STROKE = "#000000"


def _rings(svg):
    return [c for c in svg.xpath('//*[local-name()="circle"]')
            if float(c.get("r", -1)) == RING_RADIUS
            and c.get("fill") == "#ffffff"
            and c.get("stroke") == "#000000"
            and c.get("stroke-width") == "1"]


def _hands(svg, stroke):
    return [l for l in svg.xpath('//*[local-name()="line"]')
            if l.get("stroke") == stroke]


def _tips(svg):
    """Small white-filled black-stroked tip circles at the short hand ends."""
    return [c for c in svg.xpath('//*[local-name()="circle"]')
            if float(c.get("r", -1)) == TIP_RADIUS
            and c.get("fill") == "#ffffff"
            and c.get("stroke") == "#000000"]


def test_blank_ring_is_white_filled_disc_with_black_outline():
    """Ring style: a single circle at RING_RADIUS with fill=white and a
    1-px black stroke."""
    svg = _doc(render("Lorem ipsum dolor sit amet, consectetur adipiscing elit."))
    assert _rings(svg), "no white-disc/black-stroke rings found"


def test_blank_ring_radius_is_nucleus_width_over_4_plus_5():
    """Ring radius = nucleus_width / 4 + 5 = 17 at 12pt."""
    svg = _doc(render("Lorem ipsum dolor sit amet, consectetur adipiscing elit."))
    rings = _rings(svg)
    assert rings
    for c in rings:
        assert float(c.get("r")) == RING_RADIUS


def _grid_dims(svg):
    """Recover (cols, rows, grid_left, grid_top) from canvas size."""
    bw = float(svg.get("width"))
    bh = float(svg.get("height"))
    GM, box_height, nucleus_h = 5, 10, 20
    cell_w, cell_h = 60, 40
    grid_left = 1 + box_height + 1 + GM         # = 17
    grid_top = 1 + GM + nucleus_h + GM          # = 31 (top label always present)
    grid_w = bw - 3 - box_height - 2 * GM
    # Total non-grid height with just a top strip = 1+5+20+5 + 5+1 = 37.
    h_top_only = grid_top + GM + 1              # = 37
    grid_h_top_only = bh - h_top_only
    if abs(grid_h_top_only / cell_h - round(grid_h_top_only / cell_h)) < 0.01:
        rows = int(round(grid_h_top_only / cell_h))
    else:
        # Bottom strip present too: subtract another nucleus_h + GM.
        rows = int(round((grid_h_top_only - nucleus_h - GM) / cell_h))
    cols = int(round(grid_w / cell_w))
    return cols, rows, grid_left, grid_top


def _blank_runs(svg):
    """Return the indices of blank cells grouped into runs of
    consecutive cell indices (reading order)."""
    cols, rows, grid_left, grid_top = _grid_dims(svg)
    cell_w, cell_h = 60, 40
    nuclei_centers = {
        (float(r.get("x")) + 24, float(r.get("y")) + 10)
        for r in svg.xpath('//*[local-name()="rect"]')
        if float(r.get("width", 0)) == 48 and float(r.get("height", 0)) == 20
    }
    used = set()
    for ci in range(cols * rows):
        col = ci % cols
        row = ci // cols
        center = (grid_left + col * cell_w + cell_w / 2,
                  grid_top + row * cell_h + cell_h / 2)
        if center in nuclei_centers:
            used.add(ci)
    blanks = [ci for ci in range(cols * rows) if ci not in used]
    runs = []
    for ci in blanks:
        if runs and runs[-1][-1] == ci - 1:
            runs[-1].append(ci)
        else:
            runs.append([ci])
    return runs


def test_blank_ring_count_matches_number_of_runs():
    """One ring per RUN of consecutive blank cells (reading order),
    not one ring per blank cell. A trailing run of N consecutive blanks
    produces 1 ring, not N."""
    svg = _doc(render("Lorem ipsum dolor sit amet, consectetur adipiscing elit."))
    runs = _blank_runs(svg)
    assert runs, "test fixture should produce at least one blank"
    assert len(_rings(svg)) == len(runs), (
        f"{len(_rings(svg))} rings vs {len(runs)} runs (blank groups: {runs})"
    )


def test_consecutive_trailing_blanks_share_one_ring():
    """A larger entropy that lands multiple consecutive trailing blank
    cells must show fewer rings than blank cells — exactly one ring
    per consecutive run."""
    # 1024-bit hex, truncated → 22 tokens + extras; usually produces a
    # grid with multiple trailing blanks.
    svg = _doc(render("0123456789abcdef" * 16))
    runs = _blank_runs(svg)
    total_blanks = sum(len(r) for r in runs)
    # The fixture is chosen so it has consecutive trailing blanks.
    assert any(len(r) >= 2 for r in runs), (
        f"test fixture didn't produce a multi-blank run: {runs}"
    )
    rings = _rings(svg)
    assert len(rings) == len(runs)
    assert len(rings) < total_blanks  # the rule actually fired


# ---- Clock hands --------------------------------------------------------


def test_each_blank_has_one_long_and_one_short_hand():
    """Two SVG <line>s per ring: white long hand (rendered via
    mix-blend-mode=difference) toward maxftok, and a black short hand
    toward minftok."""
    svg = _doc(render("Lorem ipsum dolor sit amet, consectetur adipiscing elit."))
    n = len(_rings(svg))
    assert n > 0
    assert len(_hands(svg, LONG_HAND_STROKE)) == n
    assert len(_hands(svg, SHORT_HAND_STROKE)) == n


def test_long_hand_uses_mix_blend_mode_difference():
    """The long hand must declare mix-blend-mode: difference, so its
    white stroke inverts to black on the white disc interior and to a
    single white pixel where it crosses the black ring rim."""
    svg = _doc(render("Lorem ipsum dolor sit amet, consectetur adipiscing elit."))
    long_hands = _hands(svg, LONG_HAND_STROKE)
    assert long_hands
    for h in long_hands:
        style = (h.get("style") or "")
        assert "mix-blend-mode" in style and "difference" in style, (
            f"long hand missing mix-blend-mode: difference (style={style!r})"
        )


def test_long_hand_starts_at_ring_center():
    """Long hand's x1,y1 equals the ring's center."""
    svg = _doc(render("Lorem ipsum dolor sit amet, consectetur adipiscing elit."))
    rings = _rings(svg)
    long_hands = _hands(svg, LONG_HAND_STROKE)
    centers = {(float(r.get("cx")), float(r.get("cy"))) for r in rings}
    for h in long_hands:
        assert (float(h.get("x1")), float(h.get("y1"))) in centers


def test_long_hand_extends_one_px_past_rim():
    """Long hand length = ring_radius + 1 = 18 at 12pt, so it crosses
    the black rim and creates the 1-px white notch via difference."""
    svg = _doc(render("Lorem ipsum dolor sit amet, consectetur adipiscing elit."))
    long_hands = _hands(svg, LONG_HAND_STROKE)
    assert long_hands
    for h in long_hands:
        x1, y1 = float(h.get("x1")), float(h.get("y1"))
        x2, y2 = float(h.get("x2")), float(h.get("y2"))
        assert abs(math.hypot(x2 - x1, y2 - y1) - LONG_HAND_LEN) < 0.01


def test_short_hand_is_half_radius():
    """Short hand length = ring_radius / 2 = 8.5 at 12pt."""
    svg = _doc(render("Lorem ipsum dolor sit amet, consectetur adipiscing elit."))
    short_hands = _hands(svg, SHORT_HAND_STROKE)
    assert short_hands
    for h in short_hands:
        x1, y1 = float(h.get("x1")), float(h.get("y1"))
        x2, y2 = float(h.get("x2")), float(h.get("y2"))
        assert abs(math.hypot(x2 - x1, y2 - y1) - SHORT_HAND_LEN) < 0.01


def test_short_hand_tip_circle_at_hand_end():
    """The short hand carries a small white-filled black-stroked tip
    circle (r=1.5) centered at its end point — visually a 'circle with
    a white dot inside'."""
    svg = _doc(render("Lorem ipsum dolor sit amet, consectetur adipiscing elit."))
    short_hands = _hands(svg, SHORT_HAND_STROKE)
    tips = _tips(svg)
    assert tips, "no tip circles found"
    assert len(tips) == len(short_hands)
    short_ends = {(float(h.get("x2")), float(h.get("y2"))) for h in short_hands}
    for t in tips:
        assert (float(t.get("cx")), float(t.get("cy"))) in short_ends


def test_long_hand_points_at_maxftok_cell():
    """White long hand direction = angle from ring center toward maxftok."""
    input_ = "Lorem ipsum dolor sit amet, consectetur adipiscing elit."
    svg = _doc(render(input_))
    rings = _rings(svg)
    long_hands = _hands(svg, LONG_HAND_STROKE)

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
    col = max_cell_idx % grid.cols
    row = max_cell_idx // grid.cols
    grid_left, grid_top = 17, 31
    max_target = (grid_left + col * 60 + 30, grid_top + row * 40 + 20)

    for r in rings:
        rcx, rcy = float(r.get("cx")), float(r.get("cy"))
        h = next(h for h in long_hands
                 if float(h.get("x1")) == rcx and float(h.get("y1")) == rcy)
        x2, y2 = float(h.get("x2")), float(h.get("y2"))
        expected = math.atan2(max_target[1] - rcy, max_target[0] - rcx)
        actual = math.atan2(y2 - rcy, x2 - rcx)
        assert abs(expected - actual) < 0.01, (
            f"ring at ({rcx},{rcy}): expected {expected:.3f}, got {actual:.3f}"
        )


def test_short_hand_points_at_minftok_cell():
    """Black short hand direction = angle from ring center toward minftok."""
    input_ = "Lorem ipsum dolor sit amet, consectetur adipiscing elit."
    svg = _doc(render(input_))
    rings = _rings(svg)
    short_hands = _hands(svg, SHORT_HAND_STROKE)

    parsed = parse(input_)
    core = parsed.core if parsed else base64.urlsafe_b64encode(input_.encode()).decode().rstrip('=')
    alphabet = parsed.alphabet if parsed else BASE64URL
    tokens, _ = tokenize_entropy(core, alphabet)
    used_ftoks = tokenize_fingerprint(compute_fingerprint(core))[:len(tokens)]
    grid = choose_grid(len(tokens), 1.0)
    median = get_median_ftok(used_ftoks)
    ci = assign_cell_indices(tokens, grid, median_token=median, sort_keys=used_ftoks)
    used_ftok_cells = [(used_ftoks[t.index], ci[t.index]) for t in tokens]
    min_cell_idx = min(used_ftok_cells, key=lambda fc: (fc[0].quant, -fc[1]))[1]
    col = min_cell_idx % grid.cols
    row = min_cell_idx // grid.cols
    grid_left, grid_top = 17, 31
    min_target = (grid_left + col * 60 + 30, grid_top + row * 40 + 20)

    for r in rings:
        rcx, rcy = float(r.get("cx")), float(r.get("cy"))
        h = next(h for h in short_hands
                 if float(h.get("x1")) == rcx and float(h.get("y1")) == rcy)
        x2, y2 = float(h.get("x2")), float(h.get("y2"))
        expected = math.atan2(min_target[1] - rcy, min_target[0] - rcx)
        actual = math.atan2(y2 - rcy, x2 - rcx)
        assert abs(expected - actual) < 0.01, (
            f"ring at ({rcx},{rcy}): expected {expected:.3f}, got {actual:.3f}"
        )
