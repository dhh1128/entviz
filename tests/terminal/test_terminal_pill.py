"""The terminal pill (docs/terminal-pill.md).

The pill is a one-line, static rendering of a value: a four-cell color-bar
histogram, then the entviz's own cells with their own nucleus colors, with the
elided runs summarized into single block glyphs.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "src"))

import pytest  # noqa: E402

from entviz.colors import get_nucleus_colors  # noqa: E402
from entviz.terminal import (BAR, CELL, SEPARATOR, Pill,  # noqa: E402
                             ansi, pill, whois)

# The gallery's Ed25519 verification key: 44 base64url chars, 264 bits, so the
# mnemonic takes its three-cell shape.
AID = "DKxy2sgzfplyr_tgwIxS19f2OchFHtLwPWD3v4oYimBx"
# Same 43-character body, non-transferable derivation code. Differs from AID in
# exactly one character, in the FIRST cell.
AID_B = "BKxy2sgzfplyr_tgwIxS19f2OchFHtLwPWD3v4oYimBx"
UUID = "550e8400-e29b-41d4-a716-446655440000"
# The gallery's Ed25519 signature: 88 chars, > 512 bits, so tokenization
# truncates to 20 cells — head 0-7, fingerprint middles 8-11, tail 12-19.
BIG = ("0BLwV6fEpOzY9iHsR2bAlKvU5eDoNyX8hGrQ1a_kJuT4dCnMxW7gFqP0Z-jI"
       "tS3cBmLwV6fEpOzY9iHsR2bAlKvU")

SGR = re.compile(r"\x1b\[[0-9;]*m")


def test_pill_is_a_pill():
    assert isinstance(pill(AID), Pill)


def test_pill_plain_is_the_visible_text():
    assert pill(AID).plain == "▅█▄▃ DKxy▂19f2▃imBx"


def test_pill_width_matches_plain():
    for value in (AID, AID_B, UUID, BIG):
        p = pill(value)
        assert p.width == len(p.plain)


def test_spans_concatenate_to_plain():
    """The host lays out columns from spans; they must not disagree with plain."""
    for value in (AID, UUID, BIG):
        p = pill(value)
        assert "".join(s.text for s in p.spans) == p.plain


def test_bar_is_four_cells_over_the_entviz_background():
    bar = [s for s in pill(AID).spans if s.channel == BAR]
    assert len(bar) == 4
    assert len({s.bg for s in bar}) == 1, "one entviz background behind all bands"


def test_bar_never_paints_a_band_over_itself():
    """The entviz background is removed from the edge palette (spec.md:417), so
    a band's color can never equal the background it is drawn on."""
    for value in (AID, AID_B, UUID, BIG):
        for s in pill(value).spans:
            if s.channel == BAR:
                assert s.fg != s.bg


def test_bar_is_normalized_to_the_tallest_band():
    """Max-normalization, not sum-normalization: some band is always full."""
    for value in (AID, AID_B, UUID, BIG):
        bar = [s.text for s in pill(value).spans if s.channel == BAR]
        assert "█" in bar


def test_cells_carry_their_own_nucleus_colors():
    cells = [s for s in pill(AID).spans if s.channel == CELL]
    for span in cells:
        assert (span.bg, span.fg) == get_nucleus_colors(_quant(span.text))


def _quant(token_text):
    """base64url token → its 24-bit quant, the same way the tokenizer does."""
    from entviz.entropy import BASE64URL, tokenize
    return tokenize(token_text, BASE64URL)[0].quant


def test_cells_are_whole_tokens_never_fragments():
    """A cut mid-cell would leave a color encoding characters not shown."""
    from entviz.entropy import parse, tokenize_entropy
    for value in (AID, UUID):
        parsed = parse(value)
        texts = {t.text for t in tokenize_entropy(parsed.core, parsed.alphabet)[0]}
        for span in pill(value).spans:
            if span.channel == CELL:
                assert span.text in texts


