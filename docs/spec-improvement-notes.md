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

---

## Deferred items (next v3 polish pass)

Items raised in a third-party review of the v3 spec draft (now
canonical at `docs/index.md`) that
were judged real but not urgent. Address in a future polish pass.

### D1. Full parser spec for input normalization
The current v3 draft defers entropy-type detection and normalization
to the Python reference implementation in `entviz/entropy.py` (~300
lines of crypto-address regexes and decoding logic). For
standards-track interoperability this needs to be published as a
separate normative document with ABNF, type-detection precedence
rules, and canonical test vectors. *Not a single-pass spec edit; its
own writing project.*

### D2. Grid-selection pseudocode
The grid-AR comparison and tight-layout dedup rules in
`choose_grid()` are concrete in code but expressed as prose in the
spec. A ~20-line pseudocode block in the grid-layout section would
remove the ambiguity. Fairly mechanical.

### D3. Blank-cell insertion ordering
Tighten the prose to make explicit that the ASCII-sort happens once
(on original ftok identities), all three potential shifts operate on
the same sorted list, and only `cell_index` (not `token_index`)
changes during a shift.

### D4. Font pinning
At hex 75%, the rendered font size is tight (only ~4.8 px of slack on
typical monospace fonts). Either pin a font family
(`font-family: "Courier New", Courier, monospace`) in the SVG output,
or commit to glyph-path embedding. Pinning is a one-sentence spec
edit; glyph paths are a larger lift.

### D5. Global rounding rules
The spec rounds the hex-font calculation but doesn't say what
rounding to apply elsewhere (color-bar band heights, ellipse radii,
HLS conversion, grid placement). Add a "Numeric precision" section
that defines a single rule (lean toward round-half-to-even) and
states where subpixel coordinates are acceptable.

### D6. HLS exact formula
Different stdlib HLS implementations agree on the L>0.5 test in
practice, but a spec-grade version should embed the conversion
formula (or normatively reference a specific definition).

### D7. Quartile-padding sort key
The "act as if blank items existed at the bottom" rule needs to
state what the blanks' sort keys are (or just say "padding items
contribute to count but never appear as the first ftok of a
quartile slot, since they have no value").

### D8. Ellipse rendering details
Antialiasing assumptions, sRGB vs linear-RGB compositing of the
alpha-blended overlay, sub-pixel handling. Different rasterizers
(SVG/Cairo/Canvas) will differ; spec should pick one.

### D9. "Actually drawn" edge rects
One sentence to add to the color-bar and SCS sections: "blank cells
produce no edge rects, hence contribute zero to the color and shape
tallies." (Currently implied but never stated.)

### D10. Normative vs explanatory prose split
The draft interleaves motivational paragraphs, implementation notes,
rationale, examples, and normative requirements. Splitting these
into separate sections (or adding MUST/SHOULD/MAY markers) would
make it easier for an implementer to extract the algorithm.

### D11. Conformance test vectors + golden output
No canonical test vectors or reference rendered images. The
reference implementation in `entviz/` is the de-facto conformance
test today. A future revision should publish:
- a curated set of input strings
- their expected normalized cores
- their expected ftoks (hex digest values)
- their expected SVG outputs (or hashes thereof)
- tolerance rules for non-determinism (e.g., font rasterization)

### D12. SCS font size: change percentage from 90% to 84%

The current spec rule `scs_pt = min(round(0.9 × reference_pt), cell_text_pt)`
produces 11pt at the 12pt reference (= 14.67 px), which is only 8.3%
smaller than the 12pt cell text (16 px). At normal viewing size the
visual difference doesn't read as "noticeably smaller."

Change the multiplier from 0.9 to 0.84: `round(0.84 × 12) = round(10.08)
= 10pt = 13.33 px`. That's a 16.7% reduction from cell text — the SCS
will visibly read as secondary. Update item 3 of this doc accordingly.

For hex inputs (cell text already at 9pt), the min still picks
cell_text_pt = 9pt and the SCS matches cell text size — unchanged.

### D13. Border + interior-separator color: change from #000000 to #808080

Currently the four bounding-rect borders and the interior separator
between the color bar and the grid margin are drawn at #000000 (pure
black). Change all five to #808080 (medium gray). Softens the frame,
reads as "structural" rather than "intrusive," and avoids visual
competition with the black edge color which is one of the four edge
colors in the palette.

Update item 2 of this doc (the color bar frame decision) to use
#808080 for both the border lines and the interior separator.

### D14. Shrink the white region below the grid to a single nucleus height

The space below grid_rect currently runs `GM + nucleus_height + GM + 1`
= 25 px at 12pt nominal: a GM gap, the nucleus-height-tall SCS line,
another GM gap, and the 1-px bottom border. The two GM gaps add
visual weight without earning their keep.

Shrink to `nucleus_height + 1` = 17 px: the SCS line abuts the grid
on top and the bottom border on the bottom, with no GM padding. The
new bounding_rect height formula becomes:

```
bounding_h = 1 + GM + grid_h + nucleus_height + 1
```

The SCS text's vertical center moves from
`grid_rect.bottom + GM + nucleus_height/2` to
`grid_rect.bottom + nucleus_height/2`. At 12pt: bounding_h drops by
8 px (was 158 for UUID, becomes 150).

