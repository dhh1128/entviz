"""The terminal pill and its whois line. See docs/terminal-pill.md.

NOT part of the entviz algorithm. Nothing here is normative, nothing is
conformance-bearing, and no port to the other implementations is implied. It is
imported explicitly (``from entviz.terminal import pill``) and never reached
from the base package.

The pill affords *recognition* — "have I seen this one, is this the one I
meant?" — and never verification. A host that needs an equality decision routes
to the full value or to a real entviz.
"""
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
    """
    text: str
    channel: str
    fg: str | None = None
    bg: str | None = None


class Pill(NamedTuple):
    """A rendered pill, split so a host can lay out columns without stripping
    escape codes — an escape has width in bytes and none on screen.

    ``width`` counts characters. The block glyphs and ``…`` are East Asian Width
    *Ambiguous*, so a terminal configured to render ambiguous characters
    double-width (some CJK setups) will disagree. Every ordinary Western
    configuration renders them narrow.
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
    return [
        Span(EIGHTHS[round(8 * band.weight / tallest)], BAR,
             fg=band.color, bg=value.background)
        for band in value.bands
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
    return Span(EIGHTHS[fill], SEPARATOR, fg=least, bg=greatest)


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
    """
    if color not in palette.COLOR_MODES:
        raise ValueError(
            f"color must be one of {palette.COLOR_MODES!r} (got {color!r})")
    out = []
    for span in rendered.spans:
        code = palette.sgr(span.fg, span.bg, color)
        out.append(f"{code}{span.text}{palette.RESET}" if code else span.text)
    return "".join(out)
