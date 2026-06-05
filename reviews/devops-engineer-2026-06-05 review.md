# DevOps / CI/CD Review: entviz

**Date:** 2026-06-05
**Effort level:** medium
**Context sources used:** AGENTS.md, README.md, this.i (partial — first 1175 lines), pyproject.toml, uv.lock (header), .gitignore, .github/workflows/ci.yml, .github/workflows/deploy-docs.yml, .github/workflows/release.yml, .github/dependabot.yml, .github/copilot-instructions.md, SECURITY.md, TODO.md, scripts/check_unicode.py, scripts/release.py (partial), src/entviz/app.py, git ls-files

---

## Evidence Inventory

- All three workflow files read in full.
- Dependabot config, pyproject.toml, uv.lock header, .gitignore read in full.
- Source files: app.py read in full; renderer.py, pipeline.py not read (not needed for a DevOps lens).
- No Docker, Helm, Kubernetes, or docker-compose files exist in the repo — this is a pure Python library/CLI, not a deployed service.
- Images were not built or inspected (no Dockerfile).
- Tests were not run (read-only review).
- Platform deployment docs (origin-platform deployment-specs-for-origin.md) not applicable — this is a standalone library repo, not an Origin Platform service.
- actions/checkout SHA `df4cb1c` (v6.0.3) runtime verified: `node24` (confirmed via curl).
- astral-sh/setup-uv SHA `fac544c` (v8.2.0) runtime verified: `node24` (confirmed via curl).

---

## Executive Summary

entviz is a Python library/CLI tool, not a containerized service, so container, Kubernetes, and Flyway categories are not applicable. The CI pipeline is well-structured with SHA-pinned actions on node24 runtimes, a lockfile-enforced test matrix, Dependabot coverage for both GitHub Actions and Python deps, and an inline invisible-Unicode gate. The primary operational gap is the release workflow, which builds and publishes an artifact without first running the test suite — a tag-triggered breakage on a buggy commit produces a released artifact with broken tests. Secondary gaps are the deploy-docs workflow (can deploy to GitHub Pages concurrently with a failing CI run) and the absence of a committed branch-protection ruleset.

---

## Top Findings

Ordered by bang-for-buck (highest operational risk reduction per unit of fix effort, first).

### F1: Release workflow builds and publishes without running tests

