# DevOps / CI/CD Review: entviz

**Date:** 2026-06-08
**Effort level:** medium
**Context sources used:** this.i (first 1146 lines; V4/V5 goals noted), AGENTS.md, README.md, pyproject.toml, uv.lock (header), .gitignore, .github/workflows/ci.yml, .github/workflows/release.yml, .github/workflows/deploy-docs.yml, .github/dependabot.yml, .github/rulesets/ (three files: README.md, protect-release-tags.json, require-review-contributors.json, apply.sh), scripts/release.py, tests/test_figures.py (imports only), scripts/paper_figures.py (imports). Prior review: reviews/devops-engineer-2026-06-05 review.md (read after forming independent view).

---

## Evidence Inventory

- All three workflow files read in full.
- Dependabot config, pyproject.toml, uv.lock header, .gitignore, .gitignore uncommitted diff all read.
- .github/rulesets/ directory and all four files read in full.
- scripts/release.py read in full.
- tests/test_figures.py read in full; scripts/paper_figures.py imports read.
- git ls-files and git diff --name-status run to check tracked-but-ignored files.
- actions/checkout SHA `df4cb1c` (v6.0.3): runtime verified `node24` via curl.
- astral-sh/setup-uv SHA `fac544c`: runtime verified `node24` via curl; confirmed against GitHub tags API — SHA maps to v8.2.0 (not v7.6.0 as stated in the deploy-docs.yml header comment).
- actions/configure-pages SHA `45bfe019` (v6.0.0): runtime verified `node24` via curl.
- actions/upload-pages-artifact SHA `fc324d35` (v5.0.0): runtime verified `composite` (no runtime warning) via curl.
- actions/deploy-pages SHA `cd2ce8fc` (v5.0.0): runtime verified `node24` via curl.
- No containers, Dockerfiles, or service infrastructure exist — a library/CLI, as expected. Not flagged.
- Tests were not run (read-only review).
- Drift check (test_figures.py) confirmed to be in testpaths and have only dev-group deps (segno); it will run in CI.

---

## Executive Summary

The pipeline has improved substantially since the 2026-06-05 review: the two highest-priority prior findings (OPS-F1 release ungated, OPS-F2 deploy-docs ungated) have both been resolved — `release.yml` now runs a full 3×Python matrix test job with `--locked` before building, and `deploy-docs.yml` now gates the deploy job on a `test` job with `--locked`. The branch and tag protection finding (prior OPS-F3) is also resolved: `.github/rulesets/` now carries two committed JSON rulesets with an idempotent `apply.sh`. The remaining operational gaps are minor: a stale version reference in the deploy-docs header comment, the release script's local pre-push test run omitting `--locked`, the absence of a `.python-version` file, and the absence of a `workflow_dispatch` trigger on `ci.yml`. None of these can ship a broken release or deploy bad docs.

---

## Top Findings

Ordered by bang-for-buck (highest operational-risk reduction per unit of fix effort, first).

### F1: deploy-docs.yml header comment names stale setup-uv version (v7.6.0 vs v8.2.0)

- **Severity:** LOW
- **Confidence:** CONFIRMED
- **Location:** `.github/workflows/deploy-docs.yml:11`
- **Finding:** Line 11 reads `# (verified): checkout@v6.0.3, astral-sh/setup-uv@v7.6.0, configure-pages@v6.0.0, upload-pages-artifact@v5.0.0 (composite), deploy-pages@v5.0.0`. The actual pinned SHA on lines 49 and 73 carries inline comment `# v8.2.0`, and GitHub's tags API confirms `fac544c` is v8.2.0 (v7.6.0 is a different SHA: `37802adc94f3`). The header comment is used as a human-readable inventory that a maintainer checks for "all actions at node24"; it is now wrong for setup-uv.
- **Operational consequence:** A maintainer auditing "is setup-uv still at node24?" by reading the header comment sees v7.6.0 and has incorrect information. The actual runtime (verified via curl on the pinned SHA) is node24 regardless, but the comment's value as a quick audit aid is degraded.
- **Recommendation:** Update line 11 to `astral-sh/setup-uv@v8.2.0`. One-character diff.

---

### F2: scripts/release.py local test run omits --locked

