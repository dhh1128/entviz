# Spec editorial review — findings & triage

**Target.** `docs/spec.md` (spec **v15**, 695 lines).
**Method.** Solo inline multi-lens review, propose-don't-apply, per `reviews/spec-editorial-plan.md`.
**Scope this session.** Phase 0 (inventory + baseline) + Phase 1 (safe copyedit). Phase 2 (reorg) = report-only.
**Anchors of truth.** reference impl (`src/entviz/`) → corpus → tests → `this.i` → change-log.
**Baseline (2026-07-11).** All 5 repos on `main`, clean. `docs/spec.md` unchanged. Keyword counts verified.

> **One consolidated file, not one-per-lens.** The plan says "one file per lens + synthesis, adapting the panel pattern." Running solo (not a panel of independent agents), a single triaged file is easier for you to adjudicate 1-to-1 than seven. Say the word and I'll split it.

---

## Risk-tier legend
- **NN** — non-normative prose (intros, rationale, captions). Edit freely.
- **NA** — normative-adjacent (contains/borders a MUST/algorithm step). Ships only with a semantic-diff argued against the impl.
- **R2119** — an RFC-2119 keyword change. Never a copyedit; individual human sign-off.

## Status (2026-07-11)
**Applied & green this session** (955 tests pass, figures regenerated): F1, F2, F3, F4, F5, F6, F7, F8, F9, N2, **N1**.
**Ruled & applied:** N1 — you chose *promote to normative*; the `DOMAIN_TAG`-constancy `MUST`/`MUST NOT` now lives in the middle-group bullet, the Note keeps only the etymology (`this.i:v6fpmid2` updated with a defensive breadcrumb).
**Ruled — no edit:** F10 — you chose *keep the full RFC-2119 boilerplate set*.
**Follow-up (out of spec-edit scope):** N3 (add exponent-notation regression test — impl/test change).
**Deferred to Phase 2:** S1–S4 (scatter/duplication).
Nothing committed — working tree only, per your review.

## Triage queue (adjudicate here; details below)

| # | Lens | Loc | Issue | Tier | Proposed | Disposition |
|---|------|-----|-------|------|----------|-------------|
| F1 | copyedit | 414 | Duplicate sentence ("The final `monospace` fallback ensures something readable is always chosen." appears twice in one paragraph) | NN | Delete the 2nd occurrence | _pending_ |
| F2 | copyedit | 9 + `spec_figures.py:81,85` | Figure-version drift: prose says "v6 entviz", baked SVG caption says "v7 entviz", spec is v15 | NN (+generator) | Drop the version qualifier from both captions; regen `assets/example.svg` | _pending_ |
| F3 | terminology | 65,207,510,617,619,621,673,681,683,684,690 | British "colour"/"coloured"/"colouring" (≈25 tokens) **+ "neighbour"×3 (line 621)**, concentrated in the v10 sections, vs house-style American | NN/NA (spelling only) | `colour`→`color`, `neighbour`→`neighbor` etc. | **applied** |
| F4 | terminology | 683,688 | British "centre" (×3) vs "center" (×14 elsewhere) | NN | `centre`→`center` | _pending_ |
| F5 | clarity | 45 | Guarantees says middle tokens "separated by blank cells" — describes v5's fixed separators, which v6 **removed** (line 338: "no fixed separator blanks") | NA | Delete "separated by blank cells" (non-contiguity is already explained next sentence + line 47) | _pending_ |
| F6 | clarity | 406 | "the first ftok in the sorted list that contains the median value" is opaque — impl (`entropy.py:1742`) takes element at 0-based index `⌊(n−1)/2⌋` of the ASCII-sorted list | NA | Reword to name the position + formula explicitly | _pending_ |
| F7 | copyedit | 5,40,42,398,406,629 | 10 `&mdash;` HTML entities vs 276 unicode `—` em-dashes | NN | `&mdash;`→`—` | _pending_ |
| F8 | copyedit | 27 | Requirements bullet "**Uses** 16 million colors…" breaks the imperative mood of every other bullet ("Work…", "Make…", "Support…", "Be…") | NN | "Uses"→"Use" | _pending_ |
| F9 | copyedit | 27 | "16 million colors (R\*256, G\*256, B\*256)" — `R*256, G*256, B*256` is nonstandard notation for 256³ | NN | "(256 × 256 × 256)" | _pending_ |
| N1 | normative | 335 | **`MUST NOT` trapped in a "Note (non-normative)."** The `DOMAIN_TAG` constancy obligation ("…**MUST NOT** be changed to track the spec version") sits inside an explicitly non-normative Note, so by §Notation it carries **no force** — yet it's load-bearing (changing it breaks every >512-bit comparison) | R2119 | Promote the obligation to normative body text (lift it out of the Note) | _needs ruling_ |
| N2 | normative | 215 & 548 | **Duplicate viewBox MUST.** The "root `<svg>` MUST carry `viewBox`…" obligation is stated twice — SVG-profile (215, canonical) and the ellipse step's *Responsive embedding* note (548) | NA | Keep 215 normative; demote 548 to a non-normative back-reference (or delete) | _pending_ |
| N3 | testing | 199 | **R022 untested.** "Implementations **MUST NOT** use exponential/scientific notation" is enforced by `_compact()` but has no negative-assertion test | NN (test gap) | Add a regression test asserting no `e`/`E` exponent in emitted numerals (impl change, not spec) | _pending_ |
| F10 | meta | 15 | Plan's premise is stale and **broader than stated**: **four** declared keywords are **never used normatively** — `SHALL`, `SHALL NOT`, `SHOULD NOT`, `RECOMMENDED` each appear **only** on the line-15 boilerplate. "Retire SHALL" is a **no-op**. | — | No change (RFC-2119 boilerplate conventionally lists the full set). Optionally trim the 4 unused. | _needs ruling_ |
| S1–S4 | structure | — | Phase-2 scatter/duplication (report-only) — see Structure section | NN | Defer to Phase 2 | _defer_ |

