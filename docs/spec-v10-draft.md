# entviz spec v10 — DRAFT delta: casual-avalanche colour levers

**Status: DRAFT.** Normative delta against [spec.md](spec.md) (current v9). Not
yet merged; `SPEC_VERSION` stays `v9` until this is integrated, the conformance
corpus is regenerated, and the figures/gallery/self-image are re-rendered (see
AGENTS.md §4). Motivation and measured effect: see
[`experiments/casual-avalanche/`](../experiments/casual-avalanche/) (README +
FINDINGS).

## Why (the problem this fixes)

entviz claims **graded discriminability** — a difference should surface to a
*glance*, not only to careful byte-by-byte inspection. But casual and careful
comparison have very different bandwidths. The surround **pattern** avalanches
richly for careful comparison and is *casually imperceptible* (half its boxes
can toggle and a glance reads "same"). What a glance reads is the **colour
gestalt** — and on a one-character change the colour gestalt is largely frozen:
the value is unchanged in ≥5/6 cells (so their entropy-derived nucleus colour,
and the surround hue that echoes it, do not move), and the entviz background is
only 2 bits, so it stays put ¼ of the time and freezes the whole surround
palette with it.

Measured (n = 100,000 one-character neighbours): in the **background-unchanged
quarter, 27.1%** of neighbours are casually colour-identical at baseline,
concentrated in dense full-grid inputs (UUID **61%**, hex-128 **61%** within
that stratum). The levers below move fingerprint signal into the **dominant,
pre-attentive colour channel**, as a few discordant colour **singletons**
against an otherwise-coherent echo field (partiality is required — singletons
must stay rare to pop out). Measured effect of the locked design: hard-quarter
colour-miss **27.1% → ~0.5%**; per-type (e.g. LEI 9.8% → 0.3%, hex-64 21.5% →
0.4%, UUID/hex-128 61% → ~2%).

These levers add **casual salience only**; they are *not* a collision-resistance
claim (the surround pattern, colour bar, ellipse, blank positions, and quartile
marks remain the careful-comparison channels). The bit reuse is intentional and
non-load-bearing.

---

## Change 1 — fingerprint-sourced surround edge colour on selected cells

Modifies *Cell Rendering Algorithm* step *"Determine this cell's edge colour"*
(spec.md ≈ line 520) and the surround description (≈ line 65). The **nucleus
colour is unchanged** (still entropy-derived, still lossless); only the surround
(edge) colour selection changes, and only for the cells named below.

A cell is a **fingerprint-edge cell** if it is the cell at grid position 0
(top-left, row-major), **or** it is the cell corresponding to the **1st or 2nd
quartile ftok** (per the quartile selection, spec.md ≈ line 326).

