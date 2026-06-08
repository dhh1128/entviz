# Spec-Conformance & Determinism Review: entviz

**Date:** 2026-06-08
**Effort level:** deep (renderer run; SVG diffed for determinism; render-model fields traced; error conditions exercised; full test + compliance suites run)
**Conformance frame:** code `SPEC_VERSION = "v7"` (`src/entviz/__init__.py:22`); `docs/spec.md` header = `**Version: 7**` — they **agree**. A golden conformance corpus **exists** (`compliance/corpus/`, 46 render + 6 error vectors, manifest pinning `cairosvg-2.9.0@scale2.0`, `channel_tol=16`, `pixel_fraction=0.002`); the checker **runs and passes** (`python -m compliance.runner` → `55/55 vectors passed`; `tests/` → `541 passed` via the project venv). The middle-cell domain tag is correct: `_MIDDLE_DOMAIN_TAG = b"entviz/fingerprint-middle/v6\x00"` (`entropy.py:1334`) — the literal `v6` is held fixed against the v7 spec, exactly as the spec mandates.
**Implementation commit:** 4c36b8878f4063eccd76c9ccb0e7678546f53292
**Context sources used:** `docs/spec.md` (full, both pages); `src/entviz/{__init__,fingerprint,colors,pipeline,renderer,layout,shapes,entropy,keccak}.py`; `compliance/{README,model,raster,corpus/manifest}.py/.json`; `tests/` (run, not all read); prior `reviews/*`. Renderer was run on hex/base58/base64url/base32/crockford32/bech32/decimal inputs, a >512-bit input, and across the size and font-size boundaries; SVG byte-diffed for within-process determinism; error conditions exercised live.

---

## Evidence Inventory

- **Read in full:** the entire normative spec (`docs/spec.md`, 552 lines), `__init__.py`, `fingerprint.py`, `colors.py`, `pipeline.py`, `renderer.py`, `layout.py`, `shapes.py`, and the load-bearing slices of `entropy.py` (normalization/parse, disproof, tokenize, EIP-55, snowflake, large-input/domain-tag, median/quartile). `compliance/{model.py,raster.py,manifest.json,README.md}`.
- **Renderer run (deep):** rendered representative inputs for hex, base58, base64url, base32 (Stellar), crockford32 (ULID), bech32 (segwit), decimal (snowflake), and a 200-char large input. Each rendered **twice** and byte-compared — **identical within a process** in every case.
- **Determinism probe:** found and confirmed a wall-clock dependency in `parse_snowflake` (F1). Rendered the *same* digit string at the current date and (by patching the `_now_ms` seam) ~6 years later — the SVG **differs** (`hex(19):` vs `snowflake:`).
- **Field tracing:** traced edge-color and ellipse-anchor derivation through to `data-*`; traced the blank-map dots and found the `(row,col)` positions are *not* in the named attributes (F2).
- **Error conditions:** font-size `<6`/`>30`, note >8 chars / spaces / punctuation, aspect-ratio out of range, and a corrupted EIP-55 checksum — all **rejected** with a `ValueError`/`EIP55ChecksumError` through the normal channel.
- **Suites:** `tests/` 541 pass (via `.venv/bin/python`; a bare `python -m pytest` mis-collects because the package is only importable inside the venv, and `test_figures.py` needs `segno` — environment-only, not a code defect). `compliance.runner` 55/55.
- **Not run:** Tier C (headless browser) is out of scope for the offline harness by design; not exercised.

---

## Executive Summary

Confidence that a clean re-implementation would agree with this one is **moderate-to-high** for the cryptographic and geometric core — the SHA-512 text-hashing, the domain-separated middle digest with its correctly-frozen `v6` tag, the bit-extension formula, the median/quartile/min-max tie-breaks, and the paint order all match the spec — but it is **broken by two concrete divergences that a second implementation will trip on**, plus a cluster of under-specification landmines. The single most dangerous risk is **F1: `parse_snowflake` consults the wall clock**, so the *same* decimal input renders a *different* SVG depending on the date the renderer runs — a direct violation of the spec's determinism MUST (§115) and a guaranteed cross-impl/cross-time divergence that the corpus cannot catch (its golden was frozen at one instant). The most urgent action is to make snowflake-vs-decimal classification time-independent (a fixed upper bound written into the spec) and add a determinism-across-time test. F2 (blank-map dot positions are emitted as boolean `="true"` flags, not the `(row,col)` the SVG profile names) is a real Tier-A recoverability gap that the reference checker silently papers over by reverse-engineering positions from pixel geometry.

