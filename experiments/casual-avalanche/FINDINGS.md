# Findings — casual-avalanche experiment

*n = 100,000 one-character-neighbour pairs, seed 1, 2026-06-18. Tables in
`results/RESULTS.md`; per-type small-input breakdowns from `diag_blanks.py` /
`diag_small.py`. This file is the narrative + the locked decision; it is not
overwritten by re-runs. The locked design is spec'd in
[`docs/spec-v10-draft.md`](../../docs/spec-v10-draft.md).*

## Headline

The casual colour-collision hole is real and measured, and concentrates exactly
where the theory predicted:

- **Baseline colour-miss in the background-unchanged ¼: 23.67%** (95% CI
  [23.1, 24.2]; definitive 100k run). About a quarter of one-character
  neighbours, in the quarter of cases where the 2-bit background does not flip,
  are **casually colour-identical**: the surround pattern churns invisibly and
  nothing in the colour gestalt moves.
- It is **concentrated in dense full-grid inputs**: within that stratum, UUID
  **61%** and hex-128 **61%** colour-miss; ~3–10% for small inputs that carry a
  blank; ~0% for >512-bit inputs (blank cascades + cell count already carry
  them).

The locked design (Change 1 + 2 below) takes the hard-¼ colour-miss to
**0.33%** and every input *type* to ≤ ~0.5%. Definitive run (the committed
`results/`): **n = 100k, seed 1, locked levers**, corpus including LEI + small
hex — baseline hard-¼ **23.67%** [23.1, 24.2] → **`hybrid` 0.33%** [0.27, 0.41]
(identical to `combined_all`, so the white-anchor branch costs nothing in
aggregate). The original 100k corpus (UUID + larger inputs only, no small
blank-bearing types) measured the hard-¼ baseline at **27.1%**; the difference
is corpus mix — small inputs that carry a blank dilute the average down — and
both round to "about a quarter".

## What works, and the two corrections I had to make along the way

Background-unchanged ¼, colour-miss (lower is better):

| lever | colour-miss | note |
|---|---|---|
| baseline | 27.10% | — |
| blanks (skip map blank) | 27.07% | **~0 effect — see correction 1** |
| topleft | 7.65% | one cell can't cover the ¼ where its own 2 bits match |
| quartile (1st+2nd) | 0.87% | the workhorse |
| blanks_all (colour map blank) | ~20% | partial — only blank-bearing inputs |
| hybrid (locked) | 0.33% | topleft+quartile+hybrid blanks |

**Correction 1 — "blanks have zero effect" was wrong; it was a lever bug.** My
first blank lever *skipped the map blank* (`not is_map_blank`). The inputs where
blank-colouring actually matters — LEI, small hex — have exactly **one** blank,
which **is** the map blank, so skipping it did nothing for precisely those
inputs. Colouring the map blank (`blanks_all`) recovers the effect
(background-unchanged ¼, colour-miss, `diag_small.py`):

| type | mean blanks | baseline | blanks (skip-map) | **blanks_all** | quartile | hybrid |
|---|---|---|---|---|---|---|
| lei | 1 | 9.8% | 9.8% | **2.9%** | 0.4% | 0.3% |
| hex-64 (8B) | 1 | 21.5% | 21.4% | **5.6%** | 1.5% | 0.4% |
| hex-72 (9B) | 1 | 20.4% | 20.4% | **4.8%** | 1.8% | 0.2% |
| hex-24B | 1 | 7.9% | 7.9% | **1.9%** | 0.1% | 0.0% |
| hex-128 (full grid) | 0 | 60.7% | 60.7% | 60.7% | 2.5% | ~2% |

**Correction 2 — but blank-colouring still cannot touch the worst cases.** The
full-grid inputs (UUID, hex-128, …) have **zero** blanks, so no blank lever ever
helps them; only **quartile** rescues those (61% → ~2%). So quartile is the
*universal* tool; blank-colouring is *complementary*, covering the small-with-
blank regime and exaggerating the rest for free.

