# Spec editorial pass — scoping & handoff

**Purpose.** Seed a *fresh* session to run a careful editorial pass over
`docs/spec.md` (694 lines, currently spec **v15**). This doc is the plan; execute
from a clean context window. Written 2026-07-11 at the end of the v15
implementation session (context there was saturated — hence the handoff).

**Goal.** Copyedit + tighten the spec: typos, dead cross-refs, redundancy,
terminology consistency, ambiguity, correct RFC-2119 usage, and (as a separate,
later phase) structural de-frankensteining. **Without shifting any
implementation's conformance posture in either direction.**

---

## 0. The prime directive (read this first — it is not obvious)

**The test suite and conformance corpus CANNOT catch a spec-*text* meaning change.**
Editing `spec.md` touches no code, so `python -m compliance.generate` and the full
test suite produce byte-identical output *even if you silently changed what a
requirement means*. The green suite only protects you from accidentally editing a
*generator*. Therefore:

- **The reference implementation (`src/entviz/`) + the corpus are the ground
  truth for behavior.** A normative sentence is "correct" iff it still accurately
  describes what the impls actually do. Verifying a normative edit = **reading the
  impl**, not running a test.
- The five impls (Python ref + entviz-rs/-js/-java/-go, all on `main`, all v15,
  all green as of 2026-07-11) are locked. The spec must keep describing *them*.
  Do NOT change the spec to describe some cleaner behavior the impls don't have.

**Anchors of truth, in priority order:** reference impl source → conformance
corpus (`compliance/corpus/*/model.json` + `golden.*`) → the test suite →
`this.i` (design rationale, keyed nodes like `v15pfxlbl`, `v14lbl`, `h4shtext`,
`s5hs1ze`, …) → `docs/spec-change-log.md`.

---

## 1. Phase 0 — Inventory & baseline (do first, cheap, high-leverage)

Deliverables before touching a single word:

1. **Requirements inventory.** Extract every `MUST / MUST NOT / SHALL / SHALL NOT
   / SHOULD / SHOULD NOT / REQUIRED / RECOMMENDED / MAY / OPTIONAL` sentence into a
   numbered checklist (`reviews/spec-requirements-inventory.md`). Current counts:
   MUST 66, MUST NOT 22, MAY 15, SHOULD 5, OPTIONAL 4, REQUIRED 3, SHOULD NOT 1,
   SHALL NOT 1, SHALL 1, RECOMMENDED 1. For each: `[id | verbatim text | section |
   normative? | impl location that realizes it | test/corpus that covers it |
   notes]`. This one artifact does **triple duty**: (a) RFC-2119 audit target,
   (b) the invariant any reorganization must preserve — *every requirement present
   exactly once, unweakened*, (c) a coverage map exposing requirements that are
   asserted-but-untested (a real finding) and spec claims that don't match the
   impl (a spec bug — higher value than any typo).
2. **Green baseline.** Confirm all 5 repos' CI green and `git status` clean-ish, so
   any later drift is attributable. (As of handoff: all green; `entviz` has one
   unrelated uncommitted edit, `docs/entviz-paper.md`.)

---

## 2. Phase 1 — Safe copyedit (low risk, high value)

Scope: typos, dead/oscillating cross-references, redundancy, terminology
consistency, ambiguity, the figure-version mess, and the RFC-2119 audit.

**Risk tiering every proposed edit:**
- **Non-normative prose** (intros, rationale, examples that aren't
  conformance-relevant, figure captions): edit freely.
- **Normative-adjacent** (a sentence containing or bordering a MUST/SHALL/algorithm
  step): allowed only with a **semantic-diff review** — show old→new and argue "same
  requirement" against the impl. When in doubt, leave it and log it as a finding.
- **RFC-2119 keyword changes are NEVER copyedits — they are semantic decisions.**
  The spec's notation section says lowercase "must" carries *no* normative force,
  so `must → MUST` (or the reverse) *changes an implementation's obligations*. Each
  such change requires explicit human sign-off + an impl cross-check, and must
  never ride along in a batch of typo fixes.

**Locked style decisions (make once, up front):**
- **MUST vs SHALL:** RFC 2119 makes them synonyms and the notation section already
  equates them, so normalization is *safe*. **Recommendation: retire SHALL —
  normalize the lone `SHALL`/`SHALL NOT` to `MUST`/`MUST NOT`** (currently 1 each
  vs 66 MUST). Mechanical, safe, removes an inconsistency.
- Pick a single spelling of recurring terms (audit for drift: "entviz" vs "glyph"
  vs "mark"; "surround" vs "border"; "nucleus"; "color bar"; "fingerprint"; "cell"
  vs "box"; American spelling per house style — color/behavior/normalize).

