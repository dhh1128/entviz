#!/usr/bin/env python3
"""Render the docs example entviz and the GitHub social-preview card.

This is the source of truth for two related assets, both written into
``docs/assets/`` alongside the rest of the documentation images:

    root-commit-entviz.svg   an entviz of THIS repo's root commit SHA. It is
                             both the example shown at the top of the docs
                             (docs/index.md) and the mark embedded in the card.
    social-card.svg          the composed 1280x640 Open Graph card (vector).
    social-card.png          the rasterized card you upload to GitHub (<1 MB).

The card is a specimen of the tool applied to itself: the repo's own root
commit SHA -- a real, immutable, crypto-grade hash -- rendered as an entviz.

Dependency-light: the Python standard library, the local ``entviz`` CLI (this
repo's own tool, on PATH after ``uv sync``), and ``cairosvg`` (a dev
dependency) for rasterization.

------------------------------------------------------------------------------
FAMILY TEMPLATE -- how to reuse this across repos
------------------------------------------------------------------------------
The look (palette, layout, typography, the left accent stripe) is SHARED so a
family of repos reads consistently. To adapt the card to another repo, change
ONLY the values in the ``KNOBS`` block below; everything under "SHARED FAMILY
CONSTANTS" stays identical across repos.

Per-repo knobs: REPO_NAME, OWNER, TAGLINE_LINES, LANGUAGE, LANGUAGE_DOT,
MARK, CAPTION.

``MARK`` selects the floating art on the right:
    "entviz-root"  -> entviz of this repo's root commit SHA (needs `entviz`).
    "<path.svg>"   -> embed an arbitrary SVG (e.g. a logo) at that path.
    None           -> text-only card (no floating mark).

Fonts: only families resolvable at raster time are used; the stacks end in
DejaVu Sans / DejaVu Sans Mono (present on most Linux/CI images), so the PNG
reproduces without bundling fonts.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
ASSETS = REPO_ROOT / "docs" / "assets"

# =============================================================================
# KNOBS -- the only things that change per repo.
# =============================================================================
REPO_NAME = "entviz"
OWNER = "dhh1128"
TAGLINE_LINES = [
    "Visualize high-entropy values",
    "as diagrams a human can",
    "compare at a glance.",
]
LANGUAGE = "Python"
LANGUAGE_DOT = "#3572A5"        # GitHub's linguist color for the language
LICENSE = "Apache-2.0"
# MARK: "entviz-root" | path to an .svg logo | None
MARK = "entviz-root"
# CAPTION: small mono line under the mark. {sha7} is filled from the resolved
# root commit when MARK == "entviz-root"; otherwise used as-is.
CAPTION = "root commit {sha7}"

# Output filenames (within docs/assets/).
ENTVIZ_SVG = ASSETS / "root-commit-entviz.svg"
CARD_SVG = ASSETS / "social-card.svg"
CARD_PNG = ASSETS / "social-card.png"

# =============================================================================
# SHARED FAMILY CONSTANTS -- keep identical across the repo family.
# =============================================================================
W, H = 1280, 640                # GitHub social preview canvas (exactly 2:1)

# The entviz palette, in CIELAB-lightness order. This is the family signature.
PALETTE = ["#ffffff", "#e7be00", "#ff3f2f", "#2f3fbf", "#000000"]
ACCENT = "#ff3f2f"              # red rule under the repo name
INK = "#111111"                 # primary text
INK_SOFT = "#333333"            # tagline text
INK_FAINT = "#6b6b6b"           # owner wordmark
INK_GHOST = "#9a9a9a"           # caption / license
HAIRLINE = "#dddddd"            # border framing the floating mark

SANS = ("'Helvetica Neue', Arial, 'Segoe UI', Roboto, "
        "'DejaVu Sans', sans-serif")
MONO = ("'JetBrains Mono', 'Menlo', 'Consolas', "
        "'DejaVu Sans Mono', monospace")

STRIPE_W = 26                   # left accent stripe (palette) width
TEXT_X = 78                     # left edge of the text column
MARK_RIGHT_MARGIN = 70          # gap from canvas right edge to the mark
MARK_TARGET_W = 450             # rendered width of the floating mark


def root_commit_sha() -> str:
    """The repo's first commit SHA -- immutable, globally unique, crypto-grade."""
    out = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "rev-list", "--max-parents=0", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.split()
    return out[-1]              # last line is the earliest root commit


def entviz_svg(value: str) -> str:
    """Render `value` as an entviz SVG via the local CLI (1:1 aspect)."""
    return subprocess.run(
        ["entviz", value, "--ar", "1:1", "--fs", "14", "--note", "git"],
        capture_output=True, text=True, check=True,
    ).stdout


def _svg_viewbox(svg: str) -> tuple[float, float]:
    vb = re.search(r'viewBox="([^"]+)"', svg).group(1).split()
    return float(vb[2]), float(vb[3])


def _svg_inner(svg: str) -> tuple[str, str]:
    """Return (viewBox, inner-markup) of an <svg> document for nesting."""
    vb = re.search(r'viewBox="([^"]+)"', svg).group(1)
    inner = svg[svg.index(">", svg.index("<svg")) + 1: svg.rindex("</svg>")]
    return vb, inner


