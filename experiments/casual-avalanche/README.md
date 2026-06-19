# Casual-avalanche experiment

*Created 2026-06-18. Measures how often a one-character input change is
**casually** detectable in an entviz, under the shipped algorithm and under
candidate "casual-avalanche" levers, to ground a spec change and a paper
section in measured data rather than intuition.*

## The question

entviz's value proposition is **graded discriminability**: a difference should
surface to a *glance*, not only to a careful byte-by-byte comparison. But the
two comparison modes have very different bandwidths, and a channel that is
high-bandwidth for careful comparison can be ~zero-bandwidth for a glance.

The motivating observation (the `550e8400-…` UUID vs its mid-character flip,
the paper's Figure 4b): half the 24-bit surround **pattern** toggled, yet a
glancing viewer read "same surround." The pattern avalanches richly for
careful comparison and *imperceptibly* for casual comparison. What the glance
reads is the **colour gestalt** — background, and the per-cell nucleus/surround
hues — and that gestalt is largely frozen on a one-character change:

- the value is unchanged in ≥5/6 cells, so their entropy-derived nucleus
  colour (and the surround hue that echoes it) does not move; and
- the entviz background is only 2 bits, so it stays put **¼ of the time**,
  and when it stays put the whole surround palette stays put with it.

So a **structural ¼ of all one-character neighbours are casually
colour-identical**. That is the hole this experiment quantifies and the levers
try to close.

## What "casual" means here (model.py)

We score the **casual colour field**: the entviz background, plus per grid
position the cell's nucleus colour and surround (edge) colour, or — for a
blank — its pill fill. We deliberately **exclude the surround pattern** (which
boxes are filled): it is the channel we just showed a glance cannot read, so
counting it would be exactly the error we are trying to correct. Two
**audit channels** that *do* already avalanche and are casually visible — the
ellipse parameters and the colour-bar band order — are tracked separately so
we can attribute any residual discriminability to them instead of
over-crediting the colour levers.

Models are built with the **reference implementation's own internals**
(`entviz.fingerprint`, `entviz.colors`, `entviz.layout`), never a
reimplementation, so the experiment cannot silently diverge from the shipped
renderer. `model.py`'s smoke check reproduces Figure 4b's SVG byte-for-byte
(white background, nucleus `#840e55…`, the lone `#a7d441→#a7d541` nucleus
move, all surround hues identical).

## The metric (metrics.py)

Perceptual distance is **CIEDE2000 (ΔE00)**, validated against the Sharma et
al. (2005) reference vectors (`ciede2000.py::selftest`). For a neighbour pair:

- **colour-distinguishable** — the background changed, **or** some grid
  position's casually-salient colour/structure changed by more than a glance
  threshold *T*. (A position that flips between cell and blank counts as
  changed regardless of *T*.)
- **whole-distinguishable** — colour-distinguishable **or** an audit channel
  (ellipse / colour-bar order) moved.

We report the **miss rate** = `1 − distinguishable` = the fraction of
one-character neighbours a glance would call identical. Lower is better.

*T* is **swept** over ΔE00 ∈ {5, 10, 20} ("visible", "clear at a glance",
"obvious") so no conclusion rests on one cutoff. Because the five palette
colours are tens of ΔE00 apart, any *discrete* palette change clears every
threshold; *T* effectively governs only the *continuous* nucleus channel.

**Conservative choices (they make the baseline look *better*, i.e. understate
the problem):** an empty blank pill that moves to a new cell is counted as a
salient change even though a thin outline on a pale field is barely visible;
and the changed token's nucleus is scored at full ΔE00 even when it is one
cell among many. We would rather under-claim the hole than inflate it.

## The levers (levers.py)

All are fingerprint-driven, so they avalanche on any input change. Each reads
2 fingerprint bits and indexes the existing 4-colour edge palette (no new
palette — preserves the CVD/L\* guarantees the paper relies on).

| lever | what it does | rationale |
|---|---|---|
| `baseline` | shipped: surround = nearest palette to nucleus (entropy echo); blanks empty | reference |
| `topleft` | top-left cell's surround hue from the fingerprint | first-fixation primacy (LTR) |
| `quartile` | 1st & 2nd quartile cells' surround hues from the fingerprint | a few discordant colour **singletons** that move with the fingerprint (preattentive pop-out; partial by design so they *stay* singletons) |
| `blanks` | every non-map blank's pill filled from the fingerprint | exploit already-fingerprint-positioned, currently near-invisible real estate |
| `combined` | all three | — |

The partiality of `quartile` is load-bearing, not a concession: pop-out
requires the discordant cells to remain rare, so colouring *all* cells would
be self-defeating.

## Sample size — what a reader should accept as rigorous

The headline run is **100,000 independent one-character-neighbour pairs**,
fixed seed, drawn across UUID / hex-128/256/512 / base64url / >512-bit inputs.
Justification:

- For any reported proportion, the Wilson 95% CI half-width is
  ≤ `0.5/√n ≈ 0.16%` at n = 100k (worst case p = 0.5), and ≈ 0.06% for the
  small post-lever rates (p ≈ 1%). The effects we care about are whole
  percentage points, so they are resolved unambiguously.
- The decisive **background-unchanged stratum** is ~¼ of the sample (~25k),
  giving a ≤ 0.31% half-width there — still far tighter than the effect sizes.
- Each per-type stratum retains thousands of pairs.
- The model is computed analytically (no rasterization), so 100k costs
  seconds-to-minutes; there is no reason to under-power. n = 10k would already
  give ±1% on the headline, but 100k forecloses any "under-powered" objection
  and keeps the stratified cells tight.

Rigor here is **reproducibility + stratification + CIs + a threshold sweep**,
not the raw N alone: the seed, this harness, and the aggregate tables are all
committed, so every number in the paper can be regenerated.

## Running it

```sh
uv run python experiments/casual-avalanche/run.py --selftest          # validate
uv run python experiments/casual-avalanche/run.py --n 100000 --seed 1  # full run
```

Outputs: `results/RESULTS.md` (human summary, stratified, with CIs) and
`results/raw.json` (full aggregates for re-tabulation in the paper).

## Files

- `ciede2000.py` — self-contained ΔE00, reference-validated.
- `model.py` — input → casual model, via the reference implementation.
- `levers.py` — candidate levers as colour-field transforms.
- `metrics.py` — casual-distinguishability scoring.
- `run.py` — sampling, stratified aggregation, Wilson CIs, self-test.
- `results/` — generated.