---

## Top Findings
Ordered by bang-for-buck.

### F1: Snowflake detection depends on wall-clock time — same input renders differently on different dates
- **Class:** DETERMINISM + CODE + SPEC
- **Severity:** CRITICAL
- **Confidence:** CONFIRMED (constructed input; rendered SVG differs across simulated time)
- **Location:** `src/entviz/entropy.py:828-831` (`parse_snowflake` → `_now_ms()`, `_SNOWFLAKE_FUTURE_WINDOW_MS`), `entropy.py:251` (`_now_ms` = wall clock); `docs/spec.md §115` (determinism MUST), `§243`/`§455` (snowflake, no deterministic detection rule).
- **Finding:** `parse_snowflake` accepts a 17–20-digit decimal only if its implied 42-bit timestamp lands in `[2015-01-01, now + 5 years]`, where `now` is **`time.time()`**. A decimal whose implied timestamp is just past `now + 5y` is rejected as a snowflake **today** and falls through to `hex`, but the *identical input* is accepted as a `snowflake` once the wall clock advances. The spec's `§115` states: *"No part of the output may depend on wall-clock time… on every platform."* The label (`snowflake:` vs `hex(19):`) is a normative render-model field (`§132`, `§140` labels), so the render model itself changes with the date. Two certified implementations run in different years — or the same implementation re-run after the corpus ages — disagree on a valid input. The corpus cannot detect this: its golden was generated at a single instant and pins whatever classification held then.
- **Evidence / example:** With `now = _now_ms()`, the digit string `2175026207895072825` (implied timestamp `≈ now + 5y + ε`) renders top label `hex(19):` today; patching `_now_ms` to `now + 6y` renders top label `snowflake:` for the *same* input, and the two SVGs are not byte-equal (`SVGs identical? False`). The spec gives **no** deterministic snowflake-detection rule at all (§243 only says "17–20 decimal digits encoding a 64-bit integer"), so even a spec-faithful re-implementation has no canonical bound to copy.
- **Recommended action:** **Fix in code AND spec.** Replace the moving `now + 5y` upper bound with a *fixed constant* timestamp (e.g. a hard ceiling baked into the algorithm and written into the spec as the normative snowflake-recognition predicate), so detection is a pure function of the input. Add a conformance/determinism test that pins two distinct `_now_ms()` values and asserts identical output. Blast radius: changing the bound reclassifies a thin band of boundary decimals (and is comparison-breaking for any such input previously rendered) — gate behind the next `SPEC_VERSION` bump and state it loudly. Until fixed, the reference implementation is **not reproducible across time**, which undermines the entire multi-impl conformance program.

### F2: Blank-map dot positions are emitted as boolean flags, not the `(row,col)` the SVG profile names — Tier A recoverable only by geometric reverse-engineering
- **Class:** CODE + SPEC
- **Severity:** HIGH
- **Confidence:** CONFIRMED (rendered SVG + checker code inspected)
- **Location:** `src/entviz/pipeline.py:527-542` (emits `data-blank-map-min="true"` / `data-blank-map-max="true"`); `compliance/model.py:315-336` (`_dot_rowcol` reverse-engineers `(row,col)` from `cx`/`cy`); `docs/spec.md §137`, `§173`.
- **Finding:** The render model (`§137`) requires the map-bearing blank to record "the `(row, col)` of the minftok and maxftok dots," and the SVG profile (`§173`) names `data-blank-map-min`, `data-blank-map-max` as carrying "its dot positions." The code instead sets both attributes to the literal string `"true"` — a presence flag — and encodes the actual position only implicitly in the circle's `cx`/`cy` geometry. The reference checker recovers the field by inverting the sub-cell geometry (`col = round((cx - mx)/sub_w - 0.5)`), i.e. from pixels, not from the named attribute. A second implementation reading the SVG-profile prose would emit `data-blank-map-min="<row>,<col>"`; that implementation would still *pass* Tier A (the checker ignores the attribute value) but a checker written faithfully to the spec text would reject the *reference* output. The named attribute and the spec disagree about what it carries.
- **Evidence / example:** `render("deadbeef")` (2×2, one map blank) emits `<circle … data-blank-map-max="true"/>` and `<circle … data-blank-map-min="true"/>` — no row/col. `model.py:_dot_rowcol` proves the recovery is geometric, not attribute-driven.
- **Recommended action:** **Fix in code** (cheapest, non-comparison-breaking at the render-model level): emit `data-blank-map-min="{row},{col}"` (and likewise max), and have the checker read it directly. **Or fix in spec** to say these attributes are boolean markers and the position is recovered from geometry (then add a normative formula for that inversion). Either way the spec and code must be made to agree on what the attribute means, because this is exactly the kind of "machine-recoverable field" the multi-impl roadmap depends on.