def test_token_order_is_grid_reading_order():
    """The whole cell model rests on this. `assign_cell_indices` inserts up to
    three blanks by SHIFTING token indices and never reorders them, so the
    non-blank cells in grid reading order are the tokens in token order. The
    pill relies on it to read cells without computing a grid at all."""
    from entviz.entropy import parse, tokenize_entropy
    from entviz.fingerprint import (compute_fingerprint, get_median_ftok,
                                    tokenize_fingerprint)
    from entviz.layout import assign_cell_indices, choose_grid

    for value in (AID, AID_B, UUID, BIG, "0123456789abcdef", "a1b2c3d4e5f6a7b8"):
        parsed = parse(value)
        tokens, _ = tokenize_entropy(parsed.core, parsed.alphabet)
        core = (parsed.prefix + parsed.core
                if parsed.prefix and parsed.prefix_semantic else parsed.core)
        ftoks = tokenize_fingerprint(compute_fingerprint(core))[:len(tokens)]
        grid = choose_grid(len(tokens))
        placed = assign_cell_indices(tokens, grid,
                                     median_token=get_median_ftok(ftoks),
                                     sort_keys=ftoks)
        by_token = [placed[t.index] for t in tokens]
        assert by_token == sorted(by_token), f"reordered for {value!r}"


def test_small_values_get_one_separator_and_large_ones_get_two():
    assert len([s for s in pill(UUID).spans if s.channel == SEPARATOR]) == 1
    assert len([s for s in pill(AID).spans if s.channel == SEPARATOR]) == 2


def test_separator_is_a_single_cell():
    for span in pill(AID).spans:
        if span.channel == SEPARATOR:
            assert len(span.text) == 1


def test_ansi_none_mode_is_exactly_plain():
    p = pill(AID)
    assert ansi(p, color="none") == p.plain


def test_ansi_256_mode_paints_and_strips_back_to_plain():
    p = pill(AID)
    out = ansi(p, color="256")
    assert out != p.plain
    assert SGR.sub("", out) == p.plain


def test_ansi_256_mode_uses_no_themed_indices():
    out = ansi(pill(AID), color="256")
    for index in re.findall(r"[34]8;5;(\d+)", out):
        assert int(index) >= 16


def test_ansi_rejects_truecolor():
    """Deliberate: 256 renders identically everywhere, truecolor would not."""
    with pytest.raises(ValueError):
        ansi(pill(AID), color="truecolor")


def test_pill_is_deterministic():
    assert pill(AID) == pill(AID)


def test_pill_ignores_the_environment():
    """A pure function of (value, options) — the host owns capability detection."""
    before = pill(AID)
    os.environ["NO_COLOR"] = "1"
    try:
        assert pill(AID) == before
    finally:
        del os.environ["NO_COLOR"]


def test_derivation_code_siblings_are_distinguishable():
    """B vs D over the same body: non-transferable vs transferable. Their first
    cells differ only in the blue byte, so color alone cannot separate them."""
    assert pill(AID).plain != pill(AID_B).plain


def test_a_change_inside_an_elided_cell_still_moves_the_pill():
    """The mnemonic cannot see the elided cells, so if the bar and separators
    did not cover them, two different values would render identically."""
    a = "550e8400-e29b-41d4-a716-446655440000"
    b = "550e8400-e29b-41d4-a716-446655441000"   # flip inside an elided cell
    assert pill(a).plain != pill(b).plain


def test_unparseable_input_fails_closed():
    """render() base64-encodes arbitrary text; the pill refuses it instead, so a
    typo in a TUI cannot come back looking like a well-formed identifier."""
    with pytest.raises(ValueError):
        pill("not an identifier at all")


def test_whois_shows_every_cell():
    from entviz.entropy import parse, tokenize_entropy
    parsed = parse(AID)
    tokens, _ = tokenize_entropy(parsed.core, parsed.alphabet)
    texts = [s.text for s in whois(AID).spans if s.channel == CELL]
    assert texts == [t.text for t in tokens]


def test_whois_carries_the_same_bar_as_the_pill():
    """So a pill and its whois line can be tied together by eye."""
    bar = lambda p: [(s.text, s.fg, s.bg) for s in p.spans if s.channel == BAR]
    assert bar(whois(AID)) == bar(pill(AID))


def test_whois_marks_material_that_has_no_cells():
    """A >512-bit input is tokenized head/middle/tail; the omitted material was
    never turned into cells, so it cannot be summarized — only marked."""
    assert "…" in whois(BIG).plain
    assert "…" not in whois(AID).plain
