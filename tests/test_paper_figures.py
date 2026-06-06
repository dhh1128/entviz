"""Drift guard for the academic-paper figures.

The figures in docs/assets/paper/ are *generated* by scripts/paper_figures.py
from the real renderer (entviz.pipeline.render) and the gallery SVGs. That makes
them track the algorithm automatically — but only if they are regenerated. These
tests make "do the figures still match the algorithm/spec?" a CI question:

  * test_figure_svg_matches_committed — regenerates each figure's SVG in-process
    and asserts it byte-matches the committed file. If the renderer, the gallery,
    or the figure code changed, this fails until someone re-runs the generator and
    commits. (The forcing function for *pixel* drift.)

  * test_figures_stamped_with_current_spec_version — asserts every committed SVG
    carries data-spec-version == the current SPEC_VERSION. A spec-version bump
    therefore trips the test even if pixels are unchanged, prompting a human to
    re-run the generator and eyeball the hardcoded annotation labels against the
    new spec. (The forcing function for *conceptual* drift.)

Only entviz + lxml + segno are needed here (NOT cairosvg / the PNG step), so the
test runs in the default CI test env. Regenerate with:
    PYTHONPATH=src .venv/bin/python scripts/paper_figures.py
"""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import paper_figures as figs  # noqa: E402
from entviz import SPEC_VERSION  # noqa: E402

OUT = os.path.join(ROOT, "docs", "assets", "paper")

REGEN = "re-run `PYTHONPATH=src .venv/bin/python scripts/paper_figures.py` and commit the result"


@pytest.mark.parametrize("fn", figs.FIGURES, ids=lambda f: f.__name__)
def test_figure_svg_matches_committed(fn):
    name, svg = fn()
    path = os.path.join(OUT, name + ".svg")
    assert os.path.exists(path), f"{name}.svg is missing — {REGEN}"
    with open(path) as fh:
        committed = fh.read()
    assert committed == svg + "\n", (
        f"{name}.svg is stale: the generator's output no longer matches the "
        f"committed figure. The renderer/algorithm or the figure code changed — {REGEN}."
    )


def test_figures_stamped_with_current_spec_version():
    stale = []
    for fn in figs.FIGURES:
        name, _ = fn()
        with open(os.path.join(OUT, name + ".svg")) as fh:
            if f'data-spec-version="{SPEC_VERSION}"' not in fh.read():
                stale.append(name)
    assert not stale, (
        f"these paper figures are not stamped with the current SPEC_VERSION "
        f"({SPEC_VERSION}): {stale}. The spec version changed since they were last "
        f"generated — {REGEN}, and re-check the hardcoded annotation labels against the spec."
    )
