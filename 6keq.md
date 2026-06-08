# PSY-F1 [HIGH]: blank-cell map red/blue dots lose their max/min meaning under achromatopsia (hue-only, ΔL*=7.8); the channel a habituated user checks first
kind: debt
tags: review-2026-06-08, blocker, perception
created: 2026-06-08T20:32Z

- 2026-06-08T20:32Z Location: src/entviz/pipeline.py:535-542; docs/spec.md §blank-cell-map. Add a non-hue cue (shape/size/label) or document the limitation. See reviews/perception-reviewer-2026-06-08 review.md.
- 2026-06-08T21:48Z Fixed in f59c018: maxftok marker is now a red PLUS (path), minftok a blue DOT (circle) — shape carries max/min so it survives achromatopsia. this.i:v8blnkmp.
