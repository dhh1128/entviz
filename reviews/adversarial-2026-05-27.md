# Adversarial Review: entviz

**Date:** 2026-05-27
**Reviewer:** Claude (Opus 4.7, 1M context)
**Algorithm version reviewed:** v4 (DRAFT, per `docs/index.md`)
**Implementation commit:** `cf2e47a6dd28886b1d3b154539fe90a4b36b525b`

---

## Working Threat Model

There is no `docs/threat-model.md` in this repository. The model below is what I
used as the frame for every finding.

**Assets.** Primary: the user's belief that two entropy values are equal (or
not). Secondary: integrity of a rendered SVG when embedded in third-party
documents.

**Trust boundaries.** entviz trusts: the input bytes (after normalization), the
display, the user's font stack, the browser's SVG rendering, the user's
attention, the user's reading of *both* label strips. entviz does not trust:
attacker-controlled HTML/CSS surrounding an embedded SVG; the user remembering
exact pixel values across sessions.

**Attacker tiers.**
* **T1.** Can choose one of the two compared values and grind it offline.
* **T2.** Can control the rendering surface for one or both entvizes (CSS in
  scope, font substitution, scale, screenshot vs live render).
* **T3.** Can manipulate the input string at the encoding layer (case, leading
  prefix, alphabet ambiguity, trailing junk).
* **T4.** Can manipulate the user's environment (CVD simulation, monochrome
  display, small screen, hostile font substitution).
* **T5.** Can construct long inputs (>512 bits) whose head-256 and tail-256
  match a target, relying on text-channel truncation.
* **T6.** Habituated insider — the user only checks one or two landmarks (color
  bar gestalt, blank-cell positions).

**Attacker win conditions.** Primary: produce `A ≠ B` such that the user,
comparing `entviz(A)` and `entviz(B)` under realistic conditions, concludes
they are the same. Secondary: cause `entviz(A)` to render differently depending
on environmental factors that should not matter (encoding, alphabet, case);
cause a stored entviz to render differently after embedding (clip-path id
collision is the documented example); inject script via the rendered SVG; DoS
the renderer with a crafted input.

**Out of scope.** Confidentiality of the input. Compromise of SHA-512.
Defenses against a user who chooses not to look.

**Accepted risks per spec.** Pure-text environments; remembering all details of
an entviz; perfect fidelity of fine nucleus-color gradations under reduced
color depth.

---

## Evidence Inventory

* Read in full: `docs/index.md` (the v4 spec), `entviz-paper.md`, `this.i`,
  `entviz/entropy.py`, `entviz/pipeline.py`, `entviz/renderer.py`,
  `entviz/colors.py`, `entviz/fingerprint.py`, `entviz/layout.py`,
  `entviz/shapes.py`, `entviz/app.py`, `bin/entviz.py`, `requirements.txt`,
  test directory listing, opening of `docs/spec-improvement-notes.md`.
* Skimmed (post-analysis): `entviz-critique-from-chatgpt.md`,
  `entviz-critique-from-gemini.md`. These two are paper critiques and do not
  overlap meaningfully with this implementation/algorithm review.
* Did not read in detail: the test files individually (used presence as
  signal), `docs/v3/*`, the `refs/` gallery assets, the bitmap renders under
  `assets/`. No code under `.github/workflows/` was examined beyond a directory
  listing; only one CI file (`ci.yml`) is present.
* **Test suite was run** (`nice -n 19 ionice -c 3 python -m pytest entviz/tests/ -x --tb=short`).
  All 316 tests pass on this commit.
* **Implementation was run** to generate example renders. Probes that produced
  concrete artifacts: SVG injection probes (`/tmp/ssh-xss.svg`); long-input
  truncation pair (`/tmp/long-A.svg`, `/tmp/long-B.svg`); the collision
  candidates file (`/tmp/entviz-collision-candidates.txt`).
* CVD analysis used the Brettel/Vienot/Mollon simulation matrices in linear
  sRGB; ΔE computed in CIELAB. These are first-order simulations, not a
  substitute for testing with real CVD observers.

---

## Perceptual Entropy Budget Estimate

