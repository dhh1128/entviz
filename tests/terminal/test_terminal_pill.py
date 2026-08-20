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

from entviz.colors import (POSSIBLE_EDGE_COLORS,  # noqa: E402
                           get_nucleus_colors)
from entviz.terminal import (BAR, BAR_ALPHABET, CELL, EIGHTHS,  # noqa: E402
                             NO_CELLS, SEPARATOR, Pill, ansi, pill, whois)

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


def test_ansi_none_mode_keeps_the_width_but_not_the_glyphs():
    """The ladder changes characters, not printable width (terminal-pill.md §4.3).

    ``plain`` is the 256 rung's text. The ``none`` rung substitutes braille that
    carries what color would otherwise have said, so the two disagree on glyphs
    and must not disagree on width.
    """
    p = pill(AID)
    stripped = ansi(p, color="none")
    assert stripped != p.plain
    assert len(stripped) == p.width


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


# ---------------------------------------------------------------------------
# The `none` rung's braille substitution (docs/terminal-pill.md §4.3)
#
# With color stripped, block glyphs keep the bar's fill levels and lose which
# band is which color. Braille has room for both: dot COUNT still reads as fill
# height, and which arrangement of that many dots was chosen names the color
# assignment. The separator goes the other way — it becomes an opaque code with
# no readable fill, because one cell cannot hold an ordered palette pair and a
# ratio in positional form.
# ---------------------------------------------------------------------------

BRAILLE = range(0x2800, 0x2900)

#: Two 128-bit hex values whose bars have the SAME four fill heights and
#: DIFFERENT color assignments. In the 256 rung color separates them; in the
#: old `none` rung nothing did.
TWIN_A = "00000000000000000000000000000001"
TWIN_B = "00000000000000000000000000000011"


def mono(span):
    """What the `none` rung prints for one span."""
    return span.mono if span.mono else span.text


def fill_of(glyph):
    """The fill height a `none`-rung bar glyph reads as: its dot count, or the
    block's own index for the one code per height that stays a block."""
    if ord(glyph) in BRAILLE:
        return bin(ord(glyph) - 0x2800).count("1")
    return EIGHTHS.index(glyph)


def test_none_rung_bar_keeps_every_fill_level():
    """Nine levels, not the seven a reserved-top-row scheme would leave."""
    for value in (AID, AID_B, UUID, BIG, TWIN_A, TWIN_B):
        for span in pill(value).spans:
            if span.channel == BAR:
                assert fill_of(mono(span)) == EIGHTHS.index(span.text)


def test_none_rung_bar_separates_what_the_block_rung_confuses():
    a, b = pill(TWIN_A), pill(TWIN_B)
    bar = lambda p, f: "".join(f(s) for s in p.spans if s.channel == BAR)
    assert bar(a, lambda s: s.text) == bar(b, lambda s: s.text), "same heights"
    assert [s.fg for s in a.spans if s.channel == BAR] \
        != [s.fg for s in b.spans if s.channel == BAR], "different colors"
    assert bar(a, mono) != bar(b, mono), "the none rung must not confuse them"


def test_none_rung_bar_glyphs_stay_bar_like():
    """Only the bottom-heaviest arrangements are in play, so a glyph still reads
    as a bar rather than as scattered dots."""
    for value in (AID, AID_B, UUID, BIG, TWIN_A, TWIN_B):
        for span in pill(value).spans:
            if span.channel == BAR:
                assert mono(span) in BAR_ALPHABET[EIGHTHS.index(span.text)]


def test_none_rung_separator_is_an_opaque_braille_code():
    for value in (AID, UUID):
        for span in pill(value).spans:
            if span.channel == SEPARATOR and span.text != NO_CELLS:
                assert ord(mono(span)) in BRAILLE


def test_none_rung_separator_names_its_color_pair_and_fill():
    """The block rung shows the ratio and paints the pair; the braille rung
    carries all three, so a value's separators survive color stripping."""
    for value in (AID, UUID):
        for span in pill(value).spans:
            if span.channel == SEPARATOR and span.text != NO_CELLS:
                pair, fill = divmod(ord(mono(span)) - 0x2800, len(EIGHTHS))
                least, greatest = divmod(pair, len(POSSIBLE_EDGE_COLORS))
                assert POSSIBLE_EDGE_COLORS[least] == span.fg
                assert POSSIBLE_EDGE_COLORS[greatest] == span.bg
                assert EIGHTHS[fill] == span.text


def test_none_rung_leaves_no_cells_marker_alone():
    """`…` means characters that became no cell at all. It has no color to lose,
    so there is nothing for braille to carry."""
    for span in whois(BIG).spans:
        if span.text == NO_CELLS:
            assert span.mono is None


def test_none_rung_is_deterministic_and_carries_no_color():
    out = ansi(pill(AID), color="none")
    assert out == ansi(pill(AID), color="none")
    assert SGR.search(out) is None


#: Heights [8, 8, 5, 8] — three cells at an extreme height leave 56 codes, under
#: the 120 a full assignment needs, so this exercises the fallback.
CRAMPED = "0000000000000000000000000000001b"


def decode_bar(p):
    """Read the `none` rung's four bar glyphs back to the number they carry."""
    spans = [s for s in p.spans if s.channel == BAR]
    code, place = 0, 1
    for span in spans:
        alphabet = BAR_ALPHABET[EIGHTHS.index(span.text)]
        code += alphabet.index(mono(span)) * place
        place *= len(alphabet)
    return code, place


def test_none_rung_bar_carries_the_whole_color_assignment():
    """Background color and band order both survive, for a bar with room.

    Decoded blind: from the glyphs alone, reconstruct which palette color the
    entviz background is and what color each of the four bands was painted, then
    check both against what the 256 rung actually paints.
    """
    from itertools import permutations
    orders = sorted(permutations(range(4)))

    for value in (AID, AID_B, UUID, BIG, TWIN_A, TWIN_B):
        p = pill(value)
        code, capacity = decode_bar(p)
        assert capacity >= 120, f"{value} is the cramped case, not this test's"

        background = POSSIBLE_EDGE_COLORS[code // len(orders)]
        others = [c for c in POSSIBLE_EDGE_COLORS if c != background]
        bands = [others[i] for i in orders[code % len(orders)]]

        bar = [s for s in p.spans if s.channel == BAR]
        assert background == bar[0].bg
        assert bands == [s.fg for s in bar]


def test_a_cramped_bar_falls_back_to_the_background_alone():
    """Three extreme heights leave too few codes. That is visible in the heights
    themselves, so the fallback needs no escape mark — and the background, the
    single most useful thing color says, still fits."""
    p = pill(CRAMPED)
    code, capacity = decode_bar(p)
    assert capacity < 120
    background = {s.bg for s in p.spans if s.channel == BAR}.pop()
    assert POSSIBLE_EDGE_COLORS[code] == background


def test_cramped_bar_still_keeps_its_fill_levels():
    for span in pill(CRAMPED).spans:
        if span.channel == BAR:
            assert fill_of(mono(span)) == EIGHTHS.index(span.text)
