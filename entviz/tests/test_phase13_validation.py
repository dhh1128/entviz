"""
Phase 13 end-to-end validation suite, plus the >512-bit blank-separator
wiring.

Validation properties (per the migration brief's "Suggested validation"):
- Determinism: identical input → byte-identical output.
- Avalanche: single-bit input change → dramatic SVG divergence in
  fingerprint-driven channels.
- Losslessness ≤ 512 bits: token text round-trips to the entropy core.
- Large input > 512 bits: text shows first 256 + blank + last 256 bits;
  fingerprint binds the full input.
- Grid constraint: no input ever produces a 1-row or 1-column grid.
"""
from lxml import etree

from entviz.entropy import parse, tokenize_entropy
from entviz.fingerprint import compute_fingerprint
from entviz.pipeline import render


def _doc(svg_str):
    return etree.fromstring(svg_str.encode())


def test_determinism_byte_identical():
    a = render("550e8400-e29b-41d4-a716-446655440000")
    b = render("550e8400-e29b-41d4-a716-446655440000")
    assert a == b


def test_avalanche_uuid_pair_dramatic_divergence():
    a = render("550e8400-e29b-41d4-a716-446655440000")
    b = render("550e8400-e29b-41d4-a716-446655440001")
    diff = sum(1 for x, y in zip(a, b) if x != y) + abs(len(a) - len(b))
    # v1 baseline for this pair was 189 chars (2.76%). v2 should be far
    # greater because every fingerprint-driven channel shifts.
    assert diff > 2000, f"avalanche too weak: {diff} chars differ"


def test_losslessness_le_512_bits_text_roundtrip():
    # 128 hex chars = 512 bits → 22 full tokens, no truncation. Concatenating
    # all token texts should equal the normalized core string.
    core = "deadbeef" * 16
    parsed = parse(core)
    tokens, is_truncated = tokenize_entropy(parsed.core, parsed.type)
    assert not is_truncated
    concatenated = "".join(t.text for t in tokens)
    assert concatenated == parsed.core


def test_large_input_text_shows_first_and_last_256():
    # 576 bits = 144 hex chars; truncate to first 64 + last 64.
    core = "deadbeef" * 18
    parsed = parse(core)
    tokens, is_truncated = tokenize_entropy(parsed.core, parsed.type)
    assert is_truncated
    assert len(tokens) == 22
    head_text = "".join(t.text for t in tokens[:11])
    tail_text = "".join(t.text for t in tokens[11:])
    assert head_text == parsed.core[:64]
    assert tail_text == parsed.core[-64:]


def test_large_input_fingerprint_uses_full_input():
    # Two inputs with same first/last 256 bits but different middle
    # produce identical truncated tokens but different fingerprints.
    head = "DEADBEEF" * 8
    tail = "FEEDFACE" * 8
    a_core = head + ("A" * 32) + tail
    b_core = head + ("B" * 32) + tail
    assert compute_fingerprint(a_core) != compute_fingerprint(b_core)


def test_large_input_avalanche_propagates_through_render():
    # The avalanche between two large inputs that share their truncated
    # text must still produce visibly different SVGs.
    head = "deadbeef" * 8
    tail = "feedface" * 8
    a = render(head + ("a" * 32) + tail)
    b = render(head + ("b" * 32) + tail)
    diff = sum(1 for x, y in zip(a, b) if x != y) + abs(len(a) - len(b))
    assert diff > 1000, f"large-input avalanche too weak: {diff} chars differ"


def test_no_degenerate_grids_across_input_sizes():
    inputs = [
        "ab",                                                       # very short
        "deadbeef",                                                 # 2 tokens
        "deadbeefdeadbeef",                                         # 3 tokens
        "550e8400-e29b-41d4-a716-446655440000",                     # UUID
        "deadbeef" * 16,                                            # 512 bits
        "deadbeef" * 32,                                            # 1024 bits
    ]
    for entropy in inputs:
        svg = _doc(render(entropy))
        # Grid is at least 2x2; we already test choose_grid directly, but
        # also confirm render() doesn't crash on extremes.
        assert float(svg.get("width")) > 0
        assert float(svg.get("height")) > 0


