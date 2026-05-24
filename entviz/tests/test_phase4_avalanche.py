"""
Phase 4 acceptance tests: median, quartile, blank placement, and visual
style derivation all switch from tokens to ftoks. The headline test is
the avalanche check on the UUID pair — v1 produced near-identical SVGs
for these two inputs (only ~3% of chars differ), v2 must produce
dramatically different output because every fingerprint-driven channel
shifts.
"""
from lxml import etree

from entviz.colors import POSSIBLE_EDGE_COLORS, select_visual_style
from entviz.entropy import parse, tokenize
from entviz.fingerprint import (
    compute_fingerprint,
    get_median_ftok,
    get_quartile_ftoks,
    tokenize_fingerprint,
)
from entviz.pipeline import render


UUID_A = "550e8400-e29b-41d4-a716-446655440000"
UUID_B = "550e8400-e29b-41d4-a716-446655440001"
UUID_A_CORE = "550e8400e29b41d4a716446655440000"
UUID_B_CORE = "550e8400e29b41d4a716446655440001"


def _uuid_token_count():
    # UUID type goes through the base64 tokenization path (token_len=4),
    # not hex, because "UUID" doesn't contain "hex" — so the 32-char core
    # yields 8 tokens. Compute it here rather than hard-coding so tests
    # stay correct if tokenization conventions change.
    parsed = parse(UUID_A)
    return len(tokenize(parsed.core, parsed.type))


def test_red_color_is_ff3f2f_not_yellow():
    # v1 had #ffdf2f which is actually a yellow nearly identical to gold.
    assert "#ff3f2f" in POSSIBLE_EDGE_COLORS
    assert "#ffdf2f" not in POSSIBLE_EDGE_COLORS


def test_get_median_ftok_returns_an_ftok():
    ftoks = tokenize_fingerprint(compute_fingerprint(UUID_A_CORE))
    med = get_median_ftok(ftoks[:_uuid_token_count()])
    assert med in ftoks[:_uuid_token_count()]


def test_get_quartile_ftoks_returns_four():
    ftoks = tokenize_fingerprint(compute_fingerprint(UUID_A_CORE))
    qs = get_quartile_ftoks(ftoks[:_uuid_token_count()])
    assert len(qs) == 4


def test_uuid_pair_have_different_median_ftoks():
    # The core security property: fingerprint avalanche means the median
    # ftok shifts for any input change. v1's median_token was the same
    # text-sorted value because UUID texts are nearly identical.
    used_a = tokenize_fingerprint(compute_fingerprint(UUID_A_CORE))[:6]
    used_b = tokenize_fingerprint(compute_fingerprint(UUID_B_CORE))[:6]
    assert get_median_ftok(used_a) != get_median_ftok(used_b)


def test_uuid_pair_have_different_quartile_ftoks():
    used_a = tokenize_fingerprint(compute_fingerprint(UUID_A_CORE))[:6]
    used_b = tokenize_fingerprint(compute_fingerprint(UUID_B_CORE))[:6]
    qs_a = get_quartile_ftoks(used_a)
    qs_b = get_quartile_ftoks(used_b)
    # At least 3 of the 4 quartile slots should differ between the two
    # pairs (allowing one possible coincidence on a small ftok population).
    differing = sum(1 for a, b in zip(qs_a, qs_b) if a != b)
    assert differing >= 3


def test_pipeline_uuid_pair_avalanche():
    # End-to-end avalanche check. v1 baseline for this pair was 189 chars
    # of difference (~3% of the SVG). v2 should be dramatically larger
    # because the fingerprint-driven bg color, edge_colors palette pick,
    # edge_shapes palette pick, blank placement, and quartile mark positions
    # all shift independently.
    a = render(UUID_A)
    b = render(UUID_B)
    diff = sum(1 for x, y in zip(a, b) if x != y) + abs(len(a) - len(b))
    assert diff > 500, f"only {diff} chars differ; expected > 500 for v2 avalanche"


def test_pipeline_bg_color_derives_from_median_ftok_not_token():
    # Compute the expected bg color from the median ftok directly, then
    # confirm the rendered SVG's background rect matches.
    used = tokenize_fingerprint(compute_fingerprint(UUID_A_CORE))[:_uuid_token_count()]
    med_ftok = get_median_ftok(used)
    expected_bg = POSSIBLE_EDGE_COLORS[med_ftok.quant & 0x03]

    svg = render(UUID_A)
    rects = etree.fromstring(svg.encode()).xpath(
        '//*[local-name()="rect"][not(ancestor::*[local-name()="defs"])]'
    )
    # Post-Phase 7: rect[0] is the white bounding rect; rect[1] is the
    # grid_rect filled with the entviz bg color.
    assert rects[1].get("fill") == expected_bg
