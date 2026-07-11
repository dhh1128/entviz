# entviz spec.md — RFC-2119 Requirements Inventory

**Target:** `docs/spec.md` (version 15, 695 lines)
**Extracted:** 2026-07-11 (read-only research pass; editorial-prep artifact)
**Scope:** Every sentence/clause containing an **ALL-CAPS** RFC-2119 keyword (MUST, MUST NOT, REQUIRED, SHALL, SHALL NOT, SHOULD, SHOULD NOT, RECOMMENDED, MAY, OPTIONAL). Lowercase uses are excluded by the spec's own §"Notation and requirements language" and are not inventoried.

Anchors of truth used for the *impl* / *test* columns: `src/entviz/{pipeline,characterize,colors,entropy,fingerprint,layout,renderer}.py`; `compliance/corpus/*/model.json`; `tests/`.

---

## Keyword totals (verified against the plan)

Counted with `grep -oE '\b<kw>\b'` on the full file, then de-nesting "MUST NOT" out of "MUST" and "SHALL NOT" out of "SHALL":

| keyword | plan expected | actual in file | of which normative | of which **definition-line-only** (line 15) |
|---|---|---|---|---|
| MUST | 66 | 66 | 65 | 1 |
| MUST NOT | 22 | 22 | 21 | 1 |
| MAY | 15 | 15 | 14 | 1 |
| SHOULD | 6 | 6 | 5 | 1 |
| OPTIONAL | 4 | 4 | 3 | 1 |
| REQUIRED | 3 | 3 | 2 | 1 |
| SHOULD NOT | 1 | 1 | **0** | 1 |
| SHALL NOT | 1 | 1 | **0** | 1 |
| SHALL | 1 | 1 | **0** | 1 |
| RECOMMENDED | 1 | 1 | **0** | 1 |

All plan counts reconcile exactly. Every keyword's count includes **one** occurrence on the RFC-2119 boilerplate sentence at **line 15** (which lists all ten keywords). That single line is definitional, not an obligation, so it is **excluded** from the numbered requirements below (recorded once as R000 for completeness).

---

## Summary of high-value findings (read this first)

### Finding 1 — The lone SHALL / SHALL NOT / SHOULD NOT / RECOMMENDED **do not exist as obligations**
The plan anticipated relocating "the lone SHALL / SHALL NOT" (Daniel pre-approved normalizing to MUST/MUST NOT). **There is nothing to relocate.** `SHALL`, `SHALL NOT`, `SHOULD NOT`, and `RECOMMENDED` each appear in `docs/spec.md` **exactly once — all four on line 15**, inside the RFC-2119 keyword-definition sentence itself. There is **no normative use** of any of them anywhere in the spec body. So:
- The spec declares four keywords it never uses. An editor could (a) leave them (harmless, standard RFC-8174 boilerplate) or (b) trim the boilerplate to only the keywords actually used (MUST, MUST NOT, REQUIRED, SHOULD, MAY, OPTIONAL). This is an editorial call, not a bug.
- **Action item for Daniel:** the pre-approved "normalize SHALL→MUST" edit is a no-op — confirm you're content leaving the unused keywords in the definition sentence, or trim them.

### Finding 2 — All-caps keyword inside NON-normative prose (mis-cased obligations)
Two all-caps keywords sit inside blocks the spec explicitly marks non-normative, so per §"Notation" they carry **no** force despite reading as obligations. Both are `MUST NOT`:

- **R-N1 (line 335)** — `DOMAIN_TAG` "... **MUST NOT** be changed to track the spec version ...". This sits inside a sentence explicitly opened `**Note (non-normative).**`. The obligation it states is real and important (changing the tag breaks every >512-bit entviz), but it is currently unenforceable-by-letter because it lives in a Note. **Recommend:** hoist this sentence out of the Note into normative body text, OR accept it as explanatory (the actual normative constant is fixed by the golden corpus). Flagged as a genuine editorial defect.
- The `MUST NOT` at **line 510** (blend-mode markers) is inside a bulleted design paragraph that is *not* marked as a Note — it reads as normative and is consistent with the normative paint-order rules. **Not** a defect; included as R-normal.

