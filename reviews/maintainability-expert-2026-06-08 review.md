# Maintainability Review: entviz

**Date:** 2026-06-08
**Effort level:** medium
**Context sources used:** README.md, AGENTS.md, CLAUDE.md, this.i (full, 2976 lines), docs/spec.md (header + key sections), src/entviz/__init__.py, src/entviz/pipeline.py (full), src/entviz/fingerprint.py (full), src/entviz/entropy.py (full), tests/ (directory listing + selected files), reviews/maintainability-expert-2026-06-05 review.md (read after forming own view)

---

## Evidence Inventory

- **README.md**: Present, well-structured developer quickstart. No significant gaps for a first reader.
- **AGENTS.md**: High-quality. Navigation section at §7 is the best project map. However, §7 still lists "Algorithm specification (current: v6)" — stale by one version.
- **this.i**: Present, 2976 lines, richly maintained through the v7 / conformance / multi-impl work. The newest nodes (s3mpr3fx, h4shtext, c0nf0rm1, c0mpsu1t, mult1mpl, s3cch41n, 1nputcap, alg0rvw1) are current. The older migration nodes (v2m1grat through v6m1grat) provide accurate historical context.
- **docs/spec.md**: Present (v7). Line 9 caption reads "A representative v6 entviz" — stale by one version.
- **src/entviz/\*.py**: Six core modules. `entropy.py` (1,459 lines), `pipeline.py` (1,058 lines) are the dominant files. `fingerprint.py` is 58 lines and compact.
- **tests/**: 50 test files. No raw `# TODO` / `# FIXME` comments found in source or test files. `TODO.md` is present at the repo root — appears to be a very early-development artifact (pre-v2) that is entirely stale.
- **Fixes confirmed from the 2026-06-05 prior review**: MNT-F2 (BASE64_ALPHABET duplicate, now single definition), MNT-F4 (globals() dispatch replaced with explicit `parse_funcs` list), MNT-F5 (dead `ellipse_params_from_digest()` v2 function removed). These are NOT re-filed.

**Quality signal**: The `this.i` density and callsite `this.i:` references throughout `entropy.py` and `pipeline.py` are exemplary. The project's intent layer is genuinely the first-line defense against future damage — which makes any gaps in it proportionally more dangerous.

---

## Executive Summary

The codebase is in strong maintainability condition after the 2026-06-05 round of fixes. The most significant new finding is a cluster of stale spec-version references: `pipeline.py`'s module docstring says "v6" when `SPEC_VERSION` is now "v7", and `AGENTS.md`'s navigation section says "(current: v6)" — two places a new developer reads early that install an incorrect mental model. A secondary finding is that `fingerprint.py`'s module docstring does not cite `this.i:h4shtext` or make the text-not-bytes hashing decision unmistakable at the module level, which the persona instructions identify as a top-tier intent-boundary concern. The remaining findings are lower urgency (stale sub-labels, an inaccurate alphabet-placeholder comment, and the ongoing render() length). No critical-severity issues found.

---

## Top Findings

Ordered by bang-for-buck (highest future-mistake-prevention per unit of fix effort, first).

---

### F1: `fingerprint.py` module docstring does not make the text-not-bytes hashing decision unmistakable

- **Severity:** HIGH
- **Confidence:** CONFIRMED
- **Location:** `src/entviz/fingerprint.py:1–19`, `this.i:h4shtext`
- **Finding:** The module-level docstring says "The fingerprint is the SHA-512 hash of the normalized entropy." This is technically correct but fatally incomplete: it does not state that the hash input is the **UTF-8 bytes of the text** (not the decoded raw bytes). `this.i:h4shtext` explicitly calls this "the one place where a future developer would expect bytes but the code uses text" and rates the wrong "optimization" (hashing decoded bytes instead) as silently breaking the cross-encoding collision resistance that is the whole point. The `compute_fingerprint()` function's own docstring (line 34) does say "UTF-8 bytes of the normalized entropy core" — but a developer skimming the module for context reads the module docstring first and may not reach the function docstring before forming a mental model.
- **Recommendation:** Add one sentence to the module docstring: "IMPORTANT: the hash is computed over the **UTF-8 bytes of the normalized core text**, not over the value's decoded raw bytes — see `this.i:h4shtext` for why this distinction is security-load-bearing and must not be 'optimized away'." Also add the `this.i:h4shtext` citation inline at line 35 in `compute_fingerprint()` so it appears at the callsite where someone would make the change. One sentence, one citation — prevents a silent security regression.
- **Fix effort:** small

---

### F2: `pipeline.py` module docstring says "v6" — stale when `SPEC_VERSION` is "v7"

- **Severity:** MEDIUM
- **Confidence:** CONFIRMED
- **Location:** `src/entviz/pipeline.py:4`
- **Finding:** Line 4 reads `"Implements the v6 algorithm specified in docs/spec.md"`. `SPEC_VERSION` is "v7" (src/entviz/`__init__.py:22`). This is the file a new developer opens first when debugging a rendering issue; the very first sentence installs a "v6" mental model when the code actually implements v7. The 2026-06-05 review (MNT-F1) fixed the far-worse "v2" variant of this issue; the "v6" residual was introduced by the v7 spec bump that happened after that review.
- **Recommendation:** Change line 4 to "Implements the v7 algorithm specified in docs/spec.md (the authoritative spec)". This is a one-line fix; the `AGENTS.md` spec-bump checklist should include updating this docstring, just as it requires re-running figure generators.
- **Fix effort:** small

---

### F3: `AGENTS.md` §7 navigation section says "(current: v6)" — stale

- **Severity:** MEDIUM
- **Confidence:** CONFIRMED
- **Location:** `AGENTS.md:108`
- **Finding:** `AGENTS.md:108` reads `- [docs/spec.md](docs/spec.md) - Algorithm specification (current: v6).` The spec is now v7. AGENTS.md is the mandatory methodology document every AI agent and human developer reads first. An agent running an intent-check that reads `AGENTS.md` §7 before looking at code will believe the spec is v6. The persona instructions call AGENTS.md the source of the project's mandatory methodology — a stale version stamp here corrupts the most-read document.
- **Recommendation:** Change "(current: v6)" to "(current: v7)". Add to the spec-bump checklist: "update AGENTS.md §7 navigation section version stamp."
- **Fix effort:** small

---

### F4: `entropy.py` line 83 alphabet-placeholder comment is factually wrong

- **Severity:** MEDIUM
- **Confidence:** CONFIRMED
- **Location:** `src/entviz/entropy.py:83–85`
- **Finding:** Lines 83–85 read:
  ```python
  # Named alphabet singletons. BASE32 is still deferred — types whose core
  # uses base32 (Bitcoin Cash CashAddr, Stellar, IPFS CID v1) still
  # declare BASE64 as a placeholder.
  ```
  This is no longer true. `parse_stellar_address` returns `BASE32` (lines 756, 760), `parse_ipfs_cid` returns `BASE32` for CIDv1 (line 1057), and `parse_bitcoin_cash_address` returns `BECH32` (line 707). The comment lists three types as "still using BASE64 as a placeholder" but none of them do; the BASE32 alphabet is not deferred. The only parser still using `BASE64` for a narrow-alphabet input is `parse_eos_address` (line 746, with its own correct inline comment). A developer reading this comment will be confused when the code contradicts it.
- **Recommendation:** Replace lines 83–85 with an accurate summary, e.g.:
  ```python
  # Named alphabet singletons. All major address formats now declare
  # their actual alphabet. The one exception is parse_eos_address, which
  # declares BASE64 as a placeholder pending a proper narrow-alphabet
  # treatment (see the inline comment at parse_eos_address).
  ```
- **Fix effort:** small

---

### F5: `docs/spec.md` line 9 caption says "A representative v6 entviz" — stale

- **Severity:** MEDIUM
- **Confidence:** CONFIRMED
- **Location:** `docs/spec.md:9`
- **Finding:** `docs/spec.md` is titled "Version: 7" but line 9 reads: `**Figure 1.** A representative v6 entviz, showing every channel at once.` This is a hardcoded annotation label of the kind that `AGENTS.md` §4 step 6 explicitly warns about: "the byte-diff catches pixel drift, but only a human catches a caption whose *meaning* went stale." The figure's pixels may be current (they're generated from the live renderer), but the label "v6 entviz" in the spec document describing v7 tells any reader the spec and figure are from different versions. Since this is the spec's opening illustration, it is the first figure a new implementer sees.
- **Recommendation:** Change "A representative v6 entviz" to "A representative v7 entviz". Add this to the spec-bump checklist alongside the figure-regeneration step.
- **Fix effort:** small

---

## Additional Patterns Noted

- **`v3_ellipse_params_from_digest` naming confusion.** The function at `pipeline.py:796` is named `v3_ellipse_params_from_digest` and its docstring says "V3-5: map raw digest bytes 60-63…". In fact, the function is still live — it is called at `pipeline.py:887` and imported directly by three test files (`test_v3_ellipse.py`, `test_phase12_ellipse.py`, `test_v5_ellipse_rmin.py`). The function name correctly indicates the digest-byte extraction algorithm is the same as v3's, but the "V3-5" label in the docstring could mislead a developer into thinking this is historical/deprecated code. The companion dict is named `_V3_OVERLAY_BY_BG` and the test file `test_v4_overlay_opacity.py` documents the name is "kept for historical continuity." The pattern is not a bug, but a developer who doesn't read the tests may delete these as dead code (as the 2026-06-05 review's F5 did for the actual dead `ellipse_params_from_digest`). A one-sentence clarification in the docstring ("Still the live extraction routine — the v3 name indicates the algorithm, not the spec version") would prevent a future false-positive dead-code finding.

- **`TODO.md` at repo root is entirely stale.** The file lists TODO items like "Implement repetition of low-order bits for tokens < 24 bits" and "Implement target aspect ratio grid selection logic" — these have been implemented for years. The file was last meaningfully touched before v2 and is now actively misleading: a developer triaging project status by reading `TODO.md` will believe the core tokenization is unimplemented. Recommendation: either delete it (VCS history preserves the original plan) or replace it with a one-liner pointing at the GitHub Issues list and the tick ledger.

- **`pipeline.py` deferred imports inside `render()`.** Lines 132–133 (`import base64`, `from .entropy import BASE64URL`) and lines 345, 1032 (`from .colors import get_nucleus_colors`) are deferred imports inside the `render()` function and `_draw_color_bar()`. There is no technical barrier to hoisting these to the module-level import block at the top of the file. Deferred imports inside long functions add navigation friction (you have to read inside the function to discover the dependency) and are idiomatic only when there is a circular-import problem to avoid, which is not the case here. The prior review (2026-06-05) noted the same pattern; it does not rise to a blocking finding but would reduce noise.

- **`render()` is still ~515 lines.** The prior review's MNT-F3 called out the monolith at ~480 lines and recommended extracting `_draw_blank_cells()` and `_draw_quartile_marks()`. The extraction of `_draw_label_strips`, `_draw_border_line`, `_draw_ellipse_overlay`, and `_draw_color_bar` into separate functions has been done. However, `render()` itself still runs from line 98 to ~611, encompassing layers 1–4 (edge rects, ellipse, nuclei/blank-map, quartile marks). The blank-cell drawing block (layers 3–3b) remains inline. The guidance from MNT-F3 stands: the blank-map drawing logic is ~85 lines of SVG construction inside a function already managing the full rendering pipeline. Extracting `_draw_blank_map()` and `_draw_quartile_marks()` would reduce the function to under 350 lines. The spec guarantees determinism; the extraction is mechanical and does not require any logic changes.

- **`fingerprint.py` uses `assert` for a correctness invariant.** Line 46–48 asserts `len(tokens) == _EXPECTED_FTOK_COUNT` inside `tokenize_fingerprint`. `assert` is stripped by Python in optimized mode (`-O`). For a correctness invariant (a wrong ftok count is a silent correctness bug, not a user error), `if/raise ValueError` would survive optimization and be more obviously load-bearing. Low priority — the project is not run with `-O` today — but worth noting beside the similar `assert` in `layout.py:76`.

- **`v4bch320` this.i node contains outdated text.** The node says "BASE32 alphabet (5 bits/char, alphabet A-Z2-7) is still deferred: Bitcoin Cash CashAddr, Stellar, IPFS CID v1 continue to use the BASE64 placeholder until a separate commit adds BASE32." This has since been implemented (BASE32 is `src/entviz/entropy.py:94`; the parsers updated). The `this.i` node is stale relative to the code. Since `this.i` is the authoritative intent layer, a stale "still deferred" claim in it is the most dangerous kind of stale documentation — it tells future reviewers and the spec-conformance lens to hunt for a bug that is already fixed.

- **`this.i:v4bch320` "Default token_len rule simplified" note is also stale.** The node records an old default rule formula and says it was "simplified." The current code uses `token_len = 24 // bits_per_char` (entropy.py:1213), which matches the "simplified" form. The node's stale "BASE64 placeholder" claim is the higher-priority fix.

---

## Future Developer FAQ

1. **Why does `fingerprint.py` hash the text, not the decoded bytes?** See `this.i:h4shtext`. Short answer: hashing the text keeps the text channel and all fingerprint-driven channels in agreement (they both see the same representation). Hashing decoded bytes would let two encodings of the same value share a gestalt while showing different cell text — channels that disagree about identity, which is exactly the failure mode entviz exists to prevent. This distinction is security-load-bearing; do not change it.

2. **Why is `_MIDDLE_DOMAIN_TAG` frozen at `"entviz/fingerprint-middle/v6\0"` even though the spec is v7?** See `entropy.py:1325–1334`. The `v6` is the version of the fingerprint-middle construction (introduced in spec v6, never changed). It is a cryptographic domain-separation constant. Changing it would alter the middle cells of every >512-bit entviz ever rendered, breaking comparison against any prior copy. It stays `v6` permanently unless the derivation itself changes.

3. **Why does `parse_eos_address` appear at the END of `parse_funcs`?** Because the EOS character class `[a-z1-5.]` is a superset of lowercase hex, so `parse_hex` must win first for even-length pure-hex inputs. See `this.i:3osr3sd1` and the comment block at `entropy.py:1078–1091`. The ordering is now explicit in the `parse_funcs` list rather than implicit in a `globals()` scan.

4. **What is `this.i` and how do I use it?** It is a structured intent file (YAML-like indented format) capturing every major design decision. Node IDs like `this.i:h4shtext` are referenced from source comments; find them by searching `this.i` for `id: h4shtext`. Reading `AGENTS.md §2` first explains the format and the mandatory "intent check before any implementation task" rule.

5. **Why does the code have `v3_ellipse_params_from_digest` — is that dead code?** No. The function is live at `pipeline.py:887` and tested directly by three test files. The `v3` prefix indicates the _algorithm_ for extracting ellipse parameters from the digest (unchanged since v3); it does not mean the function is a v3-era artifact. The companion dict `_V3_OVERLAY_BY_BG` is similarly live but retained under the historical name. Do not delete these.

---

## Residual Unknowns

- Whether `this.i:v4bch320`'s stale "BASE64 placeholder" claim for Bitcoin Cash / Stellar / IPFS CID was formally closed or whether there are other `this.i` nodes with similar outdated "deferred" language (a full cross-reference between `this.i` status fields and current code was not done at medium effort).
- The `TODO.md` deletion decision: the file has not been updated since the early v1→v2 era; whether there is a reason it was retained (historical reference, onboarding artifact) was not investigated.

---

## Decisions Needed

- **`TODO.md`**: Delete it (VCS is the archive), or replace with a redirect to the GitHub Issues list and tick ledger? The current content actively misleads.
- **`this.i:v4bch320` and the `entropy.py:83` comment**: Both claim "BASE32 is still deferred" — they should be corrected. Should the `this.i` node be updated (the BASE32 work is done) or a new `this.i` decision node recorded for the completion? Per AGENTS.md §2, closing a deferred work item in `this.i` is a decision worth capturing.

---

## Findings Manifest

```yaml
findings:
  - id: MNT-F1
    persona: maintainability-expert
    title: fingerprint.py module docstring missing text-not-bytes hashing intent (h4shtext)
    severity: HIGH
    confidence: CONFIRMED
    location: src/entviz/fingerprint.py:1-19
    dedupe_key: fingerprint-missing
    recommended_disposition: recommend-fix
    rationale: >
      The module docstring says "SHA-512 hash of the normalized entropy" without
      clarifying that the hash input is UTF-8 text (not decoded bytes). this.i:h4shtext
      identifies this as the intent-boundary with the highest damage potential: the wrong
      optimization (hashing decoded bytes) is silent and breaks cross-encoding collision
      resistance. Fix is one sentence in the module docstring plus one citation at line 35.
    revisit_condition: null
    fix_effort: small
    tier: null
    cost_category: null
    measurement: null

  - id: MNT-F2
    persona: maintainability-expert
    title: pipeline.py module docstring says "v6" but SPEC_VERSION is "v7"
    severity: MEDIUM
    confidence: CONFIRMED
    location: src/entviz/pipeline.py:4
    dedupe_key: pipeline-stale
    recommended_disposition: recommend-fix
    rationale: >
      Line 4 reads "Implements the v6 algorithm". SPEC_VERSION = "v7". A developer opening
      the file reads the wrong spec version first. The prior review fixed "v2 -> v6"; the
      v7 bump introduced this again. One-word fix; high first-impression value.
    revisit_condition: null
    fix_effort: small
    tier: null
    cost_category: null
    measurement: null

  - id: MNT-F3
    persona: maintainability-expert
    title: AGENTS.md §7 navigation says "(current: v6)" — stale by one spec version
    severity: MEDIUM
    confidence: CONFIRMED
    location: AGENTS.md:108
    dedupe_key: this-i-stale
    recommended_disposition: recommend-fix
    rationale: >
      AGENTS.md is the mandatory methodology document every AI agent and developer reads
      first. A stale "(current: v6)" in the spec navigation link poisons the initial
      intent-check for any agent or human that follows the AGENTS.md §2 protocol.
    revisit_condition: null
    fix_effort: small
    tier: null
    cost_category: null
    measurement: null

  - id: MNT-F4
    persona: maintainability-expert
    title: entropy.py alphabet comment incorrectly claims BASE32 is "still deferred"
    severity: MEDIUM
    confidence: CONFIRMED
    location: src/entviz/entropy.py:83-85
    dedupe_key: entropy-stale
    recommended_disposition: recommend-fix
    rationale: >
      Comment states "Bitcoin Cash CashAddr, Stellar, IPFS CID v1 still declare BASE64
      as a placeholder" — none of them do (Stellar/IPFS use BASE32, BCH uses BECH32).
      A developer auditing alphabet correctness will look at this comment and conclude
      there is a known bug where there is none, or miss a real bug because they trust
      the (wrong) comment.
    revisit_condition: null
    fix_effort: small
    tier: null
    cost_category: null
    measurement: null

  - id: MNT-F5
    persona: maintainability-expert
    title: docs/spec.md Figure 1 caption says "v6 entviz" in a v7 spec document
    severity: MEDIUM
    confidence: CONFIRMED
    location: docs/spec.md:9
    dedupe_key: spec-stale
    recommended_disposition: recommend-fix
    rationale: >
      The spec document header says "Version: 7" but Figure 1's caption says
      "A representative v6 entviz" — the opening illustration of the v7 spec is labeled
      as the previous version. AGENTS.md §4 step 6 explicitly flags caption staleness
      as a human-eye concern the byte-diff cannot catch.
    revisit_condition: null
    fix_effort: small
    tier: null
    cost_category: null
    measurement: null
```