Per-channel rough estimates of *perceptually-discriminable* bits, vs. the
spec's nominal bits. Conservative under realistic conditions (20/40 vision at
desktop reading distance, no print-quality calibration). Per-cell estimates
multiply by token count (up to 22); per-entviz estimates are not multiplied.

| Channel | Nominal (per cell × 22 cells) | Normal vision, 16M | CVD (deutan/protan) | 256-gray | Small / 20/40 |
|---|---|---|---|---|---|
| Text (verbatim) | up to 512 (≤512-bit inputs) | ~100–512* | ~100–512* | ~100–512* | drops sharply <10pt |
| Surround pattern (24 bits/cell) | 528 | ~5–7/cell × 22 ≈ 110–150 | similar (binary) | similar | ~3–5/cell × 22 ≈ 65–110 |
| Nucleus bg (24 bits/cell) | 528 | ~5–6/cell × 22 ≈ 110–130 | ~2–3/cell × 22 ≈ 45–65 | ~3–4/cell × 22 ≈ 65–90 | ~3–4/cell × 22 ≈ 65–90 |
| Per-cell edge color | 0 (deterministic from nucleus) | 0 | 0 | 0 | 0 |
| Entviz bg (2 bits) | 2 | 2 | ~1 (red/gold collapse) | ~1 | 2 |
| Color bar (4 buckets, count⁴ skew) | ~6–10 (top color + rough ratios) | ~4–6 | ~3 | ~3–4 | ~3–4 |
| Ellipse overlay | 16 (anchor) × 16³ (rx,ry,rot) = ~64K combinations ≈ 16 nominal | ~6–8 (rough silhouette) | ~6 | ~6–8 | ~4–5 |
| Blank-cell positions + clock hands | ~10–14 (positions + 2 angles, quantized) | ~6–10 | ~6–10 | ~6–10 | ~4–6 |
| Quartile marks (4 cells × orientation) | ~16–20 | ~6–10 | ~6–10 | ~6–10 | ~3–5 |

\* Text channel is verbatim; "perceptual bits" doesn't apply the same way —
under habituation the user typically scans only a few landmark cells, so the
*effective* bits under quick comparison are much smaller than the nominal.

**Summed perceptual entropy under realistic comparison conditions** (sum of
non-text channels, since text is verbatim but may not be carefully read):

* Normal vision, 16M color, side-by-side, careful comparison: **roughly 220–270 bits**.
* Habituated user landmarks-only (color bar + blank positions + ellipse gestalt + 1–2 cell glances): **roughly 25–40 bits**.
* CVD severe deuteranopia: **roughly 130–180 bits**.

The headline result: **the algorithm clears the randomart bar (~20–24 bits) by
a wide margin under careful comparison**, validating the paper's thesis. But
the *habituated-user landmark-only* budget (~30 bits) is close enough to the
randomart benchmark that a determined T1+T6 attacker could grind a near-match
on the gestalt channels with ~2³⁰ ≈ 10⁹ trial inputs. That is well within the
budget of any attacker who can iterate fingerprints (which is anyone — the
fingerprint computation is public and SHA-512 is cheap).

---

## Executive Summary

entviz's multi-channel design is sound in principle and clears the randomart
perceptual-entropy benchmark by a comfortable margin under careful
side-by-side comparison. The implementation is mostly clean and the test
suite is comprehensive (316 tests pass).

The most important weaknesses are concentrated at the **input normalization
boundary** (where alphabet detection, case normalization, and prefix/suffix
stripping decide what bytes enter SHA-512) and at the **human-factor seams**
(the user must read both label strips and check the truncation marker, but the
spec offers no convention or affordance for confirming they did). Several
inputs that are *visually identical to a reading user* parse to *different*
fingerprints (F1, F2), and a long-input attacker can construct two distinct
inputs whose text channel is byte-identical and whose only differences live in
fingerprint-driven gestalt channels (F4). There is also a confirmed unhandled
exception (F3, a soft DoS).

**Most urgent actionable item:** anchor `BITCOIN_CASH_REGEX` with `$` and add a
catch around `parse_hex_multihash`'s `bytes.fromhex()` call. These are
one-line fixes that close a silent-truncation attack and an uncaught-exception
crash, respectively.

---

## Top Findings

