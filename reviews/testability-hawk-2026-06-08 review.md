# Testability Review: entviz

**Date:** 2026-06-08
**Effort level:** medium
**Run label:** 2026-06-08 review
**Context sources used:** `this.i` (lines 1–1650), `AGENTS.md`, `pyproject.toml`, `.github/workflows/ci.yml`, `src/entviz/app.py`, `src/entviz/pipeline.py`, `src/entviz/entropy.py`, `compliance/model.py`, `compliance/runner.py`, `compliance/raster.py`, `compliance/generate.py`, `compliance/corpus.py`, `compliance/corpus/manifest.json`, `docs/spec.md` (Conformance section), all 60 test modules in `tests/`, prior review `reviews/testability-hawk-2026-06-05 review.md` (read after forming own view).

---

## Evidence Inventory

- **Repo:** Python library + CLI (`entviz`), `uv`-managed, pytest-driven, 3.10/3.11/3.12 matrix.
- **Test count:** 523 test functions across 60 test files (up from 475 in the 2026-06-05 review — new tests added since then).
- **CI:** `.github/workflows/ci.yml` runs `uv run --locked --python ${{ matrix.python-version }} pytest` on all three versions. No coverage tool, no `--group render` install.
- **Conformance corpus:** 46 render vectors, 6 error vectors, 3 invariant pairs; golden artifacts (`model.json`, `golden.svg`, `golden.png`) present for all render vectors.
- **Tests not run:** Suite not executed in this review session (unattended mode). No exit-status or branch-coverage data available.
- **Prior review dispositions:** All five prior findings (TST-F1 through TST-F5) are resolved:
  - F1 (`app-untested`): `tests/test_app.py` now exists with 18 tests covering all CLI paths.
  - F2 (bare `pass` statements): `test_crc_tokens.py` now asserts `quartiles[3] is None`; `test_snowflake.py` no longer has a vacuous-pass test for the pre-epoch case.
  - F3 (`snowflake-flaky`): all window-boundary tests use the `fixed_clock` monkeypatch fixture.
  - F4 (`losslessness-untested`): `test_phase13_validation.py:48` now passes `parsed.alphabet`, not `parsed.type`.
  - F5 (`render-unhandled`): `test_pipeline.py` now contains `test_render_rejects_empty_input`, `test_render_rejects_whitespace_only_input`, and `test_render_rejects_input_over_cap`.
- **Independence satisfied:** own analysis of production code and tests completed before reading prior review output.

---

## Executive Summary

The test suite has improved substantially since the 2026-06-05 review — all five prior findings are fixed and the new `test_app.py` is comprehensive. The most significant remaining structural gap is that **Tier B of the conformance suite (visual pixel comparison) never runs in CI**: `cairosvg` is in the optional `[render]` dependency group, not `[dev]`, so `uv run --locked pytest` silently skips the three Tier B tests without noting what was omitted. This means the golden PNG rasters committed alongside model.json can become stale without any automated detection, and the multi-implementation roadmap's primary visual-correctness guarantee is untested in every push/PR cycle. A secondary finding is that Tier B's runner never asserts that the installed rasterizer matches the one that generated the golden PNGs — running with a different cairosvg version would compare incompatible images without warning. Fixing the CI gap (adding cairosvg to the dev group or a separate CI step) is the highest-priority remaining action.

---

## Top Findings

Ordered by bang-for-buck (most real bugs prevented per unit of fix effort, first).

### F1: Conformance Tier B (golden-raster comparison) never runs in CI

