"""Drift guard for the documentation gallery (docs/assets/gallery/ + gallery.html).

The gallery SVGs are *generated* from the live renderer by scripts/gallery.py:
each card's image is exactly ``render(entropy, **kwargs)`` for a curated input.
They are never hand-edited. Before this guard existed the gallery was the one
self-image with no drift test — a renderer/algorithm change could leave the
committed gallery (and the entvizes embedded from it into paper/spec figures)
silently stale until the next release cut regenerated it.

These tests make "does the gallery still match the algorithm?" a CI question,
mirroring tests/test_figures.py:

  * test_gallery_svg_matches_committed — regenerates each entry's SVG in-process
    and asserts it byte-matches the committed file (or, if an input no longer
    renders, that no stale file lingers). Forcing function for pixel/algorithm
    drift, and a spec-version bump trips it too (render() stamps the version).

  * test_gallery_dir_matches_entries — the set of committed SVGs equals exactly
    the set the generator would write, catching renamed/removed entries that
    left orphaned files (the generator wipes the dir each run, so an orphan is
    real drift).

  * test_gallery_html_stamped_with_current_versions — the page title carries the
    current SPEC_VERSION and library __version__; a lib-version bump that does
    not change SVG bytes still trips this.

Only entviz is needed (no cairosvg / raster step), so this runs in the default
CI env. Regenerate with:
    uv run python scripts/gallery.py
"""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import gallery  # noqa: E402
from entviz import SPEC_VERSION, __version__  # noqa: E402
from entviz.pipeline import render  # noqa: E402

GALLERY_DIR = os.path.join(ROOT, "docs", "assets", "gallery")
GALLERY_HTML = os.path.join(ROOT, "docs", "gallery.html")
REGEN = "re-run scripts/gallery.py and commit the result"

ENTRIES = list(gallery.iter_entries())
IDS = [fn for _t, fn, _l, _e, _k in ENTRIES]


def _renders(entropy, kwargs):
    """(ok, svg): the generator writes an SVG only when render() succeeds; a
    parser corner case that raises produces an error card and no file."""
    try:
        return True, render(entropy, **kwargs)
    except Exception:
        return False, None


@pytest.mark.parametrize("section,filename,label,entropy,kwargs", ENTRIES, ids=IDS)
def test_gallery_svg_matches_committed(section, filename, label, entropy, kwargs):
    path = os.path.join(GALLERY_DIR, filename)
    ok, svg = _renders(entropy, kwargs)
    if not ok:
        assert not os.path.exists(path), (
            f"{filename}: input no longer renders, but a committed gallery SVG "
            f"still exists — {REGEN}.")
        return
    assert os.path.exists(path), f"{filename} is missing — {REGEN}."
    with open(path, encoding="utf-8") as fh:
        committed = fh.read()
    # gallery.py writes render() output verbatim (no trailing newline).
    assert committed == svg, (
        f"{filename} is stale: the generator's output no longer matches the "
        f"committed gallery SVG. The renderer/algorithm changed — {REGEN}.")


@pytest.mark.parametrize("section,filename,label,entropy,kwargs", ENTRIES, ids=IDS)
def test_gallery_entry_renders(section, filename, label, entropy, kwargs):
    """Every curated gallery input MUST render without raising.

    The gallery is a showcase, not a fuzz corpus: an entry that raises is a
    broken sample (a bogus/invalid address, a mistyped checksum), not an
    interesting edge case. gallery.py degrades a raise into an inline error
    card so the page still builds, which means a broken sample can sit in the
    committed gallery unnoticed. This guard makes "the whole gallery renders"
    a CI invariant so curated inputs stay valid."""
    try:
        svg = render(entropy, **kwargs)
    except Exception as e:  # noqa: BLE001 — the whole point is to surface any raise
        raise AssertionError(
            f"gallery entry {filename} ({label!r}) failed to render: "
            f"{type(e).__name__}: {e}. Fix the sample input in scripts/gallery.py "
            f"(the gallery is a curated showcase — every entry must render)."
        ) from e
    assert svg.lstrip().startswith("<svg"), f"{filename}: render() did not return an SVG"


def test_gallery_dir_matches_entries():
    """No orphans, no missing: the committed SVG set equals what the generator
    would write (only entries that render successfully get a file)."""
    expected = {fn for _t, fn, _l, e, k in ENTRIES if _renders(e, k)[0]}
    on_disk = {f for f in os.listdir(GALLERY_DIR) if f.endswith(".svg")}
    assert on_disk == expected, (
        f"gallery dir out of sync — unexpected={sorted(on_disk - expected)}, "
        f"missing={sorted(expected - on_disk)}; {REGEN}.")


def test_gallery_html_stamped_with_current_versions():
    with open(GALLERY_HTML, encoding="utf-8") as fh:
        page = fh.read()
    stamp = f"Entviz {SPEC_VERSION}, generated by lib v{__version__}"
    assert stamp in page, (
        f"gallery.html title is not stamped with the current versions "
        f"({stamp!r}); the spec or library version changed — {REGEN}.")
