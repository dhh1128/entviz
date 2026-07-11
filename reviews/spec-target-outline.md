# Spec Phase-2 reorg — target outline (the editorial spine)

**Purpose.** The human-owned target structure for reorganizing `docs/spec.md`
(v15) in Phase 2 of the editorial pass. Phase 0+1 (copyedit/terminology/clarity +
the requirements inventory) are done and committed; this is the seed for the
*structural* pass. Drafted 2026-07-11; **Daniel owns it — edit freely before executing.**

Companion docs (same folder): `spec-editorial-plan.md` (the overall plan; see its
Phase 2 section), `spec-requirements-inventory.md` (R001–R092 — the hard invariant),
`spec-editorial-findings.md` (faults A–H and scatter S1–S4 this outline resolves).

---

## Launching the Phase-2 session

Open a **fresh** Claude Code session in `~/code/entviz` (clean context — this is a
moves-and-merges pass over a 695-line doc and wants a full window). Paste this as
the opening prompt:

> Execute Phase 2 (structural reorg) of the entviz spec editorial pass. Read, in
> order: `reviews/spec-target-outline.md` (the target spine — follow it),
> `reviews/spec-requirements-inventory.md` (the hard invariant: every requirement
> R001–R092 must survive in the reorganized doc **exactly once, wording
> unweakened**), and the Phase 2 section of `reviews/spec-editorial-plan.md`.
> Reorganize `docs/spec.md` to the target spine — this is **moves and merges, not
> a rewrite**; preserve normative sentences verbatim unless a merge demands a
> seam, and show a semantic diff for any normative sentence you alter. After
> moving, reconcile the result against the inventory line-by-line and repair every
> `](#anchor)` cross-reference (the anchor set changes — see the outline's repair
> checklist). Regenerate figures only if a caption/generator string changed. Keep
> the full test suite green. Do NOT push; Daniel reviews. Update `this.i` for any
> structural decision that changes meaning.

---

## Ground rules (the prime directive, restated)

1. **The inventory is a hard invariant.** After every move, each R001–R092 must be
   present exactly once, unweakened. Reconcile line-by-line at the end. A dropped
   or duplicated requirement is a Phase-2 failure; a typo is not.
2. **Moves and merges, not a rewrite.** Carry normative sentences verbatim. Where a
   merge needs a connective seam, keep it non-normative and show old→new.
3. **Conformance-safety.** Editing `spec.md` touches no code, so the test suite
   CANNOT catch a meaning change — the reference impl (`src/entviz/`) + corpus are
   ground truth. Verify any normative reword by reading the impl, not by running tests.
