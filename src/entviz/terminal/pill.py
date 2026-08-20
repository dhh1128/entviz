"""The terminal pill and its whois line. See docs/terminal-pill.md.

NOT part of the entviz algorithm. Nothing here is normative, nothing is
conformance-bearing, and no port to the other implementations is implied. It is
imported explicitly (``from entviz.terminal import pill``) and never reached
from the base package.

The pill affords *recognition* — "have I seen this one, is this the one I
meant?" — and never verification. A host that needs an equality decision routes
to the full value or to a real entviz.
"""
import math
from itertools import combinations, permutations
from typing import NamedTuple

from ..colors import (POSSIBLE_EDGE_COLORS, closest_palette_color,
                      get_nucleus_colors, select_visual_style)
from ..entropy import parse, tokenize_entropy
from ..fingerprint import (compute_fingerprint, get_median_ftok,
                           tokenize_fingerprint)
from . import palette

#: Span channels. A host that wants to restyle or measure one part of a pill
#: selects on these rather than parsing the rendered text.
BAR = "bar"
CELL = "cell"
SEPARATOR = "separator"
GAP = "gap"

#: Lower block glyphs, 0/8 through 8/8, filling from the bottom.
EIGHTHS = " ▁▂▃▄▅▆▇█"

#: Marks material that was never tokenized at all, so has no cells to summarize.
NO_CELLS = "…"

#: Braille patterns are U+2800 plus a bitmask over the cell's eight dots.
_BRAILLE = 0x2800

#: Dot bit values in width-first-from-the-bottom order — dots 7 8 3 6 2 5 1 4.
#: Filling in this order makes a glyph's dot COUNT equal its fill height, which
#: is what lets the `none` rung keep the bar's ordinal reading as density while
#: spending the choice of *arrangement* on something else.
_DOT_BITS = (0x40, 0x80, 0x04, 0x20, 0x02, 0x10, 0x01, 0x08)

#: How many braille arrangements per height the bar may draw on. Lexicographic
#: order over ``_DOT_BITS`` puts the bottom-heaviest arrangements first, so a
#: small cap keeps every glyph reading as a bar rather than as scattered dots.
#: Measured over 100,000 digests, the full color assignment fits 98.0% of draws
#: at 6, 82.2% at 4, and 99.4% uncapped; 6 is the knee.
_BAR_ARRANGEMENTS = 6

#: The orders the four bands can take over the four non-background colors.
_BAND_ORDERS = tuple(sorted(permutations(range(len(POSSIBLE_EDGE_COLORS) - 1))))

#: Which palette color is the entviz background, times that order: 5 * 24.
_ASSIGNMENTS = len(POSSIBLE_EDGE_COLORS) * len(_BAND_ORDERS)


def _bar_alphabet() -> tuple[tuple[str, ...], ...]:
    """For each fill height, the glyphs the `none` rung may print for it.

    The braille arrangements come first, ramp-first, then the block glyph — so
    every height has one more code than it has arrangements, and the two heights
    with only a single arrangement (empty and full) are not degenerate.
    """
    alphabet = []
    for height in range(len(EIGHTHS)):
        glyphs = []
        for combo in combinations(range(len(_DOT_BITS)), height):
            bits = 0
            for dot in combo:
                bits |= _DOT_BITS[dot]
            glyphs.append(chr(_BRAILLE + bits))
            if len(glyphs) == _BAR_ARRANGEMENTS:
                break
        alphabet.append(tuple(glyphs) + (EIGHTHS[height],))
    return tuple(alphabet)


#: Indexed by fill height. Public because it is the `none` rung's counterpart to
#: :data:`EIGHTHS` — a host measuring or restyling a pill needs both.
BAR_ALPHABET = _bar_alphabet()

#: Cells above this size take the three-group mnemonic shape.
_THREE_GROUP_BITS = 256

#: A truncated (>512-bit) input tokenizes to head 0-7, fingerprint middles 8-11,
#: tail 12-19. The middles are identified by token index, not grid position.
_MIDDLE_TOKENS = range(8, 12)


