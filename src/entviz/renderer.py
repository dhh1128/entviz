from lxml import etree
from .layout import Cell, Point
from .colors import get_nucleus_colors, closest_palette_color, VisualStyle


# Pinned monospace fallback chain (review F-A5; refreshed for cross-platform
# coverage in v6). JetBrains Mono leads: not preinstalled anywhere, but widely
# installed by developers and the strongest at homoglyph disambiguation, so
# viewers who have it get the best rendering. The rest route each platform to a
# good preinstalled mono — Menlo (macOS, iOS), Consolas (Windows), DejaVu Sans
# Mono / Liberation Mono (Linux), Roboto Mono / Noto Sans Mono (Android,
# ChromeOS) — and bare `monospace` is the last resort. Bare `monospace` alone
# (the pre-F-A5 value) left glyph metrics and homoglyph behavior up to each
# viewer's OS, a real cross-viewer hazard for the text channel.
MONOSPACE_FONT_FAMILY = (
    '"JetBrains Mono", "Menlo", "Consolas", "DejaVu Sans Mono", '
    '"Liberation Mono", "Roboto Mono", "Noto Sans Mono", monospace'
)


class Renderer:
    def __init__(self, style: VisualStyle, grid):
        self.style = style
        self.grid = grid

    def render_edges(self, svg: etree.Element, ftok, cell: Cell, nucleus_bg: str,
                     edge_override=None):
        """
        v4 surround: 24 small boxes around the nucleus. Bit i of ftok.quant
        (LSB=bit 0) selects box i (clockwise from the top-left of the top
        row). A set bit draws a small box filled with this cell's edge
        color — the palette entry (one of the 4 non-bg colors) that is
        perceptually closest to the nucleus_bg under weighted RGB
        distance. A clear bit draws nothing.

        v10: `edge_override` (a hex color) forces the edge color instead of
        the nearest-palette echo — used for the fingerprint-edge cells
        (top-left + 1st/2nd quartile), whose surround colour is drawn from
        the fingerprint so it avalanches to a casual glance.

        v10: the set boxes are emitted as a SINGLE `<path>` (one subpath per
        box) rather than one `<rect>` each — repeated box rects were ~a third
        of a dense entviz. The bit pattern and edge color are declared on the
        cell GROUP (`data-surround-bits` / `data-edge-color`) by the caller, so
        a checker recovers the channel from the attribute, not by measuring
        geometry; this path is purely the rendered pixels. `svg` is the
        surround layer — painted before the cell groups and the ellipse overlay
        — so the path MUST stay here for the overlay to composite over the boxes
        exactly as before (paint order is normative). Returns
        `(surround_bits, edge_color)` for the caller to stamp on the cell group.
        """
        edge_color = (edge_override if edge_override is not None
                      else closest_palette_color(nucleus_bg, self.style.edge_colors))
        bw = cell.box_width
        bh = cell.box_height
        bits = 0
        subpaths = []
        for i in range(24):
            if not (ftok.quant >> i) & 1:
                continue
            bits |= (1 << i)
            origin = cell.box_origin(i)
            subpaths.append(f"M{origin.x} {origin.y}h{bw}v{bh}h-{bw}z")
        if subpaths:
            etree.SubElement(svg, 'path', fill=edge_color, d="".join(subpaths))
        return bits, edge_color

    def render_nucleus(self, svg: etree.Element, token, cell: Cell,
                       text_size_px=None, bg_override=None, inner_border=None):
        """Nucleus rect + centered token text.

        `bg_override` (a hex color) forces the nucleus background — used for
        the v6 fingerprint-middle cells, which are painted with the entviz
        background color. The foreground color follows the same Oklab
        contrast rule (computed by re-deriving via get_nucleus_colors on the
        override color's quant). When None, the bg is the token's entropy
        color as usual.

        `inner_border` (a hex color) draws a 1-px stroke flush with the
        nucleus edge — used to frame the v6 fingerprint-middle cells so they
        read as distinct from the entropy cells. When None, no border.
        """
        if bg_override is not None:
            r = int(bg_override[1:3], 16)
            g = int(bg_override[3:5], 16)
            b = int(bg_override[5:7], 16)
            bg_color, fg_color = get_nucleus_colors(r | (g << 8) | (b << 16))
        else:
            bg_color, fg_color = get_nucleus_colors(token.quant)
        n = cell.nucleus
        etree.SubElement(svg, 'rect',
                         x=str(n.left), y=str(n.top),
                         width=str(n.size.width), height=str(n.size.height),
                         fill=bg_color)
        if inner_border is not None:
            # 1-px stroke flush with the nucleus boundary: centered on the
            # half-pixel just inside each edge, so the stroke's outer edge sits
            # exactly on the nucleus rect and paints its outermost pixel ring
            # (no gap of background color between the frame and the edge).
            etree.SubElement(svg, 'rect',
                             x=str(n.left + 0.5), y=str(n.top + 0.5),
                             width=str(n.size.width - 1), height=str(n.size.height - 1),
                             fill='none', stroke=inner_border,
                             **{'stroke-width': '1'})
        if text_size_px is None:
            text_size_px = cell.size.height / 2
        text_el = etree.SubElement(svg, 'text',
                                   x=str(n.center.x), y=str(n.center.y),
                                   fill=fg_color,
                                   **{"font-size": str(text_size_px),
                                      "text-anchor": "middle", "dominant-baseline": "central"})
        text_el.text = token.text

    def draw_quartile_mark(self, svg: etree.Element, cell: Cell,
                           quartile_index: int, fg_color: str):
        """
        v4 quartile mark: small right triangle in one corner of the nucleus.
        Both legs = nucleus_height / 2; the right-angle vertex sits at the
        nucleus corner matching the quartile (1st=TL, 2nd=TR, 3rd=BR,
        4th=BL); each leg runs along one of the nucleus's two edges meeting
        at that corner. Filled in the cell's text foreground color so the
        mark sits on top of the nucleus_bg in the same color as the cell
        text (black on light nuclei, white on dark) — small enough not to
        intrude on text readability, but unambiguous as a corner marker.
        Quartile identity comes from triangle orientation alone.
        """
        n = cell.nucleus
        leg = n.size.height / 2
        if quartile_index == 0:        # 1st: TL corner
            pts = [n.top_left,
                   Point(n.left + leg, n.top),
                   Point(n.left, n.top + leg)]
        elif quartile_index == 1:      # 2nd: TR corner
            pts = [n.top_right,
                   Point(n.right - leg, n.top),
                   Point(n.right, n.top + leg)]
        elif quartile_index == 2:      # 3rd: BR corner
            pts = [n.bottom_right,
                   Point(n.right, n.bottom - leg),
                   Point(n.right - leg, n.bottom)]
        else:                          # 4th: BL corner
            pts = [n.bottom_left,
                   Point(n.left, n.bottom - leg),
                   Point(n.left + leg, n.bottom)]
        etree.SubElement(
            svg, 'polygon',
            points=" ".join(f"{p.x},{p.y}" for p in pts),
            fill=fg_color,
        )
