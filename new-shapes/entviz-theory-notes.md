# entviz — design rationale & perceptibility theory (notes for the paper rewrite)

This document explains **why** the entviz edge-glyph design ended up where it did, what the
numbers in the comparison matrices actually measure, and how each decision connects to
perceptibility theory. It is written as source material for rewriting the academic paper, so it
separates **established perceptual theory** from **design choices/heuristics we adopted** and from
**model-dependent computed results**. Those three have different epistemic standing and the paper
should not blur them.

---

## 1. What the glyph is, and what "distinctiveness" has to mean

entviz renders a high-entropy value as a small grid of cells. Each cell is a fixed **nucleus**
rectangle plus six **edge slots** that carry the entropy. The reader's task is *same-or-different at
a glance* — a verification task, not a reading task. So the design objective is not "look nice" and
not "encode maximum bits"; it is **perceptual discriminability of a small fixed alphabet of edge
shapes under severe size reduction.**

Two consequences follow immediately and shape everything else:

- **The alphabet is tiny and closed.** Each set is 3 shapes + 1 empty. With so few symbols, the
  thing that matters is not average separation but the **worst case** — the closest pair a human
  will ever have to tell apart. The objective is therefore **maximin**: maximize the *minimum*
  pairwise distance over the whole set. Averages hide the failure mode and must not be the headline
  metric.

- **Empty is a member, not a background.** A slot with no edge (negative space) is a legitimate,
  maximally-available symbol. Every shape must be distinguishable **both from the other shapes and
  from blank.** This turns out to be the binding half of the problem (§5).

---

## 2. The perceptual floor and what survives it

*(Established psychophysics, applied; the specific thresholds below are our design heuristics, flagged as such.)*

Under reduction, edges are read at roughly **6 px**. We treat ~6 px as the floor below which human
same/different judgement is unreliable, and we therefore **score on an 18×6 raster** for the upright
glyph (and 12×6 for the rotated/tabbed form). Finer rasters were dropped as sub-threshold.
*(Epistemic flag: the 6 px figure is an adopted design threshold, not a measured constant; the paper
should present it as a modelling choice with a sensitivity caveat, not a law.)*

What actually survives to 6 px, in order of robustness:

1. **Mass** — the total ink (the DC / zeroth-moment term). This dominates.
2. **Centroid / position** — where that mass sits (first moment). Secondary but real.
3. **Coarse distribution** — rough left/right, outer/inner balance.

What does **not** survive: fine concavities, individual peaks, exact solidity, curvature detail.
These are "full-size character only." This is why the design is **angular, never curved**: the paper's
own JND hierarchy puts **length and aspect ratio among the strong discriminability channels and
curvature as the weakest**; curves also degrade worst under the 24→16 horizontal compression
(§6) and clash with the rectangular nucleus. Angular shapes preserve the strong channels (length,
aspect, position) and survive both truncation and rasterization. *(Established: Weber-law / JND
framing. Applied claim: curvature is the channel to avoid here — well-supported by the hierarchy the
paper already asserts.)*

---

## 3. The central insight: inner/outer visibility is asymmetric

The cell has an orientation the naïve metric ignored. **y = 0 is the outer edge — the cell boundary
— a high-contrast, fully visible border. y = 8 is the inner edge, flush against the nucleus, where
the shape is gradient-blended into the body and barely readable.** So *a pixel's perceptual weight
depends on its distance from the nucleus*: outer ink is loud, inner ink is quiet.

The first metric we used (plain L2 over coverage) was **blind to this** — it weighted every cell
equally and so **credited invisible inner ink as if it were fully visible.** That is not a cosmetic
error; it produced a *wrong design conclusion*. Under the unweighted metric one shape looked like the
problem child, and we nearly "fixed" the wrong shape. When we corrected the metric, the diagnosis
**inverted**: the real weak member was the one carrying a large fraction of its mass as invisible
inner ink. The paper should tell this as a cautionary methodological point: **a distinctiveness
metric that ignores a real figure/ground asymmetry will confidently mislead.**

---

## 4. Why we weight the *centroid* by distance-from-nucleus but **not** the *mass*

This is the subtle decision and it deserves precise language in the paper, because "we added a
weighting" undersells it. There are **two different questions**, and they get **two different
treatments**:

- **Mass / area answers a physical question:** *is there ink here?* A faint inner pixel is still a
  pixel of ink. For the **physical descriptor (`area%`) we leave it unweighted** — we do not lie
  about how much ink exists. Weighting the mass would amount to asserting that inner ink is partly
  *absent*, which is false.