class Span(NamedTuple):
    """One run of text with the colors it is painted in.

    ``fg``/``bg`` are spec sRGB colors, not palette indices — resolving them to
    a terminal happens in :func:`ansi`, so the same Pill can be rendered at any
    color depth (and measured without being rendered at all).

    ``mono`` is what the `none` rung prints instead, when stripping color would
    otherwise lose something the glyph can carry. It is always the same
    printable width as ``text``, and ``None`` for spans with nothing to recover.
    """
    text: str
    channel: str
    fg: str | None = None
    bg: str | None = None
    mono: str | None = None


class Pill(NamedTuple):
    """A rendered pill, split so a host can lay out columns without stripping
    escape codes — an escape has width in bytes and none on screen.

    ``width`` counts characters, and is the same on both color rungs even though
    the `none` rung prints different glyphs. The block glyphs and ``…`` are East
    Asian Width *Ambiguous*, so a terminal configured to render ambiguous
    characters double-width (some CJK setups) will disagree. Every ordinary
    Western configuration renders them narrow — and braille is EAW *Neutral*, so
    the `none` rung is the less exposed of the two.
    """
    spans: tuple[Span, ...]
    plain: str
    width: int


class _Cell(NamedTuple):
    """One entviz cell, as much of it as the pill needs."""
    text: str
    nucleus: str        #: the token's 24-bit quant read out as sRGB
    ink: str            #: white or black, by the spec's Oklab rule
    edge: str           #: nearest edge-palette entry to the nucleus
    boxes: int          #: how many of the 24 surround boxes the ftok fills


class _Band(NamedTuple):
    color: str
    weight: float


class _Value(NamedTuple):
    cells: tuple[_Cell, ...]
    truncated: bool
    size_bits: int
    background: str     #: the entviz background color
    bands: tuple[_Band, ...]


def _read(value: str) -> _Value:
    """Run the value through the library's own pipeline and keep what the pill
    needs. Deterministic and pure: no environment, no terminal, no clock.

    Fails closed on anything the parser does not recognize. ``render()`` falls
    back to base64-encoding arbitrary text, which is right for a visualization
    and wrong here — a mistyped identifier in a TUI must not come back looking
    like a well-formed one.
    """
    parsed = parse(value.strip())
    if parsed is None:
        raise ValueError(
            "not a recognized entropy value; the pill fails closed rather than "
            "falling back to base64 the way render() does")
    tokens, truncated = tokenize_entropy(parsed.core, parsed.alphabet)
    if not tokens:
        raise ValueError("no tokens produced from input entropy")

    fingerprint_core = (parsed.prefix + parsed.core
                        if parsed.prefix and parsed.prefix_semantic
                        else parsed.core)
    digest = compute_fingerprint(fingerprint_core)
    ftoks = tokenize_fingerprint(digest)[:len(tokens)]
    style = select_visual_style(get_median_ftok(ftoks))

    cells = []
    for token, ftok in zip(tokens, ftoks):
        nucleus, ink = get_nucleus_colors(token.quant)
        cells.append(_Cell(
            text=token.text, nucleus=nucleus, ink=ink,
            edge=closest_palette_color(nucleus, style.edge_colors),
            boxes=bin(ftok.quant & 0xFFFFFF).count("1"),
        ))

    from ..characterize import characterize
    return _Value(
        cells=tuple(cells),
        truncated=truncated,
        size_bits=characterize(value)["size_bits"],
        background=style.bg_color,
        bands=_color_bar_bands(digest, style.edge_colors),
    )


def _color_bar_bands(digest: bytes, edge_colors) -> tuple[_Band, ...]:
    """The entviz color bar's four bands: first-appearance order, weight
    ``count**4`` (spec.md:511, :513)."""
    counts = [0, 0, 0, 0]
    first_seen = {}
    slice_index = 0
    for byte in digest:
        for shift in (0, 2, 4, 6):
            pattern = (byte >> shift) & 0x03
            counts[pattern] += 1
            first_seen.setdefault(pattern, slice_index)
            slice_index += 1
    order = sorted(range(4),
                   key=lambda p: (first_seen.get(p, 256 + p), p))
    return tuple(_Band(edge_colors[p], float(counts[p]) ** 4) for p in order)


