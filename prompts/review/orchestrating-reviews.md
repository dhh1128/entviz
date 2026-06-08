# Orchestrating Adversarial Code Reviews — entviz

The orchestrator-side companion to the review-persona prompts in this folder
(`spec-conformance-auditor.md`, `perception-reviewer.md`, `security-hawk.md`,
`devops-engineer.md`, `architect.md`, `testability-hawk.md`,
`maintainability-expert.md`).

Use this when you run the personas as **subagents at a milestone** — spawning
several, collecting their findings, deduplicating across them, and adjudicating
dispositions, with no human in the loop (or with human input deferred). Each
persona prompt describes *its* half of the contract; this doc describes how to
drive the panel and combine the results.

> **About this vendored set.** entviz is a personal, spec-driven, single-author
> open-source project — a Python reference implementation of an algorithm
> defined in [`docs/spec.md`](../../docs/spec.md), on the way to multiple
> certified implementations (`entviz-rs`, `entviz-js`, …) checked against a
> shared conformance corpus. These personas were adapted from a general
> multi-persona panel and **deliberately de-coupled from any specific employer
> platform, methodology, or service architecture.** They assume only what this
> repo actually is: a `uv`-managed Python library + CLI that emits SVG, with a
> `this.i` intent layer, a `docs/spec.md` using RFC 2119 language, and a
> `reviews/` directory of prior reviews. Two lenses are bespoke to entviz —
> **spec-conformance** (is the algorithm provably correct, deterministic, and
> spec-conformant?) and **perception** (does the output actually let a human
> eye discriminate two values?) — because those are the project's two core
> claims and no generic lens covers them.

---

## 1. Spawning a persona

Each prompt has an **Invocation Contract** section defining two modes and a set
of knobs. To run one unattended, set `mode: unattended` and pass whatever else
applies:

| Knob | Meaning |
|---|---|
| `mode` | `interactive` (default) or `unattended`. Unattended = no human answers mid-run; the persona never blocks and never writes `this.i`. |
| `effort` | `medium` (default) or `deep`. |
| `max_findings` | size of the Top Findings list (default 5; spec-conformance and perception default 7, because entviz has many independent channels). |
| `run_label` | goes in the report filename so milestones/concurrent runs don't collide (default: today's date). |
| `prior_dispositions` | findings already adjudicated in earlier runs (accepted-risk / deferred / rebutted). The persona must not re-litigate these — they behave like resolved `this.i` tensions. |

When driving the panel as a **Workflow** (§7), these orchestrator-level knobs
also apply: `model` (run-wide model override), `overrides` (per-persona
`{PREFIX: {effort, model}}`), `verify` (`off`/`default`/`all` pre-merge
refutation pass), and `personas: 'auto'` (git-aware lens scoping).

### Per-persona effort/model tiering

Each persona carries a default effort + model. For entviz: **spec-conformance**
runs **deep on the strongest model** (correctness is the project's headline
claim and its findings can invalidate every previously-rendered entviz);
**perception** runs **deep**; the inherited defect lenses (security, devops,
architect, testability, maintainability) run **medium** unless escalated.
Resolution at fan-out is per-persona `overrides[PREFIX]` → run-wide
`effort`/`model` → persona default.

### Verification pass

Before the exact-key merge, a `Verify` phase adversarially tries to **refute**
high-stakes findings against the repo (each finding needs only itself + the
tree, not the merged view). Scope is gated by `verify`: `off` skips it;
`default` verifies findings from `spec-conformance-auditor`/`security-hawk` or
any `CRITICAL`; `all` verifies every `CRITICAL`/`HIGH` `recommend-fix`. A
**refuted** finding is removed from the queue that flows into merge + synthesis
but is **recorded** in the report's `## Refuted (excluded from findings)`
section, so nothing is silently lost.

For entviz specifically: a spec-conformance finding that claims "the code
violates spec §X" is *verifiable against the spec text and the renderer* and is
exactly the kind of claim the verify pass should challenge — confirm the cited
MUST exists and the code truly diverges before it survives.

---

## 2. Severity is a fix-obligation, not a bug-triage score

All defect-lens personas use one scale: **CRITICAL / HIGH / MEDIUM / LOW**.
There is no per-persona variant, so sort the merged queue directly.

The scale measures **how mandatory the fix is, relative to tolerating the code
as-is** — e.g. before raising a PR, or before declaring the work "good enough":

| Level | Obligation |
|---|---|
| **CRITICAL** | Must be fixed before this code is tolerated as-is. Leaving it is not acceptable. |
| **HIGH** | Default expectation is "fix before moving on." Deferring requires an explicit, recorded decision (tension node / accepted risk). |
| **MEDIUM** | Worth fixing; acceptable to defer with a note. |
| **LOW** | Optional; fix if convenient. |

