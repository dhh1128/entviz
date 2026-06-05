# Security Review: entviz

**Date:** 2026-06-05
**Effort level:** deep
**reviewed commit:** 0b873e5 (dirty working tree: no — only untracked review output added)
**Context sources used:** `AGENTS.md`, `CLAUDE.md`, `docs/threat-model.md`, `SECURITY.md`,
`README.md`, `pyproject.toml`, `src/entviz/*.py` (app, pipeline, entropy, fingerprint,
renderer, shapes, keccak, colors, layout), `.github/workflows/*.yml`,
`.github/dependabot.yml`, `scripts/check_unicode.py`. Prior reviews
(`reviews/adversarial-2026-05-27.md`, `…-06-02.md`) consulted only AFTER forming an
independent model, to check disposition of any overlapping finding.

---

## Evidence Inventory

entviz is a **pure offline CLI + library** that renders a high-entropy identifier
(UUID, hash, crypto address, AID/CESR, SSH key, snowflake, LEI, etc.) into a static
SVG for human eyeball comparison. It is **not an Origin platform service**: there is
no RFC 9421 signature path, no nonce/replay cache, no AID-to-key verification, no
database, no network endpoints, no JWT/OAuth/session, no cross-cell exchange. The
entire authentication / authorization / DB-boundary / cross-service portion of the
security-hawk checklist is therefore **not applicable**, and I confirmed that absence
by reading the full source tree rather than assuming it.

The attack surface that *does* exist is exactly the one the project's own
`docs/threat-model.md` enumerates: (1) the human near-collision-resistance judgment
(primary asset), and (2) the integrity/safety of an emitted SVG embedded in a
third-party page (secondary asset), plus the listed secondary win "DoS the renderer
with a crafted input (uncaught exception, super-linear resource consumption)."

Tests were not run as a suite; instead I executed targeted dynamic probes under
`uv run` for the DoS, escaping, and ReDoS hypotheses (results inline below). A
concrete CVE scan was attempted: `pip-audit`/`osv-scanner`/`trivy` are not installed
in this environment, so I verified the single runtime dependency by version instead —
`lxml 6.1.1` (current; no open advisories as of the knowledge cutoff). I am flagging
that the advisory-DB scan could not be run as tooling rather than silently skipping
it (see Residual Unknowns).

Orientation context was strong: a real, well-developed threat model and two prior
adversarial reviews exist, so confidence on the relevant findings is high.

---

## Executive Summary

entviz's security posture is strong and clearly the product of prior adversarial
review: SVG output is built through lxml (attributes and text are auto-escaped), the
out-of-band `--note` caption is aggressively sanitized, clip-path ids are 64-bit
salted against cross-embed collision, the CI/release supply chain is close to
best-in-class (full-SHA-pinned actions, least-privilege tokens, `persist-credentials:
false`, an invisible-Unicode guard, a locked lockfile), and no secrets are committed.
The one genuine, fixable security defect is a **denial-of-service via unbounded
input**: `render()` has no length cap and tokenizes the *entire* multi-megabyte input
into ~1.7M Python objects before discarding all but the head/tail — a 10 MB input
burns ~14.5 s of CPU and a 50 MB input ~48 s, all wasted work, when the SHA-512 that
actually binds the input costs 0.07 s. This is the exact "super-linear resource
consumption" secondary win the threat model lists, and it matters for any server-side
caller of the public `render()` API.

---

## Top Findings

Ordered by bang-for-buck.

### F1: Unbounded input → wasted full-tokenize DoS in `render()` / `tokenize_entropy()`
- **Severity:** MEDIUM
- **Confidence:** CONFIRMED
- **Location:** `src/entviz/entropy.py:1308` (`tokenize_entropy` calls
  `tokenize(core, alphabet)` on the whole core) and `src/entviz/pipeline.py:59`
  (`render` applies no input length cap); CLI entry `src/entviz/app.py:14`
  (`parser.add_argument('entropy')`, unbounded).
- **Finding:** For inputs over 512 bits, `tokenize_entropy` only keeps 8 head + 4
  middle + 8 tail tokens (`entropy.py:1317-1334`), but it first calls
  `tokenize(core, alphabet)` over the *entire* string (`entropy.py:1308`), building one
  `Token` namedtuple per token for the whole input. Measured: a 10 MB hex input
  produces 1,747,627 tokens and takes ~14.4 s; 50 MB takes ~48 s. The full-tokenize
  result is used only for the `len(all_tokens) <= _MAX_TOKENS` branch decision and
  `n_bytes`, both of which are derivable in O(1) from `len(core)` without materializing
  any tokens. By contrast `sha512` over the same 10 MB is 0.073 s and the disproof/parse
  pass is ~0.6 s — so essentially 100% of the cost is throwaway work. There is no upper
  bound on input size anywhere upstream (CLI argparse, `render`, `parse`).
- **Exploit path:** The threat model names "DoS the renderer with a crafted input
  (super-linear resource consumption)" as a secondary win. A server or batch job that
  calls the public `entviz.pipeline.render()` on user-supplied bytes (the same
  "server-side entviz renderer" scenario the F3 finding in `adversarial-2026-05-27.md`
  already contemplated) lets an attacker pin a core for tens of seconds and force
  ~100+ MB of transient allocation per request with a single large paste — cheap to
  send, expensive to absorb, and trivially repeatable. Even the local CLI is a
  foot-gun (paste a large file, wait 48 s). Cost is roughly linear, not exponential, so
  it is a resource-exhaustion nuisance rather than an instant kill — hence MEDIUM, not
  HIGH.