- **Distinctiveness answers a perceptual question:** *will a human see this difference?* Here the
  visibility gradient is real and must enter. So **only the distinctiveness computation multiplies
  each cell's coverage by a band weight `w(y)` before taking the L2 distance.**

The non-obvious part: **because `w` depends only on `y` (the vertical band), it rescales the vertical
axis only.** To first order it leaves the horizontal centroid `cx` untouched and acts on the vertical
centroid `cy`. So, analytically, *"weight distinctiveness by distance from the nucleus" is the same
operation as "let centroid-y differences count more and discount inner mass."* That is exactly why
the right statement is **"weight the centroid by distance from the nucleus, but treat mass
physically"** — they are the same knob viewed from two angles. *(Epistemic flag: "leaves `cx`
untouched to first order" is an analytic approximation, exact only because `w` is a function of `y`
alone; higher-order coupling exists if mass is unevenly distributed in `x` within a band, but it is
negligible at this raster.)*

Concretely the weights are **4 / 3 / 2 / 1** across the four bands `y∈[0,2)/[2,4)/[4,6)/[6,8)`,
outer→inner. **These weights are the tunable knob, not a derived constant** — a steeper inner
discount is defensible and the paper should present 4/3/2/1 as a reasonable first calibration of the
figure/ground contrast gradient, not as measured. The weighting is Weber-like in spirit: it scales a
difference by the *relative visibility* of the region it occurs in.

Two derived descriptor columns make the weighting legible:

- **`visMass%` = Σ w·cov ⁄ Σ w** — the share of mass that is actually *visible*. This, not `area%`,
  is the **actionable lever**: to push a shape away from empty you must add **outer** mass, not just
  any area.
- **`wCy`** — the visibility-weighted centroid-y, pulled toward the visible outer edge relative to
  the physical `cy`.

The ratio **`visMass% ⁄ area%`** exposes wasted ink. In the locked sets the three cubist shapes and
P1 sit around **0.90** (little wasted; P2 also ≈ 0.90 after its base was made more triangular); the binding-constraint shapes are the low-ratio ones — **P3 ≈
0.76** is the most inner-heavy member and, not coincidentally, the one closest to empty (§5).

---

## 5. Distinguishing from emptiness is the binding constraint

Because empty is a member, each shape must clear a minimum distance **from the zero vector**. In the
weighted metric, *distance-from-empty is just the norm of a shape's weighted coverage vector* — so a
shape that is **sparse** or **inner-heavy** (low `visMass%`) collapses toward empty *perceptually*
even when it has respectable physical area.

The matrices confirm this is **the** bottleneck: in both sets the matrix minimum is a
**shape-vs-empty** entry, not a shape-vs-shape entry —

- cubist: **C3 ↔ empty ≈ 11.5** (C3 has the lowest `visMass%`, 20.5),
- polygon: **P3 ↔ empty ≈ 10.4** (P3 has the lowest `visMass/area`, 0.76).

Design implication the paper should state plainly: **you cannot solve discriminability by spreading
shapes apart from each other alone.** You must simultaneously hold every shape a safe distance from
the origin, and the lightest shape sets the bar for the whole set. Much of the late design work was
raising the lightest shape's *outer* mass (not its area) to lift that one number.

---

## 6. Rotation, the tab, and why there are two forms per shape

Edges populate the six slots by rotation. A slot reached by a 90°/270° rotation maps the 24-wide
edge into a channel only ~16 wide, so a wide shape cannot survive intact: we keep a **16-wide
truncation window (the "tab")** and discard the ends on rotation. Hence **every wide shape has two
forms** — the **full** form (upright, 0°/180°) and the **tabbed** form (rotated, 90°/270°) — and
**both must be scored.** The rotation pivot is the **hinge** at the tab's outer-left corner,
`(window_left, 0)`.

The tabbed matrix matters because truncation could in principle collapse a pair. It does not: tabbed
distances track the full ones closely (e.g. cubist binding 11.59 → 11.52; polygon 10.57 → 10.36).
The reason is exactly the visibility weighting — **truncation mostly shaves low-weight inner/edge
mass**, so it costs little perceptual distance. This is a payoff of the weighted metric: it predicts
*a priori* that truncation should be nearly free, and the numbers bear it out. *(Earlier, under the
unweighted metric, truncation looked alarming — another artifact the weighting dissolved.)*

---

## 7. Connecting regions and Gestalt — tuned, not maximized