This is a coupled change with bounding_rect.height in the spec, all
geometry/golden tests that depend on bounding_h, and the SCS
y-coordinate computation in `_draw_shape_count_summary`.

### Where to find these later

To work on any deferred item, ask: *"work on D{N} from the deferred
section of spec-improvement-notes.md"* or *"polish the v3 draft to
address the deferred items"*. The full review text that produced
items D1–D11 is captured in the conversation that led to commit
`e201654` (the "tighten v3 draft on six interoperability hazards"
commit); the *fixed* items from that review are 1, 2, 3, 6, 7, 11,
and 15, all already integrated into the draft. Items D12–D14 came
from visual review of refs/v3-6b/ output.

### D16. Find a way to draw the ellipse overlay for inputs < 256 bits

V3-5's skip rule omits the overlay entirely whenever the grid has
fewer than 6 interior corners (equivalent to "< 256 bits of input").
The current geometry — `rx, ry ∈ [cell_h, d_far − cell_w]` — produces
a degenerate radius range on smaller grids, which is why the skip
rule exists. But the small-input cards in `refs/gallery-v3/` feel
visually weaker than the large-input cards because they lack the
gestalt-level silhouette the overlay provides.

Find a different geometry that produces a meaningful overlay on
smaller grids too. Some candidates:

- **Scale the radius range with grid size.** Use
  `r_min = grid_diagonal × min_fraction`, `r_max = grid_diagonal ×
  max_fraction` with fractions chosen so the math works at 2×2
  too. Loses the "radius respects cell geometry" property but
  gains universal applicability.
- **Different anchor pool for small grids.** Below the threshold,
  allow perimeter-cell corners (the v2 enumeration) rather than
  strictly-interior corners. Gives 2×2 a real anchor pool instead
  of forcing a fixed center.
- **Different shape primitive for small grids.** A Bezier curve or
  open arc may read better at small grid sizes than an ellipse,
  whose closed-curve property isn't visible when most of it is
  clipped.
- **Just shrink the radius bounds.** `r_min = cell_h / 2`,
  `r_max = d_far / 2`. Gives smaller overlays that may still read.

A visual prototype (similar to the overlay-options gallery we did
earlier) would help pick a direction. The acceptance criteria are
roughly: every grid ≥ 2×2 produces an overlay, the overlay reads
as a curve (not a flat-edge clip), and the 16-level discretization
still gives visibly distinct shapes between adjacent steps.

### D17. UUID / hex-content non-hex types: tokenize as hex or as base64?

A UUID like `550e8400-...-446655440000` normalizes to a 32-character
hex string but is given type `"UUID"`. The tokenizer treats anything
without `"hex"` in its type name as base64-style (4-char tokens,
6 bits per char). So a UUID becomes 8 tokens of 4 hex chars each,
and the nucleus colors are computed by reading each 4-char chunk as
if it were base64.

Visible consequence: a UUID ending in `"0000"` gives a nucleus
quant of `0xD34D34` (~#344dd3, blue), not 0 (black). Because '0'
is at index 52 in the standard base64 alphabet, not 0. Most viewers
expect "all zeros in the token → black background." The current
behavior reads as a bug to a careful observer.

Same applies to other hex-content but non-hex-typed inputs (Bitcoin
Cash addresses with their hex-like Base32 alphabet, etc.).

Options:
- **Treat UUID as hex.** parse_uuid sets `type="UUID"`; change to
  `type="hex"` or special-case in `tokenize()`. Token count for a
  32-char UUID becomes ~6 (instead of 8); the chosen grid changes;
  goldens shift.
- **Generic rule: if the core is pure hex, tokenize as hex regardless
  of type name.** Cleaner, automatic. Same effect.
- **Document the quirk and live with it.** The current behavior is
  a deliberate consequence of treating type-name as the tokenizer's
  signal; adopters who care can flatten the hex via the unknown-type
  fallback.

The "tokenize pure-hex-content as hex" rule (option 2) seems most
honest. Worth a visual A/B before deciding — the change shifts
both token count and nucleus colors for every UUID-style input.

### D15. Per-edge gradient is invisible after v3 path transforms

V3-6b's per-edge gradient renders effectively as a uniform color
because the gradient endpoints are defined in *screen* coordinates,
but the v3 shape `<path>` has its own `transform="translate(…) scale(…)`
(plus optional rotate). SVG resolves `userSpaceOnUse` gradient coords
in the *post-transform* local user space of the referencing element,
so the gradient line ends up far outside the path's content area and
the path renders with the gradient's start color uniformly.

The fix is to redefine the gradient endpoints in **canonical 24×8
coordinates** — e.g., `x1=12, y1=8, x2=12, y2=0` regardless of edge.
The path's transform then applies to BOTH the path geometry AND the
gradient, so the gradient ends up perpendicular to the edge in the
correct direction after rotation. Since all edges share the same
canonical inner→outer direction (y=8→y=0), the same gradient
endpoint pair works for all edges; only the colors vary per edge.

Currently this bug just removes the gradient visual; both stops'
colors are still emitted, so the visual is a flat per-edge color
(the gradient's start stop). Strictly speaking this means the spec
guarantee "edge fill is a gradient" is not honored by the v3-6b
renderer.
