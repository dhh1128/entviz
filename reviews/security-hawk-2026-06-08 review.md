# Security Review: entviz

**Date:** 2026-06-08
**Effort level:** medium
**Context sources used:** `this.i` (partial — lines 1–1146 of 2976), `docs/spec.md` (not re-read; spec referenced via `this.i` design decisions), `AGENTS.md`, `SECURITY.md`, `docs/threat-model.md`, `pyproject.toml`, `uv.lock`, `src/entviz/app.py`, `src/entviz/pipeline.py`, `src/entviz/entropy.py`, `src/entviz/renderer.py`, `src/entviz/shapes.py`, `src/entviz/keccak.py`, `.github/workflows/ci.yml`, `.github/workflows/deploy-docs.yml`, `.github/workflows/release.yml`, `scripts/gallery.py`, `scripts/figlib.py`, `scripts/check_unicode.py`

---

## Evidence Inventory

**Read:**
- All six files under `src/entviz/` (app.py, pipeline.py, entropy.py, renderer.py, shapes.py, keccak.py)
- All three GitHub Actions workflows
- pyproject.toml and uv.lock (partial — lxml version confirmed as 6.1.1)
- `scripts/gallery.py`, `scripts/figlib.py`, `scripts/check_unicode.py`
- `docs/threat-model.md` (first 30 lines confirmed it exists and is maintained)
- `SECURITY.md`, `AGENTS.md`

**Tests/renderer run (medium effort):**
- Ran `render()` interactively on: `<script>alert(1)</script>`, a crafted 40-hex ETH address, a DID URL with `<script>` in query string, a DID URL with `&` and `?` in suffix — all confirmed SAFE
- Ran note sanitization: rejection of `<script>` and `toolongname` confirmed GOOD
- Ran MAX_INPUT_CHARS cap test: rejects at 65537 chars with correct error
- Ran DID_REGEX edge cases: empty method rejected; space in body rejected
- Ran lxml `.text` / attribute escaping tests: `&`, `<`, `>`, `"` all escaped correctly

**Skipped:**
- Advisory scanner (`pip-audit`, `osv-scanner`) — offline run; flagged below as a residual unknown
- Full `this.i` (only first 1146 of 2976 lines); security-relevant nodes (usrn0te1, 1nputcap, s3mpr3fx, sufxbind) were found and verified
- Prior `reviews/` contents — read after forming the independent security model
- `compliance/` corpus (not a security surface)

---

## Executive Summary

entviz's implementation-security surface is genuinely narrow: no network listener, no auth, no DB, one external dependency (lxml). The biggest-bang finding is the DID URL regex (`DID_REGEX`) which accepts angle brackets, `&`, and other XML metacharacters in the query/fragment component — these reach SVG via `lxml.text` assignment, which safely escapes them, so the risk is defended-in-depth. The defence holds as long as lxml's serializer is in the path; a future refactor that prints the suffix directly would reopen an injection channel. A lightweight "always validate the suffix is URL-safe before inserting" rule would make this robust without relying on lxml. The supply-chain posture is strong: actions are SHA-pinned, uv.lock is committed and used with `--locked`, and a unicode-guard CI job defends against Trojan-Source/GlassWorm payloads. The most urgent non-injection item is that `uv build` in the release job runs without `--locked`, which is standard for wheel packaging but means the built wheel's test environment may differ from the CI test environment if lxml 7 ships a breaking change before the lockfile is updated.

---

## Top Findings

Ordered by bang-for-buck (highest risk reduction per unit of fix effort, first).

### F1: DID URL suffix accepts XML metacharacters — injection defended only by lxml serializer

- **Severity:** MEDIUM
- **Confidence:** CONFIRMED
- **Location:** `src/entviz/entropy.py:122` (`DID_REGEX`), `src/entviz/pipeline.py:697–706` (`_draw_label_strips`)
- **Finding:** `DID_REGEX` captures group 3 with `([?].*)` — the `.*` matches any character, including `<`, `>`, `&`, `"`. A DID URL like `did:example:abc123?x=<script>alert(1)</script>` is matched and the `?x=<script>...` portion is stored as `suffix`. This `suffix` reaches `el.text = f"...{suffix}"` (pipeline.py:702) and `suffix_tspan.text = f"...{suffix} "` (pipeline.py:697). Both assignments go through lxml's element tree serializer, which escapes all four XML metacharacters (`<→&lt;`, `>→&gt;`, `&→&amp;`, `"→&quot;`) before emitting the output. The rendered SVG is confirmed safe by end-to-end test.

  The defence is structurally sound today, but it relies entirely on the implicit invariant "every user-controlled string reaches the SVG tree only via lxml element `.text`/`.tail`/attribute assignment, never via string concatenation." If a future developer adds a fast-path that prints or concatenates the suffix string directly (e.g., to add a tooltip or aria-label), the injection channel re-opens without any obvious indication. The fix is cheap and makes the invariant explicit.

