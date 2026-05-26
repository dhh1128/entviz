# Spec improvement notes (post-v2)

Issues observed after rendering a gallery of real entvizes (see
`refs/gallery/`). These are inputs to the *next* spec revision — they
are not commitments. Each item describes the problem, the proposed
direction, and any open questions that need to be settled before
implementation.

---

## 1. Color bar bands look almost uniform in practice (LOCKED)

**Problem.** In real-world inputs, the four edge-color counts cluster
around the mean. With 132 edge rects on a 22-cell grid and 4 colors,
each color averages ~33 uses. Random variation typically puts every
band within a band-height ratio of roughly 0.8–1.2, so the color bar
becomes a row of four near-equal stripes that doesn't communicate
much at a glance. That defeats its purpose as a *gestalt difference
amplifier*.

**Decision.** Apply the skew `count_i ^ 4` to each color's count
before computing band heights:

```
band_height_i ∝ count_i ^ 4
```

Renormalize so the bands sum to the bounding-rect height as before.

**Why 4 specifically.** Cubing (counts^3) provided moderate skew but
still left runners-up as visible bands when the count lead was modest.
Fourth-power more aggressively collapses runners-up so the dominant
color reliably claims most of the bar even when the absolute count
lead is small (gallery comparison: see
`refs/gallery/`, `refs/gallery3/`, `refs/gallery4/`). Higher exponents
would push toward "winner takes everything" with no useful secondary
information; lower exponents leave the bar too uniform to read at a
glance.

**Implementation details.**
- Counts of 0 stay at 0 height (skewing zero is still zero); the
  skew applies only to nonzero bands.
- Band ordering: descending by `count^4`. Since `x^4` is monotonic
  for non-negative x, this is identical to descending by `count`,
  so the existing ordering rule is unchanged — only the heights
  shift.
- Tiebreak between equal counts remains by the color's index in
  `edge_colors` (unchanged from v2). Cubing equal counts still
  yields equal cubed counts, so the tiebreak is still meaningful.
- The bar no longer permits "exact count recovery" from band height
  — but the color bar was never a precise channel anyway. The
  gestalt benefit of a readable dominance pattern is worth the
  trade.

---

## 2. Color bar needs a visible frame (LOCKED)

**Problem.** The v2 bounding rect has a black border on top, right,
and bottom only — the color bar's left edge is the canvas edge with no
black line. There's also no black line between the color bar and the
grid area. The result reads as if the color bar is floating outside
the entviz rather than being part of it. It also makes "the entviz"
visually ambiguous: is the bounding rect the whole thing, or just the
grid + SCS?

**Decision.** Three coupled changes:

1. **Black 1-px line on the color bar's left edge.** This makes the
   bounding rect a closed box on all four sides — much easier to read
   as one unit.
2. **Black 1-px line on the color bar's right edge** (separating it
   from the grid area). The color bar then looks like a deliberate
   inset panel rather than a leftmost margin.
3. **Color bar width = `edge_size`** (= `2·GM`, 8 px nominal at
   12pt/96 DPI). The v2 width of `GM` (4 px) was too narrow for the
   bands to read as distinct color blocks; widening to `edge_size`
   gives the bands real presence and makes the cubed-skew dominance
   (item 1) visually obvious.

**Updated bounding rect width formula:**

```
v2:  bounding_w =       GM     + GM + grid_w + GM + 1
v3:  bounding_w = 1 + edge_size + GM + grid_w + GM + 1
              = 1 +    2·GM   + GM + grid_w + GM + 1
```

Net change: `+1 + GM` (one extra px for the new left border, plus the
color-bar widening from `GM` to `2·GM`). At nominal: `141 → 146` px
for the 2-col UUID example.

**Updated horizontal layout, left to right:**

| Width | Contents |
|---|---|
| 1 | black left border |
| 2·GM | color bar (drawing region; height shrinks by 2 px from top/bottom black borders) |
| 1 | black interior separator |
| GM | white margin |
| `grid_w` | grid_rect |
| GM | white margin |
| 1 | black right border |

`bounding_rect.height` formula is unchanged. The color bar's *drawing
region* in screen coords runs from `y = 1` to `y = bounding_h - 1`
(the top and bottom black border lines cover its top and bottom
pixel rows), giving the color bar an effective drawing height of
`bounding_h - 2`.