Adjacent cells compose into a larger perceived figure, and the design deliberately supports that:
horizontal neighbours meet at **L/R seams** (the connector registers on `x=0` and `x=24`, matched so
a left-edge's right side meets a right-edge's left side at `y∈[4,8]`), and vertical neighbours meet
**outer-to-outer** (an X-mirror at `y=0`). These seams aid **Gestalt grouping / good continuation** —
they let the composite read as one coherent fingerprint rather than a noisy field of unrelated marks,
which stabilizes the overall same/different judgement.

Crucially these regions are **tuned, not maximized.** They are a *constraint* (make the seams line up
so the figure coheres), not the *objective* (which is per-pair distinctiveness). Over-investing in
seam continuity would homogenize the shapes and shrink the maximin distance. The paper should frame
seams as a Gestalt-level scaffolding layer sitting *above* the per-cell discriminability layer, with
the two in mild tension.

A related, important limitation: **the metric sees only mass and position — it cannot see "shape
category" or Gestalt similarity.** Two members can be numerically well-separated yet still read as
"the same kind of thing" (the classic trap: a large triangle and a small triangle look like *one
shape scaled*, not two shapes). We addressed this with several **metric-neutral, perceptually-real
moves** — edits that barely move the numbers but break the scaled-copy reading (e.g. P1's *symmetric*
upper-left V-notch, which splits its edge into two equal-length segments; P3's right-flank
concavity). These are invisible to the L2 score but decisive to a human, and the paper should be
explicit that **part of the design lives in a perceptual register the quantitative metric does not
capture** — the metric is necessary, not sufficient.

---

## 8. How to read the comparison matrices (for the methods section)

Each off-diagonal cell is the **band-weighted Euclidean (L2) distance** between two members'
visibility-weighted coverage vectors on the scoring raster (18×6 full, 12×6 tabbed). **Bigger =
more discriminable.** It is a *perceptual-distance proxy*, deliberately coarse, consistent with §2:
an L2 on a low-resolution raster approximates a low-spatial-frequency comparison (mass + first
moment), which is what survives at 6 px; the band weighting overlays the figure/ground contrast
gradient.

- The **empty column/row** is the **norm** (distance from the zero vector) — how far each shape is
  from blank.
- The **matrix minimum is the set's discriminability bottleneck**; the design pushes that number up.
- **Descriptor columns:** `area%` = physical ink (unweighted, honest about quantity); `visMass%` =
  visible ink (the lever); `outer%` = share in the outer half; `cx,cy` = physical centroid; `wCy` =
  perceptual centroid pulled outward; `peaks`/`solidity` = full-size character only, **sub-threshold
  at 6 px and informational, not load-bearing.**

*(Epistemic flag on all numbers: they are deterministic outputs of our raster model — even-odd
polygon fill, 4×4 supersampled coverage, band cutoffs on the integer grid, weights 4/3/2/1. They are
reproducible but model-relative; absolute magnitudes are only meaningful **within** a set and a form.
Cross-set magnitude comparisons are not meaningful. The paper should report them as relative/ordinal
evidence for the maximin argument, with the model fully specified so they are replicable.)*

---

## 9. The design arc, as methodological narrative

Three turning points are worth keeping because they are instructive, not just historical:

1. **Making empty a member** (dropping a former shape to negative space) revealed that
   *lightest-shape-vs-empty* is the binding constraint — reframing the whole objective around the
   origin, not just inter-shape spread.
2. **Re-deriving the metric** to respect inner/outer visibility *inverted a prior conclusion* and
   dissolved a truncation "alarm" that had been a pure artifact. Lesson: validate that the metric
   encodes the real perceptual asymmetries before trusting its rankings.
3. **Separating "metric-neutral but perceptually-real" edits** from metric-moving ones made explicit
   that the quantitative objective and the Gestalt/category objective are *different layers*, and
   that good design serves both.

### One-paragraph abstract-ready summary
entviz amplifies the visual difference between high-entropy values by rendering them as small angular
edge-glyphs optimized for *worst-case* (maximin) discriminability at a ~6 px perceptual floor, where
only mass and coarse position survive. Because the cell's inner edge is occluded against the nucleus
while its outer edge is a high-contrast boundary, discriminability is scored with a **band-weighted**
metric that discounts inner ink (operationally: weighting the centroid by distance from the nucleus
while leaving physical mass unweighted), and every shape is held distinct **both from its peers and
from empty negative space** — the latter being the binding constraint. Cross-cell seams provide
Gestalt scaffolding without being maximized, and a residual layer of category-breaking shape edits
addresses similarity that the quantitative metric cannot perceive.
