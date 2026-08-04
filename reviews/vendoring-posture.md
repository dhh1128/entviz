# The paper vendoring posture, and what is still undecided

**Compiled:** 2026-08-03; trimmed 2026-08-04 once the spec half shipped. Scope: `entviz` (python reference), `entviz-js`, `entviz-go`,
`entviz-java`, `entviz-rs`, `entviz-adversarial`, and the published copies in `papers`.
Sources: each repo's `tick` ledger, `entviz-js/CLAUDE-SECURITY-20260731-170021/`,
`reviews/paper-todo.md`, `reviews/pk-feedback-disposition.md`, `papers/.vendored-sources.yml`.

Everything below marked *verified* was checked by running code or reading the file, not
inferred from a report.

---

## Status

**Q-EXTR (is a bech32 HRP identity-bearing?) is RESOLVED and shipped.** The answer was yes,
bound by prefix-fold; the reasoning is in `this.i:hrpb1nd`, the normative text in
`docs/spec.md` under *How identity material is bound*, and the release notes in
`docs/spec-change-log.md` under v16. Cross-repo sequencing now lives in
[`RELEASE-TRAIN.md`](RELEASE-TRAIN.md), which supersedes the per-item tables that used to sit
in this file. What remains here is the vendoring analysis, which is not yet decided.

---

### Q-8VQC — What vendoring model do we want for the paper?

Today: `docs/entviz-paper.md` in this repo is canonical; `papers/amp-diff.md` is a hand-copied
derivative; `papers/.vendored-sources.yml` pins the upstream sha256 and `papers/scripts/check_drift.py`
compares the current upstream against that pin.

**The guard reports "12 in sync" right now, and the two files still differ in content.**
Verified by diffing them:

- Reference **[8]** upstream cites the spec as *"Algorithm Specification (draft)"* at a
  `github.com/dhh1128/entviz/blob/main/docs/spec.md` URL; the published copy cites
  *"Version 15"* at `https://dhh1128.github.io/entviz/spec`. The published one is better and
  it never flowed back.
- The reference **numbering diverges**. The published copy inserts the m-glance companion at
  [35] and shifts [35]–[39] down by one; upstream cites the companion as [40]. `papers`'
  `fix_ref_nums.py` does this, and CI enforces it there.
- Figure paths differ (`assets/paper/*.svg` upstream vs `assets/amp-diff/*.png` published) —
  mechanical and expected.

So the drift guard is structurally one-directional: it hashes the *upstream* file, so a local
edit in `papers` is invisible to it by construction. Three further holes:

- It runs only inside `publish.py`'s preflight (`papers/scripts/publish.py:183`), not in
  `papers/.github/workflows/ci.yml`.
- Even if it ran in CI it would report `skip-upstream`, because `../entviz` is not checked out
  in the Actions runner.
- Nothing on the entviz side notices when `docs/entviz-paper.md` changes. Commit `3707031`
  (Jul 31, the Paul Knowles response) had to be re-vendored by hand; next time nothing will
  say so.

Options:

1. **Generate, don't copy.** Make `papers/amp-diff.md` a build artifact: a script reads
   upstream, strips the title block, prepends the frontmatter, rewrites figure paths, runs
   `fix_ref_nums.py`, and writes the file. CI regenerates and fails on any diff. Reverse drift
   becomes impossible; the [8] citation gets fixed by fixing it upstream. Cost: one script,
   plus deciding where the frontmatter lives.
2. **Two-way pin.** Add a `local_sha256` to the ledger and check both directions, plus an
   entviz-side CI check that fails when the paper changes without a matching re-pin. Keeps the
   hand-edit workflow; catches drift after the fact instead of preventing it.
3. **Single copy.** Delete `docs/entviz-paper.md`, make `papers` canonical, leave a pointer in
   entviz docs. Simplest, but the figures and the spec live here and the entviz docs site
   loses its paper.

Recommendation: **1**, with the reference-[8] text fixed upstream first so the generated
output matches what is already published.

---

The per-item queues that used to follow — cross-port work, the paper items, and
housekeeping — moved to [`RELEASE-TRAIN.md`](../RELEASE-TRAIN.md), which is now the single
place to look for what is next across the family.
