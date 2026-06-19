"""Drift guard for the GitHub social-preview card and the docs example entviz.

scripts/social_card.py is the source of truth for three coupled assets in
docs/assets/:

    root-commit-entviz.svg   entviz of THIS repo's root commit SHA — embedded
                             both in the card and at the top of docs/index.md.
    social-card.svg          the composed 1280x640 Open Graph card (the
                             *vector source of truth*, per the script).
    social-card.png          a raster of that SVG, uploaded to GitHub.

Before this guard existed the card had no drift test: an algorithm change could
leave the self-image (a render of the repo's own root commit) silently stale.

These tests regenerate the SVGs in-process and byte-match them against the
committed files — no `entviz` console script on PATH and no cairosvg needed, so
they run in the default CI env (mirroring tests/test_figures.py). Regenerate
with:
    uv run python scripts/social_card.py

The PNG is a *derived raster* of the (guarded) SVG; raster bytes are not stable
across cairosvg / font versions, so it is not byte-compared. We assert only its
structural validity (present, canvas size, under GitHub's 1 MB cap). Its content
sync is guaranteed transitively: regenerate after any SVG change.
"""
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import social_card as sc  # noqa: E402

REGEN = "re-run scripts/social_card.py and commit the result"


def test_root_commit_entviz_matches_renderer():
    """root-commit-entviz.svg must be the current render of the root commit."""
    sha = sc.root_commit_sha()
    expected = sc.entviz_svg(sha)
    with open(sc.ENTVIZ_SVG, encoding="utf-8") as fh:
        committed = fh.read()
    assert committed == expected, (
        f"root-commit-entviz.svg is stale: the renderer/algorithm changed and "
        f"the embedded mark no longer matches — {REGEN}.")


def test_social_card_svg_matches_generator():
    """social-card.svg must match the composed card the generator builds now."""
    sha = sc.root_commit_sha()
    mark = sc.entviz_svg(sha)
    caption = sc.CAPTION.format(sha7=sha[:7])
    expected = sc.build_card_svg(mark, caption)
    with open(sc.CARD_SVG, encoding="utf-8") as fh:
        committed = fh.read()
    assert committed == expected, (
        f"social-card.svg is stale: the card layout or the embedded entviz "
        f"changed — {REGEN}.")


def _png_dimensions(path):
    """(width, height) from a PNG's IHDR chunk, using only the stdlib."""
    with open(path, "rb") as fh:
        header = fh.read(24)
    assert header[:8] == b"\x89PNG\r\n\x1a\n", f"{path} is not a PNG"
    width, height = struct.unpack(">II", header[16:24])
    return width, height


def test_social_card_png_present_and_valid():
    """The uploaded PNG exists, is the GitHub canvas size, and is under 1 MB."""
    assert os.path.exists(sc.CARD_PNG), f"social-card.png is missing — {REGEN}."
    size = os.path.getsize(sc.CARD_PNG)
    assert size < 1_000_000, (
        f"social-card.png is {size/1024:.0f} KB, over GitHub's 1 MB cap — {REGEN}.")
    assert _png_dimensions(sc.CARD_PNG) == (sc.W, sc.H), (
        f"social-card.png is not {sc.W}x{sc.H} — {REGEN}.")
