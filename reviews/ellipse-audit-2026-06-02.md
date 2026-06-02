# Ellipse overlay audit (2026-06-02)

Audit of the v4/v5 hybrid-anchored ellipse overlay, requested during early
v6 planning. Two questions:

1. **Correctness** — are there grids/parameters where the rendering math goes
   degenerate (empty/inverted radius range, clip-to-nothing, division by zero)?
2. **Sizing** — is the overlay always *noticeable but partial*? The overlay's
   value is the gestalt contrast between covered (darkened) and uncovered parts
   of the entviz. It fails if it covers almost nothing (invisible) or almost
   everything (no contrast). Two entvizes are distinguishable if **any** of
   three coarse perceptual features differ (a disjunction, not a conjunction):
   the **coverage ratio**, the **location** of the dark region, **or** its
   **aspect/shape**. Two overlays "look alike" only when they match on *all
   three*. The eye judges this by gestalt, not by measuring axes.

**Method.** Drove the real implementation (`choose_grid`,
`enumerate_interior_corners` / `enumerate_external_corners`, the
`r_min`/`r_max` mapping in `_draw_ellipse_overlay`) across every token count
1–22 and target aspect ratios 0.25–8.0, at 12pt geometry
(`cell_w = 3.75·fpx = 60`, `cell_h = 2.5·fpx = 40`, `r_min = cell_h/2 = 20`).
All findings are scale-invariant (radii and cell dims scale linearly with font
size) except where 6pt is called out. Reproduction scripts in the appendix.

> **Visually confirmed (2026-06-02).** cairosvg was re-added as an opt-in dev
> tool (the `render` dependency group; not a runtime dep). A rasterized
> prototype matrix (5 grids × draws nearest 8/30/60/85% coverage) confirms the
> coverage findings by eye: the too-faint floor shows as a barely-perceptible
> edge sliver on 3×3 and 11×2 at 8%; the near-total ceiling swamps 4×4 (80%),
> 4×6 (85%), and 11×2 (85%), leaving only a thin light sliver; 2×2 is naturally
> self-limiting (~52% max); the ~30% draws are the sweet spot and look clearly
> distinct across grids (OR-diversity visible). Conclusion stands: clamp
> coverage to ~15–60%.

## Q1 — Correctness: no degenerate math

Across the full sweep, the radius range `[r_min, r_max]` (with
`r_max = d_far − cell_w`, `d_far` = distance from anchor to the farthest
grid-rect corner) is **always valid**: `r_max` exceeds `r_min` by ≥ 20px on the
smallest grid (2×2) and grows from there. The defensive guard
`if r_max <= r_min: return` (`pipeline.py:776`) **never fires** for any grid
entviz can produce, and the interior↔external anchor switch at the
`≥ 6 interior corners` threshold is continuous (no grid is left without a valid
anchor pool). The "always draws an overlay" guarantee (spec line 267) holds.

**Sub-finding (non-breaking): small-grid radius discretization is below JND.**
On 2×2 / 2×3 the `[r_min, r_max]` band is only ~20–90px wide, so the 16-step
`rx`/`ry` discretization yields ~1.3–6px per step at 12pt — and **0.6–3px per
step at 6pt**. The spec claims (line 288) that 16 steps sit near the
just-noticeable-difference threshold; that is false on the smallest grids,
where adjacent radius steps are visually identical. The radius channel
therefore under-delivers entropy on small grids. This compounds the spatial
diversity problem below.

## Q2 — Sizing, reframed as coverage + location

