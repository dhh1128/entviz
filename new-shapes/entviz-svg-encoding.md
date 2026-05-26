# entviz — efficient SVG encoding (defs + use + transforms)

Goal: render a full glyph (a grid of cells, each with up to six edge slots) at **minimum filesize**,
reusing one definition per shape and placing instances with `<use>` + transforms — while respecting
the rule that **90°/270° placements must use the tabbed (truncated) geometry**, not the full shape.

The short version: **define geometry once, place it with cheap `<use>` references, move all styling
into a single CSS class, define the inner-edge gradient once, and author every path in integer
coordinates using `h`/`v` shorthands.** The biggest single win is usually *not* the geometry — it is
killing per-element style attributes and per-cell gradient definitions.

---

## 1. Inventory the unique geometry first

There are only **6 base shapes** (C1–C3, P1–P3); **empty has no geometry** (emit nothing). For
rotation you need a separate *tabbed* definition **only for shapes that actually carry mass outside
their 16-wide window** — the rest rotate with their full path unchanged:

| shape | full def | separate tab def? | hinge (pivot) | notes |
|---|---|---|---|---|
| C1 | `#c1` | **yes** `#c1t` (win 2–18) | (2,0) | mass at x<2 and x>18 is dropped on rotation |
| C2 | `#c2` | **yes** `#c2t` (win 6–22) | (6,0) | has holes → `fill-rule:evenodd` |
| C3 | `#c3` | **yes** `#c3t` (win 4–20) | (4,0) | corner at x<4 dropped on rotation |
| P1 | `#p1` | no — spans 0–16, full = tab | (0,0) | no truncation |
| P2 | `#p2` | no — body 8–24 = window 8–24 | (8,0) | self-touching → `evenodd`; pivot only |
| P3 | `#p3` | **yes** `#p3t` (win 0–16) | (0,0) | right tab x>16 dropped on rotation |
| empty | — | — | — | render nothing |

So the whole alphabet is **10 path defs** (6 full + 4 tab) + **1 nucleus rect** + **1 inner-edge
gradient**. Everything else in the file is `<use>`.

---

## 2. Style once, not per element

Per-instance `fill="…" stroke="…" fill-rule="evenodd"` repeated across hundreds of edges is the
quiet majority of a naïve file. Move it to one `<style>` block and reference by class. A `<use>`
inherits presentation, so put the class on the `<use>` (or on a wrapping `<g>` per cell):

```svg
<style>
  .e { fill: url(#ie); fill-rule: evenodd; }   /* edge ink + inner-edge gradient + holes */
  .nuc { fill: #1b1b1b; }                        /* nucleus */
</style>
```

This alone removes ~30–50 bytes from every drawn element.

---

## 3. Define the inner-edge gradient once

The flush/blended inner edge (y=8 against the nucleus) is a gradient. **An inline gradient per cell
is the single most expensive mistake** (~150–300 bytes each × every cell). Define it once in
`<defs>` and reference it from the shared class (`fill:url(#ie)` above):

```svg
<linearGradient id="ie" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="#1b1b1b"/>           <!-- outer: opaque -->
  <stop offset="1" stop-color="#1b1b1b" stop-opacity="0"/> <!-- inner: blends into nucleus -->
</linearGradient>
```

(`x1..y2` in objectBoundingBox units so it auto-fits each placement; tune stops to the real
figure/ground blend.)

---

## 4. Author paths as integer `h`/`v` shorthands

All canonical coordinates are integers in a 24×8 box, and the cubist shapes are almost entirely
axis-aligned — so use relative `h`/`v` (one number each) instead of absolute `L x,y` (two numbers).
Pack holes/detached pieces as extra subpaths in the **same** `d` (even-odd resolves add vs. subtract):

```svg
<!-- C3 full: post[16,20] + mid strip + corner square, one even-odd path -->
<path id="c3" class="e" d="M16,0h4v8h-4v-2h-4v-2h4ZM0,6h2v2h-2Z"/>

<!-- C3 tabbed (win 4–20): corner square at x<4 dropped; re-origin to the window if you prefer -->
<path id="c3t" class="e" d="M16,0h4v8h-4v-2h-4v-2h4Z"/>

<!-- P2: diagonals can't use h/v, but stays integer & single subpath (self-touching evenodd) -->
<path id="p2" class="e" d="M16,0L12,4 8,8 14,8 18,0 22,8 24,8 24,4 20,0Z"/>
```

Keep the authoring viewBox at 24×8 (or per-tab local) so **no coordinate ever needs a decimal** —
decimals roughly double the bytes of every number and defeat gzip's run matching.

---

## 5. Place with `<use>` + transform; swap to the tab variant at 90°/270°