Ordered by bang-for-buck. The first three are 1–3 line fixes with outsized
impact; the rest require more work but matter more strategically.

---

### F1: Lowercase pure-hex inputs are silently misclassified as EOS addresses, producing a different entviz than the same hex in mixed/upper case

- **Layer:** ALGO + IMPL
- **Severity:** HIGH
- **Confidence:** CONFIRMED (constructed examples below)
- **Threat-model attacker:** T3 (or even an unwitting user)
- **Location:** `entviz/entropy.py:77` (`EOS_REGEX`), `entviz/entropy.py:459` (`parse_eos_address`), parser-dispatch order at `entviz/entropy.py:585` (registered before `parse_hex`).
- **Finding.** `EOS_REGEX = re.compile(r"(^[a-z1-5.]{1,11}[a-z1-5]$)|(^[a-z1-5.]{12}[a-j1-5]$)")` is the EOS chain's address regex, but its character class `[a-z1-5.]` happens to be a superset of the lowercase hex digits `[a-f0-5]` for many strings. Because `parse_eos_address` runs *before* `parse_hex` (parser registration order), a lowercase hex literal like `'ff112233'`, `'abcdef12'`, `'deadbeef'`, or `'cafebabe'` is silently classified as an **EOS address with alphabet=base64**, while its uppercase counterpart `'FF112233'` or any mixed-case `'FfFf1122'` falls through to `parse_hex` with alphabet=hex. The two paths use different `bits_per_char` and different per-character lookups, so they produce different quants per token and a different fingerprint (because the fingerprint hashes the alphabet-dependent normalized core; lowercase-hex's EOS pass leaves the core unchanged, while mixed-case hex normalizes to lowercase under `parse_hex`).
- **Exploit path.**
  * `render('FF112233')` ≠ `render('ff112233')` — confirmed.
  * `render('abcdef12')` ≠ `render('AbCdEf12')` — confirmed.
  * A user who copies a hex address from one source (lowercase) and a colleague who copies from another (uppercase) compare entvizes and see two visibly different pictures, with two different type labels (`EOS:` vs `hex(8):`). They reasonably conclude the addresses are different and refuse a legitimate transaction (DoS on the user). Reverse: a malicious actor who knows the rendering rule serves the victim a lowercase form, expecting the victim's mental reference (an uppercase one) to look different.
  * The same EOS regex also catches `'aaaa'`, `'cafe'`, `'face'`, `'qpzry'`, `'iiiii'` — many short inputs that a user might paste as random bytes.
- **Recommended action.** **Fix in code, immediately.** Either (a) move `parse_eos_address` after `parse_hex` in the dispatch order so genuine hex always wins, (b) tighten `EOS_REGEX` to require at least one non-hex character or minimum length 12 (the spec-mandated EOS length), or (c) remove the speculative single-token EOS short-form match entirely (real EOS accounts are typically 12 chars). Add a regression test fixing the result for `'ff112233'` to be `Parsed(type='hex', ...)`. Also document the principle: parser dispatch order must put narrow/checksumed formats before broad heuristic ones.

---

### F2: Disproof-path BASE32 detection does NOT case-normalize, breaking the RFC-4648 invariant

- **Layer:** ALGO + IMPL
- **Severity:** HIGH
- **Confidence:** CONFIRMED
- **Threat-model attacker:** T3 (or unwitting user)
- **Location:** `entviz/entropy.py:638` — `core = entropy.lower() if detected in (BECH32,) else entropy`
- **Finding.** RFC 4648 base32 is canonically case-insensitive (the `BASE32_ALPHABET_EITHER_CASE` constant at `entviz/entropy.py:31` and the case-insensitive disproof match at `entviz/entropy.py:678` both acknowledge this). But the disproof-path normalization at line 638 *only* lowercases when the detected alphabet is `BECH32`. So `'ABCDEFGHIJ'` → `Parsed(alphabet=BASE32, core='ABCDEFGHIJ')` and `'abcdefghij'` → `Parsed(alphabet=BASE32, core='abcdefghij')`. Down-stream, `tokenize` falls back to a case-insensitive char lookup *only if the strict lookup fails*, but the SHA-512 fingerprint is computed over `core.encode('utf-8')` (in `fingerprint.py:35`), so the two cases hash to different bytes and produce different entvizes.
- **Exploit path.**
  * `render('ABCDEFGHIJ')` ≠ `render('abcdefghij')` — confirmed.
  * Same canonical base32 value (both decode to the same bytes), different entviz, and the user has no clue from the label strip (`base32:` for both) that what they are looking at is a case-collision artifact.
