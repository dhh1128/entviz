---
name: review-board
description: >-
  Run entviz's multi-persona adversarial review panel over this repo. Spawns a
  vendored Workflow that fans out specialized reviewers — spec-conformance &
  determinism (correctness/cryptographic rigor), perception/psychophysics
  (human discriminability/CVD/grayscale), testability, maintainability,
  security, and devops (architect on request) — adversarially refutes
  high-stakes findings, dedupes by concept, and writes per-persona + synthesis
  reports to reviews/. Use when the user says "run the review board", "run a
  review panel on entviz", "review the code with the personas", or wants a
  broad multi-lens code review at a milestone. Read-only on source; writes only
  to reviews/ (uncommitted). Opt-in / explicit invocation only — it can spawn
  many subagents.
user-invocable: true
allowed-tools: Bash, Read, Workflow
---

# /review-board — entviz multi-persona adversarial review panel

Runs entviz's own vendored review panel: a deterministic `Workflow` that spawns
one specialized reviewer per persona, verifies the high-stakes findings, dedupes
across personas, and persists the reports to `reviews/`.

This is **entviz-specific tooling** — self-contained in this repo, with no
dependency on any external prompt clone. The persona prompts live in
[`prompts/review/`](../../../prompts/review/) and the workflow script in
[`.claude/workflows/review-panel.js`](../../workflows/review-panel.js). The
panel reads source **read-only** and writes its output to `reviews/`
(uncommitted); it never commits, and never touches `this.i`.

## When to run

At a milestone, before a release, or after a substantial change to the renderer,
the spec, the fingerprint/color/layout code, or the conformance suite. It is
**opt-in**: only run it when the user explicitly asks for it (it can spawn a
dozen-plus subagents and is token-heavy).

## How to run

1. **Resolve the target.** This skill always reviews **this repo**. Capture the
   repo root and today's date from a trustworthy shell (the session cwd), so the
   workflow targets the right tree and stamps the milestone:
   ```bash
   git rev-parse --show-toplevel
   git rev-parse --abbrev-ref HEAD
   date +%F
   ```

2. **Pick the persona set.** Default panel (omit `personas`): `SPEC, PSY, TST,
   MNT, SEC, OPS`. Add the architect lens by passing
   `personas: ['SPEC','PSY','TST','MNT','SEC','OPS','ARC']`, or pass
   `personas: 'auto'` to let a git-aware Scope phase choose lenses from the diff
   and skip ones a recent review already covers. The user may also name a
   subset (e.g. "just spec-conformance and perception" →
   `personas: ['SPEC','PSY']`).

3. **Invoke the Workflow** with the resolved absolute repo root as `target` and
   a dated milestone label. Example:
   ```
   Workflow({
     scriptPath: '<repo-root>/.claude/workflows/review-panel.js',
     args: {
       target: '<repo-root>',                 // absolute path from step 1
       milestone: '<YYYY-MM-DD> review',       // from `date +%F`
       // personas: ['SPEC','PSY','TST','MNT','SEC','OPS'],  // omit for the default six
       // verify: 'default',  // 'off' | 'default' | 'all' — adversarial refutation of high-stakes findings
     }
   })
   ```
   The Workflow returns immediately with a task id and notifies you on
   completion; watch live progress with `/workflows`.

4. **Relay the result.** When it completes, read the synthesis report it wrote
   (`reviews/review-panel-<milestone>.md`) and summarize for the user: the
   posture, the CRITICAL/HIGH `recommend-fix` blockers, anything the verify pass
   refuted, and the per-persona report filenames. The reports are uncommitted —
   leave committing to the user.

## Knobs (all optional)

| Arg | Default | Meaning |
|---|---|---|
| `target` | — (required) | Absolute repo root (or relative + `baseDir`). |
| `milestone` | `"review"` | Run label; goes in every report filename. |
| `personas` | the default six | Array of prefixes/names, or `'auto'` for git-aware scoping. |
| `verify` | `'default'` | `'off'` / `'default'` (spec-conformance, security, or any CRITICAL) / `'all'` (every CRITICAL+HIGH recommend-fix). |
| `effort` | per-persona | Run-wide override (`'medium'`/`'deep'`). |
| `model` | per-persona | Run-wide model override. |
| `overrides` | — | Per-persona `{PREFIX: {effort, model}}`. |
| `concurrency` | `3` | Personas fan out in chunks of this many (RAM ceiling). |

## Personas

| Prefix | Lens | Default |
|---|---|---|
| `SPEC` | Spec-conformance & determinism — provable correctness, cryptographic rigor, cross-impl parity | deep / strongest model |
| `PSY` | Perception & psychophysics — discriminability, CVD, grayscale, JND, oral readout | deep |
| `SEC` | Implementation security — SVG/HTML injection, path traversal, supply-chain, parser DoS | medium |
| `OPS` | DevOps — CI/CD, release/publish gating, Pages deploy, action pinning | medium |
| `ARC` | Architecture — module decomposition, the spec↔impl boundary, multi-impl readiness (opt-in) | deep |
| `TST` | Testability — TDD discipline, conformance-suite coverage, determinism tests | medium |
| `MNT` | Maintainability — intent boundaries (`this.i`), naming, idiom, dead code, stale docs | medium |

See [`prompts/review/orchestrating-reviews.md`](../../../prompts/review/orchestrating-reviews.md)
for the severity scale, the `dedupe_key` convention, and the manifest schema the
personas share.
