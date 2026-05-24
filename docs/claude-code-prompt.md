# Task: migrate the entviz implementation from spec v1 to spec v2

You are working in a repository that contains a complete, clean Python implementation of **version 1** of the entviz algorithm. The specification has been revised to **version 2** (see `index2.md`, which is the authoritative source — read it in full before writing code). Your job is to transform the existing implementation so it implements v2.

A great deal of v1 carries over unchanged: tokenization of the input, grid-layout selection, per-cell geometry (cell/nucleus/edge-rect math), the clockwise edge-rect indexing, the `color_shift`/`shape_shift` XOR mechanics, the foreground-color (luminosity) rule, and the geometry of the edge shapes themselves. Reuse all of that. The list below tells you exactly what is conceptually different in v2 so you don't have to reverse-engineer it from the spec. Where the spec and this document agree, follow the spec; if you think they conflict, stop and ask rather than guessing.

Treat `index.md` as the contract. This document is a map of the deltas.

---

## The single most important conceptual change: tokens vs. ftoks

v1 had one source of data: the **input entropy**, serialized to text and split into **tokens**. Every channel — text, nucleus background color, edge colors, edge shapes, median/quartile calculations, blank placement — was derived from those tokens.

v2 introduces a second source: the **fingerprint**, which is the **SHA-512 hash of the normalized input**. The fingerprint is tokenized the same way the entropy is, into 24-bit chunks called **ftoks**. The data sources now split responsibilities:

- **Tokens (from the entropy) drive only two things:** the **text** of each cell and the **nucleus background color** of each cell. This preserves losslessness for inputs ≤ 512 bits.
- **Ftoks (from the fingerprint) drive everything else:** edge colors, edge shapes, the median and quartile calculations, blank-cell placement, the entviz background color, the color bar, the shape count summary, and the ellipse overlay.

Why: the input entropy may be *chosen* rather than *generated* (a UUID, raw hex, a base64url blob), so two inputs can differ by a single bit while looking almost identical. Hashing first guarantees an avalanche effect, so any difference explodes across all the fingerprint-driven channels.

### Concrete consequences for the code

1. **Compute the fingerprint** with `hashlib.sha512` over the normalized entropy bytes (stdlib, no new dependency). SHA-512 is always 64 bytes.

2. **Tokenize the fingerprint into ftoks** using the *same* tokenization routine you already use for the entropy, applied to the 64-byte digest serialized as base64url. This yields **21 full ftoks (4 base64url chars / 3 bytes / 24 bits each) plus one partial ftok** built from the trailing single byte and extended to 24 bits by repeating its low-order bits — exactly the same partial-token extension v1 already does. So **the fingerprint always provides exactly 22 ftoks**, indexed 0–21.

3. **Each ftok needs both representations**, just as tokens already do in v1: its base64url **string** (used for ASCII and mirror-image sorting) and its 24-bit **quant** (used for color/shape bit extraction). You already have this dual representation for tokens; replicate the pattern for ftoks.

4. **"Used ftoks" = the first `token_count` ftoks**, in ftok-index order. They map **one-to-one to tokens by index**: used ftok *i* corresponds to the token whose token index is *i*. Any ftoks beyond `token_count` are unused. Because `token_count` is at most 22 (see large-input handling below) and there are 22 ftoks, there are always enough. **Do not use modular indexing** — it is plain truncation to the first `token_count` ftoks.

5. **The cell-rendering function now takes two inputs per cell:** the token `T` (for text + nucleus background) and its corresponding used ftok `F` (for edges). In v1, "the quant for T" fed both the nucleus and the edges. In v2, the nucleus background color comes from **`T`'s quant**, and the **edge nums come from `F`'s quant**. This is the change most likely to be missed — search the v1 cell renderer for every place the token quant feeds edge logic and repoint those to the ftok quant.

6. **Median and quartiles are now computed over the used ftoks, not the tokens.** The mechanics are identical to v1 (ASCII sort with token/ftok-index tiebreak for the median; mirror-image sort divided into four quartiles), but the list being sorted is the used ftoks. The resulting **median ftok** and **quartile ftoks** still locate *cells* through the 1:1 ftok→token→cell correspondence: the cell you act on is the cell of the token that corresponds to that ftok.

7. **Entviz background color** comes from the 2 low-order bits of the **median ftok**'s quant (v1 used the median token). **Edge shapes array** is built from the low 4 bits of the **second quartile ftok**'s quant (v1 used the second quartile token).

8. **Blank-cell placement** is unchanged in mechanism (insert up to 3 blanks, shifting cell indices), but it is now keyed off the median ftok and the ASCII-sorted ftok list rather than tokens. Quartile marks are drawn in the cells corresponding to the four quartile ftoks.

