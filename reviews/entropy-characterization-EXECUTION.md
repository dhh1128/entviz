# Entropy characterization — EXECUTION runbook (autonomous run)

_Started 2026-07-07. Orchestrator: Claude (Opus 4.8). User away; full authority granted (see below)._

This runbook is the durable source of truth for executing the entropy
characterization redesign across 5 repos + spec + docs. It is written so that a
fresh session can resume from it if context is lost. **Design is fully
specified in `reviews/entropy-characterization-redesign.md`** (the DESIGN doc) —
this file is the operational plan.

## Authority granted by the user (2026-07-07, before going away)

1. **Push:** commit AND push directly to `main` in all repos without asking
   (lifts the standing "ask before commit/push" rule for THIS run). Commits MUST
   be `-s`/signed-off, **no squash**. entviz-js is the exception → see #5.
2. **Release scope:** **land on main only.** NO version tags, NO registry
   publishing (PyPI/npm/crates/Maven/Go). Code + spec + docs only.
3. **Corpus:** **add the new structured fields to the shared conformance
   corpus** (`compliance/corpus/*/model.json`), so all 5 impls must emit them
   identically. The checker is STRICT (rejects extra/missing keys), so corpus +
   all impls move together.
4. **Dev docs:** one canonical integration guide in **entviz `docs/`** + each
   port's README links to it with a language-specific snippet.
5. **Pre-existing work:** every repo had uncommitted work predating this task.
   User said **commit it first as a baseline** (its own signed-off commit),
   then build the characterization change on top.
6. **entviz-js branch:** do the JS/React work **on `feat/disclosure-lifecycle-ux`**
   and push there (NOT main). All other repos → main.

## Non-negotiable invariants

- **MODEL-ONLY + byte-identical labels.** The fingerprint hash input, all
  rendered pixels, and every label STRING stay byte-identical. New fields are
  ADDITIVE to `model.json`. Goldens (golden.svg/png) MUST NOT change content.
- **`size_bits` is REPORTING-ONLY.** It MUST NOT be wired into the >512-bit
  truncation trigger, which keeps using `_core_byte_length` =
  `len(core) × bits_per_char // 8`, unchanged. They diverge for 65–86-char text
  cores; re-pointing moves goldens. (DESIGN doc, Wrinkle 2.)