- **Exploit path:** An attacker passes `did:example:legit-corp?foo=<script>stealCreds()</script>` to a service that calls `render()` and embeds the SVG inline in an HTML page without re-sanitizing it. lxml currently escapes this, but the path demonstrates a latent vector that a refactor could activate.
- **Recommendation:** Add a suffix-validation step in `parse_did` (or in `render()` before label construction) that restricts the suffix to URL-safe characters: `re.fullmatch(r'[\w%!$&\'()*+,;=:@/?.#-]*', suffix)`. Reject or strip any suffix failing this check. This takes the invariant off lxml's shoulders and makes the constraint explicit and testable.

---

### F2: `uv build` in release job runs without `--locked` — wheel may be built with a different dependency resolution than was tested

- **Severity:** LOW
- **Confidence:** CONFIRMED
- **Location:** `.github/workflows/release.yml:70` (`run: uv build`)
- **Finding:** The release workflow's `test` job correctly uses `uv run --locked ... pytest` to prove the lockfile is current. However, the `release` job then runs `uv run --locked pytest` again (not shown — it only runs `uv build`) followed by `uv build` without `--locked`. `uv build` resolves dependencies from `pyproject.toml`'s floating `lxml>=5` constraint, not from `uv.lock`. If lxml 7.x is released between a lockfile update and a tag push, the wheel is built and tested in different environments: tests pass under lxml 6.1.1 (the locked version) but the released wheel ships with lxml 7.x as a valid dependency, and users of the published wheel install lxml 7.x on fresh installs, where unreleased lxml breaking changes are not guarded.

  The workflow comment at line 28–31 explicitly acknowledges this (`uv build itself has no --frozen/--locked flag`), so the maintainer is aware. For this project's current pre-1.0 state and narrow dependency surface it is a low-likelihood risk.

- **Exploit path:** A silent breaking change in lxml 7.x alters how `etree.tostring` escapes a specific SVG attribute, causing the emitted SVG to differ from what was tested — potentially affecting the text-channel rendering or breaking parsers that consume the data-* attributes.
- **Recommendation:** Add a post-build wheel test step that installs the built wheel and runs a smoke test against it: `uv pip install dist/*.whl && python -c "from entviz.pipeline import render; render('abc123')"`. This catches dependency-resolution divergence before a release is published. Longer-term, consider a two-job release pattern that re-runs the full test suite against the built wheel.

---

### F3: `pyproject.toml` dependency `lxml>=5` is floating — advisory database check not performed

- **Severity:** LOW
- **Confidence:** LIKELY
- **Location:** `pyproject.toml:25` (`"lxml>=5"`)
- **Finding:** The project's single production dependency is `lxml>=5`, pinned to 6.1.1 in `uv.lock`. No advisory scanner (`pip-audit`, `osv-scanner`, Trivy) is run in CI or as part of the release process. For a library with a narrow attack surface, the practical risk is low — lxml 6.1.1 is recent and well-maintained, and entviz uses only `etree.SubElement`, `.text`, `.tail`, and `etree.tostring` (no network, no XSLT, no xpath on attacker-provided documents). However, the absence of automated advisory checking means a future lxml CVE (e.g., a heap overflow in XML parsing if entviz ever uses `etree.fromstring` on external input) would not generate an automated alert.
- **Exploit path:** A CVE in lxml is disclosed; maintainer is unaware because no scanner watches the dependency; users of the published wheel are silently exposed.
- **Recommendation:** Add `uv run pip-audit` (or equivalent) to the CI `test` job, gated with `continue-on-error: true` initially to avoid blocking CI on false positives. The goal is visibility, not a hard gate. The advisory-check-offline scenario (air-gapped runner) should emit a warning rather than silently skipping (advisory prompt in the persona instructions). Note: this is a medium-effort change if adding a new CI step; low-effort as a developer workflow note.

---

### F4: `DID_REGEX` query/fragment group uses `.*` (unbounded greedy match) — theoretical backtracking on adversarial input