---

## Large-input handling (new in v2)

v1 implicitly assumed the whole input fit in the grid. v2 supports inputs of any size:

- If the entropy is **≤ 512 bits**, tokenize the whole thing as before. `token_count` ≤ 22.
- If the entropy is **> 512 bits**, **do not tokenize the whole input**. Tokenize only the **first 256 bits (first 32 bytes)** and the **last 256 bits (last 32 bytes)** of the normalized entropy, and treat the two groups as separated by **one blank cell**. This caps `token_count` at 22. The fingerprint is still computed over the *entire* input, so the whole value is bound into the visualization through the fingerprint-driven channels even though the text shows only the ends.

The text channel is therefore lossless only up to 512 bits; above that it shows the two ends and relies on the fingerprint for integrity. The spec's requirements section states this explicitly.

---

## Grid changes

- **1×N and N×1 grids are now invalid.** The minimum grid is **2 columns by 2 rows.** Update the layout-selection logic to exclude any candidate layout with fewer than 2 columns or fewer than 2 rows, then pick the best remaining layout by the existing aspect-ratio rule. (The worked example in the spec was also updated to drop the 11×1 and 1×11 options.)

---

## Terminology trap: "bounding rect" changed meaning

This will bite you if you rename mechanically. In **v1**, "bounding rect" meant the rectangle containing just the grid of cells. In **v2**:

- That concept is now called the **grid rect**.
- The term **bounding rect** is *reused* for the larger outer canvas that contains the color bar, the grid rect, and the shape count summary.

So when the v2 spec says "bounding rect," it means the outer canvas, not the grid. Rename the v1 concept to `grid_rect` everywhere, and introduce a new `bounding_rect` for the outer canvas. Do not let the old variable name silently carry the new meaning.

---

## New geometry and layout

