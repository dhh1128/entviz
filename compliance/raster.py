"""Tier B: canonical rasterization (the visual authority).

docs/spec.md → Conformance → "Canonical rasterization (Tier B)" requires that
an implementation's SVG, rasterized by one fixed reference rasterizer, match the
golden raster outside text-glyph regions, within a small anti-aliasing
tolerance.

**Text-region exclusion** is implemented the simplest robust way: every
``<text>`` element is *stripped* from the SVG before rasterization, of both the
golden and the candidate. SVG text has no layout side effects on other
elements, so stripping it leaves every other channel — surround boxes, nucleus
fills, the ellipse overlay, color-bar band fills, blank outlines + map dots, and
the gray borders — in exactly its painted place. Glyph shape (which varies by
platform font, explicitly a non-goal) therefore never enters the pixel
comparison; text is proven instead by Tier A. What remains *is* a proof of
layering, color, position, size, and occlusion of every non-text channel.

The reference rasterizer for this corpus is **CairoSVG** at a fixed scale; its
name + version + scale are recorded in the corpus manifest. (resvg is the
intended longer-term authority for closer browser fidelity; the rasterizer is
pluggable and pinned per corpus, so swapping it only requires regenerating the
golden PNGs.)
"""
from __future__ import annotations

import io
from dataclasses import dataclass

from lxml import etree

# Fixed rasterization scale (output px per SVG user unit). 2.0 gives sub-pixel
# headroom for the 1-px borders and thin ellipse stroke without ballooning file
# size. Recorded in the manifest so goldens are reproducible.
DEFAULT_SCALE = 2.0

# Per-channel (0-255) tolerance: anti-aliasing only. A conformant non-text
# channel must paint the same color in the same place; AA fringes at edges may
# differ by a few levels between equal SVGs rendered twice.
DEFAULT_CHANNEL_TOL = 16
# Allow this fraction of pixels to exceed the channel tolerance (AA fringe area
# scales with the perimeter of painted shapes, a small share of total area).
DEFAULT_PIXEL_FRACTION = 0.002


def rasterizer_id() -> str:
    """Human-readable id of the pinned reference rasterizer (for the manifest)."""
    try:
        import cairosvg
        ver = getattr(cairosvg, "__version__", "unknown")
    except Exception:  # pragma: no cover - import guard
        ver = "unavailable"
    return f"cairosvg-{ver}@scale{DEFAULT_SCALE}"


def strip_text(svg: str | bytes) -> bytes:
    """Return the SVG with every <text> element removed (Tier B exclusion)."""
    if isinstance(svg, str):
        svg = svg.encode("utf-8")
    root = etree.fromstring(svg)
    for el in list(root.iter()):
        tag = el.tag
        if isinstance(tag, str) and tag.split("}")[-1] == "text":
            parent = el.getparent()
            if parent is not None:
                parent.remove(el)
    return etree.tostring(root)


def rasterize(svg: str | bytes, scale: float = DEFAULT_SCALE,
              exclude_text: bool = True) -> bytes:
    """Rasterize an entviz SVG to PNG bytes via the pinned reference rasterizer."""
    import cairosvg
    data = strip_text(svg) if exclude_text else (
        svg.encode("utf-8") if isinstance(svg, str) else svg)
    return cairosvg.svg2png(bytestring=data, scale=scale)


@dataclass
class RasterDiff:
    ok: bool
    width: int
    height: int
    total_pixels: int
    diff_pixels: int            # pixels exceeding channel tolerance
    max_channel_diff: int
    fraction: float
    note: str = ""


def compare_png(golden_png: bytes, actual_png: bytes,
                channel_tol: int = DEFAULT_CHANNEL_TOL,
                pixel_fraction: float = DEFAULT_PIXEL_FRACTION) -> RasterDiff:
    """Compare two PNGs pixel-by-pixel (RGBA), within tolerance."""
    from PIL import Image
    import numpy as np

    a = Image.open(io.BytesIO(golden_png)).convert("RGBA")
    b = Image.open(io.BytesIO(actual_png)).convert("RGBA")
    if a.size != b.size:
        return RasterDiff(
            ok=False, width=a.size[0], height=a.size[1],
            total_pixels=a.size[0] * a.size[1], diff_pixels=-1,
            max_channel_diff=-1, fraction=1.0,
            note=f"size mismatch golden={a.size} actual={b.size}",
        )
    aa = np.asarray(a, dtype=np.int16)
    ba = np.asarray(b, dtype=np.int16)
    delta = np.abs(aa - ba)
    per_pixel_max = delta.max(axis=2)
    over = per_pixel_max > channel_tol
    diff_pixels = int(over.sum())
    total = per_pixel_max.size
    frac = diff_pixels / total if total else 0.0
    return RasterDiff(
        ok=(frac <= pixel_fraction),
        width=a.size[0], height=a.size[1], total_pixels=total,
        diff_pixels=diff_pixels, max_channel_diff=int(per_pixel_max.max()),
        fraction=frac,
    )
