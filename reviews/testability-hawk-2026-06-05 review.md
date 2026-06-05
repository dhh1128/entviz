# Testability Review: entviz

**Date:** 2026-06-05
**Effort level:** medium
**Run label:** 2026-06-05 review
**Context sources used:** `this.i` (full), `AGENTS.md`, `pyproject.toml`, `src/entviz/pipeline.py`, `src/entviz/entropy.py`, `src/entviz/fingerprint.py`, `src/entviz/colors.py`, `src/entviz/layout.py`, `src/entviz/renderer.py`, `src/entviz/app.py`, `.github/workflows/ci.yml`, representative test files across all 53 test modules (all examined).

---

## Evidence Inventory

- **Repo type:** Python library + CLI entry point (`entviz` command). Not a service; no HTTP endpoints, no DB, no Kafka.
- **Test framework:** pytest (no unittest), `--strict-markers`, single test path `tests/`.
- **Test count:** 475 test functions across 53 test files.
- **CI:** `.github/workflows/ci.yml` runs `uv run --locked --python ${{ matrix.python-version }} pytest` on 3.10/3.11/3.12 — the full suite, no test skipping.
- **Coverage tool:** None configured in `pyproject.toml` or CI. No JaCoCo equivalent, no pytest-cov invocation.
- **Origin Platform layers context:** Not applicable — this is a Python library, not a Java/Spring Boot service. The multi-layer (unit/web/data/integration) taxonomy does not map here. This review assesses testability for a pure-Python library.
- **Prior review output:** Not read before forming assessment (independence requirement).
- **Tests actually run:** Not run in this review session (unattended mode).

---

## Executive Summary

entviz has an unusually dense, well-structured test suite for a visualization library: 475 tests covering parsing correctness, geometry, color, layering invariants, avalanche properties, adversarial findings, and individual spec-version increments. The biggest structural gap is the complete absence of CLI tests (`app.py` has zero test coverage), leaving argument parsing, aspect ratio clamping, font-size bounds, and the `ValueError`-to-`parser.error` conversion path entirely unverified by automation. The second gap is two intentionally incomplete tests (acknowledged by `pass` statements instead of assertions) that reduce confidence in the quartile-token non-multiple-of-4 edge case and a snowflake timestamp boundary. The third gap is time-dependent tests that couple to `time.time()` in ways that will silently shift behavior in ~5 years.

---

## Top Findings

Ordered by bang-for-buck.

### F1: CLI entry point (`app.py`) has zero test coverage

- **Severity:** HIGH
- **Confidence:** CONFIRMED
- **Location:** `src/entviz/app.py` (entire file, ~50 lines)
- **Finding:** `app.py` implements argument parsing, aspect-ratio and font-size validation, the `render()`-call-with-error-handling path, and both stdout and file output modes. No test file imports from or invokes the CLI. `grep -rn "app\.py\|from entviz.app\|import app" tests/` returns zero hits.
- **Consequence:** The following bugs can ship undetected:
  - An invalid `--ar` format that bypasses the regex silently passes `1.0` (default) instead of erroring.
  - Font-size bounds (`< 6` or `> 30`) could drift if the guard expression is accidentally reversed.
  - The `--note` argument is wired in `app.py`; the `sanitize_note()` ValueError path through `parser.error()` is never exercised end-to-end. A maintainer who changes how `render()` raises (e.g., wrapping in a custom exception) would silently break the CLI output message.
  - File output mode (the `args.output` branch) is untested; a `sys.stdout.write` vs `f.write` inconsistency in encoding would be invisible.
- **Recommendation:** Add `tests/test_app.py` using `subprocess.run(['entviz', ...])` or, simpler, direct invocation of `main()` with `sys.argv` patched via `monkeypatch.setattr` (pytest) and stdout captured. Test: happy-path stdout output, `--ar` format validation error, font-size boundary error, `--note` invalid value, file output mode.
- **Fix effort:** small

---

### F2: Two tests with explicit `pass` instead of assertions — structural test holes