Introduce these (all dimensions are in the spec's measurements section; values shown are for the nominal 12pt / 96 DPI case):

- **Grid margin (GM)** = `edge_size / 2` = half the width of a left/right edge rect = **4 px** nominal.
- **Bounding rect** dimensions:
  - width = `GM + GM + grid_width + GM + 1`
  - height = `1 + GM + grid_height + GM + nucleus_height + GM + 1`
- The bounding rect is filled **white**, with a **1-px black line** along its **top, right, and bottom** edges only. The **color bar forms the entire left edge** (width = GM, full height); there is **no black line on or around the color bar**, and the top/bottom black lines stop at the color bar's right edge.
- The **grid rect** sits at offset `(GM + GM, 1 + GM)` inside the bounding rect.
- Use the **bounding rect as a clipping region** for all drawn content (so the ellipse overlay is truncated at the edge). Draw clipped content first; draw the black border lines last so they are never overwritten.

---

## Rendering is now layered (structural change to the draw loop)

v1 most likely renders each cell completely in one pass (edges + nucleus + text together). v2 requires **distinct layers with a global draw order**, because the ellipse overlay must sit on top of all edges but underneath all nuclei. Restructure the rendering so it proceeds in this order:

1. White background fill of the bounding rect.
2. **All edge rects of all cells** (every cell's edge shapes), across the whole grid.
3. The **ellipse overlay** (see below).
4. **All nuclei and their text**, across the whole grid.
5. **Quartile marks.**
6. The **color bar** (left) and **shape count summary** (bottom).
7. The **black border lines** on top.

The key inversion from v1: you can no longer finish a cell entirely before moving to the next, because the overlay has to land between the edge layer and the nucleus layer for *all* cells. Separate "draw this cell's edges" from "draw this cell's nucleus + text" into two passes.

---

## Edge shapes: rename + gradient fill

**Shapes were renamed. We are going to change their geometry, too. But for now, assume that did NOT change.** Keep every shape's drawing code exactly as-is and only rename. The mapping is positional:

| v1 name (array 0) | v2 name | letter |
| --- | --- | --- |
| triangle | fin | F |
| hook | axe | A |
| rect | brick | B |
| box | inf | I |

| v1 name (array 1) | v2 name | letter |
| --- | --- | --- |
| slant | wave | W |
| hammer | hole | H |
| pyramid | keel | K |
| double bars | mound | M |

The capital letters (F, A, B, I, W, H, K, M) are all distinct and are used as the shape labels in the shape count summary. (Note: you are *not* redrawing or smoothing the shapes in this task — any "smoother/organic" shape redesign is being handled separately and is out of scope here.)

**Edge fill changed from solid to gradient.** v1 filled each edge shape with a solid edge color. v2 fills each edge shape with a **linear gradient** running from the **nucleus background color** at the boundary the edge rect shares with the nucleus, to the **edge color** at the outer boundary of the edge rect, perpendicular to that shared boundary. This makes the nucleus color appear to bleed outward into the shapes. The gradient's start color is the cell's nucleus background color (token-derived); the end color is the edge color (ftok-derived). All other shape rendering — rotations per edge index, compression on edges 2 and 5, 45-45-90 triangles — is unchanged.

---

## New gestalt features to add

### Color bar (left edge)
Tally how many times each of the four edge colors is actually drawn across all edge rects, **excluding blank cells**. Divide the color bar's height into horizontal bands, one per color with a nonzero count, each band's height proportional to that color's share of the total. Sort bands **descending by count, most frequent at top**, tiebreaking by the color's order in the `edge_colors` array. The bar is the leftmost GM-wide strip and spans the full bounding rect height.

### Shape count summary (bottom)
Tally how many times each edge shape is actually drawn, **excluding blank cells**. For each shape with a nonzero count, form a token `X##` (capital letter + count zero-padded to 2 digits). Sort **descending by count, alphabetical by letter as tiebreak**. Join with single spaces, render in the **same fixed-width font and size as the cell text**, **right-justified to the right edge of the grid rect**, on the line reserved below the grid (top edge at `grid_rect bottom + GM`). Sorting by count means two entvizes with different shape distributions show the summary in a different order — that ordering difference is itself a comparison cue. In interactive output, add a **tooltip with the shape's full name** when hovering an edge shape.

### Ellipse overlay
A large, partially transparent ellipse that contributes a gestalt-level silhouette. Derive its four parameters from raw SHA-512 digest bytes (number the 64 digest bytes 0–63):

- **anchor**: enumerate the outer corners of the grid's perimeter edge rects; select one with `digest[60] % corner_count`.
- **axis ratio**: map `digest[61]` onto the range 1:1 to 1:2.5 (ratio of the two semi-axes).
- **rotation**: map `digest[62]` onto 0°–180°.
- **opacity**: map `digest[63]` onto 10%–30%.

Center the ellipse on the anchor corner; size it so its **smaller semi-axis ≥ half the diagonal of the bounding rect**, guaranteeing it always overflows the bounding rect and is clipped to an arc rather than appearing as a closed ellipse. Fill: convert the **entviz background color** to HLS; if luminosity > 0.5 fill **black**, else fill **white**; apply at the derived opacity. Draw it **above the edge layer, below the nucleus layer** (see layering above).

(Implementation note: you'll need a precise, fixed enumeration order for the perimeter-corner pool so output is reproducible. If the spec hasn't pinned one, choose a deterministic order — e.g., clockwise starting from the top-left corner of the grid rect — and document it in a comment.)

---

## Other corrections

- **Red color value:** the `possible_edge_colors` array literal must use **`#ff3f2f`** for red. (v1 had `#ffdf2f`, which is actually a yellow nearly identical to gold; that was a bug.) The full array is white `#ffffff`, gold `#ffd966`, red `#ff3f2f`, blue `#2f3fbf`, black `#000000`.
- **Corner rects:** the four corner rects of each cell remain reserved. Continue drawing quartile marks in the corner rects of the four quartile cells. Leave all other corner rects **empty** — do **not** implement connectors or any other corner-rect content; that is explicitly a future extension point.

---

## Reuse / preserve (do not rewrite these)

- The `entropy` parse/normalize module and its tests — keep as the normalization oracle.
- Grid-layout selection (only add the 2×2 minimum).
- Cell, nucleus, and edge-rect geometry math.
- Clockwise edge-rect indexing.
- `color_shift` / `shape_shift` accumulation and the XOR-with-shift color/shape selection.
- The luminosity → foreground-color rule.
- The geometry of each edge shape and its per-edge rotation/compression.
- The partial-token bit-extension routine (now also applied to the partial ftok).

---

## Suggested validation

- **Determinism:** same input → byte-identical output.
- **Avalanche:** flip one bit of a UUID-style input; confirm the fingerprint-driven channels (edges, colors, blank placement, color bar, SCS, ellipse) change dramatically while the text channel changes minimally. This is the security property the whole migration exists to provide.
- **Losslessness ≤ 512 bits:** the displayed text round-trips to the original normalized entropy.
- **Large input > 512 bits:** text shows first 256 + last 256 bits with a blank separator; the whole input still affects the fingerprint-driven channels.
- **Grid constraint:** no input ever produces a 1-row or 1-column grid.
- v1 full-image golden tests will **not** match v2 (blank placement and many channels now derive from the fingerprint). Regenerate goldens from v2 output rather than trying to preserve v1's.

Before you start, read `index.md` end to end, then propose a short migration plan (which modules/functions change, which are added) and wait for confirmation if anything here seems to conflict with the spec.