def _esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_card_svg(mark_svg: str | None, caption: str) -> str:
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" font-family="{SANS}">',
        '<defs>'
        '<filter id="lift" x="-20%" y="-20%" width="140%" height="140%">'
        '<feDropShadow dx="0" dy="6" stdDeviation="9" '
        'flood-color="#000000" flood-opacity="0.16"/>'
        '</filter></defs>',
        # whole canvas is white -- the mark floats on it beside the text.
        f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
    ]

    # ---- left accent stripe: the 5-color palette (family signature) -----
    band = H / len(PALETTE)
    for i, color in enumerate(PALETTE):
        parts.append(
            f'<rect x="0" y="{i * band:.2f}" width="{STRIPE_W}" '
            f'height="{band:.2f}" fill="{color}"/>'
        )

    # ---- floating mark on the right, vertically centered -----------------
    # The entviz itself is centered on H/2; the caption sits just below it.
    if mark_svg:
        mw, mh = _svg_viewbox(mark_svg)
        scale = MARK_TARGET_W / mw
        dw, dh = mw * scale, mh * scale
        dx = W - MARK_RIGHT_MARGIN - dw
        dy = (H - dh) / 2
        vb, inner = _svg_inner(mark_svg)
        # soft drop shadow + hairline frame, so it reads as floating on white.
        parts.append(
            f'<rect x="{dx:.1f}" y="{dy:.1f}" width="{dw:.1f}" height="{dh:.1f}" '
            f'rx="8" fill="#ffffff" filter="url(#lift)"/>'
        )
        parts.append(
            f'<svg x="{dx:.1f}" y="{dy:.1f}" width="{dw:.1f}" height="{dh:.1f}" '
            f'viewBox="{vb}">{inner}</svg>'
        )
        parts.append(
            f'<rect x="{dx:.1f}" y="{dy:.1f}" width="{dw:.1f}" height="{dh:.1f}" '
            f'rx="8" fill="none" stroke="{HAIRLINE}" stroke-width="1"/>'
        )
        if caption:
            cx = dx + dw / 2
            cy = dy + dh + 28
            parts.append(
                f'<text x="{cx:.1f}" y="{cy:.1f}" font-family="{MONO}" '
                f'font-size="22" fill="{INK_GHOST}" text-anchor="middle">'
                f'{_esc(caption)}</text>'
            )

    # ---- left text column ------------------------------------------------
    parts.append(
        f'<text x="{TEXT_X}" y="156" font-size="34" font-weight="600" '
        f'fill="{INK_FAINT}" letter-spacing="2">{_esc(OWNER)}</text>'
    )
    parts.append(
        f'<text x="{TEXT_X}" y="300" font-size="140" font-weight="800" '
        f'fill="{INK}" letter-spacing="-2">{_esc(REPO_NAME)}</text>'
    )
    parts.append(
        f'<rect x="{TEXT_X}" y="332" width="120" height="6" fill="{ACCENT}"/>'
    )
    y = 408
    for line in TAGLINE_LINES:
        parts.append(
            f'<text x="{TEXT_X}" y="{y}" font-size="32" '
            f'fill="{INK_SOFT}">{_esc(line)}</text>'
        )
        y += 44

    # ---- footer: language dot + name, then license -----------------------
    fy = 562
    parts.append(f'<circle cx="{TEXT_X + 9}" cy="{fy - 9}" r="9" fill="{LANGUAGE_DOT}"/>')
    parts.append(
        f'<text x="{TEXT_X + 28}" y="{fy}" font-size="26" '
        f'fill="{INK_SOFT}">{_esc(LANGUAGE)}</text>'
    )
    parts.append(
        f'<text x="{TEXT_X + 170}" y="{fy}" font-size="26" '
        f'fill="{INK_GHOST}">{_esc(LICENSE)}</text>'
    )

    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def main() -> int:
    sha = root_commit_sha()
    caption = CAPTION.format(sha7=sha[:7])

    # 1) the example/mark entviz -- written so docs/index.md can embed it too.
    mark_svg = None
    if MARK == "entviz-root":
        mark_svg = entviz_svg(sha)
        ASSETS.mkdir(parents=True, exist_ok=True)
        ENTVIZ_SVG.write_text(mark_svg)
        print(f"wrote {ENTVIZ_SVG.relative_to(REPO_ROOT)}")
    elif MARK:
        mark_svg = Path(MARK).read_text()

    # 2) the composed card (vector source of truth).
    svg = build_card_svg(mark_svg, caption)
    CARD_SVG.write_text(svg)
    print(f"wrote {CARD_SVG.relative_to(REPO_ROOT)}")

    # 3) rasterize to PNG.
    try:
        import cairosvg
    except ImportError:
        sys.stderr.write(
            "cairosvg is required to rasterize the PNG.\n"
            "  uv add --dev cairosvg   (or)   pip install cairosvg\n"
        )
        return 1
    cairosvg.svg2png(
        bytestring=svg.encode(), write_to=str(CARD_PNG),
        output_width=W, output_height=H,
    )
    size_kb = CARD_PNG.stat().st_size / 1024
    print(f"wrote {CARD_PNG.relative_to(REPO_ROOT)} ({size_kb:.0f} KB, {W}x{H})")
    if CARD_PNG.stat().st_size > 1_000_000:
        sys.stderr.write("WARNING: social-card.png exceeds 1 MB.\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