The original draft of this audit measured flank curvature ("near-straight
smudge"). Per maintainer guidance, that is **not** the concern: a straight-ish
arc is fine. The concern is **what fraction of the entviz is darkened, and
where**. Recomputed on that basis.

### Coverage fraction (darkened share of grid area)

Sampled over **all** reachable draws (anchor × `rx_step` × `ry_step` ×
rotation), coverage = fraction of grid-rect area inside the clipped ellipse:

| grid | mode | min% | p10 | median | p90 | max% | share <8% (too faint) | share >80% (near-total) |
|------|------|-----:|----:|-------:|----:|-----:|----------------------:|------------------------:|
| 2×2  | ext  |  3 |  9 | 19 | 40 | 57 |  8% | 0% |
| 2×3  | ext  |  2 |  8 | 22 | 45 | 66 | 10% | 0% |
| 3×3  | ext  |  1 |  8 | 26 | 57 | 77 | 10% | 0% |
| 3×4  | int  |  4 | 12 | 30 | 58 | 78 |  3% | 0% |
| 4×4  | int  |  3 | 12 | 31 | 64 | 85 |  4% | 1% |
| 4×5  | int  |  3 | 11 | 32 | 66 | 91 |  5% | 2% |
| 4×6  | int  |  2 | 10 | 32 | 68 | 93 |  6% | 3% |
| 2×6  | ext  |  1 |  8 | 28 | 63 | 83 | 11% | 1% |
| 6×2  | ext  |  1 | 10 | 37 | 72 | 85 |  7% | 3% |
| 8×3  | int  |  2 | 12 | 44 | 77 | 89 |  3% | 7% |
| 2×11 | int  |  2 | 12 | 43 | 75 | 87 |  3% | 5% |
| 11×2 | int  |  2 | 12 | 46 | 80 | 91 |  6% | 10% |

**Interpretation.** The *typical* overlay is good — medians sit at ~19–46%, a
healthy partial split. The **tails are the problem**:

- **Too-faint tail.** 3–11% of inputs darken < 8% of the grid → the overlay is
  barely noticeable. Fails the "noticeable" requirement.
- **Near-total tail.** On larger / near-square grids, up to **7–10% of inputs**
  darken > 80% of the grid (max reaches 91–93% on 4×5/4×6). The overlay then
  swamps the entviz and the covered-vs-uncovered contrast — its entire value —
  is lost. This is the maintainer's stated worry, confirmed reachable.

The useful coverage band is roughly **15–65%**; the current parameterization
lets draws fall well outside it at both ends.

### Joint diversity (do two overlays look alike?)

Collision = two independent draws match on **all** distinguishing features.
Signature per draw built from (coverage bucket; which 3×3 super-tiles are >50%
dark; elongation + orientation of the covered region's principal axes).
Collision probability = Σ fᵢ². The middle column keys on coverage + location
only (the conjunctive over-estimate from the first pass); the right column adds
the aspect/shape axis to match the OR discrimination model:

| grid | mode | # anchor positions | P(alike) cov+loc | P(alike) cov+loc+**aspect** |
|------|------|-------------------:|-----------------:|----------------------------:|
| 2×2  | ext  |  8 | 5.1% | **1.3%** |
| 2×3  | ext  | 10 | 4.0% | **0.8%** |
| 3×3  | ext  | 12 | 4.7% | **0.7%** |
| 3×4  | int  |  6 | 5.6% | **0.9%** |
| 4×4  | int  |  9 | 3.0% | **0.5%** |
| 4×6  | int  | 15 | 5.1% | **0.6%** |
| 6×2  | ext  | 16 | 6.7% | **1.4%** |
| 8×3  | int  | 14 | 7.7% | **1.5%** |
| 11×2 | int  | 10 | 8.2% | **2.2%** |

**Interpretation.** Under the correct OR model — distinguishable if coverage
*or* location *or* aspect differs — overlay diversity is **good**: two random
entvizes look alike only ~0.5–2.2% of the time (≈ 1 in 45–200 pairs), best on
small/mid grids and worst on the most elongated grids (11×2 at 2.2%). The
aspect/shape axis is doing real work: it roughly quarters the collision rate
versus coverage+location alone. The small anchor pool (as few as 6 positions)
is therefore **not** a serious limiter in practice; positional diversity is
adequate once shape is counted. This is acceptable as-is.

## Conclusions and proposed v6 changes

1. **No correctness fix needed.** The math is sound on every reachable grid.
2. **The one real fix (ADOPTED): clamp the radius bounds `d_far`-relative.**
   The tails were the problem: 3–11% of draws darkened < 8% (barely visible) and
   up to 7–10% on large/near-square grids darkened > 80% (swamping). A
   *grid-relative* clamp (`rx ≤ k·grid_width`) was tried first and rejected — it
   tanks the floor (25–54% of draws < 8%) because corner-anchored small ellipses
   get clipped to nothing. The fix that works is **`rx, ry ∈ [0.22·d_far,
   0.58·d_far]`** (replacing the v5 `[r_min, d_far − cell_w]`): the floor scales
   with the grid so small grids aren't slivers and large grids aren't tiny, and
   the ceiling caps swamping. Measured result across the ar=1.0 grids (and the
   extreme 2×N/N×2 grids): coverage min ~8%, median ~32–36%, max ~70%, with the
   <8% and >70% tails both ≈ 0. Visually confirmed via the prototype
   (`scripts/ellipse_prototype.py`, candidate A) — smallest draws are compact
   visible blobs, largest always leave a clear light margin. This also fixes the
   small-grid discretization sub-finding (the step now scales with `d_far`). The
   degenerate guard never fires (`0.58·d_far > 0.22·d_far` always).
3. **Diversity needs no fix.** Under the OR discrimination model (coverage *or*
   location *or* aspect), two overlays collide only ~0.5–2.2% of the time — the
   anchor pool size is a non-issue once shape is counted. (The small-grid radius
   discretization sub-finding from Q1 is cosmetic, not a diversity threat;
   address opportunistically if the coverage-clamp rework touches that code.)
4. **Re-prototype before committing the `k`/floor constants**, ideally with a
   real renderer installed so the coverage band can be confirmed by eye, not
   just by the metric.

These supersede the now-moot "flatness" framing and the stale deferred item
**D16** (small grids already get overlays; the issue is tuning, not existence).

## Appendix — reproduction

`coverage` (per-grid darkened-fraction distribution):

```python
import math, numpy as np
from entviz.layout import choose_grid, Point
from entviz.pipeline import (enumerate_interior_corners,
    enumerate_external_corners, _HYBRID_INTERIOR_THRESHOLD)
FPX=16.0; CELL_W=3.75*FPX; CELL_H=2.5*FPX; R_MIN=CELL_H/2; N=120
def pool(cols,rows):
    if (cols-1)*(rows-1)>=_HYBRID_INTERIOR_THRESHOLD:
        return "int", enumerate_interior_corners(cols,rows,CELL_W,CELL_H,Point(0,0))
    return "ext", enumerate_external_corners(cols,rows,CELL_W,CELL_H,Point(0,0))
def dfar(a,W,H): return max(math.hypot(c[0]-a.x,c[1]-a.y) for c in [(0,0),(W,0),(0,H),(W,H)])
def coverage_dist(cols,rows):
    mode,pts=pool(cols,rows); W,H=cols*CELL_W,rows*CELL_H
    xs=(np.arange(N)+0.5)/N*W; ys=(np.arange(N)+0.5)/N*H; GX,GY=np.meshgrid(xs,ys)
    covs=[]
    for a in pts:
        r_max=dfar(a,W,H)-CELL_W
        if r_max<=R_MIN: continue
        for rxs in range(16):
            for rys in range(16):
                rx=R_MIN+(rxs/15)*(r_max-R_MIN); ry=R_MIN+(rys/15)*(r_max-R_MIN)
                for rts in range(0,16,2):
                    th=math.radians((rts/15)*180); dx=GX-a.x; dy=GY-a.y
                    ct,st=math.cos(-th),math.sin(-th); xr=dx*ct-dy*st; yr=dx*st+dy*ct
                    covs.append(((xr/rx)**2+(yr/ry)**2<=1.0).mean())
    return np.array(covs)
```

Run with `PYTHONPATH=src`. The spatial-diversity script (3×3 super-tile
signature + Σfᵢ² collision estimate) and the browser prototype generator
(`/tmp/ellipse_proto.html`) are in the v6 working session; fold them into
`scripts/` if this audit drives a permanent regression test.