*(No all-caps MUST/SHOULD/etc. was found inside a `Rationale (non-normative)` or `Warning` block that would flip its status — the line-170 `Warning` block's `MUST` at line 170 is genuinely normative and is intended to be.)*

### Finding 3 — Spec-vs-impl mismatches
After reading the reference impl, **no hard spec-vs-impl contradiction was found** in the sampled requirements — the reference implementation is the spec's oracle and tracks it closely. Two items are worth an editor's eye as *soft* mismatches / imprecision (not outright bugs):

- **M1 — `data-input-bytes` is SHOULD in the profile (line 224) but the reference impl always emits it** (`pipeline.py:366`). Not a contradiction (emitting a SHOULD is conformant), but the corpus goldens therefore *always* contain it, so the "SHOULD" is de-facto "MUST" for anything compared against goldens field-for-field. Editor may want to note the asymmetry. Low severity.
- **M2 — Font-family SHOULD chain (line 414) vs. rasterization hoist.** The SVG the impl emits carries the full spec chain (`renderer.py:15`, set once on root per `pipeline.py:355`), so the **SVG is conformant**. The known cairosvg "hoist monospace to front" behavior (MEMORY: `cairosvg-mono-font-hoist`) happens only in the PNG rasterization path and does **not** alter the emitted SVG — so it is **not** a spec-vs-impl mismatch at the normative (SVG) layer. Recorded here only to preempt a false-positive during review.

**Bottom line: 0 hard mismatches; 2 soft/advisory items (M1, M2).** The single highest-value editorial finding is Finding 1 (dead keywords) + Finding 2's R-N1 (a real obligation trapped in a non-normative Note).

### Finding 4 — Asserted-but-untested requirements
Coverage is strong. The conformance corpus has 12 `err-*` vectors covering every Error-conditions bullet; `test_closed_profile.py` covers the closed profile; `test_v13`/`test_characterize.py` cover the characterization attributes; `test_snowflake.py` covers the wall-clock-determinism rule. The requirements with **no discoverable dedicated test** (marked `UNTESTED?` in the table) are mostly *serialization-freedom* MAYs and *prose-guidance* SHOULDs that are inherently hard to test and low-risk:
- R-line199 `MUST NOT use exponential notation` — enforced by `_compact()` (`pipeline.py:126`) but no test was found asserting "no `e`/`E` in any numeric attribute" directly. **Likely UNTESTED as a negative assertion** — worth a one-line regression test.
- R-line605 (`+hash` tspan SHOULD) — visual/structural guidance; no dedicated test found.
- Several `MAY` serialization-freedom clauses (path-vs-rects surround, hoisted font-family, grouped channels) are covered indirectly by `test_conformance_invariances.py` but not each individually.

Estimated **~8 requirements** lack a dedicated, name-matchable test (see `UNTESTED?` rows). None are high-risk error paths.

---

## Requirement table

Legend: **N?** = normative? (Y / **N**=all-caps-but-non-normative). `impl`/`test` are best-effort locations from a targeted search, not exhaustive.

| id | line | kw | section | verbatim (trimmed to obligation) | N? | impl | test/corpus |
|---|---|---|---|---|---|---|---|
| R000 | 15 | *all* | Notation & requirements language | "The key words MUST, MUST NOT, REQUIRED, SHALL, SHALL NOT, SHOULD, SHOULD NOT, RECOMMENDED, MAY, and OPTIONAL … are to be interpreted as described in RFC 2119 and RFC 8174 … when, and only when, they appear in all capitals." | N (definitional) | — | — |
| R001 | 40 | MUST | Concepts | "Implementations MUST hash the UTF-8 bytes of the normalized core string … not the value's decoded raw bytes." | Y | `fingerprint.py` / `pipeline.py` (fingerprint step) | `test_fingerprint.py` |
| R002 | 19 | MUST | Notation (Conformance intro) | "the *error conditions* every implementation MUST enforce." | Y | `pipeline.render` guards (`pipeline.py:180–193`), entropy parser | `err-*` corpus (12), `test_phase13_validation.py` |
| R003 | 110 | REQUIRED | Conformant implementation | "**entropy** — the input string to visualize (REQUIRED)." | Y | `pipeline.render(entropy_text, …)` | `test_pipeline.py` |
| R004 | 111 | OPTIONAL | Conformant implementation | "**target aspect ratio** — a positive rational `W:H` (OPTIONAL; default `1:1`)." | Y | `render(target_ar=1.0)` `pipeline.py:164` | `test_grid_selection.py`, `ar-*` corpus |
| R005 | 112 | OPTIONAL | Conformant implementation | "**reference font size** — an integer point size (OPTIONAL; default `12`)." | Y | `render(font_size_pt=12)` | `fs-6/fs-12/fs-24` corpus |
| R006 | 112 | MUST | Conformant implementation | "An implementation MUST support at least the range `[6, 30]` points." | Y | `pipeline.py:188` | `fs-6/fs-24`, `err-fontsize-*` |
| R007 | 113 | OPTIONAL | Conformant implementation | "**user note** — an OPTIONAL out-of-band caption … never as part of the entropy string." | Y | `sanitize_note` `pipeline.py:68` | `test_user_note.py` |
| R008 | 115 | MUST | Conformant implementation | "An implementation MUST be **deterministic**: identical render inputs MUST yield conformant-equivalent output on every invocation, on every platform." | Y | whole pipeline; salt from fingerprint | `test_conformance_invariances.py`, `test_snowflake.py` |
| R009 | 115 | MUST | Conformant implementation | "(second MUST in same sentence — outputs MUST NOT depend on wall-clock/locale/env/random)." | Y | (no time/locale/random calls) | `test_snowflake.py` (wall-clock rule) |
| R010 | 125 | MUST | Conformance levels | "A claim of conformance MUST state the level and the corpus (spec) version it was certified against." | Y | — (process/claim requirement) | `compliance/runner.py` (level reporting) |
| R011 | 142 | MUST | The render model (Tier A) | "An implementation MUST expose enough machine-readable structure in its SVG — at minimum the attributes enumerated in the SVG profile — for a checker to recover every field of the render model unambiguously." | Y | `pipeline.py:358–390` (data-* emit) | `test_v5_data_attributes.py`, `compliance/model.py` |
| R012 | 146 | MUST | Entropy characterization | "An implementation MUST emit the characterization onto the root `<svg>` as `data-*` attributes — data-encoding, data-scheme, data-role, data-size-basis, data-entropy-type, data-size-bits, and data-qualifiers / data-parts." | Y | `pipeline.py:380–388` | `test_characterize.py` |
| R013 | 152 | MUST | Entropy characterization (`role`) | "`role` MUST be asserted **only from the generic recognizer**." | Y | `characterize._describe_from_parsed` `characterize.py:143`, `_cesr_role` | `test_characterize.py` |
| R014 | 154 | MUST NOT | Resolution A (`size_basis`) | "It is scheme-driven and MUST NOT be inferred from the alphabet or from the content's appearance." | Y | `characterize._size_bits` / `size_basis` scheme map `characterize.py:85` | `test_characterize.py` |
| R015 | 155 | (MUST via NOT) | Resolution A (`size_bits`) | "`size_bits` is reporting-only and is NOT the >512-bit truncation basis." *(the 'NOT' here is emphasis, not a 2119 keyword — see note)* | Y (see notes) | `characterize._size_bits` | `test_characterize.py` |
| R016 | 161 | (see 163) | Resolution A | *(size_bits computed-from-core prose; the MUST is at 163)* | — | — | — |
| R017 | 163 | MUST / MUST NOT | Resolution A (non-pow-2) | "for base58/base36/decimal an implementation MUST decode the core to its integer value and take its minimal byte length; it MUST NOT use the tokenizer's `bits_per_char`." | Y | `characterize._decoded_bytes_integer` `characterize.py:62`, `_size_bits:85` | `test_characterize.py` |
| R018 | 166 | MUST NOT | Resolution A (`size_basis` driver) | "`size_basis` is driven by scheme … It MUST NOT be inferred from `encoding` nor from the content's appearance." | Y | `characterize.py` size_basis scheme map | `test_characterize.py` |
| R019 | 170 | MUST | Resolution A — Warning | "The large-input trigger MUST keep using the existing tokenization byte length (`floor(len(core) × bits_per_char / 8)`), unchanged." | Y (Warning block, but normative) | `entropy.py` / `pipeline.py` large-input threshold (64-byte) | `test_large_input.py`, `hex-1024`/`b64-large` corpus |
| R020 | 190 | MUST NOT | Equivalence relation | "The following are purely serialization-level differences. They MUST NOT be treated as non-conformance, and the equivalence relation ignores them." | Y | `_normalize_numbers` `pipeline.py:151`, `compliance/model.py` | `test_conformance_invariances.py` |
| R021 | 194 | MUST / MUST NOT | Equivalence relation (numeric) | "A conformance checker MUST compare these fields numerically within [0.01 px] tolerance and MUST NOT require byte-identical numerals." | Y | `compliance/model.py` numeric compare | `test_conformance_invariances.py`, `test_runner_external.py` |
| R022 | 199 | MUST NOT | Numeric serialization | "implementations MUST NOT use exponential/scientific notation (e.g. `1e-7`)." | Y | `_compact` `pipeline.py:126` (uses `%.3f`) | **UNTESTED?** (no negative-assertion test found) |
| R023 | 199 | SHOULD | Numeric serialization | "Implementations SHOULD emit the compact form — at most 3 fractional digits, no trailing zeros, integer-valued numbers with no decimal point, and `-0` written as `0`." | Y | `_compact` `pipeline.py:126–133` | `test_conformance_invariances.py` (compact form) |
| R024 | 199 | MAY | Numeric serialization | "an implementation MAY use its language's native fixed-precision formatter … without a hand-written rounder." | Y | `_compact` uses `f"{x:.3f}"` | (impl choice; n/a) |
| R025 | 205 | MUST | Canonical rasterization (Tier B) | "An implementation's SVG, rasterized by that same rasterizer at that DPI, MUST match the golden raster." | Y | `renderer.py` (SVG→PNG), goldens | `test_compliance.py` (Tier B), `test_figures.py` |
| R026 | 207 | MUST | Canonical rasterization (Tier B) | "**Every other channel** … MUST match the golden raster within the corpus's stated per-channel tolerance." | Y | renderer + goldens | `test_compliance.py` |
| R027 | 213 | MUST | SVG profile | "A conformant SVG MUST satisfy the following." | Y | `pipeline.py` SVG assembly | `test_v5_data_attributes.py`, `compliance/model.py` |
| R028 | 215 | MUST | SVG profile | "The root `<svg>` MUST carry `width`, `height`, and `viewBox=\"0 0 <bw> <bh>\"`." | Y | `pipeline.py` root svg attrs (`viewBox` ~`pipeline.py:355–370`) | `test_issue31_quiet_margin.py`, `test_v5_data_attributes.py` |
| R029 | 216 | MUST | SVG profile | "The SVG MUST carry the spec-version and library-version stamps (`data-entviz-version`, `data-entviz-lib`) and the grid dimensions (`data-cols`, `data-rows`)." | Y | `pipeline.py:364–368` | `test_v5_data_attributes.py` |
| R030 | 217 | MUST | SVG profile | "Each grid cell MUST be identifiable by `data-cell-index` and locatable by `data-cell-col`/`data-cell-row`." | Y | `pipeline.py` cell group attrs | `test_v5_data_attributes.py` |
| R031 | 217 | MUST | SVG profile | "Blank cells MUST be flagged (`data-cell-blank`), the map-bearing blank distinguished (`data-cell-blank-map`) with marker positions carried as `\"row,col\"` in `data-blank-map-min`/`data-blank-map-max`." | Y | `pipeline.py` blank-map emit; `_blank_map_sub_center:107` | `test_v6_blank_map.py` |
| R032 | 217 | MUST | SVG profile | "a checker MUST be able to recover each `(row, col)` from the attribute value directly, without measuring pixel geometry." | Y | `data-blank-map-*` string attrs | `test_v6_blank_map.py`, `compliance/model.py` |
| R033 | 218 | MUST | SVG profile (surround) | "Each filled cell MUST declare its surround channel on the cell group: `data-surround-bits` carries the 24-bit pattern as a hex integer … and `data-edge-color` carries the edge color whenever at least one box is set." | Y | `pipeline.py` cell group | `test_v4_surround.py`, `test_v5_data_attributes.py` |
| R034 | 218 | MUST | SVG profile (surround) | "A checker MUST recover the surround bits and edge color from these attributes, not by measuring box geometry." | Y | data-* attrs | `compliance/model.py`, `test_v4_surround.py` |
| R035 | 218 | MAY | SVG profile (surround) | "The boxes themselves MAY be rendered as a single `<path>` (one subpath per set box) or as individual rects." | Y | `pipeline.py` surround (path form) | `test_conformance_invariances.py` |
| R036 | 218 | MUST | SVG profile (surround) | "either way they MUST sit in the surround layer (painted before the cell nuclei and the ellipse overlay)." | Y | `pipeline.py` paint order | `test_phase8_layering.py` |
| R037 | 219 | MUST | SVG profile (color bar) | "Each color-bar band MUST carry its stable uppercase identifier (`data-color-bar-band` ∈ {W,G,R,B,K}), its `data-color-bar-rank` …, and `data-color-bar-letter`." | Y | `_draw_color_bar` `pipeline.py:1177` | `test_v9_color_bar.py`, `test_v5_color_bar_letters.py` |
| R038 | 220 | MUST | SVG profile (color bar) | "The color bar MUST expose its two markers and slot count: `data-bar-marker-left`, `data-bar-marker-right`, and `data-bar-slots` (K)." | Y | `_draw_color_bar` `pipeline.py:1177` | `test_v9_color_bar.py` |
| R039 | 221 | MUST | SVG profile (ellipse) | "When an ellipse overlay is present, its parameters MUST be exposed (`data-ellipse-anchor-x/-y`, `-rx`, `-ry`, `-rotation-deg`)." | Y | `_draw_ellipse_overlay` `pipeline.py:1043` | `test_phase12_ellipse.py`, `test_v3_ellipse.py` |
| R040 | 222 | MUST | SVG profile | "Truncated (large-input) renders MUST set `data-truncated`; a user note MUST be exposed on its `<text>` element as `data-user-note`." | Y | `pipeline.py:370`, `:884/:890` | `test_v5_truncation.py`, `test_user_note.py` |
| R041 | 222 | MAY | SVG profile | "Logical channels MAY be grouped and tagged with `data-channel`." | Y | `pipeline.py` channel groups | `test_conformance_invariances.py` |
| R042 | 223 | MAY | SVG profile (font carriage) | "the monospace fallback chain MAY be set once on an ancestor of the `<text>` elements (e.g. the root `<svg>`) and inherited." | Y | `pipeline.py:355` (root set once) | `test_conformance_invariances.py` |
| R043 | 223 | MAY | SVG profile (font carriage) | "a `<text>`'s rendered size MAY be carried as a `font-size` presentation attribute … rather than inside a `style` declaration." | Y | `_draw_label_strips` `pipeline.py:830` | `test_conformance_invariances.py` |
| R044 | 223 | MUST / MUST NOT | SVG profile (font carriage) | "A conformant checker MUST recover the rendered size class from either form, and MUST NOT require a per-`<text>` `font-family`." | Y | `compliance/model.py` size-class recovery | `test_conformance_invariances.py` |
| R045 | 224 | SHOULD | SVG profile | "The root `<svg>` SHOULD carry `data-input-bytes`, the byte length of the raw input as serialized for fingerprinting." | Y | `pipeline.py:366` (always emitted) | `test_v5_data_attributes.py` — **soft mismatch M1** |
| R046 | 224 | MAY | SVG profile | "two conformant renderings of the same value MAY differ in `data-input-bytes` (e.g. dashed vs. undashed UUID) … a checker recovering it MUST exclude it when comparing." | Y | `compliance/model.py` (excludes it) | `test_conformance_invariances.py` (uuid dash) |
| R047 | 224 | MUST | SVG profile | "a checker recovering it MUST exclude it when comparing renderings for equivalence." | Y | `compliance/model.py` | `test_conformance_invariances.py` |
| R048 | 225 | MUST | SVG profile (clip-path) | "The clip-path `id` confining the ellipse overlay MUST be unique within the enclosing HTML document." | Y | `_draw_ellipse_overlay` id salt `pipeline.py:1043` | `test_v4_clip_id_uniqueness.py` |
| R049 | 227 | MUST | Closed profile | "Any other element, or any rendering element outside its channel, is non-conformance: a checker MUST reject it (`validate_closed_profile`)." | Y | `compliance` / `validate_closed_profile` | `test_closed_profile.py` |
| R050 | 229 | MUST | Paint order | "Implementations MUST paint in the following back-to-front order." | Y | `pipeline.py` draw order | `test_phase8_layering.py` |
| R051 | 241 | MUST / MUST NOT | Error conditions | "A conformant implementation MUST reject the following inputs with an error and MUST NOT emit an SVG for them." | Y | `pipeline.render` guards + parser | `err-*` corpus (12), `test_phase13_validation.py` |
| R052 | 243 | MUST | Error conditions (EIP-55) | "a mixed-case Ethereum (EIP-55) address whose case pattern fails the EIP-55 checksum — the error MUST identify the first mismatched-case digit." | Y | `entropy.py` EIP-55 (uses `keccak.py`) | `test_f7_eip55.py`, `err-eip55-bad-checksum` |
| R053 | 244 | (MUST via 241) | Error conditions (checksum) | "an input that structurally matches a checksummed scheme but whose bound checksum fails to verify (base58check, bech32/bech32m, CashAddr, LEI MOD 97-10)." | Y | `entropy.py` checksum verifiers | `test_v14_label_and_checksums.py`, `err-{btc,ltc,bch,cosmos,lei}-*` |
| R054 | 245 | MUST NOT | Error conditions (user note) | "a user note that violates sanitization … The note MUST NOT be silently truncated or otherwise mangled." | Y | `sanitize_note` `pipeline.py:68` | `test_user_note.py`, `err-note-{control,nonascii,too-long}` |
| R055 | 246 | (MUST via 241) | Error conditions (params) | "render parameters outside the implementation's supported range — e.g. a reference font size outside `[6, 30]` or aspect-ratio component outside bounds." | Y | `pipeline.py:188–193` | `err-fontsize-{low,high}` |
| R056 | 248 | MUST NOT | Error conditions (grid) | "an implementation MUST NOT emit a single-row or single-column grid regardless." | Y | `layout.py` grid selection (min 2×2) | `test_grid_selection.py` |
| R057 | 250 | MUST | Error conditions | "Rejection MUST be reported through the implementation's normal error channel (exception, non-zero exit, etc.)." | Y | `raise ValueError` throughout | `test_phase13_validation.py` |
| R058 | 255 | MUST (×3) | Algorithm — Normalize | "Normalization MUST eliminate case differences … It MUST identify prefixes that are not true entropy … It MUST identify suffixes that are checksums or derivations of the true entropy." | Y | `entropy.parse` | `test_entropy.py` |
| R059 | 256 | MUST / MUST NOT | Normalize — swap test | "The fingerprint (and, where possible, the cells) MUST bind exactly the identity bits and MUST NOT bind the rest." | Y | `entropy.parse` prefix/core/suffix + fold | `test_cesr_semantic_prefix.py`, `test_swhid_gitoid.py` |
| R060 | 259 | MUST | Normalize — identity | "**Identity** … It MUST bind the fingerprint. (CESR derivation code B/C/D/E)." | Y | `entropy.py` CESR core retention | `test_cesr_semantic_prefix.py`, `cesr-*` corpus |
| R061 | 274 | MUST | Normalize — disproof | "If no specific-format parser matches, the implementation MUST attempt alphabet detection by disproof … The order MUST be: hex → base32 → bech32 → base58 → base64 → base64url." | Y | `entropy.py` disproof detection | `test_v4_disproof_fallback.py` |
| R062 | 275 | MUST NOT | Normalize — UTF-8 fallback | "UTF-8 is the canonical byte encoding for the fallback path; implementations MUST NOT use other encodings (Latin-1, UTF-16, etc.)." | Y | `entropy.py` fallback (utf-8) | `test_entropy.py`, `test_extra_alphabets.py` |
| R063 | 279 | MUST | Normalize — EIP-55 | "A mixed-case Ethereum address whose case pattern **fails** the EIP-55 checksum MUST be rejected at parse time with an error identifying the first mismatched-case digit." | Y | `entropy.py` EIP-55 + `keccak.py` | `test_f7_eip55.py`, `err-eip55-bad-checksum` |
| R064 | 281 | MAY / MUST | Normalize — checksum verification | "A parser MAY surface a bound checksum as a suffix only if it has VERIFIED it … the implementation MUST reject the input with an error." | Y | `entropy.py` checksum verifiers | `test_v14_label_and_checksums.py` |
| R065 | 286 | MUST / MUST NOT | Normalize — LEI | "a failing ISO/IEC 7064 MOD 97-10 check … MUST reject — it MUST NOT fall through to a generic base36 encoding." | Y | `entropy.py` LEI verifier | `test_v4_lei.py`, `err-lei-bad-checksum` |
| R066 | 293 | MUST (×2) | Normalize — DIDs | "an implementation MUST treat `:` as an ordinary body character and MUST end the method-specific-id only at the first `/`, `?`, or `#` (or end of input)." | Y | `entropy.py` DID parser | `test_v11_did_urn.py`, `did-*` corpus |
| R067 | 295 | MUST | Normalize — DID URL tail | "The DID URL tail is a free annotation and MUST be dropped." | Y | `entropy.py` DID parser | `test_v11_did_urn.py`, `did-web-urldrop`, `did-key-fragment` |
| R068 | 297 | MUST NOT | Normalize — DID core | "The core MUST NOT be percent-decoded." | Y | `entropy.py` DID parser | `test_v11_did_urn.py` |
| R069 | 306 | MUST | Normalize — URNs | "The r-/q-/f-components are a free annotation and MUST be dropped." | Y | `entropy.py` URN parser | `test_v11_did_urn.py` |
| R070 | 315 | MUST NOT | Algorithm — Fingerprint | "implementations MUST NOT decode the core to its underlying raw bytes before hashing." | Y | `fingerprint.py` / `pipeline.py` fingerprint step | `test_fingerprint.py` |
| R071 | 326 | MUST / MUST NOT | Tokenization — snowflake | "Snowflake detection MUST be deterministic and MUST NOT consult the wall clock." | Y | `entropy.py` snowflake classifier | `test_snowflake.py` |
| R072 | 335 | MUST NOT | Large-input (Note, non-normative) | "The `v6` in `DOMAIN_TAG` … MUST NOT be changed to track the spec version." | **N** (inside `Note (non-normative)`) | `DOMAIN_TAG` const `pipeline.py`/`fingerprint.py` | `test_v6_fingerprint_middle.py` — **Finding 2 / R-N1** |
| R073 | 390 | MUST | Algorithm — grid | "the implementation MUST choose the grid layout that produces an overall rectangle with an aspect ratio closest to the target, without being less than the target …, and with at least 2 columns and 2 rows." | Y | `layout.py` grid selection | `test_grid_selection.py`, `test_layout.py` |
| R074 | 414 | SHOULD | Algorithm — font chain | "Implementations SHOULD render every text element … with the font-family fallback chain `\"JetBrains Mono\", \"Menlo\", …, monospace`." | Y | `renderer.py:15` `MONOSPACE_FONT_FAMILY` | `test_figures.py` — **soft item M2** |
| R075 | 414 | MUST NOT | Algorithm — font chain | "Implementations MUST NOT use a bare `monospace` declaration without a fallback chain." | Y | `renderer.py:15` (full chain) | `test_conformance_invariances.py` |
| R076 | 471 | MUST (×2) | Algorithm — bg color | "The implementation MUST select the 2 low-order bits of the quant of the median ftok … The implementation MUST then remove the selected color … to form the edge palette." | Y | `colors.select_visual_style` `colors.py:39`, `get_nucleus_colors` | `test_colors.py`, `test_phase4_avalanche.py` |
| R077 | 510 | MUST NOT | Color-bar markers (v9) | "Implementations MUST NOT draw these markers with `mix-blend-mode`, a `difference`/invert filter, or any other compositing-against-the-backdrop trick." | Y (not a Note) | `_draw_color_bar` markers `pipeline.py:1177` | `test_v9_color_bar.py` |
| R078 | 548 | MUST | Ellipse — responsive embedding | "The root `<svg>` element MUST carry a `viewBox=\"0 0 {bw} {bh}\"` attribute in addition to width and height." | Y (dup of R028) | `pipeline.py` root svg | `test_issue31_quiet_margin.py` |
| R079 | 558 | MUST | Label strip — top label (v15) | "implementations MUST derive it from the same `encoding`/`scheme`/`role`/`qualifiers`/`size_basis`/`size_bits`/`parts` fields they emit as `data-*` attributes, NOT by fusing a per-parser type string." | Y | `characterize.render_label` `characterize.py:496` | `test_v15_prefix_labels.py`, `test_v14_label_and_checksums.py` |
| R080 | 587 | MUST | Label strip — bottom label | "Because a bound checksum is now shown, it MUST have been verified … so the bottom strip never displays a checksum that does not check out." | Y | `entropy.py` verify + `characterize` suffix | `test_v14_label_and_checksums.py` |
| R081 | 589 | MAY | Label strip — user note | "Implementations MAY accept an optional user note — a short, human-supplied caption." | Y | `render(note=…)` / `sanitize_note` | `test_user_note.py` |
| R082 | 594 | MUST (×2) / MUST NOT | Label strip — user note sanitize | "The note MUST be sanitized to printable ASCII … A note that violates these constraints MUST be rejected with an error — it MUST NOT be silently truncated or otherwise mangled." | Y | `sanitize_note` `pipeline.py:68–89` | `test_user_note.py`, `err-note-*` |
| R083 | 596 | MUST | Label strip — user note attr | "The note's `<text>` element MUST carry a `data-user-note=\"<note>\"` attribute." | Y | `pipeline.py:884/:890` | `test_user_note.py` |
| R084 | 600 | MUST | Label strip — truncation marker | "The marker MUST be rendered with these visual attributes, distinct from the rest of the top label (bold; `#a00000`; same size; anchor)." | Y | `_draw_label_strips` `pipeline.py:851–856` | `test_v15_prefix_labels.py`, `test_figure_marker_colors.py` |
| R085 | 603 | MAY | Label strip — marker color | "Implementations MAY substitute a different dark red provided (a) WCAG AA vs white, (b) Oklab L in [0.35,0.55], (c) hue-distinct under CVD." | Y | `pipeline.py:853` (`#a00000`) | `test_figure_marker_colors.py` |
| R086 | 605 | SHOULD | Label strip — marker anchor | "The `+hash` segment and the rest of the label SHOULD be rendered as a bold dark-red `<tspan>` followed by its tail … within a single `<text>` element." | Y | `pipeline.py:851–856` (single `<text>`+tspan) | **UNTESTED?** (structure not asserted by a dedicated test) |
| R087 | 641 | MAY | Cell rendering — edge color | "implementations MAY substitute true CIELAB ΔE if they prefer, with the understanding that the choice of palette entry per cell may differ on borderline cases." | Y | `colors.weighted_rgb_distance` `colors.py:58` / `closest_palette_color:70` | `test_colors.py` |
| R088 | 643 | MUST | Cell rendering — fingerprint-edge (v10) | "For each such cell the implementation MUST set the edge color to `edge_palette[q & 0b11]` …" | Y | `pipeline.py` fingerprint-edge cells | `test_v10_casual_avalanche.py` |
| R089 | 658 | MUST | Cell rendering — font size | "the middle cells MUST be sized down independently or their 5 glyphs overflow the nucleus." | Y | `pipeline.py` per-cell size (token_chars) | `test_v3_hex_font.py`, `test_large_input.py` |
| R090 | 667 | MAY | Cell rendering — mixed sizes | "a single entviz MAY mix rendered sizes (full-size 4-char head/tail and 0.80× 5-char Crockford middle on the same large input)." | Y | `pipeline.py` per-cell size | `test_large_input.py` |
| R091 | 688 | MAY | Blank-cell map — marker overflow | "On a dense grid a marker MAY overflow its sub-cell; that is acceptable." | Y | `_blank_map_sub_center` `pipeline.py:107` | `test_v6_blank_map.py` |
| R092 | 499 | MAY | Color bar — letter bleed | "On a band too short to contain the full glyph height, the top of the glyph MAY bleed above the band — that is acceptable." | Y | `_draw_color_bar` `pipeline.py:1177` | `test_v9_color_bar.py` |

**Note on R015/R016/R053/R055:** a few rows fold in a `NOT`/`MUST` that is expressed once and governs a bulleted list (e.g. Error-conditions line 241's MUST/MUST NOT heads a 4-item list at lines 243–246; the per-item obligations R052–R055 inherit it). These are listed both at the head (R051) and per-item so the checklist stays 1-to-1 with checkable behaviors. `size_bits … is NOT the truncation basis` (line 155) uses "NOT" as emphasis, not the 2119 keyword — it is normative by virtue of the R019 Warning-block MUST, not by an all-caps keyword of its own.

---

## Editorial action items (distilled)

1. **Dead keywords (Finding 1):** SHALL, SHALL NOT, SHOULD NOT, RECOMMENDED are declared (line 15) but never used. Decide: keep boilerplate or trim to {MUST, MUST NOT, REQUIRED, SHOULD, MAY, OPTIONAL}. The pre-approved "SHALL→MUST" normalization is a **no-op**.
2. **R072 / R-N1 (Finding 2):** the `DOMAIN_TAG` "MUST NOT change" obligation (line 335) is trapped inside a `Note (non-normative)`. Either promote it to normative body text or downgrade the wording — currently it reads as an obligation but carries no force by the spec's own rules.
3. **R022 (line 199) no-exponential-notation** appears **untested as a negative assertion** — a one-line regression test ("no numeric attribute matches `[eE]`") would close it.
4. **R045 / M1:** `data-input-bytes` is SHOULD but always emitted by the reference impl (and therefore present in every golden) — consider noting the de-facto-MUST asymmetry, or leave as-is.
5. Duplicate `viewBox` MUST at **lines 215 and 548** (R028 ≡ R078) — an editor may consolidate.
