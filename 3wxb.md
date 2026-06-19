# Fingerprint-derived text in a special cell (e.g. cell 1) on short inputs, to resist text-steering
kind: idea
tags: v11, steering, casual-avalanche
created: 2026-06-19T03:46Z

- 2026-06-19T03:46Z From the entviz-adversarial steering discussion (2026-06-18). Idea: make one special cell (candidate: cell 1, the 2nd reading-order/fixation cell) display TEXT derived from the FINGERPRINT (e.g. a Crockford-5 readout of a digest) instead of from the input-token content — on SHORT inputs. Essentially the short-input analog of the existing large-input fingerprint-middle cells (which already render Crockford-5 of the  digest; v10 neutralizes their bg + frames them).

Why: it directly attacks the one residual hard case Phase 4 left open — the text-STEERING near-collision. The attacker can freely SET entropy-derived channels (cell text, nucleus colors) by choosing the input, so a steerer can match most cells and reach small d. But fingerprint-derived text is UN-steerable: to match it the attacker must grind, not set. So a steered forgery would differ in that cell (it avalanches), and a habituated reader who always reads cell 1 — or a seeded cell-walk that hits it — catches the forgery. It's effectively a built-in, fingerprint-bound checksum cell a person can read/compare aloud.

Connections: complements the un-steerable color anchor (fp-edge at cell 0, tick ~6dbx) — this adds an un-steerable TEXT anchor at cell 1. Together: the first two fixation cells carry un-grindable signal (color at 0, text at 1).

Key tradeoff to weigh: LOSSLESSNESS. Short inputs (<=512 bits) are currently fully lossless — every cell's text is real input content, so reading all cells recovers the value and no forgery survives a full read. Replacing a cell's text with fingerprint readout removes that token's content from the visible text, so the input is no longer fully readable from the cells (a core entviz property for short inputs). Options to consider: (a) accept the minor losslessness reduction (one token moves to a label/elsewhere); (b) make it an ADDITIONAL cell rather than replacing an input token; (c) show it only when it doesn't cost the last bit of recoverability. Also decide: which cell, what digest (primary vs ), and how it reads aloud.

Evaluate via: the text-steering grinder (does it raise the steered-collision cost / force a grind on that cell?) and the cell-walk (a reader hitting the fp cell catches any non-grinded forgery).
- 2026-06-19T03:46Z Correction (shell ate two words above): both blanks should read "second" — i.e. "Crockford-5 of the second digest" and "what digest (primary vs second)". The second digest is the domain-separated SHA-512 that already drives the large-input middle cells and the v10 color-bar markers.