- **Severity:** MEDIUM
- **Confidence:** CONFIRMED
- **Location:**
  - `tests/test_crc_tokens.py:52` — `test_quartile_tokens_non_multiple_of_4`: checks that `quartiles[0,1,2]` are correct for 5 tokens but leaves the 4th quartile (index 6 = out-of-bounds) unchecked with a comment "My current implementation doesn't return None if out of bounds? Let me check idx < count." and then `pass`.
  - `tests/test_snowflake.py:93` — `test_reject_decimal_predating_discord_epoch`: the test body explains why it is "mathematically impossible" to construct the desired input, then `pass`.
- **Consequence:**
  - For `test_crc_tokens`: the 4th quartile's behavior (None vs. a padding token) is a spec-mandated property used in the pipeline's quartile-mark rendering (`pipeline.py:484-503`). If `get_quartile_tokens` ever returns a non-None 4th entry for 5-token inputs when spec requires None, `render()` could draw an erroneous quartile mark. The test does not catch this.
  - For `test_snowflake`: the snowflake test comment is correct (the construction is impossible), but the test silently passes rather than documenting why it is vacuously true or using `pytest.skip`. A future reader sees a passing test with no assertions and cannot distinguish "correctly vacuous" from "intentionally unfinished."
- **Recommendation:**
  - `test_quartile_tokens_non_multiple_of_4`: add `assert quartiles[3] is None` (if that is the spec) or whatever the specified value is; remove the `pass`.
  - `test_reject_decimal_predating_discord_epoch`: replace `pass` with `pytest.skip("construction of a pre-Discord-epoch 17-digit snowflake is mathematically impossible")` with a brief explanation. This makes the intent explicit and distinguishes "we can't test this branch" from "we forgot to test it."
- **Fix effort:** small

---

### F3: Time-dependent tests using `time.time()` will drift silently over years

- **Severity:** MEDIUM
- **Confidence:** CONFIRMED
- **Location:** `tests/test_snowflake.py:98,108,117,165` — four tests call `int(time.time() * 1000)` to build snowflake inputs relative to "now", then assert acceptance or rejection based on the 5-year future window.
- **Consequence:** These tests have a built-in expiry:
  - `test_accept_decimal_within_future_window` generates a snowflake 1 year ahead of now and asserts it parses as a snowflake. If the test is run in an environment with a skewed clock (e.g., a container with a far-future date set in CI) or if a large leap occurs, the assertion can fail or become vacuous.
  - `test_reject_decimal_at_5_year_window_boundary_plus_one` is fragile: the "5 years + 1 day" boundary is relative to the current wall clock; a CI run on a slow machine could straddle the threshold.
  - More fundamentally: the `_SNOWFLAKE_FUTURE_WINDOW_MS = 5 * 365 * 86400 * 1000` constant in `entropy.py` is also wall-clock dependent but is never frozen at test time, so the tests and production code both move together — any refactor that separates them (e.g., injecting a clock) would immediately reveal the coupling.
- **Recommendation:** Inject the current-time into `parse_snowflake` as an optional parameter (`_now_ms: int = None`) defaulting to `int(time.time() * 1000)`, so tests can pass a pinned value. This makes the tests deterministic across decades and makes the production cutoff boundary explicit and testable at any desired epoch. Alternatively, use freezegun or monkeypatching of `time.time` for the four offending tests if the production API change is not wanted.
- **Fix effort:** small-to-medium (API change is small; updating callers and tests is mechanical)

---

### F4: `test_losslessness_le_512_bits_text_roundtrip` passes `parsed.type` (a string) to `tokenize_entropy` instead of `parsed.alphabet`

- **Severity:** MEDIUM
- **Confidence:** CONFIRMED
- **Location:** `tests/test_phase13_validation.py:44-46`

```python
parsed = parse(core)
tokens, is_truncated = tokenize_entropy(parsed.core, parsed.type)   # <-- bug
```

- **Finding:** `tokenize_entropy` accepts both an `Alphabet` instance and a legacy string type name, and internally translates string names via a substring match (`"hex" in type_name.lower()`). Passing `parsed.type` (here `"hex"`) works coincidentally, but the test is exercising the legacy compatibility path, not the current production path. The production pipeline (`pipeline.py:100`) passes `parsed.alphabet` (an `Alphabet` object). If `tokenize` ever drops legacy string support (the comment calls it "backwards compat"), this test breaks in a misleading way — and it may silently pass even after the legacy path is removed if the string still happens to match. More practically: for types whose type string does not contain "hex" or "58" (e.g., `"UUID"`, `"ETH"`, `"LEI"`, `"snowflake"`), the legacy branch falls through to `BASE64`, producing the wrong alphabet. The test only uses `"hex"` so it does not currently fail, but the test is testing a different code path than the one that matters.
- **Consequence:** The losslessness test could pass even if the real production path (using `parsed.alphabet`) is broken, masking a regression in how the alphabet is threaded through `tokenize_entropy`.
- **Recommendation:** Change `tokenize_entropy(parsed.core, parsed.type)` to `tokenize_entropy(parsed.core, parsed.alphabet)` — a one-word fix that makes the test exercise the real production path.
- **Fix effort:** small