- **Severity:** LOW
- **Confidence:** CONFIRMED
- **Location:** `scripts/release.py:128-129`
- **Finding:** `run_tests()` runs `["uv", "run", "pytest"]` without `--locked`. The CI workflow and the release workflow's test job both use `uv run --locked ... pytest`; the local pre-push gate in the release script is inconsistent. If `uv.lock` is stale with respect to `pyproject.toml` at tag time, the local run succeeds (uv resolves fresh), the tag is pushed, and the release workflow's gating test job catches the stale lockfile (because it uses `--locked`). The gate still holds — the release workflow blocks — but the developer gets the failure reported by CI rather than locally.
- **Operational consequence:** A lockfile divergence that would otherwise be caught locally before pushing is deferred to the CI gate, wasting a round trip. No broken release can ship (the release workflow always runs `--locked`), so this is a latency-and-friction issue, not a correctness issue.
- **Recommendation:** Change `run(["uv", "run", "pytest"])` to `run(["uv", "run", "--locked", "pytest"])` in `run_tests()`. The change is a one-word addition; it makes the local pre-push gate consistent with what CI will run.

---

### F3: No .python-version file

- **Severity:** LOW
- **Confidence:** CONFIRMED
- **Location:** Repository root (absent); `.gitignore:99` (line `# pyenv\n.python-version` ignores it by default)
- **Finding:** `pyproject.toml` declares `requires-python = ">=3.10"` and the CI matrix tests 3.10/3.11/3.12, but no `.python-version` file exists to signal the development-baseline interpreter. The `.gitignore` file explicitly ignores `.python-version`, so even if one were created it would not be committed. `uv sync` derives an interpreter at first run and pins it in `.venv/`, but a contributor who starts with `uv run` without a prior `uv sync` picks whatever interpreter uv selects from the floor.
- **Operational consequence:** A new contributor (or a CI environment with an unusual Python) may run tests against a Python version not in the declared set without a clear signal. No breakage is likely at the 3.10 floor, but the development-baseline interpreter is undocumented.
- **Recommendation:** Add a `.python-version` file (e.g. `3.12`) at the repo root and un-ignore it in `.gitignore` (remove the `# pyenv` stanza or add an exception `!.python-version`). This communicates the recommended development interpreter without restricting which Python CI tests against.

---

### F4: ci.yml has no workflow_dispatch trigger

- **Severity:** LOW
- **Confidence:** CONFIRMED
- **Location:** `.github/workflows/ci.yml:1-4`
- **Finding:** The CI workflow triggers only on `push` and `pull_request` to `main`/`master`. There is no `workflow_dispatch` trigger. `deploy-docs.yml` has `workflow_dispatch`, so docs deploys can be manually re-triggered, but CI cannot be re-run on a commit without pushing a new commit (or using `gh run rerun`).
- **Operational consequence:** After a flaky infrastructure failure or after a manual fix that does not warrant a new commit, the maintainer must push an empty commit or use `gh run rerun` to re-run CI. Minor ergonomic friction; no correctness risk.
- **Recommendation:** Add `workflow_dispatch:` to the `on:` block of `ci.yml`. One-line change.

---

### F5: README badges now all present; no new badge gaps

- **Severity:** LOW (noting that prior OPS-F5 is resolved)
- **Confidence:** CONFIRMED (resolution confirmed)
- **Location:** `README.md:3-5`
- **Finding:** The 2026-06-05 review flagged that only the CI badge was present. `README.md` now carries all three badges: CI, Deploy Docs, and Release, each pointing at the correct workflow file. This finding is retained in the manifest as `recommend-accept-risk` to formally record the resolution.
- **Operational consequence:** None; this is a resolved item.
- **Recommendation:** No action required.

---

## Additional Patterns Noted

- **Prior OPS-F1 (release ungated) — RESOLVED.** `release.yml` now has a `test` job (3×Python matrix, `--locked`) that the `release` job declares `needs: test`. Direct edge from publishing to tests confirmed. This was the highest-priority prior finding; it is closed.

- **Prior OPS-F2 (deploy-docs ungated) — RESOLVED.** `deploy-docs.yml` now has a `test` job (`--locked`, Python 3.12) that the `deploy` job declares `needs: test`. Permissions are scoped per-job: the test job holds `contents: read` only; `pages: write` and `id-token: write` are on the deploy job only. Concurrency `group: pages`, `cancel-in-progress: false` prevents racing deploys. This is clean.

- **Prior OPS-F3 (branch/tag protection not IaC) — RESOLVED.** `.github/rulesets/` now contains two committed JSON rulesets (`require-review-contributors.json` and `protect-release-tags.json`) plus an idempotent `apply.sh`. Both rulesets are `enforcement: active`. The README documents the one-time apply step and re-export procedure for UI drift. This is well done.

- **Prior OPS-F4 (uv build without --frozen) — PARTIALLY MITIGATED.** The release workflow's `test` job runs `--locked` on the tagged commit, which asserts lockfile currency before `uv build` runs. The comment in `release.yml:28-31` explains why this is the correct defense (`uv build` has no lockfile flag; the protection is in the gating test). This is architecturally correct, though the explanation is in a comment rather than enforced. No separate `uv sync --locked` step before `uv build` is needed given the test gate already ran `--locked` in the same workflow on the same checkout.