---

## Lens: copyedit / cruft

**F1 — duplicate sentence (line 414, NN).** In the "Font-family fallback chain" paragraph the sentence *"The final `monospace` fallback ensures something readable is always chosen."* occurs **twice** (once after the platform list, once again a clause later before "Implementations MUST NOT use a bare `monospace`…"). Classic 15-pass frankenstein artifact. Delete the second occurrence; the surrounding MUST NOT is untouched, so no normative impact.

**F2 — figure-version drift (line 9 + generator, NN).** The opening illustration is triply inconsistent:
- `docs/spec.md:9` prose caption: "A representative **v6** entviz".
- `scripts/spec_figures.py:81` docstring + `:85` **baked-into-SVG** caption: "A **v7** entviz of a 256-bit input".
- Actual spec version: **15**.

`figlib.py` already stamps the true version dynamically via `data-spec-version="{SPEC_VERSION}"` (never stale), so the human captions shouldn't hardcode a number at all. **Proposed:** drop the version qualifier from both — prose → "A representative entviz, showing every channel at once."; generator caption → "A representative entviz of a 256-bit input: …". Then regenerate `assets/example.svg` (+ gallery/social-card per AGENTS.md §4) and expect `tests/test_figures.py` to gate. This is the "hunt ALL stale version strings" item; the only other hit — `paper_figures.py:363` "entviz v9 large-input demo" — is a **paper** asset (out of scope; deferred paper pass). Gallery "CID v1" / addresses are legitimate.

**F7 — em-dash entity inconsistency (NN).** 10 `&mdash;` entities (lines 5, 40, 42, 398, 406, 629) among 276 unicode `—`. Both render identically; normalize the 10 to `—` for clean by-eye diffing.

**F8 / F9 — Requirements bullet 6 (line 27, NN).** "**Uses** 16 million colors (R\*256, G\*256, B\*256)." Two nits: the verb breaks the imperative mood of the list, and `R*256, G*256, B*256` is unusual notation. Proposed: "**Use** 16 million colors (256 × 256 × 256). However, guarantee…".

## Lens: terminology consistency

**F3 — British "colour" (NN/NA — spelling only).** ~25 occurrences across 11 lines, heavily clustered in the v10 "Casual avalanche" section and the v10 blank-fill / map-rendering steps (a distinct authoring pass). House style is American (memory: `american-spelling`; and the spec elsewhere writes "color bar", "background color", "edge color"). `colour→color`, `coloured→colored`, `colours→colors`, `colouring→coloring`, `recolour→recolor`. Pure spelling; safe even inside normative sentences (e.g. 510) since it changes no meaning — but I'll still show each NA one in the apply step.