- **Severity:** HIGH
- **Confidence:** CONFIRMED
- **Location:** `.github/workflows/release.yml` (entire file)
- **Finding:** The `release` workflow is triggered by a `v*` tag push and immediately runs `uv build` followed by `gh release create`. There is no test job, no `needs:` reference to CI, and no `uv run --locked pytest` step. A tag pushed on a commit that has broken tests (or that CI hasn't finished evaluating yet) produces a published GitHub Release containing a wheel built from untested code.
- **Operational consequence:** A user who installs from PyPI (once wired up) or from a GitHub Release artifact receives a broken build. Even before PyPI is live, the GitHub Release artifact is the canonical delivery mechanism, so the gate is already meaningful.
- **Recommendation:** Add a `test` job to `release.yml` that runs `uv run --locked --python 3.12 pytest` and make the `release` job `needs: test`. This adds ~30 seconds to the release pipeline and guarantees no release artifact escapes without a green test run.

---

### F2: deploy-docs can publish to GitHub Pages while CI is red

- **Severity:** MEDIUM
- **Confidence:** CONFIRMED
- **Location:** `.github/workflows/deploy-docs.yml:13-22`
- **Finding:** `deploy-docs` triggers on `push: branches: [main]` with a `paths:` filter covering `docs/**`, `zensical.toml`, and `.github/workflows/deploy-docs.yml`. It has no `needs:` reference to the `CI` workflow and no `workflow_run` gate. A push to main that modifies `docs/` and simultaneously breaks a Python source file will dispatch both `CI` (which will fail) and `deploy-docs` (which will succeed, deploying the new docs). The deployed documentation can therefore diverge from a passing codebase state.
- **Operational consequence:** The docs site can advance to a state that corresponds to a broken commit, confusing readers and making it harder to correlate a doc change with the library version it describes.
- **Recommendation:** Add a `workflow_run` trigger that gates `deploy-docs` on the `CI` workflow completing successfully on `main`, replacing or supplementing the push trigger. Alternatively, add a `needs: ci` cross-job dependency if the workflows are consolidated. At minimum, scope the `push` trigger more tightly so it only fires on commits where `src/**` has not changed (which is the safe subset where docs-only changes can't have broken the library).

---

### F3: Branch and tag protection not committed as infrastructure-as-code

- **Severity:** MEDIUM
- **Confidence:** CONFIRMED
- **Location:** Repository root (no `rulesets/` directory or committed `.github/ruleset-*.json`)
- **Finding:** No repository ruleset or branch protection rule is committed to the repository. Protection for `main` (require PR, disallow force-push) and tag immutability (prevent tag deletion/update) are, at best, click-configured in the GitHub UI — a state invisible to code review, not auditable via diff, and easily lost during a repo settings reset or fork.
- **Operational consequence:** A force-push or tag retarget to `main` or a `v*` tag is possible without safeguards. Mutable release tags are a supply-chain retargeting vector; a force-push to main erases history and can corrupt CI run associations. For a library where users may pin to a tag, this risk is real.
- **Recommendation:** Export the current branch/tag protection rules to a committed JSON ruleset file in `.github/` (GitHub supports downloadable rulesets via the REST API). Document the one-time "apply ruleset" step in AGENTS.md alongside the "one-time setup" note already in `deploy-docs.yml`.

---

### F4: `release.py` uses `subprocess.run` without `--locked` for `uv build`

- **Severity:** LOW
- **Confidence:** CONFIRMED
- **Location:** `.github/workflows/release.yml:35` (`run: uv build`)
- **Finding:** `ci.yml` explicitly uses `uv run --locked` to enforce that the lockfile is current before running tests. The `release.yml` job runs `uv build` without `--frozen` or `--locked`, which means if `uv.lock` is somehow out of sync with `pyproject.toml` at tag time (e.g., a dependency was added to pyproject.toml but the lockfile was not regenerated before tagging), `uv build` will silently succeed using whatever uv resolves — potentially a different set of transitive dependencies than CI tested.
- **Operational consequence:** The released wheel could be built against different transitive deps than the tested lockfile. Low likelihood given Dependabot keeps the lockfile current, but it closes a subtle reproducibility gap.
- **Recommendation:** Change the build step to `uv build --frozen` (or add a prior `uv sync --locked --frozen` step) so the build fails loudly if the lockfile is stale.

---

### F5: README has only one workflow badge; deploy-docs and release workflows have no visibility

- **Severity:** LOW
- **Confidence:** CONFIRMED
- **Location:** `README.md:3`
- **Finding:** The README carries a single CI badge. The `Deploy Docs` and `Release` workflows have no badges. A contributor who watches the README gets no signal when a docs deploy or a release build fails.
- **Operational consequence:** Failures in deploy-docs or release are invisible at the repo's primary landing page. Silent deploy failures leave the published docs site stale with no notification.
- **Recommendation:** Add two badges after the CI badge: one for `deploy-docs.yml` (workflow name `Deploy Docs`) and one for `release.yml` (workflow name `Release`). The platform convention is lowercase single-word names but those workflows already use multi-word names; either standardize the names or add the badges using the current names.

---

## Additional Patterns Noted

- **No pre-commit hook for Unicode guard**: `ci.yml` runs `check_unicode.py` as a `unicode-guard` job, but there is no `.pre-commit-config.yaml` that runs the same check locally. A developer can push a commit with Trojan-Source characters without seeing a failure until CI. Low risk for a solo-maintainer project; worth adding `pre-commit` if contributors expand.

- **No `.python-version` file**: `pyproject.toml` declares `requires-python = ">=3.10"` and CI enforces the 3.10/3.11/3.12 matrix, but there is no `.python-version` file for `pyenv` users. A developer running `python` or `uv run` without an explicit `--python` flag will pick whatever their shell resolves. `uv`'s virtual environment mitigates this in practice (it pins at sync time), but a one-line `.python-version = 3.12` would clarify the development-baseline interpreter.

- **TODO.md is substantially stale**: `TODO.md` still lists items like "Implement token-to-cell assignment" and "Update bin/entviz.py" that were completed in spec v3/v4/v5. Stale TODO entries create false impressions of incomplete implementation to new contributors. Not a DevOps concern per se, but stale docs degrade onboarding.

- **`release.yml` grants `contents: write` at the workflow level**: The permission is necessary for `gh release create`. It is scoped correctly (only the release workflow, not CI or deploy-docs), but the comment explaining why `contents: write` is needed (artifact upload, not git push) would help a security reviewer understand the scope is intentional. Currently the only comment is in the CI workflow about the same pattern.

- **No `workflow_dispatch` on CI**: The `ci` workflow has no `workflow_dispatch` trigger. This means CI cannot be manually re-triggered on a commit without pushing a new commit or using `gh run rerun`. For a library this is a minor ergonomic gap, not a correctness issue.

- **Dependabot `docker` ecosystem not configured**: The `dependabot.yml` covers `github-actions` and `uv` but not `docker`. This is correct for the current state of the repo (no Dockerfile). If a Dockerfile is added later, Dependabot will need a `docker` ecosystem entry to track base-image updates.

- **`uv.lock` missing from Dependabot `commit-message` configuration**: The Dependabot entries don't set `commit-message: prefix:` or `assignees:`. Minor ergonomic gap — PRs get generic titles.

---

## Residual Unknowns

- **GitHub UI branch/tag protection settings**: Cannot be verified without API access to the live repo. The finding (F3) is based on the absence of a committed ruleset file; the settings may still be configured in the UI.
- **PyPI trusted publisher registration**: `release.yml` notes that PyPI publishing is "not wired up yet." The intended OIDC trusted publisher setup cannot be evaluated until wired.
- **Actual Dependabot PR backlog**: Cannot verify whether open Dependabot PRs are accumulating without accessing the live repository.
- **`astral-sh/setup-uv` node24 runtime**: Verified via `curl` against the pinned SHA (`fac544c`). SHA-pinning means this will not regress until Dependabot bumps it.

---

## Decisions Needed

- **Release gate policy**: Should the release workflow be gated on a separate test job (adding ~30s), or is the expectation that the maintainer verifies CI is green before tagging? The current `scripts/release.py` does not check CI status before pushing a tag. Adding the gate in the workflow is lower friction than adding a CI check to the release script.
- **deploy-docs gating strategy**: `workflow_run` gates add latency (docs don't deploy until CI finishes, ~3 min). If the paths filter (`docs/**` only, no `src/**`) is tight enough, the risk is acceptable. Decide whether to add the gate or document the accepted risk.
- **Branch protection as IaC vs. UI-only**: If the repo remains solo-maintained, UI-only protection is functionally adequate. If it grows contributors, committed rulesets remove a category of "who changed the settings?" ambiguity.

---

## Findings Manifest

```yaml
findings:
  - id: OPS-F1
    persona: devops-engineer
    title: Release workflow builds and publishes without running tests
    severity: HIGH
    confidence: CONFIRMED
    location: .github/workflows/release.yml
    dedupe_key: release-untested
    recommended_disposition: recommend-fix
    rationale: Tag-triggered release job runs uv build and gh release create with no test job or needs:test gate; broken commits can produce published artifacts.
    revisit_condition: null
    fix_effort: small

  - id: OPS-F2
    persona: devops-engineer
    title: deploy-docs deploys to GitHub Pages without gating on CI success
    severity: MEDIUM
    confidence: CONFIRMED
    location: .github/workflows/deploy-docs.yml:13-22
    dedupe_key: deploy-docs-ungated
    recommended_disposition: recommend-fix
    rationale: deploy-docs is an independent workflow with no needs:/workflow_run gate on CI; a docs-touching push to main deploys even when tests are red.
    revisit_condition: null
    fix_effort: small

  - id: OPS-F3
    persona: devops-engineer
    title: Branch and tag protection not committed as infrastructure-as-code
    severity: MEDIUM
    confidence: CONFIRMED
    location: .github/ (no ruleset file)
    dedupe_key: github-branch-protection-missing
    recommended_disposition: recommend-defer
    rationale: No committed ruleset for main branch or v* tags; protection may exist in UI but is not auditable or version-controlled.
    revisit_condition: When the repo gains more than one regular contributor or when PyPI publishing is wired up.
    fix_effort: small

  - id: OPS-F4
    persona: devops-engineer
    title: Release artifact built without enforcing lockfile (no --frozen)
    severity: LOW
    confidence: CONFIRMED
    location: .github/workflows/release.yml:35
    dedupe_key: release-lockfile-unenforced
    recommended_disposition: recommend-fix
    rationale: uv build lacks --frozen; lockfile divergence (rare but possible) produces a wheel with different transitive deps than CI tested.
    revisit_condition: null
    fix_effort: small

  - id: OPS-F5
    persona: devops-engineer
    title: deploy-docs and release workflows have no README badges
    severity: LOW
    confidence: CONFIRMED
    location: README.md:3
    dedupe_key: readme-badges-missing
    recommended_disposition: recommend-defer
    rationale: Only the CI workflow has a status badge; deploy-docs and release failures are invisible at the repo landing page.
    revisit_condition: When the docs site becomes a primary delivery channel or release cadence increases.
    fix_effort: small
```
