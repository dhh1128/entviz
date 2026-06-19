# Casual-avalanche results

- pairs: **100000**  seed: 1  skipped(resampled): 66  elapsed: 872.9s

- audit channels (fraction of pairs that move): ellipse 100.0%, colour-bar order 99.0%


Miss-rate = fraction of one-char neighbours a glance would call identical. Lower is better. ΔE00 threshold T=10 ('clear at a glance'); Wilson 95% CI in brackets.


## All pairs  (n=100000)

| lever | colour-miss | whole-miss | mean singletons | ≥1 singleton |
|---|---|---|---|---|
| baseline |   5.94%  [ 5.80,  6.09] |   0.04%  [ 0.03,  0.05] | 5.91 | 92.8% |
| topleft |   1.96%  [ 1.88,  2.05] |   0.04%  [ 0.03,  0.05] | 6.23 | 97.5% |
| quartile |   0.22%  [ 0.19,  0.25] |   0.04%  [ 0.03,  0.05] | 6.96 | 99.7% |
| blanks |   5.93%  [ 5.79,  6.08] |   0.04%  [ 0.03,  0.05] | 5.98 | 92.8% |
| blanks_all |   4.70%  [ 4.57,  4.83] |   0.04%  [ 0.03,  0.05] | 6.08 | 94.6% |
| combined |   0.15%  [ 0.13,  0.18] |   0.04%  [ 0.03,  0.05] | 7.20 | 99.8% |
| combined_all |   0.08%  [ 0.07,  0.10] |   0.04%  [ 0.03,  0.05] | 7.30 | 99.9% |
| hybrid |   0.08%  [ 0.07,  0.10] |   0.04%  [ 0.03,  0.05] | 7.29 | 99.9% |

## Background-unchanged stratum (the hard ¼)  (n=25099)

| lever | colour-miss | whole-miss | mean singletons | ≥1 singleton |
|---|---|---|---|---|
| baseline |  23.67%  [23.14, 24.20] |   0.16%  [ 0.12,  0.22] | 4.00 | 76.3% |
| topleft |   7.82%  [ 7.50,  8.16] |   0.16%  [ 0.12,  0.22] | 4.53 | 92.2% |
| quartile |   0.87%  [ 0.76,  0.99] |   0.16%  [ 0.12,  0.22] | 5.65 | 99.1% |
| blanks |  23.64%  [23.12, 24.17] |   0.16%  [ 0.12,  0.22] | 4.07 | 76.4% |
| blanks_all |  18.73%  [18.26, 19.22] |   0.16%  [ 0.12,  0.22] | 4.17 | 81.3% |
| combined |   0.61%  [ 0.52,  0.71] |   0.16%  [ 0.12,  0.22] | 5.99 | 99.4% |
| combined_all |   0.33%  [ 0.27,  0.41] |   0.16%  [ 0.12,  0.22] | 6.09 | 99.7% |
| hybrid |   0.33%  [ 0.27,  0.41] |   0.16%  [ 0.12,  0.22] | 6.08 | 99.7% |

## Background-changed stratum  (n=74901)

| lever | colour-miss | whole-miss | mean singletons | ≥1 singleton |
|---|---|---|---|---|
| baseline |   0.00%  [ 0.00,  0.01] |   0.00%  [ 0.00,  0.01] | 6.55 | 98.3% |
| topleft |   0.00%  [ 0.00,  0.01] |   0.00%  [ 0.00,  0.01] | 6.80 | 99.3% |
| quartile |   0.00%  [ 0.00,  0.01] |   0.00%  [ 0.00,  0.01] | 7.40 | 100.0% |
| blanks |   0.00%  [ 0.00,  0.01] |   0.00%  [ 0.00,  0.01] | 6.62 | 98.3% |
| blanks_all |   0.00%  [ 0.00,  0.01] |   0.00%  [ 0.00,  0.01] | 6.72 | 99.0% |
| combined |   0.00%  [ 0.00,  0.01] |   0.00%  [ 0.00,  0.01] | 7.60 | 100.0% |
| combined_all |   0.00%  [ 0.00,  0.01] |   0.00%  [ 0.00,  0.01] | 7.71 | 100.0% |
| hybrid |   0.00%  [ 0.00,  0.01] |   0.00%  [ 0.00,  0.01] | 7.70 | 100.0% |

## Threshold sensitivity — colour-miss, background-unchanged stratum

| lever | T=5 | T=10 | T=20 |
|---|---|---|---|
| baseline | 21.00% | 23.67% | 27.02% |
| topleft | 6.92% | 7.82% | 8.99% |
| quartile | 0.78% | 0.87% | 0.98% |
| blanks | 20.98% | 23.64% | 26.99% |
| blanks_all | 16.79% | 18.73% | 21.31% |
| combined | 0.57% | 0.61% | 0.68% |
| combined_all | 0.33% | 0.33% | 0.39% |
| hybrid | 0.33% | 0.33% | 0.39% |

## Per-type colour-miss (all pairs, T=10) — locked `hybrid`

| type | baseline | quartile only | hybrid (locked) |
|---|---|---|---|
| b64url256 (n=11192) | 1.05% | 0.02% | 0.01% |
| hex128 (n=11089) | 15.74% | 0.59% | 0.46% |
| hex256 (n=11147) | 1.43% | 0.03% | 0.01% |
| hex512 (n=11108) | 0.09% | 0.00% | 0.00% |
| hex64 (n=11172) | 4.60% | 0.38% | 0.09% |
| hex72 (n=11153) | 5.26% | 0.54% | 0.08% |
| large1600 (n=5412) | 0.00% | 0.00% | 0.00% |
| lei (n=11025) | 2.12% | 0.12% | 0.00% |
| uuid (n=16702) | 15.41% | 0.19% | 0.07% |