**The figure-version bug (already spotted):** "A v7 entviz" internal caption vs
"Figure 1. A representative v6 entviz" in a v15 spec. This is only *partly* prose:
the internal caption is baked into the generated SVG by `scripts/figlib.py` /
`scripts/spec_figures.py` / `scripts/paper_figures.py` (hardcoded version string),
the "Figure 1" line is spec prose. Fixing spans generator code + prose + a figure
regen. **Hunt ALL hardcoded version/annotation strings in the generators**, not
just this one — AGENTS.md §4 step 6 flags this class ("only a human catches a
caption whose *meaning* went stale"). After any generator edit, regenerate figures
(`PYTHONPATH=src ... scripts/spec_figures.py` + `paper_figures.py`) and the
gallery/social-card per AGENTS.md §4, and expect `tests/test_figures.py` to gate.

---

## 3. Phase 2 — Reorganization (high risk — do NOT bundle with Phase 1)

The "frankenstein from 15 AI passes" restructuring is effectively a **near-rewrite**
and is where requirements silently get dropped or duplicated. Rules:
- Drive it from a **human-authored target outline** (Daniel's editorial spine). An
  AI reorganizing autonomously is *how the frankenstein happened*; the AI executes
  against the outline, it does not invent the structure.
- Treat the Phase-0 requirements inventory as a **hard invariant**: after moving
  anything, reconcile the new document against the inventory line-by-line — every
  requirement present *exactly once*, wording unweakened, cross-refs repaired.
- Consider whether full reorg is worth the risk vs. targeted section-level cleanup.
  A defensible middle path: fix *local* scatter (consolidate a topic that's split
  across 3 places) without a global re-architecture.

---

## 4. Review method (adapt the papers/ editorial-panel pattern)

Read-only, **propose-don't-apply**, triaged findings — like `editorial-panel`, but
with spec-specific lenses and one your paper panel lacks:

- **normative-language** — RFC-2119 correctness (missing where a real obligation
  exists; present where it's only descriptive; keyword consistency).
- **conformance-safety / drift adjudicator** — THE gatekeeper. Every proposed edit
  tagged {non-normative | normative-adjacent | rfc2119-semantic} + "meaning
  preserved? (argued against impl)". Nothing normative-adjacent ships without its
  ruling.
- **clarity / ambiguity** — can two conforming impls read this sentence
  differently? (the highest-value spec defect.)
- **terminology consistency** — one term per concept, per the glossary you build.
- **copyedit / cruft** — typos, dead refs, redundancy, stale version strings.
- **structure / exposition** — scatter, ordering, forward-references (Phase-2 fuel;
  in Phase 1 it only *reports*, doesn't move things).

**Finding schema:** `[lens | location (line/section) | issue | proposed edit |
risk tier | disposition]`. Output to `reviews/` (uncommitted), one file per lens +
a synthesis, mirroring how the panel skills already write there. Daniel adjudicates
the tiered queue; apply safe → risky, RFC-2119 items last and individually.

---

## 5. Known issues already spotted (seed the finder)

- Figure version inconsistency v6/v7 in a v15 spec (§2 above) — and the generic
  "hunt all stale hardcoded version strings" it implies.
- Spec is a patchwork of 15 successive AI edit passes → scattered logic, likely
  duplicated/near-duplicated rationale, and topics split across distant sections
  (Phase 2).
- Single stray `SHALL`/`SHALL NOT` amid 66 `MUST` (Phase 1 normalize).
- Out of scope but adjacent: `docs/entviz-paper.md` still references the old
  `fingerprint of` marker and pre-v14 `hex(200)` label format (it's a version
  behind and is a separately-curated artifact — Daniel's deferred paper pass, NOT
  part of the spec editorial).

---

## 6. File map

- `docs/spec.md` — the target (694 lines, v15).
- `docs/spec-change-log.md` — per-version history (do not rewrite; append only).
- `src/entviz/{pipeline,characterize,entropy}.py` — reference impl = behavior truth.
- `compliance/corpus/*/{model.json,golden.svg,golden.png}` — conformance ground truth.
- `this.i` — design rationale, `[[keyed]]` nodes; cite when a requirement's *why*
  matters. Per CLAUDE.md, update `this.i` for any significant editorial *decision*.
- `scripts/{figlib,spec_figures,paper_figures,social_card,gallery}.py` — generators;
  home of the hardcoded figure/version strings.
- `AGENTS.md` §4 — mandatory regen rules (figures/gallery/social-card) + the
  stale-caption warning.
- `../papers/.claude/…/editorial-panel` (and repo skills `editorial-panel`,
  `review-board`) — the pattern to adapt; not directly reusable (tuned for prose,
  and neither has the conformance-safety lens).

---

## 7. Start-here checklist for the fresh session

1. Read this doc, then `docs/spec.md` end-to-end once (no edits).
2. Build `reviews/spec-requirements-inventory.md` (Phase 0).
3. Confirm the green baseline across the 5 repos.
4. Get Daniel's ruling on the two up-front style decisions (retire SHALL; term
   glossary) and whether Phase 2 reorg is in-scope now or later.
5. Run the multi-lens review → triaged findings in `reviews/`.
6. Apply Phase-1 safe edits (non-normative first), semantic-diff every
   normative-adjacent one, RFC-2119 keyword changes last and individually signed
   off. Regenerate figures/gallery if any generator string changed; keep CI green.
7. Do NOT push; Daniel reviews. (Solo-repo rule: ASK before committing/pushing.)
