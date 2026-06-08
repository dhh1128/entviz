# TST-F1 [HIGH]: conformance Tier B (golden-raster) never runs in CI — cairosvg is in optional [render] group so importorskip skips every Tier B test; visual regressions undetected
kind: debt
tags: review-2026-06-08, blocker, test
created: 2026-06-08T20:32Z

- 2026-06-08T20:32Z Location: compliance/runner.py; tests/test_compliance.py:85-89; .github/workflows/ci.yml. Move cairosvg into the CI dependency group / wire Tier B into CI. See reviews/testability-hawk-2026-06-08 review.md.