- For a **fingerprint-edge cell**, the implementation **MUST** set the surround
  *edge colour* to `edge_palette[q & 0b11]`, where `q` is the cell's own used
  ftok *quant* (for the top-left cell, the ftok of the token rendered there;
  for a quartile cell, that quartile ftok's quant), and `edge_palette` is the
  4-entry edge palette (spec.md ≈ line 382, order preserved). The 2 low-order
  bits select the index 0..3.
- For **every other filled cell**, the edge colour **MUST** be chosen by the
  existing nearest-`weighted_rgb_distance`-to-nucleus rule (unchanged).
- **Idempotence / overlap:** if the top-left cell is also a quartile cell, the
  rule applies once; both derivations name the same cell and the same ftok, so
  the result is identical.
- **Absent targets:** if a quartile ftok is null (small inputs whose
  mirror-sort quartile falls in padding, spec.md ≈ line 326) or its cell — or
  position 0 — is **blank**, there is no edge colour to override (a blank has no
  surround). The blank instead follows Change 2.

Rationale notes (non-normative): the background already uses the *median* ftok's
low 2 bits; a per-cell ftok's low 2 bits are an independent draw under
avalanche, so each fingerprint-edge cell's hue changes with probability ¾ on any
input change. Quartile cells are chosen because they are *already* fingerprint-
positioned check cells (they carry the quartile mark) and they **move** with the
fingerprint, so the discordant-hue location is itself a second casual cue. The
top-left cell is fixed because it is the first-fixation point in left-to-right
reading. The set is deliberately small (≤ 3 cells) so the discordant hues remain
pre-attentive singletons rather than confetti.

## Change 2 — hybrid fingerprint fill for blank cells

Modifies *blank cell* rendering (spec.md ≈ line 554) and *Map rendering*
(≈ line 562). Every blank retains its rounded-rect **pill outline** (the "gap"
semantic and the cell-vs-nucleus distinction are preserved); the change is the
pill **interior fill**.

Let the blanks be enumerated in cell-index order; the **map blank** is the
lowest-indexed blank (it carries the min/max markers, unchanged in position).

- A **non-map blank** **MUST** be filled with `edge_palette[d & 0b11]`, where
  `d` is digest byte `digest[32 + j]` and `j` is the blank's 0-based index among
  the *coloured* blanks in cell-index order. (Byte range 32..59 is disjoint from
  the ellipse bytes 60..63.)
- The **map blank** fill is **hybrid**, keyed on the total blank count:
  - **If the map blank is the only blank** (`blank_count == 1`): fill it with
    `edge_palette[d & 0b11]` (same per-blank rule, `j = 0`), **and** draw *both*
    map markers (the max **plus** and the min **dot**) in the **luminance-
    contrast colour** against that fill — `#ffffff` if the fill's Oklab L < 0.6,
    else `#000000` (the same rule that picks cell-text foreground, spec.md
    ≈ line 514). Max/min identity is carried by **shape** (plus vs dot), which
    the v8 design already made the primary cue (spec.md ≈ line 571, "the colours
    are retained as a redundant cue"); recolouring the markers therefore costs
    only that redundant hue.
  - **If there are two or more blanks** (`blank_count >= 2`): the map blank keeps
    its v9 fill — `#ffffff` when the entviz background is not white, `#e7be00`
    (gold) when it is — as a **findable white/gold anchor**, and its markers keep
    their v9 colours (red plus `#d62828`, blue dot `#1d4ed8`). Only its *sibling*
    blanks are fingerprint-coloured (above).

Rationale (non-normative): blank **positions** already avalanche, but on dense
full grids there are no blanks, and the most common small inputs that *do* have
a blank (LEI; small hex; 18-char base36) have exactly **one** — which is the map
blank. Colouring siblings only (the naïve rule) therefore does nothing for
exactly those inputs (measured: null effect). The hybrid colours the map blank
precisely when it is the sole blank, capturing that case (LEI 9.8% → 2.9% from
this lever alone), while preserving the white-anchor/findability aesthetic on
the multi-blank inputs — which are already casually well-discriminated, so they
lose nothing by keeping the anchor. The two regimes (sole-blank vs multi-blank)
are disjoint input populations, so the branch never trades the avalanche away
where it is needed.

## Change 3 — fingerprint (middle) cells: explicitly UNCHANGED

The four fingerprint/middle cells of a >512-bit entviz (spec.md ≈ line 253)
keep their neutral nucleus (= entviz background colour), gold/white frame, and
primary-fingerprint surround pattern. This was considered for a colour lever and
**deliberately declined**:

1. the neutral fill is a *semantic* marker ("fingerprint readout, not literal
   entropy"); colouring it would erase that distinction, and these cells already
   avalanche in their designed channel — the **text** (the 96-bit read-aloud
   Crockford readout);
2. >512-bit inputs are the **most** casually robust class measured (≈0% colour-
   miss even in the background-unchanged quarter — blank cascades plus cell count
   already carry them), so there is no hole to close; and
3. large grids already spend the singleton budget on Changes 1–2; the four
   neutral cells are part of the **coherent field** the singletons pop against —
   colouring them too would push toward confetti and *erode* pop-out.

---

## Conformance / model impacts (for integration)

- The per-cell record (spec.md ≈ line 136) gains no new field; `edge color`
  simply has a new derivation for fingerprint-edge cells. Tier-A checkers
  already compare edge colour, so golden renders change but the schema does not.
- `data-cell-quartile` and `data-cell-blank-map` already expose the cells a
  checker needs to validate the new derivations; consider adding
  `data-cell-fp-edge` to flag fingerprint-edge cells explicitly.
- The blank map markers' colours become a function of fill in the sole-blank
  case; conformance tolerance on those marker pixels must allow the recolour.
- On adoption: bump `SPEC_VERSION` to `v10`, regenerate the conformance corpus,
  gallery, paper/spec figures, and the README/social-card self-image
  (AGENTS.md §4 steps 5–7), and eyeball figure captions for stale meaning.
