# TST-F1 [HIGH]: conformance Tier B (golden-raster) never runs in CI — cairosvg is in optional [render] group so importorskip skips every Tier B test; visual regressions undetected
kind: debt
tags: review-2026-06-08, blocker, test
created: 2026-06-08T20:32Z
closed: 2026-06-08T21:06Z

- 2026-06-08T20:32Z Location: compliance/runner.py; tests/test_compliance.py:85-89; .github/workflows/ci.yml. Move cairosvg into the CI dependency group / wire Tier B into CI. See reviews/testability-hawk-2026-06-08 review.md.
- 2026-06-08T21:01Z Fix committed in 115b231: CI installs libcairo2 + runs pytest --group render so Tier B executes (green locally, cairosvg 2.9.0). LEFT OPEN pending CI confirmation that cross-machine libcairo AA stays within the ±16/0.2% Tier B tolerance — that's the only unverified part. Relates to TST-F2 (rasterizer identity check) / SPEC-F5 (pin DPI).
- 2026-06-08T21:06Z VERIFIED in CI (PR #10, run 27166865352): all three Python jobs show '563 passed' (not 562+1 skipped), so Tier B executed and passed cross-machine on GitHub's libcairo 1.18.0 — within the ±16/0.2% raster tolerance. The cross-machine-AA concern did not materialize. Fix: 115b231.