---

### F5: No coverage for `render()` error path (`ValueError: "No tokens produced"`)

- **Severity:** LOW
- **Confidence:** CONFIRMED
- **Location:** `src/entviz/pipeline.py:102-103` — `raise ValueError("No tokens produced from input entropy.")`
- **Finding:** The `render()` function raises `ValueError` if `tokenize_entropy` returns an empty token list. No test asserts that `render("")` or `render("  ")` (whitespace-only) raises `ValueError`. The empty-string case in `test_entropy.py` only tests `parse("")` returning `None`, not `render("")`. The CLI's `app.py` catches this `ValueError` and routes it to `parser.error()`, but that CLI path is also untested (F1).
- **Consequence:** A future refactor could change the empty-input behavior (e.g., returning an empty SVG, raising a different exception, or adding a fallback) without a test failing. Callers embedding `render()` in a library context depend on this contract.
- **Recommendation:** Add a test: `with pytest.raises(ValueError): render("")` and `with pytest.raises(ValueError): render("   ")`. This is a two-line addition.
- **Fix effort:** small

---

## Additional Patterns Noted

- **Test naming style is procedural, not BDD.** Most tests are named `test_render_contains_text_tokens`, `test_24_surround_boxes_per_cell_when_all_bits_set`, etc. — these describe the implementation detail, not the behavioral contract. BDD-style names (`test_single_bit_change_in_input_changes_all_fingerprint_channels`) would make the intent clearer and the test readable as documentation. Not blocking; flagged per the platform's BDD naming convention.

- **`test_quartile_circles` in `test_pipeline.py:47-50` over-constrains the count.** It asserts `1 <= len(circles) <= 4`. A 1-token input (e.g., `"ab"`) might produce 0 or 4 quartile circles depending on whether the same ftok occupies all four quartile slots. The test uses `HEX_256` which always has ≥1 token, so this passes; but the `>= 1` lower bound is not guaranteed by the spec (a 1-token input has one ftok in all quartile positions but the degenerate-token rendering behavior is not separately tested). Low risk in practice.

- **`test_colors.py` only tests `relative_luminance`.** The `select_visual_style`, `weighted_rgb_distance`, `closest_palette_color`, and `get_nucleus_colors` functions are tested indirectly through higher-level tests but have no direct unit tests for their internal logic (e.g., no test that `select_visual_style` returns all 4 non-bg colors in `edge_colors`, no test for the Oklab lightness threshold crossover at L=0.6). Given the security-adjacent nature of contrast correctness (wrong foreground color on a nucleus makes text unreadable), direct tests for these would be a quality improvement.

- **`_draw_label_strips`, `_draw_color_bar`, `_draw_ellipse_overlay`, `enumerate_perimeter_points`, `enumerate_interior_corners`, `enumerate_external_corners`** in `pipeline.py` are tested only through `render()` integration calls, never unit-tested directly. This makes it hard to diagnose which sub-step failed when a geometry test breaks.

- **`sanitize_note` is tested directly in `test_user_note.py`** — this is a good pattern (direct unit test of a helper). The same pattern could be applied to other helpers in `pipeline.py` above.

- **`test_phase13_validation.py:89-102` (`test_no_degenerate_grids_across_input_sizes`)** only asserts that `render()` doesn't crash and the SVG has positive width/height. It does not verify `data-cols >= 2` and `data-rows >= 2` via the structured data attributes. A 1-column or 1-row degenerate grid that happens to produce a positive-width SVG would not be caught.

