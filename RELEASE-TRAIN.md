# The entviz release train

The entviz family is six repositories with one spec. This file is the **ordering** — what has
to happen, in what sequence, for a spec change to reach every implementation. Per-repo work
items live in each repo's `tick` ledger; this file says which tick can start when, and why.

It exists because `tick` is per-repo with no cross-repo view, so a six-repo propagation has
nowhere else to live. When you want to know "what's next", read this file, not six ledgers.

**Repos.** `entviz` (this one — the spec, the reference implementation, the conformance
corpus and runner), `entviz-js`, `entviz-go`, `entviz-java`, `entviz-rs` (the ports), and
`entviz-adversarial` (the companion paper). The published papers live in `dhh1128/papers`.

---

## The dependency that governs everything

**A port cannot move to a new spec version until this repo has cut and pushed the tag.**

Every port's CI checks out `dhh1128/entviz` at a pinned tag to get the corpus and the runner:

```yaml
- name: Check out the entviz reference (spec + corpus + runner)
  uses: actions/checkout@…
  with:
    repository: dhh1128/entviz
    ref: v0.16.0          # <- the pin
```

The runner asserts that the corpus's `spec_version` equals the implementation's rendered
`data-entviz-version`, and fails loudly on a mismatch. So a port that bumps its own
`SPEC_VERSION` without moving the pin goes red, and a port that moves the pin before the tag
exists cannot check out at all. The two moves are one move.

All four ports run **Tier A** (render model) *and* **Tier B** (canonical raster), so a change
that alters goldens binds everywhere, not only where cell text changes.

## The shape of a spec release

```
  1. entviz: land the change, regenerate the corpus, cut and push the tag
                                  |
                                  v
  2. four ports in parallel — each does the same five things
        entviz-js   entviz-go   entviz-java   entviz-rs
                                  |
                                  v
  3. each port releases its own package (npm / Go module / Maven Central / crates.io)
```

Stage 2 is a fan-out: the four ports never touch each other and can run concurrently. Stage 3
is per-port and optional — a port can sit conformant-but-unreleased indefinitely.

### Stage 1 — the reference release

1. Land the spec change, the reference implementation, and the tests.
2. Regenerate the corpus: `PYTHONPATH=src:. uv run --group render python -m compliance.generate`.
3. Regenerate the gallery (`scripts/gallery.py`) and the figures (`scripts/spec_figures.py`,
   `scripts/paper_figures.py`). **Do not commit re-rendered PNGs** unless the SVG changed
   visibly: the committed rasters come from a different font stack and are not reproducible on
   every machine, so regenerating them churns bytes and the vendored pins in `../papers` for
   no reason. The conformance corpus rasters *are* reproducible and must be regenerated.
4. Bump `SPEC_VERSION` and `__version__` in `src/entviz/__init__.py`. The library's MINOR
   tracks the spec major: spec `v16` → lib `0.16.x`.
5. Update `docs/spec-change-log.md` with a "What's new in vN" section, and record the rationale
   in `this.i`.
6. `python3 scripts/release.py --minor -m "spec v16"` — bumps, regenerates the gallery, commits,
   tags, pushes. The pushed tag triggers `.github/workflows/release.yml`, which builds and
   publishes to PyPI via Trusted Publishing.
7. **By hand, and easy to forget:** `release.py` does *not* regenerate the social card. Run
   `uv run --group render python scripts/social_card.py`, commit the result, and re-upload
   `docs/assets/social-card.png` under repo **Settings → Social preview** — regenerating the
   file does not update the GitHub setting.

### Stage 2 — each port, five things

Identical in all four. Do them as one commit per port so the pin and the version move together.

1. Implement the spec change in the parser/renderer.
2. Bump the port's `SPEC_VERSION` constant.
3. Bump the `ref:` pin in `.github/workflows/ci.yml` (both the Tier-A and Tier-B jobs — each
   checks out the reference separately) to the new tag.
4. Update the port's own unit tests and any golden fixtures.
5. Verify locally against the corpus before pushing: Tier A, then Tier B.

### Stage 3 — per-port publication

Each port's `release.yml` fires on its own tag and publishes to its ecosystem. **These are
one-way doors** — crates.io yanks but does not delete, and Maven Central is permanent. Cut them
deliberately, one at a time, not as a batch.

---

## Current state — spec v16 (2026-08-04)

v16 makes the bech32 HRP identity-bearing; see `docs/spec-change-log.md` and `this.i:hrpb1nd`.
It changes rendered output for every bech32-family value and moves four golden rasters.