The top and bottom black border lines now extend the full width of
the bounding rect (not just from `x = GM` rightward as in v2), since
there's no longer a "naked" color bar strip to skip — the color bar
is now framed by its own black lines.

---

## 3. Shape count summary styling (LOCKED)

**Problem.** SCS text currently renders at the same size and weight as
the cell text (16 px monospace, black). It competes for attention with
the cell text and looks like another row of token text rather than a
quiet summary.

**Decision.**

- **Fill = `#444`** (dark gray) instead of pure black. Quiet but
  legible. `#444` is L≈0.27 in HLS — comfortably in the "dark" half,
  so the ellipse-fill luminance rule (item 4) is unaffected.

- **Rendered font size = `min(0.9 × reference_font_size,
  cell_text_rendered_font_size)`** (then rounded to whole points).
  In words: the SCS is 90% of the reference size, *but never larger
  than the cell text itself*.

  Why the `min`: for hex inputs, item 5 already shrinks the cell text
  to 75% of reference (rendered = 9pt at 12pt reference). 90% of
  reference (10.8pt → 11pt) would then be *larger* than the cell
  text, which inverts the intended hierarchy. The `min` keeps the SCS
  the same size as the cell text in the hex case, with the visual
  hierarchy coming entirely from the `#444` fill instead. For
  non-hex inputs, the SCS clearly reads as secondary at both font
  size (90%) and color (`#444`).

**Worked values** at 12pt reference:

| Cell text type | Cell text rendered pt | SCS rendered pt |
|---|---|---|
| 4-char (base64 / base58) | 12 | 11 *(= round(0.9 × 12) = 10.8 → 11)* |
| 6-char (hex) | 9 | 9 *(= min(11, 9))* |

**Line height reserved beneath the grid** stays at `nucleus_height`
(unchanged from v2). It's a fixed slot in the bounding rect height
formula and shouldn't shift just because the SCS text happens to be
smaller — that would couple the bounding-rect height to the rendered
font size, which is unwanted (geometry only depends on reference).

## Terminology (used throughout this doc and the next spec revision)

- **Reference font size** — the configurable input (nominally 12pt)
  that drives *all geometry*: nucleus_height, cell dimensions, GM,
  bounding rect, edge_size, color bar width, etc. Reference never
  appears in SVG output directly; it's only used to compute pixel
  layout.

- **Rendered font size** — the actual size applied to a specific
  text element when emitted to SVG. Defaults to the reference, but
  may be reduced per the rules above (75% for hex cell text, 90% of
  reference for SCS, capped by cell text size). Different text
  elements within the same entviz can have different rendered sizes;
  this never affects geometry.

---

## 4. Ellipse overlay rework (LOCKED)

**Problem.** v2's ellipse is sized so its smaller semi-axis is ≥ half
the diagonal of the bounding rect. At that scale the visible arc reads
as a near-straight gradient edge, not as a curvy gestalt silhouette.
The overlay also picks its anchor on the bounding rect's perimeter,
which compounds the flatness — the curve enters and exits the bounding
rect on nearby edges.

**Decision.** The overlay is still a single semi-transparent ellipse,
but every input changes:

- **Anchor** moves from the bounding rect's perimeter to a strictly-
  interior corner of the grid (a cell-corner that is not on the
  bounding box of the grid). The anchor is at the *center* of the
  ellipse, not on its boundary. Pool size for an N×M grid is
  `(N−1) × (M−1)`.
- **Both axes (rx, ry) are independent** and each drawn from
  `[cell_h, d_far − cell_w]`, where `d_far` is the distance from the
  chosen anchor to the farthest outer corner of the grid. The lower
  bound prevents tiny invisible curves; the upper bound prevents the
  v2 "ellipse so big the visible arc is flat" failure.
- **Rotation** uniformly in `[0°, 180°)`.
- **Opacity is fixed at 20%** (no entropy). The 10–30% range from v2
  was below human perception threshold; eliminating that knob saves
  a digest byte and removes a meaningless tuning surface.
- **Clipping target is the grid rect**, not the bounding rect. The
  overlay must never leak into the margins, color bar, or SCS row.
- **Fill color** keeps the v2 rule: convert the entviz bg color to
  HLS; if L > 0.5 fill black, else fill white.

