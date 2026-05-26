# entviz — comparison matrices (locked sets)

Evaluation raster is **18×6 (~6 px)** for the full form and **12×6** for the tabbed form — the ~6 px floor below which human same/different judgement is unreliable, so finer rasters are not scored. All distinctiveness numbers use the **band-weighted visibility metric**: per-cell coverage is multiplied by a weight w(y) ∈ {4,3,2,1} from outer band to inner band before the L2 distance is taken. Mass/area columns are left **physical (unweighted)**.

## CUBIST set — comparison matrices

### Per-member descriptors

| Member | area% | visMass% | outer% | cx | cy | wCy | peaks | solidity |
|---|---|---|---|---|---|---|---|---|
| C1 | 31.2 | 28.3 | 27.6 | 8.20 | 4.47 | 3.31 | 3 | 0.39 |
| C2 | 68.8 | 61.6 | 59.9 | 13.48 | 4.52 | 3.47 | 4 | 0.73 |
| C3 | 22.9 | 20.5 | 20.3 | 15.73 | 4.45 | 3.41 | 2 | 0.40 |
| C4 (empty) | 0.0 | 0.0 | 0.0 | — | — | — | 0 | — |

*area%* = physical coverage of the 24×8 cell (unweighted — a faint inner pixel still counts). *visMass%* = the same coverage **band-weighted** by distance from the nucleus (4/3/2/1, outer→inner): the share of mass that is actually *visible*. *outer%* = fraction of mass in the outer half. *cx,cy* = physical centroid. *wCy* = visibility-weighted centroid-y (pulled toward the visible outer edge). *peaks* = local maxima along the outer profile; *solidity* = area ÷ convex-hull area (1.0 = convex).

### Band-weighted distinctiveness — FULL form (18×6, untruncated — the upright glyph)

| | C1 | C2 | C3 | C4 |
|---|---|---|---|---|
| **C1** | — | 21.12 | 17.14 | 13.30 |
| **C2** | 21.12 | — | 18.33 | 19.26 |
| **C3** | 17.14 | 18.33 | — | 11.59 |
| **C4** | 13.30 | 19.26 | 11.59 | — |

**Binding (closest) pair: C3↔C4 = 11.59** — this is the number the whole set is optimized to push up.

### Band-weighted distinctiveness — TABBED form (12×6, rotation-kept window — the glyph at 90°/270°)

| | C1 | C2 | C3 | C4 |
|---|---|---|---|---|
| **C1** | — | 17.05 | 16.92 | 12.92 |
| **C2** | 17.05 | — | 15.15 | 16.18 |
| **C3** | 16.92 | 15.15 | — | 11.52 |
| **C4** | 12.92 | 16.18 | 11.52 | — |

**Binding (closest) pair: C3↔C4 = 11.52** — this is the number the whole set is optimized to push up.


---

## POLYGON set — comparison matrices

### Per-member descriptors

| Member | area% | visMass% | outer% | cx | cy | wCy | peaks | solidity |
|---|---|---|---|---|---|---|---|---|
| P1 | 52.1 | 47.0 | 45.7 | 7.69 | 4.49 | 3.40 | 1 | 0.97 |
| P2 | 29.2 | 26.4 | 26.4 | 16.93 | 4.38 | 3.38 | 1 | 0.64 |
| P3 | 29.2 | 22.2 | 20.5 | 6.41 | 5.19 | 4.14 | 2 | 0.38 |
| P4 (empty) | 0.0 | 0.0 | 0.0 | — | — | — | 0 | — |

*area%* = physical coverage of the 24×8 cell (unweighted — a faint inner pixel still counts). *visMass%* = the same coverage **band-weighted** by distance from the nucleus (4/3/2/1, outer→inner): the share of mass that is actually *visible*. *outer%* = fraction of mass in the outer half. *cx,cy* = physical centroid. *wCy* = visibility-weighted centroid-y (pulled toward the visible outer edge). *peaks* = local maxima along the outer profile; *solidity* = area ÷ convex-hull area (1.0 = convex).

### Band-weighted distinctiveness — FULL form (18×6, untruncated — the upright glyph)

| | P1 | P2 | P3 | P4 |
|---|---|---|---|---|
| **P1** | — | 19.93 | 16.09 | 17.26 |
| **P2** | 19.93 | — | 15.71 | 12.09 |
| **P3** | 16.09 | 15.71 | — | 10.57 |
| **P4** | 17.26 | 12.09 | 10.57 | — |

**Binding (closest) pair: P3↔P4 = 10.57** — this is the number the whole set is optimized to push up.

### Band-weighted distinctiveness — TABBED form (12×6, rotation-kept window — the glyph at 90°/270°)

| | P1 | P2 | P3 | P4 |
|---|---|---|---|---|
| **P1** | — | 12.06 | 15.96 | 17.26 |
| **P2** | 12.06 | — | 14.31 | 12.10 |
| **P3** | 15.96 | 14.31 | — | 10.36 |
| **P4** | 17.26 | 12.10 | 10.36 | — |

**Binding (closest) pair: P3↔P4 = 10.36** — this is the number the whole set is optimized to push up.