- **Recommendation:** Two cheap, independent fixes; do both. (a) In
  `tokenize_entropy`, decide the large-input branch from `len(core)` /
  `_core_byte_length(core, alphabet)` directly and tokenize only the
  `core[:head_chars]` and `core[-tail_chars:]` windows — never the whole core — so the
  cost becomes O(head+tail) regardless of input size. (b) Add an explicit input-length
  cap (a `MAX_INPUT_CHARS`, e.g. a few megabytes) in `render()` that raises
  `ValueError` (the CLI already turns `ValueError` into a clean `parser.error`), so a
  hostile input is rejected loudly instead of absorbed. A test asserting that a 10 MB
  input renders in well under a second (post-fix) locks in the regression boundary.

---

## Additional Patterns Noted

These were examined and found **adequately defended** — listed so the next reviewer
need not re-derive them, not as defects:

- **SVG content/attribute injection (XSS / style bleed):** Token text is assigned via
  lxml `text_el.text = token.text` (`renderer.py:93`) and all attributes via
  `etree.SubElement(..., key=value)` — lxml escapes `< > & "` in both positions.
  Dynamic probe with `render('<script>alert(1)</script>"><svg onload=alert(1)>')`
  produced no raw `<script`/unescaped angle brackets in the output. The arbitrary-text
  fallback additionally base64url-encodes the input before it ever reaches the DOM
  (`pipeline.py:74-80`). No `style=`/`font-family` value is derived from input — they
  are constant or numeric.
- **`--note` caption (trust-adjacent field):** `sanitize_note` (`pipeline.py:37-56`)
  strict-rejects anything but `^[A-Za-z0-9]{1,8}$`; injection attempt
  `sanitize_note('a"><x')` raises `ValueError`. It never enters the fingerprint, and is
  carried in a distinct `data-user-note` attribute (lxml-escaped). Matches the
  threat-model "User note" section.
- **Cross-embed clip-path id collision:** `clip_id` is salted with 64 bits of the
  fingerprint (`pipeline.py:243-244`), closing prior finding F-A3.
- **Vendored Keccak-256 (`keccak.py`):** custom crypto, but used *only* for EIP-55
  case-checksum validation (not for any security boundary), and cross-checked against
  published EIP-55 vectors in `tests/test_f7_eip55.py`. Acceptable.
- **ReDoS:** the parser runs many anchored regexes; the widest-looking one
  (`BECH32_GENERIC_REGEX`) matched a 100 k adversarial string in 0.002 s. No
  catastrophic backtracking observed.
- **CI / supply chain:** actions full-SHA-pinned with human-readable `# vN` comments;
  `permissions: contents: read` on CI, scoped `contents: write` only on release;
  `persist-credentials: false` everywhere; `unicode-guard` job runs
  `check_unicode.py`; tests run `--locked` (proves `uv.lock` is current);
  `release.yml` passes the tag via `env:` not direct `${{ }}` interpolation;
  `deploy-docs` uses OIDC + artifact, no `pull_request_target`, no `workflow_run`
  push, no unpinned tags, no `curl | bash`. Dependabot covers both `github-actions`
  and the `uv` ecosystem. No SNAPSHOT/mutable deps, no typosquat candidates (single
  dep: `lxml`).
- **Secrets in source/history:** pattern scan over `*.py/*.toml/*.yml/*.md/*.json`
  found none; SECURITY.md present with private-reporting flow.

---

## Residual Unknowns

- **CVE/advisory scan not run:** no `pip-audit`/`osv-scanner`/`trivy` in this
  environment. I verified `lxml==6.1.1` is current and has no advisory I am aware of as
  of the knowledge cutoff, but an online scan against a live advisory DB was not
  possible. Recommend wiring `pip-audit` (or `uv pip audit`) into CI to make this a
  standing gate rather than a point-in-time human check.
- **Git history secret scan** was limited to current file state plus a content
  pattern grep; a full `git log -p` entropy sweep was not performed. Nothing in the
  current tree suggests a committed secret ever existed (no `.env`, no key material,
  no service config), so this is low-risk, but a `gitleaks` history pass would close it
  definitively.

---

## Decisions Needed

- **What is the intended deployment surface of `render()`?** If it is ever exposed as
  a hosted/HTTP renderer (the README ships it as a library + PyPI-track package, and
  prior reviews already reason about "a server-side entviz renderer"), the F1 input cap
  becomes a HIGH-priority hardening item rather than MEDIUM. If it is forever
  local-CLI-only, MEDIUM is right but the wasted-tokenize fix is still worth taking
  purely as a correctness/perf cleanup.

---

```yaml
findings:
  - id: SEC-F1
    persona: security-hawk
    title: Unbounded input causes wasted full-tokenize DoS in render()/tokenize_entropy()
    severity: MEDIUM
    confidence: CONFIRMED
    location: src/entviz/entropy.py:1308
    dedupe_key: render-input-unbounded
    recommended_disposition: recommend-fix
    rationale: >
      render() has no input length cap and tokenize_entropy() tokenizes the entire
      multi-MB core into ~1.7M objects before discarding all but head/tail; 10MB=~14.5s,
      50MB=~48s of wasted CPU+memory vs 0.07s for the SHA-512 that actually binds the
      input. Matches the threat model's "super-linear resource consumption" secondary
      win; relevant to any server-side caller of the public render() API.
    revisit_condition: null
    fix_effort: small
```
