# Repository rulesets (infrastructure-as-code)

Branch and tag protection for this repo lives here as version-controlled JSON
so it is **auditable and reviewable** rather than existing only in the GitHub
UI (closes review finding OPS-F3). Each `<name>.json` is a ruleset payload in
the shape accepted by the [rulesets REST API][api].

## Files

- **`require-review-contributors.json`** — protects the default branch (`main`):
  blocks deletion and force-pushes (`non_fast_forward`), requires a pull request
  with 1 approving review (stale reviews dismissed on push, last-push approval
  required), and requires the CI checks `unicode-guard` and `test (3.10|3.11|3.12)`
  to pass with the strict (up-to-date-branch) policy. The repository **Write**
  role (`bypass_actors`, role id 2) may bypass, so the solo maintainer can still
  push directly — tighten this when more contributors join.
- **`protect-release-tags.json`** — protects release tags (`refs/tags/v*`,
  consumed by `release.yml`) from deletion and from being moved
  (`non_fast_forward`). Creating a *new* `v*` tag (the normal release flow) is
  unaffected; only deleting or force-updating an existing one is blocked. Same
  Write-role bypass.

## Applying / updating

The committed JSON is the source of truth. After editing a file (or to
bootstrap a fresh clone of the protection), run:

```
./.github/rulesets/apply.sh            # defaults to dhh1128/entviz
```

It is idempotent — it updates the existing ruleset (matched by `name`) or
creates it if absent. Requires an authenticated `gh` and `jq`.

> As of this commit the committed JSON matches the live rulesets (both have
> been applied), so no apply is needed right now; the script is for future
> changes and fresh setups.

## Keeping in sync (detecting drift)

If protection is changed in the UI, re-export so the repo reflects reality:

```
gh api repos/dhh1128/entviz/rulesets/<id> \
  | jq '{name, target, enforcement, bypass_actors, conditions, rules}' \
  > .github/rulesets/<name>.json
```

then commit the diff. `gh api repos/dhh1128/entviz/rulesets` lists ids/names.

## Possible future additions

- **CodeQL as a required check.** `Analyze (actions)` / `Analyze (python)` run
  on PRs but are not blocking. Add them to `required_status_checks` if you want
  security analysis to gate merges.
- **Code-owner review.** `require_code_owner_review` is off and there is no
  `CODEOWNERS` file; add both if review routing becomes useful.

[api]: https://docs.github.com/en/rest/repos/rules