**F4 — British "centre" (NN).** Lines 683 (×2), 688: `centre→center` (14 "center" already present).

**Terminology audit (clean / no action).** Checked the plan's watch-list: *box* (surround unit) vs *cell* (grid unit) — distinct, consistent; *surround* vs *border* — distinct (border = the gray frame + middle-cell frame; surround = 24-box ring), though "border" is mildly overloaded (frame, middle-cell frame) — not worth churn; *mark/marker* — overloaded (quartile mark, blank-map markers, color-bar markers, truncation marker) but each is always qualified; *nucleus*, *fingerprint*, *color bar*, *ftok/token* — used consistently. No single-concept drift found beyond spelling.

## Lens: clarity / ambiguity  *(the highest-value defect class)*

**F5 — stale "separated by blank cells" (line 45, NA).** The Guarantees paragraph says the >512-bit text channel shows head + tail + "4 middle tokens … **separated by blank cells**." That phrasing describes **v5's two fixed separator blanks (at cells 8 and 13)**, which **v6 deleted** — line 338 is explicit: "There are **no fixed separator blanks**: head/middle/tail are a logical token ordering, not fixed cell positions." Under v6, blanks are fingerprint-driven (median/ASCII-endpoint shift) and may fall *anywhere*, so the groups are "not contiguous" (line 47) — they are not *separated by* blanks. Verified against impl (`entropy.py:1550` "there are NO fixed separator blanks"; `pipeline.py:222`). **Proposed:** delete "separated by blank cells" — the immediately-following sentence and line 47 already carry the non-contiguity correctly. Meaning preserved (removes a false statement).

**F6 — opaque "median ftok" definition (line 406, NA).** "Identify the first ftok in the sorted list that **contains the median value**." An ftok doesn't "contain" a value (it *is* a 24-bit quant), and this isn't the median of the quants — it's the middle **element by rank** of the list sorted by ASCII text. Impl is authoritative (`entropy.py:1731-1742`): `sorted_tokens[(n-1)//2]`. The current wording could let a careless reader pick "the ftok whose quant is the median quant" — a different cell. **Proposed reword:** *"Identify the ftok at the median position of the ASCII-sorted list — the element at 0-based index ⌊(n − 1) / 2⌋. (For an even count this is the first ftok of the middle pair.)"* Matches `(n-1)//2` exactly; strictly less ambiguous.

*(Wider clarity sweep: the hard normative machinery — partial-ftok bit-extension, the 22-ftok split, histogram/band-order, slot count `K`, ellipse anchor enumeration & `rx/ry/rotation`, background selection, marker slots `second[12]/[13] mod K` — was checked for cross-impl divergence and reads unambiguously and self-consistently. F5/F6 are the two genuine ambiguity/accuracy defects found.)*

## Lens: normative-language (RFC-2119)

**F10 — the "stray SHALL" is already gone (meta).** The plan's Phase-1 premise ("Single stray SHALL/SHALL NOT amid 66 MUST") is **stale**: `grep '\bSHALL\b'` finds occurrences **only on line 15**, the boilerplate keyword list. There is nothing to normalize in the body. Keeping the two unused keywords in the RFC-2119 list is conventional and harmless; the only optional edit is trimming them from the list. **Needs your ruling** (the approved "retire SHALL" action no longer applies). Also note SHOULD is **6**, not the plan's 5 (minor drift, not a defect).

**Systematic pass → `spec-requirements-inventory.md`** (complete; 92 numbered requirements R001–R092). Headline results:

**N1 — `MUST NOT` inside a non-normative Note (line 335, R2119).** The single most actionable normative defect. The paragraph opens *"**Note (non-normative).**"* and later says the `DOMAIN_TAG` string *"is a fixed domain-separation constant and **MUST NOT** be changed to track the spec version."* By the spec's own §Notation ("An implementation cannot become non-conformant by disregarding a note"), that `MUST NOT` has **zero normative force** — but it guards a hard invariant (any change to `DOMAIN_TAG` alters the middle cells of every >512-bit entviz and breaks comparison against all prior copies; cf. `this.i:v6fpmid1/v6fpmid2`). **Proposed:** lift the obligation into the normative bullet body — e.g. keep the etymology in the Note, but state normatively where `DOMAIN_TAG` is defined: "`DOMAIN_TAG` is a fixed constant; implementations **MUST** use the exact string `"entviz/fingerprint-middle/v6\0"` and **MUST NOT** alter it to track the spec version." Individual sign-off (R2119).