One definition serves all four rotations (and mirrors) of a slot. Rotate **about the hinge** so the
edge lands on the correct register, and **switch the href to the `…t` tab variant for 90°/270°**:

```svg
<!-- upright slots (0° / 180°): full geometry -->
<use href="#c3"  transform="translate(CELL_X,CELL_Y)"/>
<use href="#c3"  transform="translate(CELL_X,CELL_Y) rotate(180 12 4)"/>

<!-- rotated slots (90° / 270°): TAB geometry, pivot on the hinge (4,0) -->
<use href="#c3t" transform="translate(CELL_X,CELL_Y) rotate(90  4 0)"/>
<use href="#c3t" transform="translate(CELL_X,CELL_Y) rotate(270 4 0)"/>
```

The 3-argument `rotate(θ cx cy)` rotates about `(cx,cy)` in the element's local frame, so set
`(cx,cy)` to the hinge from the table in §1. For the **outer↔outer vertical seam** (an X-mirror at
y=0), reuse the *same* def with a reflection instead of a new path:

```svg
<use href="#c3" transform="translate(CELL_X,CELL_Y) scale(1,-1) translate(0,-8)"/>
```

Mirroring + the four rotations means **one def can yield up to eight oriented placements** with no
new geometry (only the tab swap distinguishes the rotated pair).

---

## 6. Skeleton

```svg
<svg viewBox="0 0 W H" xmlns="http://www.w3.org/2000/svg">
  <style>.e{fill:url(#ie);fill-rule:evenodd}.nuc{fill:#1b1b1b}</style>
  <defs>
    <linearGradient id="ie" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#1b1b1b"/>
      <stop offset="1" stop-color="#1b1b1b" stop-opacity="0"/>
    </linearGradient>
    <rect id="nuc" class="nuc" x="0" y="0" width="48" height="16" rx="1"/>
    <path id="c1" class="e" d="…"/> <path id="c1t" class="e" d="…"/>
    <path id="c2" class="e" d="…"/> <path id="c2t" class="e" d="…"/>
    <path id="c3" class="e" d="M16,0h4v8h-4v-2h-4v-2h4ZM0,6h2v2h-2Z"/>
    <path id="c3t" class="e" d="M16,0h4v8h-4v-2h-4v-2h4Z"/>
    <path id="p1" class="e" d="M0,8 0,4 3,3 4,0 12,0 16,8Z"/>   <!-- full = tab -->
    <path id="p2" class="e" d="M16,0L12,4 8,8 14,8 18,0 22,8 24,8 24,4 20,0Z"/>
    <path id="p3" class="e" d="…"/> <path id="p3t" class="e" d="…"/>
  </defs>

  <!-- one cell: nucleus + its filled edge slots -->
  <use href="#nuc" transform="translate(100,60)"/>
  <use href="#c3"  transform="translate(100,52)"/>            <!-- top edge, 0° -->
  <use href="#p2t...or #p2" transform="translate(148,60) rotate(90 8 0)"/> <!-- right edge, 90°, tab -->
  <!-- empty slots: emit nothing -->
</svg>
```

(The `nuc` rect dimensions and the slot offsets per cell come from the layout geometry; the point
here is that every cell is *only* a handful of `<use>` lines plus possibly one `<use href="#nuc">`.)

---

## 7. Byte budget and gzip

- **Geometry defs:** fixed ~10 short paths, on the order of ~0.4–0.8 KB total, paid once regardless
  of glyph size.
- **Per placement:** a `<use href="#xx" transform="translate(…)rotate(…)"/>` is ~50–70 bytes — and
  it is *highly repetitive*, so gzip crushes it. A glyph with `6N` slot placements is roughly
  `defs + 6N×~60 bytes` raw, but transfers far smaller because the markup is near-identical line to
  line.
- **Optimize for gzip, not just raw:** maximizing repetition (shared class, shared gradient,
  identical `<use>` shape) shrinks the raw file *and* improves the compression ratio. Inlining unique
  paths/gradients per cell hurts twice — bigger raw and worse compression.
- **Drop** `xmlns:xlink`/`xlink:href` (use bare `href`, supported in all current renderers), default
  attributes, and any editor metadata.

**Caveats.** Confirm the tab variant's local origin aligns with its hinge before trusting
`rotate(θ hx hy)` — an off-by-one origin shifts the rotated edge off its register. `<use>` of a
gradient-filled shape with `objectBoundingBox` units rescales the gradient to each instance's box,
which is what you want for the inner-edge blend; switch to `userSpaceOnUse` only if you need a single
shared gradient frame. And the seam geometry (L/R registers, outer X-mirror) must be authored so
edges actually meet at the shared coordinate — that is a geometry property of the shapes, independent
of this encoding.
