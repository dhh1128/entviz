"""
V3-1: color bar band heights are weighted by count^4, not raw counts.
The skew amplifies the dominance of the most-used color so the bar
reads as a clear pecking order instead of four near-equal stripes
(see docs/spec-improvement-notes.md item 1).
"""
from lxml import etree

from entviz.layout import Point, Rect, Size
from entviz.pipeline import _draw_color_bar


def test_band_heights_use_count_pow_4():
    # Counts (4, 3, 2, 1) under raw weighting → bands (4, 3, 2, 1) / 10
    # = (40, 30, 20, 10) px of a 100-px-tall bar.
    # Under count^4 weighting → (256, 81, 16, 1) / 354 ≈
    # (72.3, 22.9, 4.5, 0.28) px. The dominant band is roughly 70+%
    # of the bar instead of 40%.
    edge_colors = ['#aaaaaa', '#bbbbbb', '#cccccc', '#dddddd']
    color_usage = {c: 4 - i for i, c in enumerate(edge_colors)}
    bounding = Rect(Point(0, 0), Size(8, 100))

    svg = etree.Element('svg')
    _draw_color_bar(svg, bounding, gm=8, color_usage=color_usage,
                    edge_colors=edge_colors)

    bands = svg.xpath('//*[local-name()="rect"]')
    assert len(bands) == 4
    heights = [float(b.get('height')) for b in bands]

    # First band should be roughly 72% of the bar — well above the
    # 40% it would get under raw counts.
    assert heights[0] > 65
    # Last band should be barely visible — well below the 10% it would
    # get under raw counts.
    assert heights[3] < 3
    # All heights still sum to the bounding rect height (last band
    # absorbs floating-point slack).
    assert abs(sum(heights) - 100) < 0.01


def test_band_heights_match_pow_4_ratios_exactly():
    # Pin the exact ratios for a single specific case so a regression
    # to raw counts (or to count^3, count^2) would fail.
    edge_colors = ['#a', '#b', '#c', '#d']
    color_usage = {'#a': 3, '#b': 2, '#c': 1, '#d': 0}
    bounding = Rect(Point(0, 0), Size(8, 1000))

    svg = etree.Element('svg')
    _draw_color_bar(svg, bounding, gm=8, color_usage=color_usage,
                    edge_colors=edge_colors)
    bands = svg.xpath('//*[local-name()="rect"]')
    # Three nonzero bands; '#d' with count 0 is omitted.
    assert len(bands) == 3
    heights = [float(b.get('height')) for b in bands]

    # Expected: 81 / 98 ≈ 0.8265 → 826.5; 16 / 98 → 163.3; 1 / 98 → 10.2
    # (last band absorbs the residual to reach 1000 exactly.)
    total = 81 + 16 + 1
    expected = [1000 * 81 / total, 1000 * 16 / total, 1000 - 1000 * 81 / total - 1000 * 16 / total]
    for h, e in zip(heights, expected):
        assert abs(h - e) < 0.01, f"band height {h} ≠ expected {e}"
