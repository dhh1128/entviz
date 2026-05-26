"""
V3-6b: render v3 edge shapes (path-based, with tab + hinge rotation).

Each v3 shape is a single SVG <path> in 24×8 canonical edge space.
Placement at a cell's edge requires:
  - scaling to per-font_size pixel units (scale = edge_size / 8)
  - rotation appropriate to the edge orientation
  - translation to the edge_rect's screen position
  - clipping to the edge_rect for rotated (vertical) edges, so canonical
    content outside the 16-wide tab window doesn't leak into neighbors

Empty shapes (C4, P4) render nothing.

Color is applied by the existing per-edge linear gradient from v2
(nucleus_bg at inner → edge_color at outer); the gradient is created
by the caller (`Renderer.render_edges`) and passed in as fill_url.
"""
from lxml import etree


# Canonical edge-space dimensions.
_CANONICAL_W = 24
_CANONICAL_H = 8


def add_v3_shape_defs(defs):
    """
    Emit the 6 non-empty v3 shape paths into <defs> as referenceable
    <path id="cN"|"pN"> elements. Each carries fill-rule="evenodd" so
    holes / pieces / self-touching outlines resolve correctly when the
    shape is referenced via <use>. No fill or transform is set here;
    those come from each <use> call site.

    Idempotent: safe to call multiple times per render (only adds defs
    that don't already exist).
    """
    from .v3_shapes import C1, C2, C3, P1, P2, P3
    existing = {
        p.get("id")
        for p in defs.xpath('./*[local-name()="path"]')
        if p.get("id")
    }
    for shape in [C1, C2, C3, P1, P2, P3]:
        sid = shape.name.lower()
        if sid in existing:
            continue
        etree.SubElement(
            defs, 'path',
            id=sid,
            d=shape.path_d,
            **{'fill-rule': 'evenodd'},
        )


def _transform_for_edge(edge_index, edge_rect, scale, hinge):
    """
    Return the SVG transform attribute string for placing a canonical
    24×8 shape at the given edge_index of a cell.

    Edges 0/1: top-left/top-right horizontal — no rotation.
    Edges 3/4: bottom-right/bottom-left horizontal — 180° around the
               canonical center.
    Edge 2: right vertical — 90° around the shape's hinge.
    Edge 5: left vertical — 270° around the shape's hinge.
    """
    if edge_index in (0, 1):
        # No rotation; just scale and translate.
        return f"translate({edge_rect.left}, {edge_rect.top}) scale({scale})"

    if edge_index in (3, 4):
        # 180° around the canonical center (12, 4). Pivot is in scaled
        # (post-scale) coordinates, hence the multiplication.
        cx = 12 * scale
        cy = 4 * scale
        return (
            f"translate({edge_rect.left}, {edge_rect.top}) "
            f"rotate(180 {cx} {cy}) scale({scale})"
        )

    # Vertical edges use the hinge for rotation.
    hx, hy = hinge
    sx = hx * scale
    sy = hy * scale  # hy is always 0 in our shapes, but keep general.

    if edge_index == 2:
        # 90° rotation. Rotated tab bbox in scaled canonical coords:
        # x ∈ [s*(window_left - 8), s*window_left], y ∈ [0, s*16].
        # Want to land at edge_rect (8×16 px at right of cell).
        tx = edge_rect.left - sx + 8 * scale
        ty = edge_rect.top
        return (
            f"translate({tx}, {ty}) rotate(90 {sx} {sy}) scale({scale})"
        )

    if edge_index == 5:
        # 270° rotation. Rotated tab bbox:
        # x ∈ [s*window_left, s*(window_left + 8)], y ∈ [-s*16, 0].
        # Want to land at edge_rect (8×16 px at left of cell).
        tx = edge_rect.left - sx
        ty = edge_rect.bottom
        return (
            f"translate({tx}, {ty}) rotate(270 {sx} {sy}) scale({scale})"
        )

    raise ValueError(f"bad edge_index {edge_index}")


def _needs_tab_clip(edge_index):
    """Vertical edges (2, 5) need clipping to confine the rotated tab."""
    return edge_index in (2, 5)


def draw_v3_shape(svg_parent, defs, shape, cell, edge_index, scale, fill_url):
    """
    Emit a v3 shape into svg_parent for the given cell and edge_index.

    Empty shapes emit nothing.

    For non-empty shapes:
      - Compute the transform mapping canonical 24×8 to the edge_rect's
        screen position.
      - For vertical edges, wrap the <path> in a <g clip-path> that clips
        to the edge_rect so the canonical content outside the tab window
        is discarded after rotation.
      - The path's fill is `fill_url` (the per-edge linear gradient
        referenced by `url(#…)`).
      - fill-rule="evenodd" so holes, pieces, and self-touching outlines
        resolve correctly.
    """
    if shape.is_empty:
        return

    edge_rect = cell.edge_rect(edge_index)
    transform = _transform_for_edge(edge_index, edge_rect, scale, shape.hinge)
    shape_href = f"#{shape.name.lower()}"

    if _needs_tab_clip(edge_index):
        # One clipPath per drawn vertical edge. V3-7 keeps these
        # per-edge because each rect is a different position; collapsing
        # them would require objectBoundingBox + per-cell layout work
        # that's outside the scope of this phase.
        clip_seq = defs.get('data-v3-clip-seq', '0')
        next_id = f"v3clip-{clip_seq}"
        defs.set('data-v3-clip-seq', str(int(clip_seq) + 1))
        cp = etree.SubElement(defs, 'clipPath', id=next_id)
        etree.SubElement(
            cp, 'rect',
            x=str(edge_rect.left), y=str(edge_rect.top),
            width=str(edge_rect.size.width), height=str(edge_rect.size.height),
        )
        # clip-path on the wrapper <g> (not on the use), so the clip rect
        # stays axis-aligned in screen space while the shape rotates
        # inside it (see test_ellipse_clip_fix for the same pattern).
        clipped = etree.SubElement(
            svg_parent, 'g', **{'clip-path': f'url(#{next_id})'}
        )
        etree.SubElement(
            clipped, 'use',
            href=shape_href, transform=transform, fill=fill_url,
        )
    else:
        etree.SubElement(
            svg_parent, 'use',
            href=shape_href, transform=transform, fill=fill_url,
        )