def _color_assignment(value: _Value) -> int:
    """Everything the bar's colors say, as one number below :data:`_ASSIGNMENTS`.

    Which palette color the entviz background is (and therefore which four are
    the bands), plus the order the bands take over those four. This is exactly
    what stripping color destroys.
    """
    others = [c for c in POSSIBLE_EDGE_COLORS if c != value.background]
    order = tuple(others.index(band.color) for band in value.bands)
    return (POSSIBLE_EDGE_COLORS.index(value.background) * len(_BAND_ORDERS)
            + _BAND_ORDERS.index(order))


def _mono_bar(heights: list[int], assignment: int) -> list[str]:
    """The `none` rung's four bar glyphs: the same fill heights, plus the color
    assignment written across their arrangements in mixed radix.

    A cell at an extreme height offers only two codes, so a bar whose heights are
    all extreme cannot hold all 120 assignments. That shortfall is a function of
    the heights alone, which both ends can see, so the fallback needs no escape
    mark: name the background color by itself and let the order go. It has room
    for that in every case, since even four two-code cells give sixteen.
    """
    radices = [len(BAR_ALPHABET[height]) for height in heights]
    code = (assignment if math.prod(radices) >= _ASSIGNMENTS
            else assignment // len(_BAND_ORDERS))
    glyphs = []
    for height, radix in zip(heights, radices):
        glyphs.append(BAR_ALPHABET[height][code % radix])
        code //= radix
    return glyphs


def _bar_spans(value: _Value) -> list[Span]:
    """Four cells, one per band, filled bottom-up.

    Normalized to the TALLEST band rather than to the sum. Four bars adding to 8
    spend nearly the whole range on the constraint — band counts cluster at
    64 +/- 7 over 256 slices, so a sum-normalized tallest bar is 3/8 about
    two-thirds of the time. Max-normalization preserves the ratios exactly while
    using the full range: 126 distinct shapes become 1836. The four cells sit
    side by side rather than stacked, so there is no total to conserve.
    """
    tallest = max(band.weight for band in value.bands) or 1.0
    heights = [round(8 * band.weight / tallest) for band in value.bands]
    mono = _mono_bar(heights, _color_assignment(value))
    return [
        Span(EIGHTHS[height], BAR, fg=band.color, bg=value.background,
             mono=glyph)
        for band, height, glyph in zip(value.bands, heights, mono)
    ]


def _shown_indices(value: _Value) -> list[int]:
    """Which cells the pill displays, by index — the React pill's mnemonic
    shape, unchanged (entviz-js/packages/core/src/describe.ts:428)."""
    last = len(value.cells) - 1
    if value.size_bits < _THREE_GROUP_BITS or len(value.cells) < 3:
        return [0, last]
    if value.truncated:
        middles = [i for i in _MIDDLE_TOKENS if i <= last]
        middle = middles[len(middles) // 2]
    else:
        middle = len(value.cells) // 2
    return [0, middle, last]


def _separator_span(run: tuple[_Cell, ...]) -> Span:
    """One block glyph summarizing the cells an elision is hiding.

    Tally each elided cell's filled surround boxes by its edge color; the most
    used color becomes the background, the least used the foreground, and the
    fill is their ratio. A gap whose rarest color is absent renders as an honest
    solid block.

    This is the pill's only look at the elided region. The cells' own channels
    cannot see it by construction, so without this and the color bar, two values
    differing only inside an elided cell would render identically.
    """
    tally = {color: 0 for color in POSSIBLE_EDGE_COLORS}
    for cell in run:
        tally[cell.edge] += cell.boxes
    present = {c: n for c, n in tally.items() if any(x.edge == c for x in run)}
    greatest = max(present, key=lambda c: (present[c], -POSSIBLE_EDGE_COLORS.index(c)))
    least = min(present, key=lambda c: (present[c], POSSIBLE_EDGE_COLORS.index(c)))
    fill = round(8 * present[least] / present[greatest]) if present[greatest] else 0
    return Span(EIGHTHS[fill], SEPARATOR, fg=least, bg=greatest,
                mono=_mono_separator(least, greatest, fill))


def _mono_separator(least: str, greatest: str, fill: int) -> str:
    """The `none` rung's separator: an opaque code, not a readable fill.

    Unlike the bar, one cell cannot hold this channel positionally — an ordered
    palette pair is 20 states on its own, so nothing readable is left over for
    the ratio. So the ratio's legibility is spent rather than the color's, and
    all three go in as one number. 225 of the 256 patterns are reachable; the
    rest stay unused deliberately, so that stripping color can never make a pill
    say MORE about a value than painting it does.
    """
    pair = (POSSIBLE_EDGE_COLORS.index(least) * len(POSSIBLE_EDGE_COLORS)
            + POSSIBLE_EDGE_COLORS.index(greatest))
    return chr(_BRAILLE + pair * len(EIGHTHS) + fill)


def _assemble(spans: list[Span]) -> Pill:
    plain = "".join(span.text for span in spans)
    return Pill(spans=tuple(spans), plain=plain, width=len(plain))


def pill(value: str) -> Pill:
    """Render ``value`` as a one-line pill: a four-cell color-bar histogram,
    then the mnemonic's cells in their own nucleus colors, with each elided run
    collapsed to a single summarizing block.

    Raises ``ValueError`` if the value is not a recognized entropy type.

    There are no channel flags. Trust posture is the host's to decide — a host
    that does not want value-derived channels shown does not call this. That
    keeps the policy in the one place that knows the value's provenance.
    """
    read = _read(value)
    shown = _shown_indices(read)
    spans = _bar_spans(read) + [Span(" ", GAP)]
    for position, index in enumerate(shown):
        if position:
            run = read.cells[shown[position - 1] + 1:index]
            spans.append(_separator_span(run) if run
                         else Span(NO_CELLS, SEPARATOR))
        cell = read.cells[index]
        spans.append(Span(cell.text, CELL, fg=cell.ink, bg=cell.nucleus))
    return _assemble(spans)


def whois(value: str) -> Pill:
    """Render ``value`` in full: the same color-bar histogram, then every cell.

    For a >512-bit input the tokenizer only ever produced head, fingerprint
    middle, and tail cells, so the omitted material has no cells to summarize.
    It is marked with ``…`` rather than a block — the block means "cells you are
    not being shown," and this is "characters that became no cell at all."
    """
    read = _read(value)
    spans = _bar_spans(read) + [Span(" ", GAP)]
    for index, cell in enumerate(read.cells):
        if read.truncated and index in (_MIDDLE_TOKENS[0], _MIDDLE_TOKENS[-1] + 1):
            spans.append(Span(NO_CELLS, SEPARATOR))
        spans.append(Span(cell.text, CELL, fg=cell.ink, bg=cell.nucleus))
    return _assemble(spans)


def ansi(rendered: Pill, *, color: str = "256") -> str:
    """Serialize a :class:`Pill` for a terminal.

    ``color`` is ``"256"`` or ``"none"``. Capability detection belongs to the
    host — ``NO_COLOR``, ``FORCE_COLOR`` and ``isatty`` are read there and
    reach this function only as this argument.

    The ``none`` rung swaps in each span's ``mono`` glyph, so it is not merely
    ``plain``. Both rungs are the same printable width, which is the only thing
    a host laying pills out in columns requires.
    """
    if color not in palette.COLOR_MODES:
        raise ValueError(
            f"color must be one of {palette.COLOR_MODES!r} (got {color!r})")
    out = []
    for span in rendered.spans:
        text = span.mono if color == "none" and span.mono else span.text
        code = palette.sgr(span.fg, span.bg, color)
        out.append(f"{code}{text}{palette.RESET}" if code else text)
    return "".join(out)