- **Severity:** HIGH
- **Confidence:** CONFIRMED
- **Location:** `compliance/runner.py`, `tests/test_compliance.py:85–89`, `.github/workflows/ci.yml`
- **Finding:** Three tests in `test_compliance.py` guard Tier B correctness — `test_reference_certifies_tier_b` (lines 85–89), the drift guard `test_committed_corpus_matches_reference` (lines 58–75, which does run, but only checks `model.json` / Tier A), and the `certify(tiers=("A","B"))` call path. All Tier B tests start with `pytest.importorskip("cairosvg")`. The CI workflow runs `uv run --locked pytest`, which installs only the `[dev]` dependency group; `cairosvg` is in the opt-in `[render]` group (`pyproject.toml:67–71`). Result: `test_reference_certifies_tier_b` is silently skipped on every push and PR, and there is no CI step that ever runs with `--group render`. The Tier A drift guard (`test_committed_corpus_matches_reference`) does run and protects `model.json` freshness, but it cannot detect raster-layer regressions — changes to color, opacity, layering order, or SVG anti-aliasing that do not alter any `data-*` attribute will pass Tier A while failing Tier B on a correct runner.
- **Consequence:** The entire pixel-correctness claim of the spec's Tier B is untested by automation. A rendering change that shifts, recolors, or rearranges visual elements without updating `data-*` attributes — for example, a change to the ellipse opacity formula, the surround-box dimensions, or the color-bar rendering — could ship without any test failing. For the multi-implementation roadmap, where Tier B is the arbiter of visual equivalence across entviz-rs/entviz-js, an undetected drift in the reference Python output means the certified golden PNGs are wrong, and downstream implementations would be certified against an incorrect standard.
- **Recommendation:** Add `cairosvg` (and `numpy`, `Pillow` — required by `raster.compare_png`) to the `[dev]` group, or add a separate CI job that installs `--group render` and runs `uv run --group render pytest tests/test_compliance.py`. The latter avoids making `cairosvg` (which requires system `libcairo`) a hard dev dependency on all contributor machines, but requires the CI runner to have `libcairo` installed. Alternatively: a dedicated `compliance-tier-b.yml` workflow on push to main (not on every PR) that installs the render group on ubuntu-latest (which has libcairo) and calls `python -m compliance.runner`. Either approach closes the gap.
- **Fix effort:** small (adding a CI job or moving `cairosvg` to `[dev]`)

---

### F2: Tier B runner does not verify rasterizer identity before comparison

- **Severity:** MEDIUM
- **Confidence:** CONFIRMED
- **Location:** `compliance/runner.py:137–149`, `compliance/raster.py:45–53`
- **Finding:** The corpus `manifest.json` records the rasterizer that generated the golden PNGs (`"rasterizer": "cairosvg-2.9.0@scale2.0"`). The runner reads `manifest["raster_scale"]`, `manifest["channel_tol"]`, and `manifest["pixel_fraction"]` but does NOT read or compare `manifest["rasterizer"]` against the current `raster.rasterizer_id()`. A maintainer running Tier B with a different cairosvg version (e.g., after an OS upgrade or a `uv update` of the render group) will compare new renders against goldens produced by a different rasterizer — obtaining pixel diffs or false passes without any diagnostic message identifying the version mismatch as the cause.
- **Consequence:** False Tier B failures or false passes on a rasterizer upgrade go undiagnosed. The spec says: "its name + version + scale are recorded in the corpus manifest" — the manifest records it, but no code enforces it. A maintainer debugging mysterious pixel diffs would need to trace back to the manifest to discover the version skew. This is also a correctness risk for the multi-impl roadmap: an entviz-rs or entviz-js implementer running `compliance.runner --impl-cmd ./entviz-cli` on a machine with a different cairosvg gets unchecked comparison results.
- **Recommendation:** At the start of `certify()` in `compliance/runner.py`, when `"B" in tiers`, read `manifest.get("rasterizer")` and compare it against `raster.rasterizer_id()`. If they differ, emit a `warnings.warn(...)` or raise (with a `force=True` escape hatch) before proceeding. A one-line check: `if manifest_rasterizer != raster.rasterizer_id(): warnings.warn(f"rasterizer mismatch: golden={manifest_rasterizer}, current={raster.rasterizer_id()}")`. Also add a test: `test_tier_b_warns_on_rasterizer_mismatch` (monkeypatch `rasterizer_id` to return a different string, assert a warning is raised).
- **Fix effort:** small

---

### F3: Golden PNG stale detection absent from CI — no Tier B drift guard