- **Recommended action.** **Fix in code.** Change line 638 to normalize case for all case-insensitive alphabets: `core = entropy.lower() if detected in (BECH32, HEX, BASE32) else entropy`, and the fingerprint then becomes case-invariant for those alphabets. Note that for `HEX` it's redundant because `parse_hex` already lowercases — but the disproof path can also reach `HEX` for short strings, so being explicit is safer. Add regression tests covering all-upper, all-lower, and mixed-case forms of a base32 input producing identical entvizes.

---

### F3: `parse_hex_multihash` raises uncaught `ValueError` on any odd-length all-hex input, killing the CLI

- **Layer:** IMPL
- **Severity:** MEDIUM (low impact but trivial fix)
- **Confidence:** CONFIRMED
- **Threat-model attacker:** any user with a malformed paste
- **Location:** `entviz/entropy.py:222–232` — `parse_hex_multihash` calls `bytes.fromhex(text)` if `HEX_REGEX.match(text)` succeeds and `len(text) >= 6`, but does not check `len % 2 == 0` first.
- **Finding.** `bytes.fromhex` requires even-length input and raises `ValueError: non-hexadecimal number found in fromhex() arg at position 7` for odd-length all-hex strings of length ≥ 7. `parse_hex_multihash` is registered *first* in `parse_funcs` (see `entviz.entropy:585`), so the exception aborts the entire `parse()` chain before `parse_hex` (which does check odd length) can handle it. Confirmed on inputs `'badcafe'` (7), `'1234567'` (7), `'aaaaaaa'` (7), `'7abcdef'` (7).
- **Exploit path.** Any user (or anyone supplying input to a service that calls `render()` on user-supplied bytes) can crash the CLI / raise an unhandled exception on the server with a 7-char odd-length all-hex input. Easy to trigger by accident; equally easy to weaponize for a soft DoS against a server-side entviz renderer.
- **Recommended action.** **Fix in code.** Either wrap the `bytes.fromhex` call in `try/except ValueError: return None`, or add `if len(text) % 2: return None` at the top of `parse_hex_multihash`. Either is one line. Add a regression test: `parse('badcafe')` should return `Parsed(type='hex', ...)` (or whichever specific parser is appropriate), never raise.

---

### F4: `BITCOIN_CASH_REGEX` lacks the `$` end-anchor — appended bytes after a valid BCH-shaped prefix are silently discarded

- **Layer:** IMPL + ALGO
- **Severity:** HIGH
- **Confidence:** CONFIRMED
- **Threat-model attacker:** T3
- **Location:** `entviz/entropy.py:81` — `BITCOIN_CASH_REGEX = re.compile(r'^((?:bitcoincash|bchtest):)?([pq][' + BECH32_ALPHABET_EITHER_CASE + ']{41})', re.I)` — note the missing `$` after the `{41}` capture.
- **Finding.** Without `$`, `re.match` (which only anchors `^`) consumes the first 42 bech32 chars and silently ignores everything after, including spaces and arbitrary text. The matched body is what reaches `core`, so the SHA-512 fingerprint is computed over the truncated prefix only. Two inputs that share their first 42 chars produce **identical entvizes**, regardless of what differs after.
- **Exploit path.**
  * `parse('pqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq [USER-FACING DIFFERENTIATOR]')` matches and returns a `Parsed("BCH", ..., core='pqqq…qqq', ...)` that ignores the appended text entirely.
  * Attacker constructs a BCH-shaped first 42 chars and tacks differing payloads on the end; the user sees the same entviz for distinct strings.
  * **In practice this attack is constrained** by the fact that real BCH addresses cluster around the same shape (`bitcoincash:q…` of length ~54), so the universe of bench32-shaped first-42-char strings that look "legit" to a user is small — but the same code path produces real silent truncation in any non-BCH context (e.g., a user pasting a BCH address with a trailing whitespace+comment).