**Discretization.** Each entropic parameter resolves to one of 16
levels (4 effective bits). 16 was chosen as the just-noticeable-
difference threshold — adjacent steps in `rx`/`ry` differ by 1.5–4 px
(at the edge of perceivability), and adjacent rotation steps differ by
~11°. More levels (32, 64) produce variants that look identical to a
human; fewer (8) start to feel coarse.

**Digest byte allocation** (same 4-byte budget as v2):

```
anchor_index   = digest[60] mod pool_size              (pool_size = (N−1)(M−1))
rx_step        = digest[61] mod 16
ry_step        = digest[62] mod 16
rotation_step  = digest[63] mod 16

rx       = r_min + rx_step       / 15 × (r_max − r_min)
ry       = r_min + ry_step       / 15 × (r_max − r_min)
rotation = rotation_step / 15 × 180°
opacity  = 0.20      (constant; no digest byte)

where r_min = cell_h and r_max = d_far(anchor) − cell_w.
```

**SVG implementation note (also a v2 bug fix — see item 6).** The
`clip-path` attribute must live on a non-rotated parent `<g>`, with
the `transform="rotate(…)"` on the `<ellipse>` inside it. If both
attributes go on the same element, the clip rectangle rotates with
the ellipse — a real SVG quirk that bites the v2 implementation
today. Concretely:

```xml
<g clip-path="url(#grid-clip)">
  <ellipse cx="…" cy="…" rx="…" ry="…"
           transform="rotate(θ cx cy)" fill="…" fill-opacity="0.2"/>
</g>
```

**Skip rule for small inputs.** *Omit the ellipse overlay entirely
when input entropy is less than 256 bits.*

The threshold was chosen because the radius math fails for all
grids smaller than 3×4: with `r_min = cell_h = 32` and
`r_max = d_far − cell_w = d_far − 64`, the range is empty
whenever `d_far ≤ 96`. That condition holds for the 2×2 (d_far
= 71), 2×3 (90), and 2×4 (90 at the middle anchor) grids — every
grid a sub-256-bit input could produce. Grids ≥ 3×4 (i.e., inputs
≥ 256 bits) always have a valid radius range at every interior
corner, and the overlay's visual richness depends on having ≥ 6
interior corners to choose from.

Two corner cases that *would* have valid math but are still
skipped under this rule: 3×2 and 4×2 (typical of 144- and 192-bit
inputs respectively). Their overlay would work but provide only
2–3 anchor choices and a narrow radius range; the spec sacrifices
them for a single declarative threshold.

**Open questions.**
- The grid_rect is reused as a SVG `<clipPath>` definition — it can
  share the same `<rect>` element as the grid_rect's fill if we want
  to save a few bytes, but that's a micro-optimization.

---

## 5. Hex token text overflows the nucleus (LOCKED)

**Problem.** Hex tokens are 6 characters (`token_len = 6`). The
nucleus rect is `nucleus_width × nucleus_height = 48 × 16` at the
12pt / 96 DPI reference. The renderer sets the cell text font size
to `nucleus_height = 16 px`. Monospace characters at 16 px are
roughly 9.6 px wide, so 6 chars need ~58 px — overflowing the
48 px nucleus by ~10 px. The text spills into the adjacent edge
rects.

This is a real bug, not a styling preference. It only manifests for
hex-typed inputs; base64 and base58 tokens are 4 chars at the same
font size and fit (~38 px).

**Decision.** *Reference-then-shrink* approach:

1. All grid geometry — cell size, nucleus size, edge rects, grid
   layout, bounding rect — is calculated from the **reference font
   size** (12pt nominally; configurable). Geometry never changes
   based on token type. This preserves cross-type visual consistency:
   a hex entviz and a base64 entviz of the same byte count have
   identical cell dimensions and grid layout.

2. **For 6-character (hex) tokens**, after all geometry is fixed,
   render the cell text at the **closest whole-point font size to
   75% of the reference**, not the reference itself. The 75% factor
   gives ~4.8 px of horizontal slack even on the widest monospace
   fonts (char-width ≤ 0.625 × em), so it doesn't depend on font
   family.

3. For 4-character (base64 / base58) tokens, render at the full
   reference font size (unchanged).

**Concrete values** at common reference sizes:

