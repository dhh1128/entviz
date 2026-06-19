"""Guard against stale blank-map marker callouts in the CRC figures.

Figure 4f (paper) and Figure 5 (spec) annotate the blank-cell map's max/min
markers. Those markers are recoloured to luminance contrast when the map cell
is fingerprint-filled (v10), so a hardcoded "red plus / blue dot" callout goes
stale silently — the figure-drift test compares SVG bytes, not whether a
callout's colour matches what it points at. This test closes that gap: each
map-marker leader dot must be drawn in the marker's *actual* rendered colour.

(The figure scripts read the colour from the embedded art; this test fails if
anyone reverts to a hardcoded colour that contradicts the render.)
"""
import os

from lxml import etree

SVG = "{http://www.w3.org/2000/svg}"
ROOT = os.path.join(os.path.dirname(__file__), "..")

FIGURES = [
    "docs/assets/paper/fig-4f-crc.svg",   # paper Figure 4f
    "docs/assets/crc.svg",                # spec Figure 5
]


def _marker_and_leader_colors(svg_path):
    """Return (art_max, art_min, leader_fills): the embedded entviz's actual
    map-marker colours (max = the plus path's stroke, min = the dot circle's
    fill) and the fills of the figure's own leader dots (direct-child circles;
    the art's markers are nested deeper, so they are excluded)."""
    root = etree.parse(svg_path).getroot()
    max_el = next(e for e in root.iter() if e.get("data-blank-map-max") is not None)
    min_el = next(e for e in root.iter() if e.get("data-blank-map-min") is not None)
    leader_fills = {c.get("fill") for c in root.findall(SVG + "circle")}
    return max_el.get("stroke"), min_el.get("fill"), leader_fills


def test_crc_figures_callout_colors_match_rendered_markers():
    for rel in FIGURES:
        path = os.path.join(ROOT, rel)
        art_max, art_min, leaders = _marker_and_leader_colors(path)
        assert art_max in leaders, (
            f"{rel}: the max-marker callout must use the plus's actual colour "
            f"{art_max!r}; leader dots were {leaders}")
        assert art_min in leaders, (
            f"{rel}: the min-marker callout must use the dot's actual colour "
            f"{art_min!r}; leader dots were {leaders}")