- **Recommended action.** **Fix in code.** Add `$` to the regex. Also audit all the other regexes in `entropy.py` for the same omission — I spot-checked and `SSH_KEY_REGEX` lacks anchors too (`r'(AAAA)([0-9A-Za-z+/]+={0,3})'`), but it is only called as a fallback inside `parse_ssh_key` after `SSH_LINE_REGEX` (which IS `^…$`-anchored) fails on the full input, so it isn't exploitable today — but a future refactor that calls `SSH_KEY_REGEX` on the whole input directly would inherit the same silent-truncation bug. The general fix is to mandate `^…$` anchoring on every parser regex and add a static-check or unit test that scans `entropy.py` for `re.compile(r'^…'` without a closing `$`.

---

### F5: Truncation of >512-bit inputs collapses the text channel for any two inputs sharing head-256 and tail-256, leaving only fingerprint-driven gestalt to detect tampering

- **Layer:** ALGO + UX
- **Severity:** HIGH
- **Confidence:** CONFIRMED (constructed pair `/tmp/long-A.svg`, `/tmp/long-B.svg`)
- **Threat-model attacker:** T5 + T6
- **Location:** `docs/index.md` (spec, "Requirements" paragraph + the truncation handling in `entviz/entropy.py:769` `tokenize_entropy`); pipeline marker at `entviz/pipeline.py:74` (`type_name = f"^…$ {type_name}"`).
- **Finding.** The spec is honest about this: large inputs have their middle elided in the text channel and bound only through the fingerprint. The intended defense is (a) the `^…$ ` truncation marker on the top label and (b) the fingerprint-driven channels (surround, blank cells, ellipse, color bar, quartile marks). Both defenses have UX gaps:
  1. The truncation marker is documented in the spec but not in any user-facing surface I can find — no tooltip, no legend, no README mention of "if you see `^…$` you must trust the gestalt because the cells lie." A reading user encountering `^…$ hex(200):` for the first time will not parse it correctly.
  2. The fingerprint-driven channels do provide avalanche under SHA-512, so two truncation-attacker inputs that share head-256 and tail-256 will differ measurably across surround/blank/ellipse/colorbar. But under habituated comparison (T6) the user is checking ~30 bits of landmarks, not the full surround pattern. A T1+T5+T6 attacker grinding inputs whose head+tail match the target and whose colorbar top color + blank positions + ellipse anchor all match has a feasible target.
  3. A user comparing two long entvizes side-by-side does not normally re-read the truncated body. The text channel reads identical, which biases the user toward "same."
- **Exploit path.**
  * Constructed pair: `[64 hex head] + [200 chars of middle A or B] + [64 hex tail]`. Cell text channels are byte-identical except for the unchanged truncation marker; only the fingerprint-driven channels differ.
  * `/tmp/long-A.svg` and `/tmp/long-B.svg` are saved as a worked example.
- **Recommended action.**
  1. *Spec change.* Promote the `^…$ ` marker from a quiet `#666` label into something attention-grabbing for the truncated case — a red border, a bold word like `TRUNCATED`, or both. The current marker is the same color and size as the rest of the label and disappears in peripheral vision.
  2. *Documentation.* Add an explicit user-facing note: "When the top label begins with `^…$`, the cell text shows only the first and last 256 bits of the input. You MUST compare the rest of the visualization (color bar, blank positions, ellipse, surround patterns) and not rely on cell text alone."
  3. *Test addition.* Add a regression test that constructs two inputs with identical head+tail and asserts that the rendered SVGs differ in the surround layer (e.g., comparing the set of `<rect>` elements drawn during `render_edges`).

---

### F6: Per-cell edge color (red/gold) collapses below CVD-severe ΔE thresholds under deuteranopia/protanopia