Net of both corrections: my initial instinct (lean on blanks) and my subsequent
over-correction (drop blanks) were both wrong. The truth is **quartile +
top-left as the universal fix, plus a hybrid blank rule** that colours the map
blank exactly when it is the sole blank.

## The map blank — why "keep it white" loses, and the hybrid

Two options for the map blank (which carries the min/max markers):

1. colour it from the fingerprint and recolour the markers for contrast;
2. keep it white as a findable anchor, colour only its siblings.

Option 2 (white anchor) **nullifies blank-colouring for LEI/small hex**, because
their *only* blank is the map blank — and the white-anomaly aesthetic it buys
needs ≥ 2 blanks, which only the multi-blank inputs (already ~0% miss) have. So
option 2 pays its cost and offers its benefit on **disjoint** input populations.

**Locked: the hybrid.** Colour the map blank from the fingerprint **only when it
is the sole blank** (single-blank small inputs get the avalanche; markers
recolour to luminance-contrast — safe because max/min identity already rides on
*shape*, plus vs dot, with colour a redundant cue per spec v8); keep it the
white/gold anchor when there are **≥ 2 blanks** (the aesthetic lands where it
can, and siblings carry the avalanche). The two regimes are disjoint, so the
branch never trades the avalanche away where it is needed. Cost of the white-
anchor branch vs always-colour, *with quartile+topleft on*: ≤ ~1.4 pp on the
smallest hex, ~0 elsewhere — small, and spent to buy findability where it helps.

## Fingerprint (middle) cells — feature, not missed opportunity

The four >512-bit fingerprint cells keep their neutral (= background) nucleus.
Declined a colour lever there, for three reasons: (1) the neutral fill is a
*semantic* marker ("readout, not literal entropy") and these cells already
avalanche in their designed channel, the **text**; (2) >512-bit inputs are the
**most** casually robust class measured (~0% colour-miss even in the hard ¼), so
there is no hole; (3) large grids already spend the singleton budget on
Changes 1–2 — the four neutral cells are part of the coherent field the
singletons pop against, so colouring them would push toward confetti and
*erode* pop-out. (Reason 3 is a perceptual-principle argument, not a measured
one — flagged for the paper's modeled-vs-measured honesty.)

## Robustness & honest caveats

- **Threshold sweep** (ΔE00 5/10/20): quartile/locked stay < ~0.8% across the
  range; baseline 24–31%. The conclusion does not depend on the glance cutoff.
- **Whole-miss ≈ 0 even at baseline** — the audit channels (ellipse 99.9%,
  colour-bar order 98.9%) almost always move. This does **not** mean a glance
  always catches the change: in the baseline's hard ¼ the only difference lives
  in the *weakest* casual channels (a translucent ellipse nudge, a thin bar
  reorder). The levers move the difference into the **dominant, pre-attentive**
  colour channel. Colour-miss — not whole-miss — is the honest glance proxy.
- `singletons` counts changed *positions*, so a blank-shift cascade inflates it;
  treat mean-singletons as a rough salience proxy, the **miss rate** as the
  headline.
- We score colour + gross structure only (the surround pattern is excluded by
  construction), and are deliberately generous to the baseline (a moved empty
  pill and the changed nucleus both count as salient), so the measured baseline
  hole is, if anything, an **under**-estimate.

## Locked design

1. **Change 1 — fingerprint-sourced surround edge colour** on the top-left cell
   and the 1st & 2nd quartile cells (2 ftok bits → edge palette). Universal fix;
   the only lever that helps full grids.
2. **Change 2 — hybrid fingerprint blank fill**: colour non-map blanks always;
   colour the map blank iff it is the sole blank (markers → luminance contrast),
   else keep it the white/gold anchor.
3. **Change 3 — fingerprint cells unchanged.**

Spec delta: [`docs/spec-v10-draft.md`](../../docs/spec-v10-draft.md). Targets
spec **v10** (breaking output change → major bump).
