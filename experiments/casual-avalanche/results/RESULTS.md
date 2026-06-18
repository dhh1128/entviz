# Casual-avalanche results

- pairs: **30000**  seed: 2  skipped(resampled): 22  elapsed: 778.1s

- audit channels (fraction of pairs that move): ellipse 100.0%, colour-bar order 99.0%


Miss-rate = fraction of one-char neighbours a glance would call identical. Lower is better. ΔE00 threshold T=10 ('clear at a glance'); Wilson 95% CI in brackets.


## All pairs  (n=30000)

| lever | colour-miss | whole-miss | mean singletons | ≥1 singleton |
|---|---|---|---|---|
| baseline |   5.92%  [ 5.66,  6.19] |   0.05%  [ 0.03,  0.08] | 5.93 | 92.8% |
| topleft |   1.98%  [ 1.83,  2.15] |   0.05%  [ 0.03,  0.08] | 6.26 | 97.5% |
| quartile |   0.21%  [ 0.16,  0.26] |   0.05%  [ 0.03,  0.08] | 6.98 | 99.8% |
| blanks |   5.91%  [ 5.65,  6.18] |   0.05%  [ 0.03,  0.08] | 6.00 | 92.8% |
| blanks_all |   4.76%  [ 4.53,  5.01] |   0.05%  [ 0.03,  0.08] | 6.11 | 94.5% |
| combined |   0.15%  [ 0.11,  0.20] |   0.05%  [ 0.03,  0.08] | 7.22 | 99.8% |
| combined_all |   0.10%  [ 0.07,  0.14] |   0.05%  [ 0.03,  0.08] | 7.32 | 99.9% |
| hybrid |   0.10%  [ 0.07,  0.14] |   0.05%  [ 0.03,  0.08] | 7.31 | 99.9% |

## Background-unchanged stratum (the hard ¼)  (n=7301)

| lever | colour-miss | whole-miss | mean singletons | ≥1 singleton |
|---|---|---|---|---|
| baseline |  24.31%  [23.34, 25.31] |   0.19%  [ 0.11,  0.32] | 3.96 | 75.7% |
| topleft |   8.15%  [ 7.54,  8.80] |   0.19%  [ 0.11,  0.32] | 4.49 | 91.9% |
| quartile |   0.85%  [ 0.66,  1.09] |   0.19%  [ 0.11,  0.32] | 5.61 | 99.2% |
| blanks |  24.27%  [23.30, 25.27] |   0.19%  [ 0.11,  0.32] | 4.03 | 75.7% |
| blanks_all |  19.57%  [18.68, 20.50] |   0.19%  [ 0.11,  0.32] | 4.13 | 80.4% |
| combined |   0.62%  [ 0.46,  0.82] |   0.19%  [ 0.11,  0.32] | 5.97 | 99.4% |
| combined_all |   0.40%  [ 0.28,  0.57] |   0.19%  [ 0.11,  0.32] | 6.06 | 99.6% |
| hybrid |   0.40%  [ 0.28,  0.57] |   0.19%  [ 0.11,  0.32] | 6.05 | 99.6% |

## Background-changed stratum  (n=22699)

| lever | colour-miss | whole-miss | mean singletons | ≥1 singleton |
|---|---|---|---|---|
| baseline |   0.00%  [ 0.00,  0.02] |   0.00%  [ 0.00,  0.02] | 6.57 | 98.3% |
| topleft |   0.00%  [ 0.00,  0.02] |   0.00%  [ 0.00,  0.02] | 6.83 | 99.3% |
| quartile |   0.00%  [ 0.00,  0.02] |   0.00%  [ 0.00,  0.02] | 7.42 | 100.0% |
| blanks |   0.00%  [ 0.00,  0.02] |   0.00%  [ 0.00,  0.02] | 6.64 | 98.3% |
| blanks_all |   0.00%  [ 0.00,  0.02] |   0.00%  [ 0.00,  0.02] | 6.74 | 99.0% |
| combined |   0.00%  [ 0.00,  0.02] |   0.00%  [ 0.00,  0.02] | 7.62 | 100.0% |
| combined_all |   0.00%  [ 0.00,  0.02] |   0.00%  [ 0.00,  0.02] | 7.73 | 100.0% |
| hybrid |   0.00%  [ 0.00,  0.02] |   0.00%  [ 0.00,  0.02] | 7.72 | 100.0% |

## Threshold sensitivity — colour-miss, background-unchanged stratum

| lever | T=5 | T=10 | T=20 |
|---|---|---|---|
| baseline | 21.11% | 24.31% | 27.43% |
| topleft | 7.07% | 8.15% | 9.37% |
| quartile | 0.79% | 0.85% | 0.99% |
| blanks | 21.07% | 24.27% | 27.38% |
| blanks_all | 17.11% | 19.57% | 21.76% |
| combined | 0.58% | 0.62% | 0.74% |
| combined_all | 0.38% | 0.40% | 0.42% |
| hybrid | 0.38% | 0.40% | 0.42% |

## Per-type colour-miss (all pairs, T=10) — locked `hybrid`

| type | baseline | quartile only | hybrid (locked) |
|---|---|---|---|
| b64url256 (n=3286) | 0.85% | 0.03% | 0.00% |
| hex128 (n=3356) | 15.64% | 0.51% | 0.45% |
| hex256 (n=3210) | 1.12% | 0.03% | 0.00% |
| hex512 (n=3374) | 0.15% | 0.00% | 0.00% |
| hex64 (n=3284) | 4.84% | 0.40% | 0.12% |
| hex72 (n=3325) | 4.72% | 0.42% | 0.06% |
| large1600 (n=1667) | 0.00% | 0.00% | 0.00% |
| lei (n=3350) | 2.33% | 0.06% | 0.00% |
| uuid (n=5148) | 15.29% | 0.27% | 0.16% |