- **Layer:** ALGO + UX
- **Severity:** MEDIUM
- **Confidence:** LIKELY (computational simulation, not human-subjects testing)
- **Threat-model attacker:** T4 (or any CVD user)
- **Location:** `entviz/colors.py:30` (palette), `docs/index.md` (spec asserts CVD usability).
- **Finding.** The spec and the paper both claim entviz is usable under common color vision deficiency. Computing the Brettel–Vienot–Mollon-simulated palette in CIELAB:
  * Under **deuteranopia**, gold (#ffd966 → ~(247,225,107)) and red (#ff3f2f → ~(170,152,36)) have ΔE ≈ **26.7**. The paper's own Table 2 quotes severe-CVD JND as **50–60** ΔE units (mild = 15–22). 26.7 is well below the severe threshold and only marginally above the mild threshold.
  * Under **protanopia**, gold (~(238,214,90)) vs red (~(123,110,42)) have ΔE ≈ **45.9** — closer, but red is much darker than under deuteranopia so the dominant cue becomes luminance, not chromaticity. Cells whose edge color was selected on the chromatic axis (red vs gold) read as "two olive shades of slightly different brightness" rather than two distinct colors.
* Practical impact on entviz: the per-cell edge color is the most visually prominent way to distinguish two cells' surround rings at a glance. If gold and red collapse, a CVD user loses one of the four palette colors as a meaningful discriminator. The color bar, which is the primary gestalt channel, also relies on these colors; a histogram dominated by gold-vs-red distribution becomes hard to read.
* The spec says "perceptual selection ensures that even color-blind viewers can detect each cell as a separate object distinct from the background" — that claim is **not supported by the math**. Detection from background (luminance contrast) survives; **discrimination between palette entries** (gold vs red) does not.
- **Exploit path.** A T4 attacker presenting two entvizes to a known-CVD user can lean on inputs whose differences live in gold/red surround patterns; the user perceives them as identical.
- **Recommended action.**
  * Replace either gold or red with a color that maintains ΔE ≥ 50 from the others under deuteranopia/protanopia simulation. Candidates to consider: a saturated cyan (#00bbcc-ish) or a deep magenta. The palette has to remain readable on the four background candidates too, so a full re-tune is required.
  * Add a **CVD snapshot test** to the test suite: simulate the four palette colors under deutan/protan/tritan/achromatopsia and assert pairwise CIELAB ΔE exceeds a threshold (use 50 as the severe-CVD bar from Table 2).
  * Update the spec's CVD claim to either (a) cite specific CVD simulation results and ΔE numbers, or (b) downgrade the claim to "detectable, but not discriminable for some pairs under severe CVD."

---

### F7: Cell-text case normalization produces *visible* lossiness that the entviz hides

- **Layer:** ALGO + UX
- **Severity:** MEDIUM
- **Confidence:** CONFIRMED (collision pairs below)
- **Threat-model attacker:** T3
- **Location:** `entviz/entropy.py:610` (`parse_hex` lowercases), `entviz/entropy.py:371` (`to_EIP55_address` re-derives case from bytes), `entviz/entropy.py:492` (UUID lowercased), `docs/index.md` (spec describes the normalization but does not warn the user).
- **Finding.** Hex (and UUID, and Ethereum) inputs are case-normalized before tokenization. The user-facing implication:
  * `render('1234567A') == render('1234567a')` — confirmed.
  * `render('DEADBEEFCAFEBABE') == render('deadbeefcafebabe')` — confirmed.
  * `render('0xDEADBEEF') == render('0xdeadbeef')` — confirmed.
  * For Ethereum specifically, `to_EIP55_address` re-derives the canonical case from the bytes, so an input with an INVALID EIP-55 case pattern (i.e., a *bad checksum*) renders to the same entviz as the same address with the *correct* case. The visualization silently fixes the checksum.
  * The "cap" oral-reading convention (spec line 68) is intended to disambiguate spoken hex, but the **visualization itself is case-blind for hex**, so the convention doesn't help when the comparison is visual.
* The harm is two-fold. (a) A user comparing two visually-readable text representations (e.g., a printed address) may see different case patterns and assume the entropy differs; the entviz says it doesn't, but the *bytes* the user actually transmits later (with their case preserved) may not match what the recipient expects. (b) Conversely, an attacker who substitutes a bad-EIP-55-case Ethereum address gets a free pass through the entviz — the wallet rejects, but only at execution time, after the user has lost time and possibly committed to a flow.
- **Recommended action.**
  * *Spec change.* Document explicitly that the text channel renders the *normalized* case, not the input case, and that two inputs differing only in case for case-insensitive alphabets produce the same entviz. Surface this in the label strip when it matters (e.g., if the input case was inconsistent with the spec's canonical form, append a `[case normalized]` marker).
  * For Ethereum specifically, validate the input EIP-55 checksum and either (a) refuse to render an address with an invalid checksum, (b) flag it in the label strip with a `[invalid checksum]` warning, or (c) preserve the user-supplied case in the cells and only validate the checksum out of band.
  * For UUIDs and hex, consider whether the punctuation-stripped (`-` removed) cell text should warn when the input contained extra characters that were elided (UUIDs without dashes are nonstandard).

---

## Additional Patterns Noted

* **F-A1.** `_DISPROOF_ORDER` rebuild is lazy and not thread-safe (global mutation). Low-impact in CLI but real in a server context. `entviz/entropy.py:659`.
* **F-A2.** `parse('0X…')` (capital X prefix on Ethereum) is permitted by the regex; `parse_hex` also accepts `'0x'`/`'0X'`. The two paths produce different `type_name` labels (`ETH` vs `hex(N)`) but identical cells if both end up at `core = lowercased_hex`. Minor inconsistency.
* **F-A3.** `clipPath` id `grid-clip-{first_8_hex}-{cols}x{rows}` has a 32-bit salt component. Birthday-bound: ~65k entvizes on one page before a collision becomes likely. The spec notes the gallery generator does belt-and-suspenders id rewriting; recommend documenting that anything embedding more than ~1000 entvizes in a single document must do the same.
* **F-A4.** No SVG output `viewBox` set; consumers that rescale the SVG via `width`/`height` attributes will see different rendered pixel sizes across hosts (and therefore different perceptual fidelity). Worth setting `viewBox="0 0 {bounding_w} {bounding_h}"` for responsive embeds.
* **F-A5.** `style="font-family: monospace;"` is the *only* font specification. The user's system monospace font determines glyph metrics and homoglyph behavior. Two viewers on different OSes (macOS Menlo vs. Linux DejaVu Sans Mono vs. Windows Consolas) will see meaningfully different cell text — particularly for hyphen, underscore, digit zero, capital O, lowercase l, digit 1, and the distinction between `0/O` and `1/I/l`. Recommend either (a) embedding a CSS `@font-face` reference to a specific monospace, or (b) documenting an explicit "use this font" recommendation and noting the homoglyph risk for other fonts.
* **F-A6.** The blank-cell ring + clock-hands combination is geometrically clever, but the long hand's `mix-blend-mode: difference` does not render in `cairosvg` (and `this.i` acknowledges this). Anyone using a non-browser SVG renderer (server-side PNG generation, PDF embedding) loses the maxftok direction indicator silently. Recommend that the spec call out the rendering-environment dependence and offer a fallback path.
* **F-A7.** `app.py` accepts `--output` as a user-supplied file path with no validation. Writes via `open(args.output, 'w')` will happily overwrite arbitrary paths the running user can write to. CLI tools commonly behave this way, but for shared-host or pipe-into-render scenarios it's worth a `--force` flag.
* **F-A8.** `bin/entviz.py` does `sys.path.insert(0, …)` from `__file__` — fine for the standard installation but means anyone who can write to the directory next to the installed script can shadow the `entviz` package import. Minor.
* **F-A9.** The bg color is selected from the **2 low-order bits of the median ftok's quant** (`entviz/colors.py:48`). Only 4 possible bgs; trivially grindable. This is acknowledged in the spec as a hint-only channel, but combined with the color-bar dominance (which depends on the same digest), a T1 attacker who matches the bg + the top color-bar band has matched two of the three highest-salience gestalt channels at an expected cost of ~16 trials.
* **F-A10.** The disproof order treats `'1'` as separator-shaped in bech32 but accepts it in hex; an input like `'10111010'` is recognized as hex (line 600) but `'qpzry1'` would never be (1 not in bech32). A user pasting a bech32 fragment with the separator `1` left in will get classified as base64 or base64url (or fall through to UTF-8 fallback) and may not understand why.
* **F-A11.** No test under `entviz/tests/` exercises SVG injection — I sanity-checked manually and `lxml.etree`'s `.text =` assignment does escape `<`, `>`, `&`, and quotes properly, so the implementation is currently safe. Adding an explicit test (input `'<script>alert(1)</script>'` → output must not contain `<script` literally) would prevent regression if the renderer is ever rewritten with string concatenation.
* **F-A12.** `parse_bitcoin_cash_address` is called even on inputs without the `bitcoincash:` / `bchtest:` prefix (the prefix is optional in the regex). Combined with F4, this means *any* string starting with `p` or `q` followed by 41 bech32 chars is classified as BCH, even when the user did not intend BCH.

---

## Residual Unknowns

Static analysis alone cannot answer these. They are the smallest experiments that would settle each:

1. **What perceptual entropy does a habituated user actually use?** A user study where participants verify their "own" SSH key entviz over several weeks and then are presented with grind-matched malicious entvizes (matched on top color bar + blank positions + bg, but differing in surround patterns) would tell us whether the 25–40 bit habituated-landmark estimate above is conservative or generous. This is the single most informative experiment the project could run.
2. **CVD discrimination in practice.** The ΔE math in F6 needs confirmation with CVD observers (or, less rigorous but cheaper, with the standard Ishihara/HRR plates as a calibration of the simulator). My calculation says gold/red collapse; an actual CVD user might disagree.
3. **Across-render-engine fidelity.** A test that renders the same entviz under `cairosvg`, Chromium, Firefox, Safari, and (for completeness) Microsoft Print to PDF, then compares pixel-level outputs, would surface font-substitution effects, `mix-blend-mode` differences, antialiasing differences, and clip-path resolution differences. Two of these (mix-blend-mode in cairosvg, clip-path id collisions across embedded entvizes) are already known issues; the systematic survey would surface unknown unknowns.
4. **20/40 vision at typical viewing distance.** What is the smallest font size at which the surround pattern remains JND-distinguishable? The spec defaults to 12pt and is parameterizable; some empirical guidance about "do not render below 10pt" or similar would be useful.
5. **Homoglyph confusability under common monospace fonts.** Render the full base64url + crockford32 + bech32 alphabets in Menlo, Consolas, DejaVu Sans Mono, Liberation Mono, and Courier; measure the per-pair confusability (e.g., compare `0/O`, `1/I/l`, `5/S`, `-/_/–`). This is feasible without a user study by computing pairwise visual distance with a perceptual image-similarity metric.

---

## Recommended Next Steps for the Maintainer

Ranked by bang-for-buck.

1. **Land the three trivial fixes (F1, F2, F3, F4).** All four are 1–3 line changes that close confirmed issues. The collision pairs in `/tmp/entviz-collision-candidates.txt` give you regression tests directly.
2. **Adopt the threat model in this document (or revise it) as `docs/threat-model.md`.** Future findings are much cheaper to triage against an explicit model.
3. **Add an SVG-injection regression test** with input `'<script>alert(1)</script>'` and assertions that the output contains `&lt;script` and not `<script`. The implementation is currently safe (thanks to `lxml`'s escaping), but it's a one-line test that prevents a regression.
4. **Add CVD snapshot tests** (one per CVD type) that assert pairwise palette ΔE > 50; or, accept the F6 finding and re-tune the palette before adding the test.
5. **Promote the `^…$ ` truncation marker into something attention-grabbing** (red border, bold word) and add a regression test that compares two inputs with shared head+tail and asserts the surround-layer SVG differs.
6. **Document a recommended comparison surface.** Side-by-side on the same screen, the same font family, the same scale, the same background. Without this, "near-collision resistance" is unverifiable in the field.
7. **Audit every regex in `entropy.py` for `^…$` anchoring.** Write a meta-test that scans the module for `re.compile(r'^…'` without a closing `$` and fails CI on any new omission.
8. **Pin the font.** Add an explicit `@font-face` or document a fallback chain that includes a specific narrow-glyph monospace; warn loudly about homoglyph drift on systems where the font substitutes.
9. **Eventually:** commission the user study described in Residual Unknown #1. Without it, the headline thesis of the entviz paper remains "theoretically supported, empirically untested."