### Severity vs. recommended_disposition

- **severity** = the finding's intrinsic fix-obligation (a property of the finding).
- **recommended_disposition** = what the reviewer recommends doing *now*, given milestone context (`recommend-fix` / `recommend-defer` / `recommend-accept-risk`).

A CRITICAL almost always maps to `recommend-fix`. **entviz-specific tension:** a
spec-level fix may carry HIGH/CRITICAL severity *and* a large `fix_effort`,
because changing the algorithm invalidates every previously-rendered entviz of
the affected inputs (a comparison-breaking change). A reviewer who recommends
deferring such a finding MUST say so loudly and name the compensating control
(e.g. "gated behind the next `SPEC_VERSION` bump").

---

## 3. The `dedupe_key` convention

Two personas seeing the same issue must produce the **same** key so the
orchestrator can merge them. The key names the *concept*, not the evidence
location (file and line live in the finding's `location` field).

**Grammar:** `<subject>-<adjective>[-<qualifier>]`, all lowercase-kebab.
- **subject** — the most stable identifier available: module / file-stem /
  channel / spec-section / artifact. For repo-global issues, the artifact
  itself (`this-i`, `github-actions`, `spec`, `fingerprint`, `palette`,
  `ellipse`, `color-bar`, `surround`, `nucleus`, `blank-map`, `quartile`,
  `text-channel`).
- **adjective** — the defect class, preferably from the recommended set below.
- **qualifier** — optional condition: `-under-cvd`, `-on-large-input`,
  `-in-grayscale`, `-cross-impl`.

### Recommended adjective set (open — extend as needed)

| Adjective | Means | Usual lens |
|---|---|---|
| `unsafe` | exploitable (SVG/HTML injection, path traversal) | security |
| `grindable` | a sub-channel an attacker can match cheaply (low entropy) | spec-conformance, security |
| `collidable` | two distinct inputs render perceptually indistinguishable | spec-conformance, perception |
| `nondeterministic` | output depends on time/locale/env/order/randomness | spec-conformance, testability |
| `noncompliant` | violates a normative MUST/SHALL in `docs/spec.md` | spec-conformance |
| `divergent` | code and spec (or code and `this.i`) disagree | spec-conformance, maintainability |
| `indiscriminable` | below the JND / collapses under CVD or grayscale | perception |
| `unbounded` | no cap / blows up on pathological input | performance, security |
| `unpinned` | mutable dependency / action / tag | security, devops |
| `unhandled` | sad path / error condition not handled (or not rejected per spec) | testability, spec-conformance |
| `flaky` | nondeterministic / wall-clock-coupled test | testability |
| `untested` | lacks adequate coverage, or structurally resists testing | testability |
| `duplicated` | repeated logic/constant that should be shared | maintainability |
| `coupled` | improper dependency / hidden ordering constraint | architect |
| `missing` | a required thing is absent (doc, this.i node, error condition, test) | any |
| `stale` | comment/docstring/label contradicts current behavior | maintainability |

**If none fits:** use the most natural single adjective and flag it as a
candidate addition in your synthesis. The set is meant to grow.

**Fuzzy-merge safety net:** exact `dedupe_key` matching under-merges, because
independent personas emit different keys for the same issue. The panel handles
this in a **synthesis-stage semantic clustering pass** (judging sameness from
title + location + rationale, conservatively); the canonical entry is the
member with the **most-obligated severity**, with the union of reporters and
locations.

Examples where the convention collapses cross-persona findings to one item:
- `surround-indiscriminable-under-cvd` ← perception + spec-conformance
- `bg-color-grindable` ← spec-conformance + security
- `text-channel-unsafe` (SVG injection) ← security + spec-conformance
- `fingerprint-nondeterministic-cross-impl` ← spec-conformance + testability
- `this-i-missing` ← maintainability (+ any lens citing absent rationale)
- `render-monolith-coupled` ← architect + maintainability

---

## 4. Manifest schema

Every persona emits a fenced-YAML manifest as the final section of its report
(and, in unattended mode, as part of its returned message). Core fields:

| Field | Notes |
|---|---|
| `id` | persona-prefixed, e.g. `SPEC-F1`, `PSY-F2`, `SEC-F3`. |
| `persona` | which reviewer produced it. |
| `title` | short human-readable summary. |
| `severity` | CRITICAL / HIGH / MEDIUM / LOW. |
| `confidence` | CONFIRMED / LIKELY / SPECULATIVE. |
| `location` | `path:line` or `docs/spec.md §section` or channel/artifact. |
| `dedupe_key` | per §3. |
| `recommended_disposition` | recommend-fix / recommend-defer / recommend-accept-risk. |
| `rationale` | one line; enough for the orchestrator to overrule without re-deriving. |
| `revisit_condition` | required when `recommend-defer`. |
| `fix_effort` | small / medium / large. |

The workflow hands each persona's `agent()` call a JSON Schema with exactly
these required fields (plus nullable `revisit_condition`, `tier`,
`cost_category`, `measurement`), so the harness enforces the shape. Emit only
these fields.

---

## 5. Collect → merge → adjudicate

1. **Collect** every persona's returned manifest (the file is durable backup).
2. **Merge** by `dedupe_key`: fold shared-key findings into one item with a
   `reported_by: [...]` list, the **most-obligated** severity, and the union of
   locations. Then run the synthesis-stage semantic clustering pass (§3).
3. **Adjudicate** against milestone policy. A sensible default:
   - any unresolved **CRITICAL** `recommend-fix` → milestone is **blocked**;
   - **HIGH** `recommend-fix` → blocked unless explicitly deferred with a recorded reason;
   - **MEDIUM/LOW** → logged, not blocking.
   Record each decision so it can be passed back as `prior_dispositions` next
   run, and surface intent-level findings to the maintainer for eventual
   recording in `this.i`. The orchestrator does **not** write `this.i`
   autonomously.

---

## 6. The entviz persona roster

| Prefix | File | Lens | Default effort/model |
|---|---|---|---|
| `SPEC` | `spec-conformance-auditor.md` | provable correctness, determinism, spec MUST-conformance, cross-impl parity, cryptographic rigor | deep / strongest |
| `PSY` | `perception-reviewer.md` | human discriminability, CVD, grayscale, JND, visual-CRC, oral readout | deep |
| `SEC` | `security-hawk.md` | implementation security: SVG/HTML injection, path traversal, supply-chain, parser DoS | medium |
| `OPS` | `devops-engineer.md` | CI/CD, release/publish gating, GitHub Pages deploy, action pinning | medium |
| `ARC` | `architect.md` | module decomposition, the spec↔impl boundary, multi-impl readiness | deep |
| `TST` | `testability-hawk.md` | test discipline (TDD), conformance-suite coverage, determinism tests | medium |
| `MNT` | `maintainability-expert.md` | intent boundaries (`this.i`), naming, idiom, dead code, stale docs | medium |

**Default panel:** `SPEC, PSY, TST, MNT, SEC, OPS`. `ARC` is a named opt-in.
(The spec-conformance and perception lenses, plus test discipline and
maintainability, are entviz's primary risk surface; security and devops run on
every panel because the tool emits embeddable SVG and ships releases.)

---

## 7. Running the panel as a Workflow

The vendored workflow script lives at
[`.claude/workflows/review-panel.js`](../../.claude/workflows/review-panel.js)
and is invoked by the `review-board` skill. It is **opt-in** (ask to "run a
review panel" / "run review-board").

It is **self-contained**: `PROMPTS_DIR` defaults to this folder
(`<repo>/prompts/review/`), so the panel does not depend on any external clone.
Targeting is explicit and verified: a preflight agent canonicalizes
`args.target` to the enclosing git repo root and aborts if it isn't a git repo
(or `args.branch` doesn't match). Each persona agent re-confirms the resolved
tree before reviewing.

```
Workflow({ scriptPath: '<repo>/.claude/workflows/review-panel.js',
           args: { target: '<repo abs path>', milestone: 'YYYY-MM-DD review',
                   personas: ['SPEC','PSY','TST','MNT','SEC','OPS'] } })
```

It mirrors the standing subagent rules on this machine: personas fan out **in
chunks of ≤3** (RAM ceiling), each agent prompt carries **`nice -n 19 ionice -c
3`** for heavy shell work, findings merge by `dedupe_key` with **most-obligated
severity winning**, refined by the synthesis-stage semantic clustering pass.

**Persistence.** The run is read-only on source but **writes its output to
`<repo>/reviews/`** (uncommitted, matching this repo's convention): a synthesis
index `review-panel-<milestone>.md` (executive summary, a table of every
finding, a fenced-JSON copy of the merged manifest) plus one
`<persona>-<milestone>.md` narrative report per persona. The workflow does
**not** commit, and does **not** touch `this.i` — promoting intent-level
findings to `this.i` is a deliberate, maintainer-ratified follow-up.

---

*Canonical definitions live here. The persona prompts reference this doc for
severity semantics and the `dedupe_key` convention rather than restating them,
so there is one source of truth.*
