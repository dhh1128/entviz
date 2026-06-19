# Anchor 2 fingerprint-edge cells to the first 2 reading-order cells (vs 1)
kind: idea
tags: v11, casual-avalanche
created: 2026-06-19T03:40Z

- 2026-06-19T03:40Z From the entviz-adversarial color-field analysis (2026-06-18). v10 has 3 fp-edge cells but only cell 0 sits at a FIXED salient position; the 2 quartile cells float (location is fingerprint-driven), so a habituated eye that always checks the same spots may not see their avalanche. Proposal: anchor the fp-edge override to the first TWO reading-order cells (top-left + next), so two un-grindable singletons land at the two most reliable fixation points.

Why it helps: (1) un-steerable, position-anchored color bits go ~2.4 -> ~4.4 (full color) / ~1.4 -> ~3.0 (grayscale red==blue) — the best kind (can't be cheated by text-steering, unlike the interior field). (2) Bigger reason: avalanche RELIABILITY at habitual fixation points. Each fp-edge color changes on a 1-char edit with p~3/4, so a single fixed anchor catches 75% of neighbor changes; two fixed anchors catch 1-(1/4)^2 ~= 94%. That is exactly v10's target failure mode (a glance missing the change).

Tradeoffs: keep total singletons <=3 (spec's 'rare singletons not confetti' rule) -> RELOCATE, don't add (anchor {0,1}, drop to <=1 quartile cell); 4+ risks killing the pop-out. Cells 0,1 are adjacent (top row) and may read as a block — consider a non-adjacent 2nd anchor (e.g. start of row 2). Tiny careful-channel loss (surround stops echoing nucleus on that cell; nucleus + pattern still carry entropy).

Decide via the DEFENDER metric, not forge-cost: re-run experiments/casual-avalanche with the 2-cell rule and check whether the residual ~2% neighbor color-miss cases (dense full grids) drop. Grinder side: extend the colorseq anchor to cells {0,1} for the forge-cost delta.