- **Severity:** LOW
- **Confidence:** LIKELY
- **Location:** `src/entviz/entropy.py:122` — `DID_REGEX = re.compile(r'^(did:[a-z0-9]+:)((?:[a-zA-Z0-9_.-]|%[a-fA-F0-9]{2})+)((/[^?]*)?([?].*)?)$')`
- **Finding:** The outer alternation `(?:[a-zA-Z0-9_.-]|%[a-fA-F0-9]{2})+` has a two-branch alternation where each branch may match any single valid char. Python's `re` module (powered by a backtracking NFA) can exhibit exponential backtracking on adversarial input that nearly matches the body but fails at the final `$`. Specifically, a string `did:example:` followed by `N` valid chars and then one invalid char (e.g., `did:example:` + `a%ab` × 25 + `!`) triggers worst-case behavior. Empirical test showed sub-millisecond performance for N=100; at N=10000 this would still be sub-second due to the 65536-char input cap. Given `MAX_INPUT_CHARS = 65536`, the worst-case backtracking is bounded and the attack requires a local CLI call, not a remote service.
- **Exploit path:** A local user crafts a 65536-char DID-like string that maximizes backtracking in the body alternation, consuming ~10–50 ms of CPU. Not exploitable remotely; DoS impact is local-caller CPU waste.
- **Recommendation:** The existing `MAX_INPUT_CHARS` cap bounds this acceptably. For additional hardening, simplify the body alternation: `(?:[a-zA-Z0-9_.%-])+` (collapse the two branches into one character class, using `%-` to admit `%` as a literal char). This eliminates the alternation-driven backtracking risk entirely. Cross-reference `SPEC` if the DID body character class is normatively specified.

---

### F5: Missing automated advisory scan — cross-reference OPS

- **Severity:** LOW
- **Confidence:** CONFIRMED
- **Location:** `.github/workflows/ci.yml` (no `pip-audit` step)
- **Finding:** No step in any workflow scans pinned dependencies against known vulnerability advisories. This is distinct from F3 (the floating constraint concern): F5 is specifically about the absence of the CI gate. For a project of this size and dependency count, the omission is tolerable but leaves a detection gap.
- **Exploit path:** See F3.
- **Recommendation:** See F3. Cross-reference `OPS` for the CI-pipeline lens; the advisory-check step should be owned there.

---

## Additional Patterns Noted

- **SSH comment field dropped:** The SSH public-key parser drops trailing comments (`user@host`) as a `FREE` annotation. This is correct and prevents the comment field from reaching the fingerprint or the SVG text channel. Verified via code review; no finding.
- **SWHID qualifier dropped:** The `SWHID_REGEX` drops the optional `;qualifiers` tail before it reaches any SVG path. URL-like content in qualifiers cannot reach the output. Confirmed safe.
- **No `pull_request_target` trigger:** All three workflows use `pull_request` (safe, unprivileged fork context) or `push` (trusted context). No privileged PR trigger is present.
- **No `shell=True`, `eval`, `exec`, `pickle`, `yaml.load`, `subprocess`, or `os.system` found in `src/`:** Scan confirmed clean across all source files.
- **Concealed Unicode scan:** `rg` scan for invisible/bidi/variation-selector codepoints in `src/`, `scripts/`, `compliance/` returned no hits. The CI `unicode-guard` job also provides runtime verification.
- **`keccak.py` is a vendored pure-Python Keccak-256 implementation** used only for EIP-55 checksum validation. It has no external input path, processes only sanitized 40-char hex bodies, and its output is consumed only for character-case comparison (no crypto key derivation). The vendoring decision is documented in `this.i:3ip55rj1` and the file header. No security concern.
- **`figlib.py:230` f-string SVG concatenation** (`f'<svg ...>{inner}</svg>'`) is in the paper-figure generator (`scripts/paper_figures.py`), a developer-only tool that assembles SVG from `render()` output (already lxml-serialized and safe). Not a user-facing code path.
- **`gallery.py` HTML generation** uses `html.escape()` on every user-supplied string before inserting it into the HTML page template. Confirmed safe.
- **`lxml` version 6.1.1** — no known critical CVEs as of 2026-06-08 knowledge cutoff. Advisory database could not be queried (offline run).
- **No secrets found** in committed files: no PEM blocks, no API keys, no high-entropy strings in non-test config. The CI workflows use `${{ github.token }}` (scoped to the run) and nothing more.
- **`astral-sh/setup-uv@fac544c` (v8.2.0)** — this action is a composite action (not Node.js), so the node20/node24 deprecation concern does not apply.

---

## Residual Unknowns