| Stage | Repo | Tick | State |
|---|---|---|---|
| 1 | `entviz` | `4dua` | **Done.** `v0.16.0` tagged and pushed 2026-08-04; CI, docs deploy and the PyPI release workflow all green. |
| 2 | `entviz-js` | `4vmj` | **Done**, local commit `e17645b`, unpushed. Tier A+B 99/99. |
| 2 | `entviz-go` | `6543` | **Done**, local commit `7d64c46`, unpushed. Tier A+B 99/99. |
| 2 | `entviz-java` | `32yv` | **Done**, local commits `9efd231`+`47b029a`, unpushed. Tier A+B 99/99. |
| 2 | `entviz-rs` | `5a5x` | **Done**, local commit `458f07c`, unpushed. Tier A+B 99/99. |
| 3 | all four | — | Not started; deliberate, one at a time. |

All four counts were re-verified centrally against the corpus, not taken from the ports' own
reports. Nothing is pushed.

**This machine's JVM toolchain is incomplete** and both facts cost an agent time: `mvn` is not
on `PATH` (user-space Maven at `~/opt/apache-maven-3.9.16/bin/mvn`), and the system JDK is a
*JRE* — there is no `javac` anywhere, so Maven fails with "release version 21 not supported".
A Temurin JDK 21 sits at `~/opt/jdk-21.0.12+8`; export `JAVA_HOME` to it.

**Two ports had no Cardano parser at all.** `entviz-go` and `entviz-java` fell through to the
generic bech32 parser for `addr1…`, so it characterized as scheme `bech32` rather than `ada` —
a pre-existing divergence from the reference that was invisible until v16 added the
`cardano-shelley` vectors. Both ports now carry a ported `parse_cardano_address`, Byron
branches included. Byron and `stake1` have no corpus vector, so those paths are covered by the
ports' own tests and by model-for-model cross-checks against the reference, not by a golden.
Worth adding corpus vectors for them.

All four ports were at v15 before this change, so v16 is one hop for each — there is no
catch-up debt underneath it.

### Riding along with stage 2

These are open in three or four ports each, and each is one change repeated. The v16 pass
already opens the parser and label layer in every port, so they are cheap to carry:

- `entropyType` (bare entropy category, no count/format/sub-label): `entviz-go 76xs`,
  `entviz-java 7zbj`, `entviz-rs 3wew`. Reference: entviz-js `bareEntropyType()`.
- Developer API docs / integration guide: `entviz-go 4p67`, `entviz-java 753v`,
  `entviz-rs 62iz`.
- Social card: `entviz-js 76ex`, `entviz-rs 6cvy`.

The umbrella for the set is `entviz 7v3e`.

---

## Independent of the train

These block nothing and are blocked by nothing. Pick them up whenever.

| Item | Where | Tick |
|---|---|---|
| Closed-profile SVG validation does not bind declared cells to painted ink (HIGH ×2) | `entviz-js` | `34mr` |
| Quadratic BigInt decode reachable ahead of the input cap | `entviz-js` | `6p7t` |
| URL fetch follows redirects while the shown provenance origin does not | `entviz-js` | `7nye` |
| The 64 KiB cap's stated cost model is wrong (703 ms measured vs ~14 ms documented) | `entviz` | `4jvs` |
| A Bitcoin **testnet** address is characterized and labeled as **mainnet** — and v16's corpus ships that wrong value as a golden | `entviz` | `6gde` |
| Review-panel adversarial pass over the code — best run *after* a spec change lands | `entviz` | `25ac` |
| `tick init` (the repo has a published paper and is a vendoring upstream) | `entviz-adversarial` | — |
| Merge issue #23 with the `locateAction` translation tick | `entviz-js` | `74sc` |

### The paper and the vendoring posture

Tracked outside `tick`, in [`reviews/vendoring-posture.md`](reviews/vendoring-posture.md)
under `Q-8VQC`:

- The vendoring model. `papers/amp-diff.md` is a hand-copied derivative of
  `docs/entviz-paper.md` with a sha256 pin on the *upstream* file only, so a papers-side edit is
  invisible to the drift guard by construction — and the two have already diverged (reference
  [8], and the reference numbering). The guard also runs only in `publish.py`'s preflight, never
  in CI.
- **A spec release makes the published paper stale.** `papers/amp-diff.md` reference [8] cites
  the spec as "Version 15". Re-check it on every spec bump; `scripts/check_drift.py` will flag
  `docs/spec.md` as a warning-level drift to prompt you.
- Table 2's JND audit, the archival DOI for the spec, the citation page-check, and the SSRN
  abstract revisions.

### Breaking changes outside the spec

`@entviz/core`'s comparison text now carries the entviz's label (`[did:key] z6Mk haXg …`). That
is a breaking change to a published npm package, independent of v16 — it can ship with the v16
port release or before it, but it needs its own version decision and release note. Tick
`entviz-js 2rf4`.