- **Severity:** MEDIUM
- **Confidence:** CONFIRMED
- **Location:** `tests/test_compliance.py:58–75` (Tier A drift guard), `compliance/corpus/*/golden.png`
- **Finding:** `test_committed_corpus_matches_reference` is an excellent Tier A drift guard: it re-renders every corpus vector in-process and diffs the extracted render model against `model.json`, failing if any field differs. It runs in CI. There is no analogous guard for the golden PNGs. After any rendering change that alters pixels without touching `data-*` attributes — a changed ellipse stroke width, a modified color-bar band height formula, an opacity adjustment, a layering order change — the committed `golden.png` files become stale without CI detecting it. The Tier B drift guard would be: "re-render each vector, rasterize it with the pinned rasterizer, and diff against the committed PNG." But this is exactly `test_reference_certifies_tier_b`, which is skipped (see F1).
- **Consequence:** The stale golden PNGs are the primary risk if F1 is not fixed. But even with F1 fixed (Tier B running in CI), there is currently no explicit assertion that the committed `golden.png` matches what the current renderer would produce for the same input — `test_reference_certifies_tier_b` calls `certify()` which generates fresh PNGs on-the-fly and compares them, but does not read the committed `golden.png` files. The committed PNGs are only used as goldens when an external implementation runs `compliance.runner --impl-cmd ./entviz-cli`; for the reference self-certification, a fresh render is compared against itself (always passes trivially). This means the committed PNGs could diverge from the current renderer's output for months without detection.
- **Recommendation:** Add a `test_committed_golden_pngs_match_reference` test (parallel to `test_committed_corpus_matches_reference`) that: (a) re-renders each vector, (b) rasterizes with the pinned rasterizer, (c) reads the committed `golden.png`, and (d) calls `raster.compare_png`. Gate it on `pytest.importorskip("cairosvg")` so it skips gracefully without the render group. This ensures the committed artifacts actually reflect the current renderer. Regeneration is already documented: `python -m compliance.generate`.
- **Fix effort:** small (the test itself is 10–15 lines; the harder part is F1 — getting CI to run it)

---

### F4: Determinism tested on a narrow two-input spread

- **Severity:** MEDIUM
- **Confidence:** CONFIRMED
- **Location:** `tests/test_phase13_validation.py:25–28`, `tests/test_compliance.py:32–35`
- **Finding:** Two tests explicitly assert byte-identical re-render determinism: `test_determinism_byte_identical` (renders a UUID twice) and `test_extract_model_is_deterministic` (renders a hex-256 string twice, checks the extracted model). Both use the same `render()` function called twice in sequence in the same process. The spec mandates determinism across all alphabets, grid sizes, truncated/non-truncated paths, and platforms. The corpus drift guard (`test_committed_corpus_matches_reference`) implicitly verifies determinism for all 46 corpus vectors by comparing a re-render against a committed golden, but it only checks the render model (Tier A), not the raw SVG bytes. A non-deterministic element that is not captured in any `data-*` attribute (e.g., a floating-point formatting change, a set-iteration order in Python 3.10 vs 3.12, a dict-ordering issue in color-bar sorting) would pass the drift guard while violating the spec.
- **Consequence:** A platform-specific nondeterminism (e.g., a Python version where some internal iteration order differs) could go undetected on the CI matrix if only the model is compared, not the SVG bytes. The spec says "byte-identical on every run and platform"; the test only says "same model on same run." Alphabets like bech32, snowflake, and the truncated large-input path have no dedicated determinism tests at all.
- **Recommendation:** Expand `test_determinism_byte_identical` into a parametrized test covering at least: a UUID (hex), a bech32 address, a snowflake, a base64 CESR AID, a >512-bit truncated input, and a non-default aspect ratio. The test pattern is two lines: `a = render(inp, **kw); b = render(inp, **kw); assert a == b`. Ten inputs, ~15 lines. Bonus: also add a cross-alphabet-normalization assertion (e.g., `render("DEADBEEF") == render("deadbeef")` for hex) to confirm that the case-normalization invariant is byte-identical at the SVG level.
- **Fix effort:** small

