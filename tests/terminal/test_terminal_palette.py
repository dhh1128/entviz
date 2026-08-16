"""The terminal pill's 256-color palette (docs/terminal-pill.md §4).

Two properties matter and neither is "nearest color wins": the five spec palette
entries are PINNED (nearest-by-RGB damages the gold/red lightness gap, which is
the palette's whole rationale), and no index below 16 is ever emitted, because
0-15 are the user's theme and would render differently per terminal.
"""
import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "src"))

import pytest  # noqa: E402

from entviz.colors import POSSIBLE_EDGE_COLORS, oklab_lightness  # noqa: E402
from entviz.terminal import palette  # noqa: E402


def _rgb(hex_color):
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def test_spec_palette_entries_are_pinned():
    """The five palette colors are a hand-chosen table, not a quantization."""
    assert palette.PALETTE_256 == {
        "#ffffff": 231,
        "#e7be00": 184,
        "#ff3f2f": 202,
        "#2f3fbf": 25,
        "#000000": 16,
    }


def test_every_spec_palette_color_is_covered():
    """If the spec's palette ever grows an entry, this table must grow too."""
    assert set(palette.PALETTE_256) == set(POSSIBLE_EDGE_COLORS)


def test_palette_quantization_preserves_lightness_order():
    """Lightness spacing is why this palette exists (spec.md:411)."""
    spec_order = sorted(POSSIBLE_EDGE_COLORS,
                        key=lambda c: oklab_lightness(_rgb(c)), reverse=True)
    quantized = [palette.rgb_of(palette.PALETTE_256[c]) for c in spec_order]
    lightness = [oklab_lightness(_rgb(c)) for c in quantized]
    assert lightness == sorted(lightness, reverse=True)


def test_palette_quantization_keeps_adjacent_lightness_gaps_wide():
    """Nearest-by-RGB collapses gold/red to 0.080. The pinned table holds the
    worst adjacent gap at 0.149, level with the spec palette's own 0.157."""
    lightness = sorted(
        (oklab_lightness(_rgb(palette.rgb_of(i)))
         for i in palette.PALETTE_256.values()), reverse=True)
    gaps = [lightness[i] - lightness[i + 1] for i in range(len(lightness) - 1)]
    assert min(gaps) >= 0.14


def test_quantize_never_returns_a_themed_index():
    """0-15 are remapped by the user's terminal theme."""
    for r in range(0, 256, 17):
        for g in range(0, 256, 29):
            for b in range(0, 256, 41):
                assert palette.quantize(f"#{r:02x}{g:02x}{b:02x}") >= 16


def test_quantize_is_exact_for_colors_in_the_cube():
    assert palette.rgb_of(palette.quantize("#5f87af")) == "#5f87af"


def test_quantize_routes_spec_palette_through_the_pinned_table():
    for spec_hex, index in palette.PALETTE_256.items():
        assert palette.quantize(spec_hex) == index


def test_sgr_none_mode_emits_nothing():
    assert palette.sgr("#ff3f2f", "#ffffff", "none") == ""


def test_sgr_256_mode_emits_indexed_codes_only():
    code = palette.sgr("#ff3f2f", "#ffffff", "256")
    assert code == "\x1b[48;5;231;38;5;202m"


def test_sgr_rejects_an_unknown_color_mode():
    with pytest.raises(ValueError):
        palette.sgr("#ff3f2f", "#ffffff", "truecolor")