# ---- blank separator for large inputs (>512 bits) ----


def test_large_input_grid_has_room_for_separator_plus_blanks():
    # For >512-bit input, the grid is sized to fit token_count + 4 extra
    # cells (3 possible median/quartile blanks + 1 separator). For
    # "deadbeef" * 18 → 22 tokens, grid_cells must be ≥ 26.
    svg = _doc(render("deadbeef" * 18))
    # Compute grid cells from bounding rect size:
    #   bounding_w = GM + GM + grid_w + GM + 1  → grid_w = bounding_w - 3*GM - 1
    # cells = (grid_w / cell_w) * (grid_h / cell_h)
    bw = float(svg.get("width"))
    bh = float(svg.get("height"))
    GM = 4
    cell_w, cell_h, nucleus_h = 64, 32, 16
    grid_w = bw - 3 * GM - 1
    grid_h = bh - 2 - 3 * GM - nucleus_h
    cells = int(grid_w / cell_w) * int(grid_h / cell_h)
    assert cells >= 26, f"grid has only {cells} cells; need ≥ 26 for 22 tokens + 4 blanks"


def test_large_input_blank_separator_creates_a_gap():
    # The separator blank sits at the cell_index between the last head
    # token (token 10 after any shifts) and the first tail token
    # (token 11 after any shifts). Concretely, the gap between
    # head's max cell_index and tail's min cell_index must be ≥ 2.
    # We can't read cell_indices directly from the SVG, but we can read
    # nucleus positions and check that at least one cell position inside
    # the grid is empty between the populated head and tail.
    svg = _doc(render("deadbeef" * 18))
    nuclei = [
        r for r in svg.xpath('//*[local-name()="rect"]')
        if float(r.get("width", 0)) == 48 and float(r.get("height", 0)) == 16
    ]
    # Convert each nucleus (x, y) to its (col, row) and then cell_index.
    # nucleus.x = grid_rect.left + col*cell_w + edge_size = 8 + 64*col + 8.
    # nucleus.y = grid_rect.top  + row*cell_h + edge_size = 5 + 32*row + 8.
    # → col = (x - 16) / 64; row = (y - 13) / 32.
    indices = set()
    for n in nuclei:
        col = int((float(n.get("x")) - 16) / 64)
        row = int((float(n.get("y")) - 13) / 32)
        # cell_index = row * cols. We don't know cols from one cell; use
        # max col + 1 as approximation, but compute final indices once we
        # know cols.
        indices.add((col, row))
    cols = max(c for c, _ in indices) + 1
    cell_indices = sorted({r * cols + c for c, r in indices})
    # There must be a gap of at least 2 somewhere in the cell_index list
    # (one for the separator; possibly more from median/quartile blanks).
    gaps = [b - a for a, b in zip(cell_indices, cell_indices[1:])]
    assert any(g >= 2 for g in gaps), (
        f"no separator gap in {cell_indices}; gaps={gaps}"
    )


def test_large_input_renders_exactly_token_count_nuclei():
    svg = _doc(render("deadbeef" * 18))
    nuclei = [
        r for r in svg.xpath('//*[local-name()="rect"]')
        if float(r.get("width", 0)) == 48 and float(r.get("height", 0)) == 16
    ]
    assert len(nuclei) == 22


def test_small_input_has_no_extra_separator():
    # For a ≤512-bit input, no separator should be inserted. The grid
    # uses token_count cells directly (plus the standard up-to-3
    # median/quartile blanks).
    svg = _doc(render("550e8400-e29b-41d4-a716-446655440000"))
    nuclei = [
        r for r in svg.xpath('//*[local-name()="rect"]')
        if float(r.get("width", 0)) == 48 and float(r.get("height", 0)) == 16
    ]
    assert len(nuclei) == 6  # UUID → 6 tokens via hex path (post-refactor)