**N2 — duplicate `viewBox` MUST (lines 215 & 548, NA).** The SVG-profile bullet (215) and the ellipse step's *Responsive embedding* note (548) both normatively require the root `<svg>` to carry `viewBox`. Same obligation, two homes. **Proposed:** 215 stays the normative statement; 548 becomes a one-line non-normative back-reference ("…as required by the [SVG profile](#svg-profile)") or is deleted. Meaning preserved (one MUST remains).

**N3 — R022 asserted-but-untested (line 199).** "Implementations **MUST NOT** use exponential/scientific notation" is *enforced* by `_compact()` but no negative test asserts it. Low-risk, but the cheapest high-value coverage add: a test that no emitted numeral matches `/[eE]/`. This is an impl/test change, out of the spec-edit scope — noted for a follow-up, not applied here.

**No hard spec-vs-impl mismatches.** The reference impl is the spec's oracle and tracks it. Two soft items reviewed and **dismissed as non-defects**: (M1, line 224) `data-input-bytes` is SHOULD yet `pipeline.py:366` always emits it — but it's *correctly* SHOULD (an omitting impl is still conformant) and explicitly excluded from the equivalence relation, so no conflict; (M2, line 414) the emitted **SVG** carries the full font-family chain (`renderer.py`), so it's conformant — the cairosvg monospace-hoist is a PNG-rasterization detail that never touches the SVG. Recorded to preempt false positives.

**F10 — four unused keywords (line 15, meta).** Confirmed and broader than the plan: `SHALL`, `SHALL NOT`, `SHOULD NOT`, and `RECOMMENDED` are each used **only** in the boilerplate — never as a live obligation. The pre-approved "retire SHALL" is a no-op. Listing the full RFC-2119 set in the boilerplate is conventional; trimming the four unused ones is a defensible minimalist choice. Your call.

## Lens: structure / exposition  *(Phase-2 fuel — report-only)*

- **S1 — large-input handling described 4×.** Requirements bullet (23), Guarantees (45–47), the Large-input subsection (330–361), and the truncation-marker section (598–613) each restate the head-8 / middle-4 / tail-8 split and reader guidance. Consolidation candidate.
- **S2 — the "192 bits (4-/6-bit) / 160 bits (5-bit)" parenthetical repeats** on lines 23, 45, 334, 336, 344.
- **S3 — the "≈2⁹⁶ partial preimage" security claim repeats** on 351, 359, 361, 613.
- **S4 — "why fingerprint hashes text not bytes"** has a canonical subsection (51–59) but its argument is partly re-litigated in the normalization step (256–272, 297) and the fingerprint step (315).

None are defects; they're the scatter Phase 2 would consolidate against a human-authored outline. Flagged, not touched.

---

## Provisional apply-order (Phase 1, after your adjudication)
1. **Safe NN batch:** F1, F7, F8, F9, F2-prose, F3, F4.
2. **Generator + regen:** F2-generator → rerun `spec_figures.py` + (paper is out-of-scope) + gallery + social_card; `tests/test_figures.py` gates.
3. **NA, semantic-diffed individually:** F5, F6, N2.
4. **R2119 / needs-ruling:** N1 (promote the trapped `MUST NOT`), F10 (trim unused keywords?).
5. **Out of this edit's scope (noted, not applied):** N3 (add exponent-notation regression test — impl/test change).

Do NOT push; you review.

---

## What I recommend applying now vs. holding
- **Apply now (safe, unambiguous):** F1, F2, F3, F4, F7, F8, F9 — pure NN cleanups + the figure-version fix with regen.
- **Apply now with the semantic-diff shown inline:** F5, F6, N2 — NA but each argued meaning-preserving against the impl.
- **Hold for your explicit ruling:** N1 (changes a keyword's force — the right fix, but R2119), F10 (boilerplate trim — cosmetic, your taste).
- **Follow-up ticket, not this session:** N3.