- **Strict checker:** `compliance/runner.py::_diff()` rejects extra/unknown AND
  missing keys. So the moment the corpus gains fields, every impl must emit them
  or fail. Land entviz (with regen'd corpus) FIRST, then ports back-to-back to
  minimize the red-CI window.

## The model being added (see DESIGN doc for full normative wording)

Additive `model.json` fields (names TBD-final at Stage 0, keep consistent across
all 5 impls):
- `encoding` : string — the alphabet name (already known internally).
- `scheme` : string|null — recognizer/namespace; null = bare encoding.
- `role` : string|null — CLOSED enum `key|signature|digest|address|identifier`
  or null. Asserted ONLY from the GENERIC recognizer (did:key→identifier NOT
  key; did:pkh→identifier NOT address; urn:isbn→identifier NOT book).
- `qualifiers` : object — network/variant/algorithm/version facets.
- `size_basis` : `"decoded"|"utf8"` — scheme-driven (did/urn/fallback→utf8),
  NOT inferred from alphabet or content shape.
- `size_bits` : int — value size, multiple of 8, from core only. Two branches
  per `size_basis` (DESIGN Resolution A). Reporting-only.
- `parts` : array of `{text, bind}` where `bind ∈ "none"|"fold"|"core"` —
  replaces the prefix + prefix_semantic overload. `bind` is a property of the
  PART at the recognizer's granularity (DESIGN Wrinkle 4).

`entropyType` (tick 3ek3) = `scheme ?? encoding` — a derived convenience.

## Key mechanics (from recon, /tmp/entviz-recon.md — VERIFY before relying)

- **Regen corpus:** `PYTHONPATH=src:. python -m compliance.generate` (regens
  input.json/model.json/golden.svg/golden.png in one pass).
- **model.json assembly:** `compliance/model.py` (`_labels()` at ~303–318 reads
  labels BACK from the rendered SVG `data-channel` groups — labels are NOT
  built from Parsed here). New characterization fields must be added to the
  model extractor/serializer AND surfaced from the pipeline so they can be
  captured. Confirm exact injection point at Stage 0.
- **Parsed consumers:** `pipeline.py` reads `.type`(→label top ~210,218–223),
  `.prefix`(~212,260 + fold), `.suffix`(~213), `.prefix_semantic`(~214,260
  gate), `.alphabet`(tokenize ~211,225), `.core`(~209,225,260).
- **spec_version:** `src/entviz/__init__.py:22`, currently `"v12"` — aligned
  across all 5 repos. Bump consistently if the model change warrants (decide at
  Stage 0; additive → likely a v-bump since model.json schema changes).
- **Conformance per port:** rs = in-process cargo test referencing
  `../entviz/compliance/corpus`; go/java/js = external CLI driven by
  `PYTHONPATH=src:. python -m compliance.runner --impl-cmd <cmd>` against the
  entviz corpus. **Ports read the entviz corpus** → regen there flows to them.
- **React "clumsy wrestling":** entviz-js `packages/core/src/describe.ts` +
  `entviz.ts` (classifyInput / entropyType vs typeName) and `packages/react/`.
  The fix: consume structured fields instead of string-parsing the label.

## Staged plan + progress ledger

Status legend: [ ] todo  [~] in progress  [x] done

### Stage 0 — spec + Python reference (CRITICAL PATH; everything depends on it)
- [ ] Verify baseline Python tests green → commit entviz pre-existing baseline
      (EXCLUDE this.i + reviews/ — those are the characterization change).
- [ ] spec.md: add normative Characterization model + Resolution A/B wording +
      the two principles (role-from-generic, bind-at-part-granularity) + the
      size_bits≠truncation-basis warning. Bump spec version if decided.
- [ ] Python: introduce structured characterization (extend/replace Parsed;
      keep back-compat where cheap). Compute size_basis, size_bits, parts+bind,
      scheme, role, qualifiers. DO NOT touch the truncation trigger.
- [ ] Emit the new fields into model.json (additive). Keep labels byte-identical.
- [ ] Regenerate corpus (`python -m compliance.generate`). Confirm goldens
      unchanged EXCEPT model.json gaining fields (git diff: golden.svg/png should
      be clean; if any golden pixel changed, STOP — invariant violated).
- [ ] Update/extend Python tests (TDD): assert the new fields per the 17
      worked cases in the DESIGN doc. Full suite green.
- [ ] this.i: expand ch4rmod3l → ch4rmod3l + s1zeb1ts, status drafted→done.
- [ ] Commit (characterization change, incl. this.i + reviews/) + push entviz main.

### Stage 1 — ports (fan out ≤2 general-purpose at a time; each pinned to its repo)
For EACH of rs / go / java / js:
- [ ] Commit that repo's pre-existing baseline (its own signed-off commit).
- [ ] Mirror the structured fields in the parse/characterization type.
- [ ] Emit the new model.json fields identically to the entviz reference.
- [ ] Re-certify against the (pushed) entviz corpus — Tier A+B green.
- [ ] Bump spec_version string if entviz did.
- [ ] Commit + push (main for rs/go/java; feat/disclosure-lifecycle-ux for js).
- entviz-rs: [ ]   entviz-go: [ ]   entviz-java: [ ]   entviz-js: [ ]
- **entviz-js also:** reconcile classifyInput entropyType/typeName into the
  canonical model; FIX the React component to consume structured fields (pills
  from scheme/role/qualifiers) instead of parsing the label string.

### Stage 2 — dev docs (can run in parallel with Stage 1 once Stage 0 pushed)
- [ ] entviz `docs/`: developer API / integration guide (tick 7srp): the
      characterization model, entropyType, per-language quickstart snippets,
      conformance tiers, comparison guidance.
- [ ] Each port README: link to the guide + a language-specific snippet.
- [ ] Commit + push (docs in entviz main; README edits with each port's commit).

### Closeout
- [ ] All 5 repos green + pushed. Update ticks 6shr (done), 3ek3 (done via
      Stage 2), 7srp (done). 
- [ ] confer notify the user with a summary + anything needing review.

## Subagent discipline (from ~/.claude/CLAUDE.md)
- ≤2 general-purpose agents concurrent (3–4 total only if extras are read-only).
- Every subagent that builds/tests/greps: run under `nice -n 19` (+ `ionice -c 3`
  for I/O-heavy). State it explicitly in the prompt.
- Each port subagent OWNS exactly one repo (disjoint file sets → no isolation
  needed since they're separate repos). Pin the repo path as a hard rule.
- Long agents: stream status to `/tmp/subagent-<repo>-status.log`, hit named
  milestones, check `/tmp/subagent-<repo>-inbox.md` at each milestone.
- Give each port subagent: this runbook path, the DESIGN doc path, the entviz
  corpus path, and the exact conformance command. Require byte-identical goldens.