- **No test for `EIP55ChecksumError` being raised through `render()`** (end-to-end). Tests in `test_f7_eip55.py` verify `parse_ethereum_address` raises directly, but nothing checks that `render("0xBadChecksum...")` propagates the error to the caller rather than silently absorbing it. The `render()` function does not have a try/except around `parse()`; it falls through correctly today, but the absence of an end-to-end test for this exception path leaves a gap.

---

## Residual Unknowns

- Tests were not run; exit-status and any existing flakiness are unknown.
- No coverage tool is configured, so branch coverage of the legacy string-alphabet compatibility path in `tokenize()` (lines 1128-1135 of `entropy.py`) is unknown.
- Whether the `_BAND_LETTER_BY_COLOR` fallback path in `_draw_color_bar` (reached when `color` is not in the dict) is exercised by any test is unknown without instrumentation; the comment "Only emit a letter for palette colors; tests that pass synthetic colors (e.g. '#a') skip the letter rendering" suggests it is not.

---

## Decisions Needed

1. **CLI test approach:** Should `tests/test_app.py` use subprocess invocation (black-box, test the installed `entviz` command) or direct `main()` invocation with `monkeypatch`? The subprocess approach is more realistic but requires the package to be installed in the test environment. Direct invocation is faster and works with `uv run pytest` without install.

2. **`test_reject_decimal_predating_discord_epoch` disposition:** The test body correctly explains the construction is impossible. Should it be deleted outright, or kept as a `pytest.skip` with documentation? If kept, it provides ongoing documentation that the past-epoch rejection path has an untestable lower bound for the current timestamp range.

3. **Clock injection for `parse_snowflake`:** Injecting `_now_ms` makes the timestamp logic deterministic in tests. Alternatively, the test could monkeypatch `time.time`. Which is preferred for this codebase?

---

## Findings Manifest

```yaml
findings:
  - id: TST-F1
    persona: testability-hawk
    title: CLI entry point (app.py) has zero test coverage
    severity: HIGH
    confidence: CONFIRMED
    location: src/entviz/app.py
    dedupe_key: app-untested
    recommended_disposition: recommend-fix
    rationale: Argument parsing, aspect-ratio/font-size validation, ValueError-to-parser.error conversion, and file output mode are all untested; a bug in any of these can ship undetected.
    revisit_condition: null
    fix_effort: small

  - id: TST-F2
    persona: testability-hawk
    title: Two tests have bare `pass` instead of assertions — intentional spec behavior goes unverified
    severity: MEDIUM
    confidence: CONFIRMED
    location: tests/test_crc_tokens.py:52, tests/test_snowflake.py:93
    dedupe_key: crc-tokens-untested
    recommended_disposition: recommend-fix
    rationale: test_quartile_tokens_non_multiple_of_4 leaves the 4th quartile return value unasserted; a wrong value could produce spurious quartile marks in render() without a failing test.
    revisit_condition: null
    fix_effort: small

  - id: TST-F3
    persona: testability-hawk
    title: Snowflake timestamp tests use time.time() and will drift over years
    severity: MEDIUM
    confidence: CONFIRMED
    location: tests/test_snowflake.py:98,108,117,165
    dedupe_key: snowflake-flaky
    recommended_disposition: recommend-fix
    rationale: Four tests couple to wall-clock time; a clock skew, CI environment anomaly, or 5-year drift will silently change test behavior without any code change.
    revisit_condition: null
    fix_effort: small

  - id: TST-F4
    persona: testability-hawk
    title: Losslessness test passes `parsed.type` (string) instead of `parsed.alphabet` to tokenize_entropy, exercising legacy compat path not production path
    severity: MEDIUM
    confidence: CONFIRMED
    location: tests/test_phase13_validation.py:44-46
    dedupe_key: losslessness-untested
    recommended_disposition: recommend-fix
    rationale: The test calls tokenize_entropy(parsed.core, parsed.type) but production uses parsed.alphabet; a regression in the real path would not be caught by this test.
    revisit_condition: null
    fix_effort: small

  - id: TST-F5
    persona: testability-hawk
    title: render() error path for empty/whitespace input is untested
    severity: LOW
    confidence: CONFIRMED
    location: src/entviz/pipeline.py:102-103
    dedupe_key: render-unhandled
    recommended_disposition: recommend-fix
    rationale: No test verifies render("") raises ValueError; a future refactor changing empty-input behavior would pass the test suite silently.
    revisit_condition: null
    fix_effort: small
```
