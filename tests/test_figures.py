"""Drift guard for the documentation figures (paper + spec).

The figures in docs/assets/paper/ (paper) and docs/assets/ (spec) are *generated*
from the live renderer by scripts/paper_figures.py and scripts/spec_figures.py
via the shared scripts/figlib.py. They are never hand-drawn or hand-edited.
These tests make "do the figures still match the algorithm/spec?" a CI question:

  * test_figure_svg_matches_committed — regenerates each figure's SVG in-process
    and asserts it byte-matches the committed file. If the renderer, the gallery,
    or the figure code changed, this fails until someone re-runs the generator
    and commits. (Forcing function for pixel/algorithm drift.)

  * test_figures_stamped_with_current_spec_version — every committed figure SVG
    carries data-spec-version == the current SPEC_VERSION, so a version bump trips
    the test even if pixels are unchanged. (Forcing function for conceptual drift.)

  * test_cell_layout_geometry_matches_renderer — the geometry the cell-layout
    figure draws (figlib.geometry) equals what a real render() actually emits, so
    the dimensioned diagram cannot quietly diverge from the renderer.

Only entviz + lxml + segno are needed (NOT cairosvg / the PNG step), so this runs
in the default CI env. Regenerate with:
    PYTHONPATH=src .venv/bin/python scripts/paper_figures.py
    PYTHONPATH=src .venv/bin/python scripts/spec_figures.py
"""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import figlib  # noqa: E402
import paper_figures  # noqa: E402
import spec_figures  # noqa: E402
from entviz import SPEC_VERSION  # noqa: E402
from entviz.pipeline import render  # noqa: E402

# (generator module, output dir) for each figure suite.
SUITES = [
    (paper_figures, os.path.join(ROOT, "docs", "assets", "paper")),
    (spec_figures, os.path.join(ROOT, "docs", "assets")),
]
CASES = [(mod, out, fn) for mod, out in SUITES for fn in mod.FIGURES]
IDS = [f"{mod.__name__}:{fn.__name__}" for mod, out, fn in CASES]

REGEN = "re-run scripts/{paper,spec}_figures.py and commit the result"


@pytest.mark.parametrize("mod,out,fn", CASES, ids=IDS)
def test_figure_svg_matches_committed(mod, out, fn):
    figlib.GENERATOR = mod.GEN  # stamp as this suite, regardless of import order
    name, svg = fn()
    path = os.path.join(out, name + ".svg")
    assert os.path.exists(path), f"{name}.svg is missing — {REGEN}"
    with open(path) as fh:
        committed = fh.read()
    assert committed == svg + "\n", (
        f"{name}.svg is stale: the generator's output no longer matches the committed "
        f"figure. The renderer/algorithm or the figure code changed — {REGEN}."
    )


def test_figures_stamped_with_current_spec_version():
    stale = []
    for mod, out, fn in CASES:
        figlib.GENERATOR = mod.GEN
        name, _ = fn()
        with open(os.path.join(out, name + ".svg")) as fh:
            if f'data-spec-version="{SPEC_VERSION}"' not in fh.read():
                stale.append(name)
    assert not stale, (
        f"these figures are not stamped with the current SPEC_VERSION ({SPEC_VERSION}): "
        f"{stale}. The spec version changed since they were last generated — {REGEN}, "
        f"and re-check the hardcoded annotation labels against the spec."
    )


def test_cell_layout_geometry_matches_renderer():
    """figlib.geometry(12) must match the dimensions a real 12pt render emits."""
    g = figlib.geometry(12)
    root = figlib.parse(render("0123456789abcdef0123456789abcdef", font_size_pt=12))
    data_cell = next(c for c in figlib.cells(root) if c.get("data-cell-blank") != "true")
    _, _, nw, nh = figlib.rect_box(figlib.nucleus(data_cell))
    box = figlib.surround_boxes(root)[0]
    bw, bh = float(box.get("width")), float(box.get("height"))
    assert (nw, nh) == pytest.approx((g["nucleus_width"], g["nucleus_height"])), \
        "nucleus geometry in figlib.geometry() diverged from the renderer; update cell-layout."
    assert (bw, bh) == pytest.approx((g["box_width"], g["box_height"])), \
        "surround-box geometry in figlib.geometry() diverged from the renderer; update cell-layout."