- **Dependabot open PR backlog** — cannot be verified without live repo API access. The `dependabot.yml` configuration is correct: `github-actions` ecosystem groups all action bumps into one PR weekly; `uv` ecosystem keeps `uv.lock` in sync (not `pip`, which would leave the lockfile stale). No configuration gap visible.

- **No CodeQL as a required check** — noted in `.github/rulesets/README.md` as a possible future addition. Not a DevOps finding at current contributor scale.

- **`.gitignore` uncommitted change** — the working tree has a modified `.gitignore` (M in git status) adding `.claude/` re-include rules. This is a pending commit, not a structural gap. No files are tracked that should be ignored (confirmed via `git ls-files | grep -E` check).

- **Generated-asset drift check** — `tests/test_figures.py` is in `testpaths = ["tests"]` and imports only `segno` (in the `dev` group, always installed in CI). It runs as part of the gating suite. Drift between committed figures and the live renderer will fail CI before reaching a release. This is working correctly.

---

## Residual Unknowns

- **Live ruleset application state** — whether the committed JSON rulesets have been applied to the live GitHub repo (i.e., `apply.sh` was run since the files were committed) cannot be verified without API access. The README states "the committed JSON matches the live rulesets," but drift over time is undetectable from the tree.
- **Dependabot PR backlog** — open PRs cannot be enumerated without live API access. The configuration is correct; whether updates are being merged is unknown.
- **PyPI Trusted Publishing** — not wired up; noted in `release.yml` header comment. OIDC setup cannot be evaluated until wired. When wired, `id-token: write` should be scoped to the publish job, not top-level.

---

## Decisions Needed

- **`.python-version` committed or not?** `.gitignore` currently silences `.python-version`. If you want it committed (for contributor UX), remove it from the ignore list. If you prefer each contributor's local Python to be unconstrained, leave the ignore and accept the undocumented baseline.

- **`workflow_dispatch` on CI?** Low-value change but zero-risk. Worth a one-liner if manual re-runs are wanted.

---

## Findings Manifest

```yaml
findings:
  - id: OPS-F1
    persona: devops-engineer
    title: deploy-docs.yml header comment names stale setup-uv version (v7.6.0 vs v8.2.0)
    severity: LOW
    confidence: CONFIRMED
    location: .github/workflows/deploy-docs.yml:11
    dedupe_key: deploy-docs-stale-comment
    recommended_disposition: recommend-fix
    rationale: Header comment says setup-uv@v7.6.0 but pinned SHA is v8.2.0 (confirmed via GitHub tags API); human audit aid is wrong.
    revisit_condition: null
    fix_effort: small

  - id: OPS-F2
    persona: devops-engineer
    title: release.py local test run omits --locked flag
    severity: LOW
    confidence: CONFIRMED
    location: scripts/release.py:129
    dedupe_key: release-script-unlocked-tests
    recommended_disposition: recommend-fix
    rationale: Local pre-push pytest in release.py omits --locked; lockfile divergence caught by CI gate but not locally, wasting a round trip.
    revisit_condition: null
    fix_effort: small

  - id: OPS-F3
    persona: devops-engineer
    title: No .python-version file to document development baseline interpreter
    severity: LOW
    confidence: CONFIRMED
    location: repository root (.python-version absent; .gitignore:99 ignores it)
    dedupe_key: python-version-missing
    recommended_disposition: recommend-defer
    rationale: No .python-version file; development baseline is undocumented, though uv.lock + CI matrix provide strong practical coverage.
    revisit_condition: When the contributor base expands beyond the solo maintainer.
    fix_effort: small

  - id: OPS-F4
    persona: devops-engineer
    title: ci.yml has no workflow_dispatch trigger
    severity: LOW
    confidence: CONFIRMED
    location: .github/workflows/ci.yml:3-4
    dedupe_key: ci-yml-missing-dispatch
    recommended_disposition: recommend-defer
    rationale: CI cannot be manually re-triggered without pushing a new commit; minor ergonomic gap, no correctness risk.
    revisit_condition: When manual re-runs become a recurring need.
    fix_effort: small

  - id: OPS-F5
    persona: devops-engineer
    title: README badges complete (all three workflows covered) — prior OPS-F5 resolved
    severity: LOW
    confidence: CONFIRMED
    location: README.md:3-5
    dedupe_key: readme-badges-missing
    recommended_disposition: recommend-accept-risk
    rationale: Prior finding OPS-F5 (missing deploy-docs and release badges) is resolved; all three badges present with correct workflow references.
    revisit_condition: null
    fix_effort: small
```