4. **Keep CI green** (proves you didn't break a generator), and **do not push.**

## Decisions locked (Daniel's rulings, 2026-07-11)

- **(a) Keep the "channels at a glance" overview — but trim it to purpose-only.**
  It earns a first-read mental model; it must NOT restate mechanics (no head/middle/tail
  bit counts, no derivation detail) — just name each of the six channels and its job,
  and point forward to the normative step. All mechanism lives in Part B.
- **(b) Fold Casual avalanche (v10) into the cell/blank substeps it explains** (the
  edge-color and blank-fill steps in "Rendering one cell"), as non-normative notes —
  not a standalone section. Its cross-cutting summary (the two-modes framing) may lead
  the "Rendering one cell" section as a short non-normative preamble.

---

## The eight flow faults this spine fixes

| | Fault (see findings A–H) | Fix in this spine |
|---|---|---|
| A | Conformance precedes the Algorithm → render model forward-references undefined quantities | Conformance moves **last** (Part C) |
| B | Input parsing split: "Entropy characterization" (in Conformance) vs "Normalize" (Algo step 1) vs label grammar (step 20) | Normalize + characterization **merge** (§6); label grammar (§15) references §6 |
| C | Large-input handling stated 4× | **One home** (§9); Requirements/overview/label cross-reference it |
| D | Six channels narrated 3× (Guarantees / render model / algorithm) | Named once (§4–5), specified once (Part B), verified once (Part C) |
| E | "Why fingerprint hashes text" far from the fingerprint step it justifies | Moves into §7 (the fingerprint) |
| F | Casual avalanche wedged between Algorithm and Cell Rendering | Folded into §13 (decision b) |
| G | Model steps interleaved with paint steps; quartile mark split from cell rendering | Grouped; quartile mark folds into §13 |
| H | Cell Rendering Algorithm is dead last, though invoked mid-algorithm | Promoted to §13, where it's invoked |

---

## Target section order

Each entry notes **← what current material feeds it** so the reorg is mechanical.

### Part A — Framing (non-normative)
1. **Introduction & goal** ← current intro + Figure 1
2. **Notation & requirements language** ← current §Notation (unchanged; keep the full RFC-2119 boilerplate per F10 ruling)
3. **Requirements & Non-requirements** ← current §Requirements + §Nonrequirements (the large-input bullet becomes a pointer to §9, per fault C)
4. **Concepts & vocabulary** ← current §Concepts, expanded into the single glossary: entviz, grid/cell/nucleus/surround/box, dimensions, capacity, entropy, token/quant, fingerprint/ftok, and the six channels *named*
5. **The channels at a glance** ← current §Guarantees, **trimmed to purpose-only** (decision a) + the read-aloud convention rescued from §"Thoughts About Comparing". Non-normative, forward-pointing. Remove restated mechanics.

### Part B — Producing an entviz (normative, pipeline order)
6. **Input normalization & characterization** ← MERGE Algorithm-step-1 (normalize: whitespace, type detection, presentation/identity/annotation swap test, bind mechanisms, multiformats, disproof, UTF-8 fallback, case norm, EIP-55, checksum verification, UUID/DID/URN) **with** Conformance's "Entropy characterization" (the 8 fields, Resolutions A/B, the two Principles). Output: normalized core + characterization.
7. **The fingerprint** ← MERGE Concepts' fingerprint blurb + §"Why the fingerprint hashes text, not decoded bytes" (fault E) + Algorithm-step-2. SHA-512 over core text, `prefix‖core` fold, the 22 ftoks.
8. **Tokenizing the entropy** ← Algorithm-step-3 body: alphabets table, token/quant, sub-24-bit bit-extension.
9. **Large inputs (head / middle / tail)** ← the current large-input subsection — the **single home** (fault C): >64-byte trigger, H8/M4/T8, the domain-separated `second` digest + `DOMAIN_TAG` (with the now-normative constancy MUST from N1), Crockford middle, scale caveat, why-middle-is-a-fingerprint.
10. **Fingerprint-derived structure** ← Algorithm steps 6–9: used ftoks → median ftok → quartiles → blank-cell placement.
11. **Grid & geometry** ← Algorithm steps 4,5,10–14: grid selection, cell indexing, reference font size + fallback chain, `font_size_px`, geometry, grid/bounding/frame rects + frame invariant.
12. **Palette & entviz background color** ← Algorithm step 15.
13. **Rendering one cell** ← PROMOTE the Cell Rendering Algorithm here (fault H), invoked by step 16. Substeps: origin; nucleus bg + fg (Oklab); edge color **+ fingerprint-edge cells**; surround layout + fill; nucleus rect; rendered font size; **quartile mark** (fold in step 17, fault G); blank-cell rendering + blank fill + map. **Casual avalanche v10 folds in here as non-normative notes** on the edge-color and blank-fill substeps (decision b), optionally led by its two-modes preamble.
14. **Whole-entviz overlays** ← Algorithm steps 18–19: color bar (histogram, first-appearance band order, letters, markers) + ellipse overlay.
15. **Label strips** ← Algorithm step 20: top grammar as **a projection of §6's characterization**, bottom suffix, user note, `+hash` truncation marker (cross-references §9, not restating it).

### Part C — Conformance & verification (normative) — everything below is now already defined
16. **Conformance** ← current §Conformance, minus the Entropy-characterization block (moved to §6): conformant implementation & render inputs → three tiers → render model (Tier A) → equivalence relation + numeric serialization → canonical rasterization (Tier B) → SVG profile + closed profile + paint order → error conditions.

### Part D — Appendices (non-normative)
17. Design-rationale pointers (`this.i` nodes); the speculative ideas from §"Thoughts About Comparing".

---

## Cross-reference repair checklist

Moving/renaming sections invalidates `](#slug)` links (GitHub auto-slugs from headings).
Current in-doc anchors that WILL change and must be repaired everywhere they're linked:

- `#conformance`, `#the-render-model-tier-a`, `#equivalence-relation`,
  `#canonical-rasterization-tier-b`, `#svg-profile`, `#error-conditions` — all move to Part C.
- `#entropy-characterization` — **moves out of Conformance into §6** (biggest single migration; every link to it, and the label step's "projection of the characterization", must re-point).
- `#entviz-algorithm`, `#cell-rendering-algorithm` — the algorithm is now Part B and cell-rendering is §13, not a trailing section.
- `#casual-avalanche-v10` — **anchor disappears** (folded into §13); every `[Casual avalanche](#casual-avalanche-v10)` link becomes a pointer to the relevant §13 substep or is dropped.

After the reorg, re-run the anchor audit (used-vs-available slugs) that Phase 1 used;
zero dead links is the gate.

## Reconciliation procedure (the last, non-optional step)

1. Walk `spec-requirements-inventory.md` R001–R092 top to bottom; for each, confirm it
   appears in the reorganized doc **exactly once**, wording unweakened. Check off each.
2. Grep for the four scatter refrains (S1–S4) and confirm each now has one home:
   large-input handling, the "192/160-bit" parenthetical, the "≈2⁹⁶ preimage" claim,
   the "why text not bytes" argument.
3. Anchor audit → zero dead links.
4. Full test suite green (generators intact). `docs/spec-change-log.md` gets an
   append-only entry describing the reorg (do not rewrite history).
5. Do NOT push.