### F3: Bare base32 fragments via disproof are lowercased, but the spec mandates base32 canonicalizes to UPPER case
- **Class:** CODE + SPEC (internally inconsistent)
- **Severity:** HIGH
- **Confidence:** CONFIRMED (constructed input)
- **Location:** `src/entviz/entropy.py:1140` (`core = entropy.lower() if detected in (BECH32, HEX, BASE32) else entropy`); `docs/spec.md §226` ("base32 canonicalizes to **upper** case, which is its RFC 4648 convention") vs `§223` ("treats the input itself as the normalized core … no re-encoding").
- **Finding:** The disproof path lowercases any input detected as base32. The spec's case-normalization rule (`§226`) explicitly singles out base32 as the one alphabet that canonicalizes to **upper** case. A bare base32 fragment (no `G…`/`M…`/`b…` prefix, so the Stellar/CID parsers — which correctly upper-case — don't fire) reaches disproof and is lowercased. Because the fingerprint is `SHA-512(core text)`, the wrong case produces a **different fingerprint, different cell text, and different every-channel output** from what a spec-faithful re-implementation computes. Separately, the spec is internally inconsistent for this path: `§223` says disproof uses "the input itself … no re-encoding" (which would *preserve* the user's case), while `§226` says base32 → upper; the code picks lower, agreeing with neither.
- **Evidence / example:** `parse("MFRGGZDFMZTWQ2LK")` → `core = "mfrggzdfmztwq2lk"`, `type = base32`, `alphabet = base32` (`core.islower() == True`). A second implementation following `§226` would hash `"MFRGGZDFMZTWQ2LK"` and diverge in every channel.
- **Recommended action:** **Fix in code** to `entropy.upper()` for the base32 branch (lower stays correct for hex/bech32 per `§226`), and **fix the spec** to resolve the `§223`↔`§226` conflict for the disproof path (state that disproof applies the per-alphabet canonical case, not the raw input). Comparison-breaking only for bare-base32-fragment inputs (an edge case with no corpus vector — note that no corpus vector exercises base32-via-disproof, only Stellar/CID via their parsers, which is why the suite is green). Add a disproof-base32 corpus vector.

### F4: Aspect-ratio error condition is checked on the ratio, not the components the spec names
- **Class:** CODE + SPEC
- **Severity:** MEDIUM
- **Confidence:** CONFIRMED
- **Location:** `src/entviz/pipeline.py:125-127` (`if not (0.01 <= target_ar <= 100)`); `docs/spec.md §195` ("an aspect-ratio component outside `[1, 100]`").
- **Finding:** The spec's error catalog rejects "an aspect-ratio component outside `[1, 100]`" — i.e. a `W:H` whose numerator or denominator leaves `[1,100]`. The code instead takes a single float `target_ar` and rejects it outside `[0.01, 100]`. These are not the same set: `target_ar = 0.5` (a legal `1:2`, both components in range) is accepted — fine — but the *reference impl's accepted bound* (`[0.01,100]` on the ratio) and the spec's stated bound (`[1,100]` on components) are different vocabularies, so a re-implementation that takes `W` and `H` separately and applies `[1,100]` per component will reject/accept different inputs at the extremes (e.g. `W=100,H=1` → ratio 100 accepted by both; `W=1,H=100` → ratio 0.01, accepted by code, and by component-rule too; but `W=200,H=2` → ratio 100 accepted by code, rejected by the component rule). The error-condition *set* is normative (`§199`), so this is a real interop gap.
- **Evidence / example:** `render("deadbeef", target_ar=200)` → rejected; the spec would express the same rejection as "component 200 > 100". The mismatch bites where ratio and component bounds diverge.
- **Recommended action:** **Fix in spec** (cleanest) to state the reference bound in ratio terms (`target_ar ∈ [0.01, 100]`), or **fix in code** to accept `W,H` components and bound each to `[1,100]`. Pick one vocabulary and make the CLI, the `render()` boundary, and the spec use it.

### F5: Tier-B rasterizer pinned by scale, not the DPI the spec requires; `lib_version` drift in the manifest
- **Class:** SPEC + CODE (conformance-suite rigor)
- **Severity:** MEDIUM
- **Confidence:** CONFIRMED
- **Location:** `compliance/raster.py:34` (`DEFAULT_SCALE = 2.0`), `:45-52` (`rasterizer_id` = `cairosvg-2.9.0@scale2.0`); `compliance/corpus/manifest.json` (`"rasterizer": "cairosvg-2.9.0@scale2.0"`, `"lib_version": "0.7.0"`); `docs/spec.md §159` ("name, version, and rendering **DPI**").
- **Finding:** The spec requires the corpus pin the reference rasterizer by "name, version, and rendering DPI." The harness pins name + version + **scale** (a CairoSVG-specific multiplier), not DPI. For a viewBox-less px-unit SVG `scale=2.0` is deterministic, but "scale" is a CairoSVG concept; a different rasterizer (the README names resvg as the "intended longer-term authority") has no `scale` knob and would need a DPI, so the pinning is not portable across the rasterizer swap the project plans. Separately, the manifest records `lib_version: 0.7.0` while `__init__.py` is `0.7.1` — a stamp drift (harmless to Tier A/B today because the drift guard compares spec_version, but it means the manifest's provenance line is stale).
- **Evidence / example:** `manifest.json` shows `"rasterizer": "cairosvg-2.9.0@scale2.0"` and `"lib_version": "0.7.0"`; `__init__.py:23` is `0.7.1`.
- **Recommended action:** **Fix in spec** to permit "scale or DPI" as the rasterizer-pinning unit (and note the equivalence), or **fix in code** to record an explicit DPI. Regenerate the manifest so `lib_version` tracks `__init__.py`, or stop recording it if it isn't load-bearing.

### F6: Snowflake future-window and several detection constants are implementation-only — the spec under-specifies the boundary between decimal types
- **Class:** SPEC
- **Severity:** MEDIUM
- **Confidence:** CONFIRMED
- **Location:** `docs/spec.md §243`, `§455`; `src/entviz/entropy.py:244-248` (`DISCORD_EPOCH_MS`, `_SNOWFLAKE_FUTURE_WINDOW_MS`).
- **Finding:** This is the spec-side half of F1. The spec describes *that* snowflakes are detected and tokenized as decimal, and that a non-snowflake digit string "falls through to hex," but gives **no rule** for the decision: no epoch, no lower/upper timestamp bound, no length-vs-value predicate. Two honest implementations will draw the snowflake/hex line in different places for the same digit string (and the equivalence relation does not list the *type label* as ignorable — it is a render-model field). Even after F1's wall-clock leak is removed, the *threshold itself* must be pinned in the spec or the divergence persists.
- **Evidence / example:** §243 says only "17–20 decimal digits encoding a 64-bit integer." The Discord epoch (`1420070400000`) and the 5-year window live only in code.
- **Recommended action:** **Fix in spec.** Write the exact snowflake-recognition predicate (epoch constant, lower bound, fixed upper bound) into the algorithm's normalization step, and add a corpus vector pair that straddles the boundary.

### F7: Tokenizer silently maps any unknown character to value 0 (defence-in-depth gap, low reachability)
- **Class:** CODE + CRYPTO (malleability surface)
- **Severity:** LOW
- **Confidence:** LIKELY (reachability is bounded by upstream validation)
- **Location:** `src/entviz/entropy.py:1237` (`if char_val == -1: char_val = 0`).
- **Finding:** Inside `tokenize`, a character not found in the declared alphabet (after the lower-case and base64±url fallbacks) is silently assigned quant-bit value `0` rather than raising. On the normative path the core is always validated/normalized to the declared alphabet upstream, so this is mostly unreachable — but it is a latent malleability seam: two distinct cores that differ only in characters outside the alphabet would tokenize identically. A spec-faithful re-implementation might instead reject, diverging on any input that reaches this branch. The spec does not define behavior for an out-of-alphabet character in `tokenize` (it assumes the core is clean), which is itself a small under-specification.
- **Evidence / example:** Code path at line 1237; not triggered by any corpus vector (all cores are pre-validated).
- **Recommended action:** **Fix in code** to assert/raise on an out-of-alphabet character (turn a silent 0 into a programmer-error exception), and **note in spec** that `tokenize` presupposes a core already in its declared alphabet. Low priority — defence in depth, not an observed defect.

---

## Additional Patterns Noted

- **`data-input-bytes` is emitted (`pipeline.py:296`) but is not in the SVG profile's REQUIRED set** — fine (advisory metadata is explicitly allowed by the equivalence relation), but worth listing in the spec's advisory-attribute notes so a checker doesn't treat its absence as a defect.
- **`pyproject.toml`/runtime import friction:** the package is only importable via the project venv; a bare `python -m pytest` mis-collects every test (`ModuleNotFoundError: entviz`) and `test_figures.py` hard-requires `segno`. Not a spec defect, but it means "run the tests" is environment-fragile — flag to the testability lens.
- **Median/quartile/min-max tie-breaks all verified correct** against §319/§321/§539-540 (`get_median_token` uses `(len-1)//2`; quartiles pad to the next multiple of 4 via `ceil`; min/max use `(quant, ∓cell_index)`). No finding — recorded so the next reviewer need not re-derive.
- **Bit-extension formula matches** the spec's worked examples (`0xAB→0xABABAB`, `0x5→0x555555`, `0xABC→0xABCABC`) — `tokenize` takes the pad from the *current* extended quant (line 1255), which is the subtle-but-correct reading. No finding.
- **Keccak-256 is on the normative path (EIP-55 only)** and is exercised by `test_f7_eip55.py::test_keccak256_vectors_eip55`; it is *not* used for any fingerprint. The `0x01` original-Keccak padding (not NIST `0x06`) is correctly chosen and documented (`keccak.py:2-7`). No finding.
- **`v3_ellipse_params_from_digest` docstring is stale** (`pipeline.py:806`): it still describes the v5 `r_min = nucleus_height`, `r_max = d_far − cell_w` bounds, while the live code uses the v6 `0.22/0.58·d_far` bounds (lines 905-906). Hand to maintainability — `stale`.

---

## Under-Specification Ledger
Cross-impl landmines the *spec* leaves open (independent of whether the Python code resolves them reasonably):

1. **Snowflake-vs-decimal boundary (F1/F6).** No epoch, no timestamp bounds, no deterministic predicate in the spec. Two impls will classify boundary decimals differently; the type label is a non-ignorable render-model field.
2. **Disproof case for base32 (F3).** §223 ("input itself, no re-encoding") contradicts §226 ("base32 → upper") for the disproof path. A re-implementer cannot tell which case to hash.
3. **Aspect-ratio bound vocabulary (F4).** Spec states `[1,100]` per *component*; the reference bounds the *ratio* `[0.01,100]`. Re-implementers taking `W:H` separately will reject/accept different extremes.
4. **Blank-map dot-position encoding (F2).** §173 names `data-blank-map-min/max` as carrying positions; the reference emits booleans and recovers position from geometry. The spec doesn't define the geometric inversion, so a checker written to the prose disagrees with the reference.
5. **Out-of-alphabet character in `tokenize` (F7).** Spec assumes a clean core; doesn't say whether an out-of-alphabet char is an error or maps to 0.
6. **Rasterizer pinning unit (F5).** §159 says "DPI"; the harness uses CairoSVG "scale". Not portable to the planned resvg authority without a stated equivalence.
7. **Color-bar letter font-size when `cell_text_px is None` / synthetic colors.** `_draw_color_bar` falls back to `bar_rect.size.width` for the font size (`pipeline.py:1045`) — a code-only fallback never reached on the normative path, but the spec pins the letter size to "the cell-text rendered size" with no fallback defined. Minor.

---

## Residual Unknowns

- **Determinism across platforms (float formatting / locale).** Static review found no `locale`, `datetime.now` in `render()`, no reliance on `hash()`/`id()`, and within-process byte-identical re-renders. But coordinate emission is Python `str(float)`; a Rust/JS port's float→string differs (`60.0` vs `60`). The equivalence relation forgives same-value formatting, so this is *probably* fine, but the smallest experiment that settles it is a **cross-impl Tier-A run** (or a CI matrix on macOS+Windows+Linux diffing the reference SVG) — not resolvable from one platform.
- **F1 blast radius on the live corpus.** Whether any *current* corpus snowflake vector sits near the moving boundary (and could flip as the corpus ages) needs a date-shifted regeneration of `snowflake-discord`/`snowflake-19` to confirm they're safely interior. The two committed vectors looked interior on inspection but were not date-stress-tested.
- **resvg parity (Tier B future).** The README plans to move the reference rasterizer to resvg; whether the current goldens survive that swap (and how DPI maps to the current `scale=2.0`) is untested here.

---

```yaml
findings:
  - id: SPEC-F1
    persona: spec-conformance-auditor
    title: Snowflake detection consults wall-clock time, so the same input renders differently on different dates
    severity: CRITICAL
    confidence: CONFIRMED
    location: src/entviz/entropy.py:828-831 and docs/spec.md §115
    dedupe_key: snowflake-nondeterministic
    recommended_disposition: recommend-fix
    rationale: parse_snowflake gates on now+5y via time.time(); a boundary decimal renders hex today and snowflake later, violating the §115 determinism MUST and diverging across impls/time. Corpus cannot catch it.
    revisit_condition: null
    fix_effort: medium
  - id: SPEC-F2
    persona: spec-conformance-auditor
    title: Blank-map dot positions emitted as boolean flags, not the (row,col) the SVG profile names; Tier A recoverable only by geometry
    severity: HIGH
    confidence: CONFIRMED
    location: src/entviz/pipeline.py:527-542 and compliance/model.py:315-336 and docs/spec.md §137,§173
    dedupe_key: blank-map-noncompliant
    recommended_disposition: recommend-fix
    rationale: Spec names data-blank-map-min/max as carrying dot positions; code emits "true" and the checker reverse-engineers (row,col) from cx/cy. A spec-faithful checker rejects the reference output.
    revisit_condition: null
    fix_effort: small
  - id: SPEC-F3
    persona: spec-conformance-auditor
    title: Bare base32 fragments via disproof are lowercased, but the spec mandates base32 canonicalizes to upper case
    severity: HIGH
    confidence: CONFIRMED
    location: src/entviz/entropy.py:1140 and docs/spec.md §226 (vs §223)
    dedupe_key: base32-noncompliant-cross-impl
    recommended_disposition: recommend-fix
    rationale: Disproof lowercases base32 cores; §226 says upper. Wrong case changes the SHA-512 fingerprint and every channel. Spec is also internally inconsistent (§223 no-re-encoding vs §226 upper).
    revisit_condition: null
    fix_effort: small
  - id: SPEC-F4
    persona: spec-conformance-auditor
    title: Aspect-ratio error condition bounds the ratio [0.01,100], but the spec names a per-component [1,100] bound
    severity: MEDIUM
    confidence: CONFIRMED
    location: src/entviz/pipeline.py:125-127 and docs/spec.md §195
    dedupe_key: aspect-ratio-divergent
    recommended_disposition: recommend-fix
    rationale: Code bounds the float ratio; spec bounds W and H components. The normative error-condition set diverges at extremes (e.g. 200:2). Pick one vocabulary in code, CLI, and spec.
    revisit_condition: null
    fix_effort: small
  - id: SPEC-F5
    persona: spec-conformance-auditor
    title: Tier-B rasterizer pinned by CairoSVG scale, not the DPI the spec requires; manifest lib_version drifts from __init__.py
    severity: MEDIUM
    confidence: CONFIRMED
    location: compliance/raster.py:34 and compliance/corpus/manifest.json and docs/spec.md §159
    dedupe_key: rasterizer-unpinned-dpi
    recommended_disposition: recommend-fix
    rationale: §159 requires DPI; harness pins a CairoSVG-only scale, not portable to the planned resvg authority. manifest lib_version 0.7.0 lags __init__.py 0.7.1.
    revisit_condition: null
    fix_effort: small
  - id: SPEC-F6
    persona: spec-conformance-auditor
    title: Spec gives no deterministic snowflake-vs-decimal detection rule (epoch/bounds live only in code)
    severity: MEDIUM
    confidence: CONFIRMED
    location: docs/spec.md §243,§455 and src/entviz/entropy.py:244-248
    dedupe_key: snowflake-missing-spec-rule
    recommended_disposition: recommend-fix
    rationale: The spec describes that snowflakes tokenize as decimal but pins no epoch, no bounds, no predicate; two impls draw the snowflake/hex line differently. Spec-side half of F1; must be pinned even after the wall-clock leak is removed.
    revisit_condition: null
    fix_effort: small
  - id: SPEC-F7
    persona: spec-conformance-auditor
    title: tokenize() silently maps out-of-alphabet characters to value 0 instead of rejecting
    severity: LOW
    confidence: LIKELY
    location: src/entviz/entropy.py:1237
    dedupe_key: tokenize-unhandled-out-of-alphabet
    recommended_disposition: recommend-defer
    rationale: Latent malleability seam (distinct cores differing only in out-of-alphabet chars tokenize identically); mostly unreachable because cores are pre-validated. A spec-faithful impl might reject and diverge.
    revisit_condition: A parser path is added that can emit a core containing characters outside its declared alphabet
    fix_effort: small
```