---

### F5: Grid minimum bound asserted at `>= 1` instead of `>= 2` via data attributes

- **Severity:** LOW
- **Confidence:** CONFIRMED
- **Location:** `tests/test_v5_data_attributes.py:69–72`
- **Finding:** `test_svg_carries_grid_dimensions` (lines 67–72) reads `data-cols` and `data-rows` from a rendered UUID SVG and asserts `cols >= 1 and rows >= 1`. The spec mandates at least a 2×2 grid (`this.i:gr1dm1n2`, spec line 197: "an implementation MUST NOT emit a single-row or single-column grid"). The assertion checks the wrong lower bound. The `test_grid_selection.py` module correctly verifies the 2×2 minimum via `choose_grid` unit tests, but those tests do not go through `render()` — they test the layout module in isolation. A bug that causes `render()` to bypass `choose_grid` and emit a 1×N or N×1 grid (e.g., by passing incorrect dimensions downstream) would not be caught by either the layout unit test (which tests the right function) or this data-attribute test (which asserts the wrong bound).
- **Consequence:** A degenerate 1-row or 1-column grid that passes through `render()` due to a bug bypassing `choose_grid` would not be caught. The spec says this MUST NOT happen. The test that checks via `data-*` attributes (the normative surface) asserts a weaker property.
- **Recommendation:** Change `assert cols >= 1 and rows >= 1` to `assert cols >= 2 and rows >= 2`. Also add a parametrized test that calls `render()` on a spread of very-short inputs (1-token, 2-token, 3-token) and asserts `int(svg.get("data-cols")) >= 2` and `int(svg.get("data-rows")) >= 2` directly from the SVG data attributes.
- **Fix effort:** small (one-line fix; 5-line parametrized expansion)

---

## Additional Patterns Noted

- **`test_no_degenerate_grids_across_input_sizes` only asserts positive width/height**, not `data-cols >= 2` and `data-rows >= 2` (same weakness as F5, different test). The test is a smoke test rather than a spec-compliance assertion. Fixing F5 above also fixes this.

- **No test for the Tier C (browser smoke) conformance path.** The spec's Conformance section mentions Tier C as a non-blocking smoke subset. The corpus has no `tier_c` vector designation and the runner has no `"C" in tiers` branch. This is consistent with Tier C being deferred in the spec as well; flagged for awareness.

- **The conformance suite error vector for empty-string input is missing from the corpus**, but this is not a spec gap: the spec's error conditions do not list empty input — it is a pipeline safeguard, not a normative MUST-reject condition. The unit tests in `test_pipeline.py` cover it. No action needed.

- **`test_extract_model_recovers_core_fields` asserts `m["cols"] >= 2 and m["rows"] >= 2`** (line 43 of `test_compliance.py`) — this is a correct bound check via the extracted model, and it does run in CI. It partially covers the F5 gap for one input (UUID). Expanding F5 would still add value for other input shapes.

- **The `_draw_label_strips`, `_draw_color_bar`, and `_draw_ellipse_overlay` helpers in `pipeline.py` are still only tested through `render()` integration calls.** This has been noted in prior reviews. Not a new finding; keeping as a pattern for completeness.

- **The `v3_ellipse_params_from_digest` function** in `pipeline.py` (lines 796–814) has dedicated tests in `test_v3_ellipse.py` — good. The `enumerate_external_corners` function also has tests in `test_v4_small_grid_ellipse.py`. `enumerate_perimeter_points` has no direct unit tests but is tested through the integration surface. Low priority.

---

## Residual Unknowns

- The test suite was not executed. Branch coverage, flake rates, and test runtime are unknown.
- Whether the committed `golden.png` files are byte-for-byte consistent with the current renderer is unknown without running `python -m compliance.generate` (which requires the render group). Based on the Tier A drift guard passing (`test_committed_corpus_matches_reference`), model.json is current, but pixel-level consistency of golden.png is unverifiable without cairosvg.
- Whether any Python 3.10/3.11/3.12 version difference produces a different SVG string for the same input (cross-version determinism) is not tested — all existing determinism tests run within a single Python process.