| Reference pt | 75% raw | Rendered hex pt |
|---:|---:|---:|
| 8   | 6.0  | 6   |
| 10  | 7.5  | 7 or 8 (round-half-to-even → 8) |
| 12  | 9.0  | 9   |
| 14  | 10.5 | 10 or 11 (→ 10) |
| 16  | 12.0 | 12  |
| 18  | 13.5 | 13 or 14 (→ 14) |

The spec should pin the rounding rule explicitly (e.g., "round
half to even" or "round half up") so two implementations don't
disagree on edge values.

**Generalization for future token lengths.** Today the only two
cases are 4-char and 6-char. If a future token type produces N
characters, the same idea applies: pick the rendered font size
such that `N × char_width ≤ nucleus_width`, then round to whole
points. For monospace at char_width = 0.6 × em:

```
font_size_px ≤ nucleus_width / (N × 0.6) = nucleus_height × 3 / (N × 0.6)
            = nucleus_height × 5 / N

rendered_font_size_pt = round_to_whole(font_size_pt_reference × min(1, 4/N))
```

For N = 4 (base64): factor = 1.0 → full reference size.
For N = 6 (hex): factor = 4/6 ≈ 0.667 → BUT we use 0.75 as the
floor for legibility (text shouldn't shrink more than 25% from
reference even if a wider future token would technically permit
that — readability matters more than fit margin past that point).

So the rule becomes:

```
rendered_font_size_pt = round_to_whole(
    font_size_pt_reference × max(0.75, min(1.0, 4 / token_chars))
)
```

For our current types this collapses to: 4-char → reference,
6-char → 75% of reference. The formula is just future-proofing.

**SCS line (item 3) is unaffected.** The SCS uses 90% of the
cell-text size (item 3) and contains at most 31 characters of
content, which fits within the SCS line's reserved nucleus-height
× ~2-cell-columns budget. No additional adjustment needed.

**Open questions.**
- Rounding rule: round-to-nearest (with half-to-even tiebreak)
  vs round-half-up vs floor. Pick before pinning. Round-half-to-
  even is the IEEE 754 default and avoids systematic bias; lean
  toward that.
- Should the spec recommend a specific monospace font family in
  the SVG output (e.g., `font-family: "Courier New", Courier,
  monospace`)? Not strictly required at 75%, but pinning it
  removes one degree of freedom for cross-implementation testing.

---

## 6. SVG clip-path bug in v2 ellipse overlay

**Problem.** `_draw_ellipse_overlay()` in `pipeline.py` puts both
`transform="rotate(…)"` and `clip-path="url(#…)"` on the same
`<ellipse>` element. By the SVG spec, `clipPathUnits="userSpaceOnUse"`
resolves the clip rect in the user coordinate system *after* the
element's transform has been applied — so the clip rect rotates along
with the ellipse. The overlay is therefore being clipped against a
rotated rectangle, not the intended axis-aligned one. The visible
artifact varies with rotation and is easy to miss; the design-time
diagrams for item 4 above made it obvious.

**Fix.** Wrap the ellipse in a parent `<g>` that carries the
`clip-path` attribute, and keep the `transform` on the `<ellipse>`
inside the group. The clip then resolves in the group's coordinate
system, which is not rotated.

```python
g = etree.SubElement(svg, 'g', **{'clip-path': f'url(#{clip_id})'})
etree.SubElement(g, 'ellipse',
                 cx=..., cy=..., rx=..., ry=...,
                 transform=f"rotate({rotation_deg} {cx} {cy})",
                 fill=..., **{'fill-opacity': ...})
```

This is a v2 bug that should land independent of the larger item-4
rework. Once item 4 lands the same pattern is required (the locked-in
design uses both transform and clip-path on the overlay).

---

## Cross-cutting notes

- Items 1, 2, and 3 are independent of each other and could be batched
  into one minor spec revision.
- Item 4 is now **locked**; the design is ready to implement. It
  changes rendered output substantially, so plan it as its own spec
  revision rather than batching with 1/2/3.
- Item 5 (hex font overflow) is a bug fix that should ship sooner
  regardless of the rest.
- Item 6 is a v2-code bug fix that can land immediately; the fix is
  also a prerequisite for item 4's correct rendering.
- All of these change rendered output, so any goldens captured under
  v2 will need to be regenerated when v3 lands.