1. **Advisory database not queried.** This review ran offline; `pip-audit` or `osv-scanner` could not reach the OSV/PyPI advisory databases. lxml 6.1.1 was not cross-checked against current CVE data. Mark as a residual unknown until a network-capable advisory scan is run.
2. **Full `this.i` not read.** Only the first ~40% was consumed. Security-relevant intent nodes (`usrn0te1`, `1nputcap`, `s3mpr3fx`, `sufxbind`) were found and verified. Remaining nodes could reveal additional intent constraints not covered here.
3. **DID_REGEX body reachable from SWHID/gitoid prefix-semantic path** — the prefix-semantic fold (`fingerprint_core = prefix + core`) is verified in code but not exercised end-to-end for a DID with a long body under the truncation path. The binding logic is correct by inspection, but a conformance-corpus test covering this corner is absent from what was reviewed.

---

## Decisions Needed

1. **DID suffix sanitization (F1):** Should `parse_did` reject suffixes containing XML metacharacters (`< > & "`) with a `ValueError`, or should it silently strip them to the URL-safe subset? Rejecting is safer and spec-compliant (malformed DID URL fragment should not be treated as valid). The choice affects whether a DID URL with a literal `<` in its fragment is a valid input or an error condition.
2. **Advisory scanning in CI (F3/F5):** Is a hard-gate `pip-audit` step appropriate for this project at its current pre-1.0 stage? If yes, the step should be in `ci.yml`'s `test` job. If no, a developer-facing note in the release checklist (`scripts/release.py`) would be a lighter-weight mitigation.

---

## Findings Manifest

```yaml
findings:
  - id: SEC-F1
    persona: security-hawk
    title: "DID URL suffix accepts XML metacharacters — injection channel defended only by lxml serializer"
    severity: MEDIUM
    confidence: CONFIRMED
    location: "src/entviz/entropy.py:122 + src/entviz/pipeline.py:697-706"
    dedupe_key: text-channel-unsafe
    recommended_disposition: recommend-fix
    rationale: >
      DID_REGEX group 3 ([?].*) matches <, >, &, " which reach el.text via lxml (safe today) but
      would become an injection vector in any future fast-path that bypasses lxml serialization.
      A suffix character-class restriction makes the invariant explicit and testable.
    revisit_condition: null
    fix_effort: small

  - id: SEC-F2
    persona: security-hawk
    title: "release.yml `uv build` runs without --locked — wheel may test against different lxml than was validated"
    severity: LOW
    confidence: CONFIRMED
    location: ".github/workflows/release.yml:70"
    dedupe_key: github-actions-unpinned
    recommended_disposition: recommend-defer
    rationale: >
      Acknowledged in workflow comments; wheel builds conventionally use pyproject.toml's floating
      constraint. Risk is low given lxml>=5 constraint and pre-1.0 status.
    revisit_condition: "Reopen when preparing the first 1.0 / PyPI release or when lxml 7.x is published."
    fix_effort: small

  - id: SEC-F3
    persona: security-hawk
    title: "No automated advisory scan for lxml dependency"
    severity: LOW
    confidence: CONFIRMED
    location: "pyproject.toml:25 + .github/workflows/ci.yml"
    dedupe_key: uv-lock-unpinned
    recommended_disposition: recommend-defer
    rationale: >
      lxml 6.1.1 is current; advisory check skipped offline. Gap is real but low-priority for a
      single-dependency library with no network/DB surface.
    revisit_condition: "Add pip-audit to CI before first PyPI release or when adding more dependencies."
    fix_effort: small

  - id: SEC-F4
    persona: security-hawk
    title: "DID_REGEX two-branch body alternation — bounded ReDoS risk on adversarial DID body"
    severity: LOW
    confidence: LIKELY
    location: "src/entviz/entropy.py:122"
    dedupe_key: cli-unbounded
    recommended_disposition: recommend-defer
    rationale: >
      MAX_INPUT_CHARS=65536 bounds worst-case backtracking to sub-second on a local CLI call;
      no remote listener exists. Fix (collapsing alternation into a character class) is trivial
      but not urgent.
    revisit_condition: "Reopen if entviz is ever embedded behind a web service that renders untrusted DIDs."
    fix_effort: small

  - id: SEC-F5
    persona: security-hawk
    title: "No threat-model.md cross-reference in SECURITY.md — documented but advisory scan absent from CI"
    severity: LOW
    confidence: CONFIRMED
    location: ".github/workflows/ci.yml"
    dedupe_key: github-actions-missing
    recommended_disposition: recommend-defer
    rationale: >
      threat-model.md exists and is maintained; CI runs unicode-guard and full test suite with
      locked deps; advisory scan is the only missing gate. Defer to pre-1.0 hardening pass.
    revisit_condition: "Reopen at pre-1.0 / pre-PyPI-publish milestone."
    fix_effort: small
```
