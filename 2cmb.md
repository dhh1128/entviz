# MNT-F1 [HIGH]: fingerprint.py module docstring omits the text-not-bytes hashing intent (this.i:h4shtext) — the highest-damage wrong-optimization seam (hashing decoded bytes is silent and breaks cross-encoding collision resistance)
kind: debt
tags: review-2026-06-08, blocker, maint
created: 2026-06-08T20:32Z
closed: 2026-06-08T21:01Z

- 2026-06-08T20:32Z Location: src/entviz/fingerprint.py:1-19 (+ cite at line 35). One-sentence docstring fix. See reviews/maintainability-expert-2026-06-08 review.md.
- 2026-06-08T21:01Z Fixed in 115b231 (branch fix/review-blockers-group-a): added text-not-bytes warning to fingerprint.py module docstring.