---

## Decisions Needed

1. **Tier B CI approach:** Should `cairosvg` be moved to `[dev]` (requires `libcairo` on all contributor machines) or should a separate CI job be added (`--group render` on ubuntu-latest, which has libcairo)? The separate-job approach is less invasive but requires a new workflow file. Consider whether Tier B should run on every PR or only on pushes to main.

2. **Rasterizer identity enforcement level:** Should a rasterizer mismatch in `certify()` be a hard error (raise), a warning, or a logged message? For automated certification of external implementations (`--impl-cmd`), a warning may be insufficient (the implementer may not see it); a failure with a `--force-rasterizer` escape is safer.

3. **Determinism test coverage vs. corpus size:** The simplest fix for F4 is to parametrize `test_determinism_byte_identical` over the corpus render vectors. This ensures the same spread as the conformance corpus without maintaining a separate fixture list. Trade-off: it couples the determinism test to the corpus inputs, but that coupling is intentional (these are the inputs the spec commits to).

---

## Findings Manifest

```yaml
findings:
  - id: TST-F1
    persona: testability-hawk
    title: Conformance Tier B (golden-raster comparison) never runs in CI
    severity: HIGH
    confidence: CONFIRMED
    location: compliance/runner.py, tests/test_compliance.py:85-89, .github/workflows/ci.yml
    dedupe_key: conformance-suite-untested
    recommended_disposition: recommend-fix
    rationale: cairosvg is not in the dev group so Tier B is silently skipped on every push/PR; golden.png drift and visual regressions ship undetected.
    revisit_condition: null
    fix_effort: small

  - id: TST-F2
    persona: testability-hawk
    title: Tier B runner does not verify rasterizer identity before comparison
    severity: MEDIUM
    confidence: CONFIRMED
    location: compliance/runner.py:137-149
    dedupe_key: conformance-suite-missing
    recommended_disposition: recommend-fix
    rationale: The manifest records the rasterizer that produced the goldens but the runner never checks it; a version upgrade silently compares incompatible images.
    revisit_condition: null
    fix_effort: small

  - id: TST-F3
    persona: testability-hawk
    title: No committed-golden-PNG drift guard — golden.png staleness undetectable in CI
    severity: MEDIUM
    confidence: CONFIRMED
    location: compliance/corpus/*/golden.png, tests/test_compliance.py
    dedupe_key: conformance-suite-missing
    recommended_disposition: recommend-defer
    rationale: No test reads the committed golden.png and compares it against a fresh render; pixel-layer regressions that don't change data-* attrs go undetected. Blocking on fixing F1 first.
    revisit_condition: After F1 (Tier B runs in CI), add test_committed_golden_pngs_match_reference alongside test_committed_corpus_matches_reference.
    fix_effort: small

  - id: TST-F4
    persona: testability-hawk
    title: Determinism tested on only two inputs; no coverage for bech32, snowflake, truncated-path
    severity: MEDIUM
    confidence: CONFIRMED
    location: tests/test_phase13_validation.py:25-28, tests/test_compliance.py:32-35
    dedupe_key: render-nondeterministic
    recommended_disposition: recommend-fix
    rationale: Spec mandates byte-identical output across all alphabets and grid sizes; only UUID and hex-256 are tested; a cross-Python-version nondeterminism on any other path would go undetected.
    revisit_condition: null
    fix_effort: small

  - id: TST-F5
    persona: testability-hawk
    title: Grid minimum bound asserted as >= 1 instead of >= 2 via data attributes
    severity: LOW
    confidence: CONFIRMED
    location: tests/test_v5_data_attributes.py:71-72
    dedupe_key: render-unhandled
    recommended_disposition: recommend-fix
    rationale: spec.md line 197 mandates >= 2x2; the data-attribute test asserts >= 1x1; a render() bug bypassing choose_grid would not be caught.
    revisit_condition: null
    fix_effort: small
```
