# Adversarial Review: entviz

**Date:** 2026-06-02
**Reviewer:** Claude (Opus 4.8, 1M context)
**Algorithm version reviewed:** v6 (DRAFT, per `docs/spec.md` header)
**Implementation commit:** `ad277326763fd0da4709c7394065fef9b5f83ad3`

---

## Working Threat Model

This review **adopts and extends** the existing `docs/threat-model.md` rather
than drafting a fresh one. That document is sound; the assets (the user's
same/different belief; SVG embedding integrity), trust boundaries, attacker
tiers T1–T6, win conditions, out-of-scope items, and accepted risks are all
appropriate and unchanged here. Two small extensions this review relies on:

- **T5 is now broader than the model states.** The model frames T5 as ">512-bit
  inputs whose head-256 and tail-256 match a target." v6 actually reserves the
  first 192 bits (8 tokens) and last 192 bits as head/tail, and replaces the
  truncated middle with a *fingerprint readout*. The relevant T5 capability for
  v6 is therefore: match the head-192, the tail-192, **and** the 4 displayed
  fingerprint tokens. The spec claims that last requirement is a ≈2⁹⁶ partial
  preimage; F1 below disputes the "96" for several alphabets.
- **A "displayed-fingerprint correlation" sub-case of T1.** v6 newly *displays*
  digest bytes 24–35 as text. Those same bytes feed the color bar and the four
  fingerprint cells' own surround, and can be the median/quartile ftok. A T1
  grinder targeting the middle text is therefore no longer grinding an
  independent channel from part of the gestalt (F2).

The model's instruction "a finding that does not map to one of these is
decoration" is followed: every finding below names a tier and a win condition.

---

## Evidence Inventory

- **Read in full:** `docs/spec.md` (v6), `docs/threat-model.md`,
  `docs/entviz-paper.md`, `reviews/adversarial-2026-05-27.md` (prior review,
  v4), `reviews/ellipse-audit-2026-06-02.md`, the v6 `this.i` decisions
  (`v6fpmid1`, `v6blnkun`, and the F5/F7/EIP-55 history), and the full Python
  source tree: `entropy.py`, `pipeline.py`, `renderer.py`, `colors.py`,
  `fingerprint.py`, `layout.py`, `app.py`. Read the v6 tests
  (`test_v6_fingerprint_middle.py`, `test_v6_blank_map.py`) and skimmed the
  large-input / truncation / color-bar tests.
- **Did not read line-by-line:** `keccak.py`, `shapes.py`, the v3/v4 test files
  (used as coverage signal), `entviz-critique-from-*.md` (per the prompt's
  independence rule; not present in repo anyway).
- **Test suite was run:** `nice -n 19 uv run pytest -q` → **419 passed** on this
  commit.
- **Implementation was run** to generate concrete artifacts and probe v6
  behavior: bit-width of the displayed middle per alphabet; middle-text
  injectivity for 5-bit and non-power-of-2 alphabets; reachability of the
  large-input path by base58/base36/decimal; head+tail+middle layout dumps;
  SVG-injection probes (hostile input text and hostile SSH comment);
  large-input blank-placement variation; confirmation that prior findings
  F1/F2/F3/F4/F7 are fixed. Collision/near-collision seeds saved to
  `/tmp/entviz-collision-candidates.txt`.
- **Perceptual claims remain partly SPECULATIVE.** I did not rasterize to PNG
  for this pass (the structural/byte-level findings did not require it, and the
  perceptual budget is inherited from the prior review with v6 deltas applied).
  Anything labeled perceptual is flagged.

**Prior findings re-checked (v4 → v6):** F1 (EOS-before-hex) — **fixed**
(`parse('ff112233')` → hex). F2 (base32 disproof case) — **fixed**
(`ABCDEFGHIJ` and `abcdefghij` share a core). F3 (odd-length hex crash) —
**fixed** (no exception; routes to a parser). F4 (`BITCOIN_CASH_REGEX` missing
`$`) — **fixed** (anchored). F5 (head/tail-only long-input collision) —
**addressed** by the v5/v6 middle, but see F1 below for a residual gap. F6
(gold/red CVD collapse) — **not fixed in palette**; v6 adds color-bar *letters*
which mitigate the color bar specifically (the most habituation-relied channel),
but the per-cell edge-color discrimination problem in F6 persists and there is
still no CVD snapshot test. F7 (EIP-55 silent normalization) — **fixed** (raises
`EIP55ChecksumError`). F-A4 (`viewBox`) — fixed (spec mandates it). F-A6
(mix-blend-mode invisible outside browsers) — **fixed** for the blank marker
(v6 map uses plain circles, no blend mode; `test_no_mix_blend_mode_in_output`
asserts it). I did **not** re-file any of the fixed items.

---

## Perceptual Entropy Budget Estimate

Inherited from the 2026-05-27 review (which clears the randomart ~20–24 bit bar
by a wide margin under careful comparison, ~25–40 bits under habituated
landmark-only comparison). v6 deltas:

| Channel | v6 change | Effect on budget |
|---|---|---|
| Color bar | Per-band letters `w/g/r/b/k`, wider bar | **+** survives CVD/mono/CSS-filter; adds a verbal discriminator to the most habituation-relied channel. Net positive, especially for T4/CVD. |
| Blank marker | Disc+clock-hands → outlined pill + position map | Roughly neutral perceptually; **+** robustness (no blend mode, renders in rasterizers); position-map is arguably *easier* to compare than two clock angles. |
| Ellipse | Coverage clamped to [0.22·d_far, 0.58·d_far] | **+** removes the invisible-sliver and grid-swamping tails; coverage now ~8–70%, median ~32%. Slightly *reduces* nominal entropy range but raises *usable* entropy. |
| Long-input middle | Body slices → fingerprint readout (text) | Middle nuclei now carry **0** bg entropy (neutral); their text avalanches for read-aloud. Net: shifts ~96 nominal text bits from "probabilistic body coverage" to "guaranteed fingerprint coverage" — but only **80 bits** for 5-bit alphabets and far fewer for base58/base36 (F1). |
| Large-input blanks | Fixed separators → median/quartile shift | **+** restores a per-input CRC-like blank-position signal that every large entviz previously lacked (all large entvizes used to share one layout). Genuine improvement. |

**Net:** v6 is a perceptual-entropy improvement over v4/v5 for the habituated
and CVD cases (color-bar letters, blank-map, varying large-input blanks). The
near-collision-resistance headline is unchanged for the common alphabets
(hex/base64url); it is *weaker than advertised* for 5-bit and non-power-of-2
alphabets on the >512-bit path (F1).

---

## Executive Summary

**Verdict: v6 is a net security and UX improvement over v5/v4, and I found no
new critical implementation vulnerability — but the headline "≈2⁹⁶ partial
preimage" protection for the redesigned long-input middle is overstated for
several alphabets, and the spec contains a factual error about which alphabets
reach that path.** The v6 fingerprint-middle redesign correctly fixes v5's
"low-entropy body could collide the middle text" defect for hex and base64url,
and SVG escaping, prior findings F1–F4/F7, and the new blank-map all hold up.
The most important issue (F1) is that the middle text displays only **80 bits**
for bech32/base32/crockford32 (not 96), is non-injective on the full middle
bytes for those alphabets, and degrades much further for base58/base36 — which
the spec wrongly claims "never reach the large-input path" but which a
200-character pasted address demonstrably does. The single most urgent
actionable item is to correct the spec's preimage claim per-alphabet and add a
read-aloud-collision regression test for the 5-bit alphabets. Beyond that, the
unfixed F6 CVD palette gap and the still-undocumented user-facing comparison
guidance remain the largest standing risks, both inherited from v4.

---

## Top Findings

Ordered by bang-for-buck.

### F1: The v6 long-input middle does not deliver the claimed ≈2⁹⁶ barrier — it is 2⁸⁰ for 5-bit alphabets, far less for base58/base36, and the spec's "never reach the large-input path" claim for non-power-of-2 alphabets is false

- **Layer:** ALGO (+ spec accuracy)
- **Severity:** MEDIUM (HIGH as a *claim* defect; the actual residual collision
  resistance is still large for realistic attackers, but the spec materially
  overstates it)
- **Confidence:** CONFIRMED (constructed/measured)
- **Threat-model attacker:** T1 + T5 (+ T6 / read-aloud)
- **Location:** `docs/spec.md` "Large-input handling" + "Why the middle is the
  fingerprint" (the "≈2⁹⁶ partial preimage" claim, repeated in
  `this.i:v6fpmid1` and the label-strip section); `src/entviz/entropy.py:987`
  `_fingerprint_token_text`, `:1083` `tokenize_entropy` trigger.
- **Finding.** The spec asserts that matching the 4 displayed fingerprint tokens
  is "~96 specific bits of the input's SHA-512 output (a partial preimage,
  ≈2⁹⁶)." That holds **only for hex and base64url** (token_len × bits_per_char =
  6×4 and 4×6 = 24 bits each → 96 bits). For the 5-bit alphabets the displayed
  token is 4 characters × 5 bits = **20 bits**, and `_fingerprint_token_text`
  renders the top 20 of each cell's 24 bits, dropping the low 4. So:
  - **bech32 / base32 / crockford32:** the middle displays **80 bits**, and the
    rendering is **not injective** on the middle bytes — the low nibble of every
    third middle byte (digest bytes 26, 29, 32, 35) is never shown. Two
    >512-bit inputs whose digests differ *only* in those nibbles render
    **identical middle text** (gestalt still differs). Measured:
    `_fingerprint_token_text(0xABCDE0, bech32)` == `_fingerprint_token_text(0xABCDEF, bech32)` == `'40x7'` (and `'VPG6'` for base32, `'NF6Y'` for crockford). This directly contradicts the spec's "**guaranteed** to avalanche on any input change" for these alphabets.
  - **base58 / base36 / decimal (the mod-fallback path):** the spec states these
    "never reach the large-input path." **They do.** A 200-character base58 or
    base36 string is truncated (byte length 150 > 64) and routed through the
    middle path; measured `truncated=True, ntok=20`. The mod fallback then
    aliases group values: base58 maps the 6 group values 58–63 onto chars 0–5,
    **base36 maps 28 of 64 group values onto duplicates**, so the displayed
    middle for base36 carries dramatically less than 80 bits and is heavily
    non-injective. (Decimal alone is safe by accident: a raw decimal string of
    >20 digits is classified as **hex** by the parser before it can reach the
    decimal path, so decimal never truncates in practice — but that is a
    parser side-effect, not the spec's stated reason.)
- **Exploit path.** A T1+T5 attacker who has matched a target's head-192 and
  tail-192 of a bech32/base32/crockford input now needs only an **80-bit**
  partial preimage (still infeasible by brute force, but 2¹⁶× cheaper than
  claimed) to make the *middle text* identical. The read-aloud / screen-reader
  comparison that v6 specifically set out to protect (`this.i:v6fpmid1`) is
  then defeated for those alphabets even though the digests differ — exactly
  the failure mode v6 claimed to "guarantee" against. For base36 the
  read-aloud middle is weak enough to be a realistic target. See
  `/tmp/entviz-collision-candidates.txt` rows 2–5 for the rendering collisions.
- **Recommended action.**
  1. *Spec fix (cheap, do first).* State the displayed-middle entropy
     **per alphabet** (96 bits for hex/base64url; 80 for the 5-bit alphabets;
     "reduced, non-injective" for base58/base36) and **delete** the false claim
     that non-power-of-2 alphabets never reach the path — or make it true by
     also routing oversized base58/base36 cores to a hex re-encode on the
     middle path.
  2. *Code option (stronger).* For the middle cells specifically, render all 24
     bits even on 5-bit alphabets by allowing a 5th character (or by mapping the
     full 24-bit value through the alphabet with carry), so the displayed text
     is injective on the middle bytes and the avalanche claim becomes true.
  3. *Test.* Add a regression test asserting that for each alphabet that can
     reach the large-input path, two inputs whose digests differ produce
     different middle text — and currently *expect it to fail* for bech32/base36
     until (1) or (2) lands, so the gap is tracked.

---

### F2: The displayed middle (digest bytes 24–35) is no longer independent of the gestalt channels it must be compared against

- **Layer:** ALGO
- **Severity:** LOW (defense-in-depth; not a standalone exploit)
- **Confidence:** CONFIRMED (analysis of which bytes feed which channels)
- **Threat-model attacker:** T1 + T6
- **Location:** `src/entviz/pipeline.py` (color bar `_two_bit_color_usage` over
  all 64 digest bytes; median/quartile over `used_ftoks` which for a large
  input is ftoks 0..19, *including* the four displayed ftoks 8–11; the four
  fingerprint cells' own surround is `render_edges(ftok)` for ftoks 8–11).
- **Finding.** v5's middle (body slices) drew from input bytes that did **not**
  feed any gestalt channel — the middle text and the gestalt were independent
  evidence. v6's middle *is* a slice of the fingerprint (bytes 24–35), and those
  exact bytes also (a) contribute 16 of the 256 color-bar 2-bit slices, (b) are
  the literal quants of the four fingerprint cells' own surround patterns, and
  (c) are candidates for the median ftok and quartile ftoks (measured P(≥1 of
  ftoks 8–11 is a quartile ftok) ≈ 0.62 on a 20-ftok input). Consequently, an
  attacker who grinds to match the displayed middle text simultaneously matches
  those four surround patterns *for free* and nudges the median/quartile/colorbar
  toward a match. The "match the middle **and** independently match the gestalt"
  framing in the spec/this.i overstates the joint barrier: the two are
  positively correlated, not independent.
- **Exploit path.** Not exploitable alone — the dominant cost is still the
  partial preimage of F1. The finding is that the *defense-in-depth multiplier*
  the spec implies (middle text × gestalt as independent channels) does not
  fully hold for v6 the way it held for v5's body slices.
- **Recommended action.** *Spec wording.* Note that the v6 middle text and parts
  of the gestalt are derived from the same digest region and are therefore
  correlated evidence, not independent; do not claim multiplicative
  independence between "matching the middle" and "matching the gestalt." If
  independence is desired, draw the displayed middle from a digest region
  disjoint from the median/quartile/colorbar inputs (hard — color bar uses the
  whole digest) or accept it as documented. Low priority.

---

### F3: Per-cell edge-color discrimination still collapses under deuteranopia/protanopia; v6 mitigated only the color bar, and there is still no CVD test

- **Layer:** ALGO + UX
- **Severity:** MEDIUM
- **Confidence:** LIKELY (computational CVD simulation from prior review; not
  re-run here, but the palette is unchanged in `colors.py:30`)
- **Threat-model attacker:** T4 (and any CVD user)
- **Location:** `src/entviz/colors.py:30` (`POSSIBLE_EDGE_COLORS`, unchanged
  since v4); `docs/spec.md` edge-color and CVD claims.
- **Finding.** This is prior finding F6, partially mitigated and partially open.
  v6's color-bar letters (`w/g/r/b/k`) are a real improvement for the *color
  bar* — they give CVD/mono/CSS-filtered users a verbal discriminator on the
  single most habituation-relied channel, which is the right place to spend the
  fix. **But** the per-cell *edge color* (the surround-ring color, chosen by
  weighted-RGB-nearest from the same 4-color palette) is untouched: gold vs red
  still collapse to ΔE ≈ 27 under deuteranopia (prior review's measurement),
  below the paper's own severe-CVD JND of 50–60. The spec still claims
  "perceptual selection ensures that even color-blind viewers can detect each
  cell as a separate object distinct from the background" — detection from
  background survives (luminance), but **discrimination between gold and red
  edge rings does not**, and the surround ring is the most prominent per-cell
  cue. There is still no CVD-simulation test in the suite (419 tests, none
  assert pairwise palette ΔE under CVD).
- **Exploit path.** A T4 attacker presenting two entvizes to a known-CVD user
  leans on differences carried by gold-vs-red surround rings; the user
  perceives the rings as the same color and falls back to the (lower-bandwidth)
  text/blank channels.
- **Recommended action.** Either (a) re-tune the palette so all pairs hold
  ΔE ≥ 50 under deutan/protan/tritan simulation (a spec change that invalidates
  prior renders — flag the cost), or (b) downgrade the spec's CVD claim to
  "detectable from background, not always discriminable pairwise under severe
  CVD," and lean on the now-lettered color bar + blank map + text as the CVD
  comparison path. Add the CVD ΔE snapshot test either way.

---

### F4: No user-facing guidance for the comparison surface or the "fingerprint of" semantics; the burden of the same/different asymmetry is entirely on the user

- **Layer:** UX
- **Severity:** MEDIUM
- **Confidence:** CONFIRMED (absence in repo)
- **Threat-model attacker:** T2 + T6 (and honest-user error)
- **Location:** `README`/docs (no recommended comparison surface); the
  `fingerprint of` marker is well-specified visually (`docs/spec.md` label-strip
  step) but its *meaning* for the reader is documented only in the spec, not in
  any artifact a comparing user sees.
- **Finding.** This is the unresolved core of prior F5 and the
  Residual-Unknowns. The spec now does a good job *visually*: `fingerprint of`
  is bold dark-red, the type parenthetical carries the byte count
  (`fingerprint of hex(130):` — confirmed in output), and the marker correctly
  signals a non-linear read. But there is still (a) no documented recommended
  comparison surface (side-by-side, same font, same scale, same background —
  without which "near-collision resistance" is unverifiable in the field), and
  (b) no user-facing explanation that a `fingerprint of` entviz's middle cells
  are a *hash readout*, so two such entvizes can share all 22 cells of text and
  still be different inputs, and the gestalt must be trusted. A first-time
  reader encountering `fingerprint of hex(130):` has no affordance telling them
  what it means; the spec's three-point "a reading user should…" list lives only
  in the spec.
- **Exploit path.** T6 habituated user (or honest user under time pressure)
  reads the middle cells as if they were input bytes, or compares two long
  entvizes by text alone, biasing toward "same." T2 controlling one rendering
  surface (different scale/font/zoom across tabs) widens the gap further.
- **Recommended action.** *Documentation, cheap.* Add a short "How to compare
  two entvizes" section to the README and a one-line legend/tooltip convention
  for `fingerprint of`. Document the asymmetry ("any visible difference → reject;
  matching is never proof of identity"). No code change required.

---

### F5: Large-input blanks can split the head/tail token blocks, eroding the "recognize the head/tail" workflow the design relies on

- **Layer:** UX (+ minor ALGO)
- **Severity:** LOW
- **Confidence:** CONFIRMED (layout dump)
- **Threat-model attacker:** T6
- **Location:** `src/entviz/pipeline.py:106–116` (v6 large inputs now use the
  short-input median/quartile blank shift); `docs/spec.md` large-input
  handling.
- **Finding.** v6's unification of blank placement (`this.i:v6blnkun`) is a
  genuine improvement — it restores a per-input CRC-like blank signal that all
  large entvizes previously lacked. The side effect: a blank can now be inserted
  **inside** the head or tail group. Measured layout for `"ab"*65`: a blank
  lands at cell index 5, between head tokens, so the head's 8 real-entropy
  tokens are no longer a contiguous visual block. The spec's rationale for H=8/
  T=8 is that the head/tail are "the real-entropy anchors a user recognizes and
  can verify against a known value" — a recognition task that benefits from
  contiguity. Splitting the head with a blank mildly degrades that (the user
  must mentally skip the blank to reassemble the head). Reading order is
  preserved, so correctness is unaffected; this is purely a recognition-ergonomics
  cost.
- **Exploit path.** Marginal. A T6 user who learned to recognize their key's
  head as a 2×4 block now sees it fragmented; cross-checking is slightly slower
  and more error-prone. Not a collision vector.
- **Recommended action.** Accept as a documented tradeoff (the CRC gain likely
  outweighs the recognition cost), **or** constrain the blank shift on large
  inputs to avoid inserting blanks within the head (indices 0–7) and tail
  (indices 12–19) token runs, placing them only at the head/middle and
  middle/tail boundaries or after the tail. If accepted, note it in the spec's
  large-input subsection.

---

### F6: `parse('badcafe')` and similar short odd-length all-hex strings classify as EOS, not hex — F3's crash is fixed but the misclassification F1(2026-05-27) warned about partially survives

- **Layer:** ALGO + IMPL
- **Severity:** LOW
- **Confidence:** CONFIRMED
- **Threat-model attacker:** T3 (or unwitting user)
- **Location:** `src/entviz/entropy.py:579` `parse_eos_address`, registered
  after `parse_hex` (`:787`); `EOS_REGEX` at `:112`.
- **Finding.** The prior review's F1 fix correctly moved `parse_eos_address`
  after `parse_hex`, so *even-length* lowercase hex now wins as hex. But
  `parse_hex` returns `None` for **odd-length** non-`0x` input (`:769`), so an
  odd-length all-lowercase-hex-ish string like `'badcafe'` (7 chars) falls
  through `parse_hex` and is caught by EOS, yielding `Parsed(type='EOS',
  alphabet=base64,…)`. So `render('badcafe')` (EOS, base64 tokenization) and
  `render('badcafe0')` (8 chars → hex) produce different entvizes for what a
  user reads as "the same hex with one more digit," and `'badcafe'` is labeled
  `EOS:` rather than `hex(7):`. This is a smaller residue of the F1 class
  (narrow-heuristic format catching generic hex) that the move-after-hex fix
  did not fully close because of the odd-length gap.
- **Exploit path.** T3 confusion / mislabeling; low impact (no two distinct
  values collide — it is a labeling and tokenization inconsistency, the inverse
  of a collision). Mostly a correctness/trust wart: the `EOS:` label on a
  pasted hex fragment is misleading.
- **Recommended action.** Tighten `EOS_REGEX` to require a minimum length (real
  EOS accounts are ≥ 12 chars, or use the 12-char `[a-j1-5]` branch only), or
  require at least one character outside the hex alphabet, so short hex-shaped
  fragments cannot be claimed by EOS. Add a test asserting `parse('badcafe')`
  is not EOS.

---

### F7: Stale v5 comments in `pipeline.py` and `entropy.py` describe behavior the v6 code no longer implements (fixed separator blanks at cells 8/13)

- **Layer:** IMPL (maintainability / correctness-of-record; security-adjacent
  because it misleads future auditors about where blanks land)
- **Severity:** LOW
- **Confidence:** CONFIRMED
- **Threat-model attacker:** none directly (audit-integrity risk)
- **Location:** `src/entviz/pipeline.py:70–83` (comment block: "fixed 22-cell
  budget: H=8 + 1 blank + M=4 + 1 blank + T=8 … cell indices 8 and 13 are the
  separator blanks … We bypass the median/quartile blank insertion entirely");
  `src/entviz/entropy.py:947–953` (`_MAX_TOKENS` comment: "Two separator blanks
  (at cell indices 8 and 13) … the pipeline inserts them around the middle
  group at render time") and `:1066–1068` (`tokenize_entropy` docstring: "the
  pipeline inserts the two separator blanks at cell indices 8 and 13").
- **Finding.** The v6 code (`pipeline.py:114` `assign_cell_indices(... median,
  sort_keys=used_ftoks)`) explicitly uses the same median/quartile blank shift
  as short inputs, and `this.i:v6blnkun` documents the removal of the fixed
  separators — but the inline comments and two docstrings still describe the v5
  fixed-blank-at-8/13 scheme that was deleted. An auditor reading the source
  (as I did) would initially conclude blanks are at fixed positions 8/13; only
  running the code (blanks measured at e.g. [5,13,17,23] for one input,
  [3,5,12,23] for another) reveals the comments are stale. This is exactly the
  kind of spec-vs-implementation-drift the prompt's section E flags, except here
  the *comments* drifted from the *code*.
- **Recommended action.** Update the three comment/docstring blocks to describe
  the v6 median/quartile shift. No behavior change. (The behavior is correct and
  tested; only the documentation-in-code is wrong.)

---

## Additional Patterns Noted

- **bech32/base32/crockford head & tail cover ~160 bits, not 192.** `tokenize_entropy`
  computes `head_chars = 8·token_len = 32 chars`, and at 5 bits/char that is 160
  bits (the spec's "192 bits, rounded to whole characters" rounds *down* by 32
  bits for these alphabets). Harmless but the spec's "first 192 bits / last 192
  bits" requirement (line 45) is not literally met for 5-bit alphabets;
  `entropy.py:1087`.
- **F-A9 (bg = 2 low bits of median ftok) persists, now interacting with the
  blank-map fill and fingerprint-cell frame.** Both the map fill and the
  fingerprint-cell border are gold-on-white / white-otherwise, keyed off the
  same 2-bit bg. A T1 grinder matching the 2-bit bg (expected ~4 tries) also
  fixes those two derived colors. Acknowledged hint-channel risk; unchanged.
  `colors.py:48`, `pipeline.py:335,382`.
- **F-A1/F-A7/F-A8 (thread-safety of disproof order, `--output` path, sys.path
  shadowing) — disproof order is now built eagerly (F-A1 fixed, `entropy.py:829`);
  `app.py --output` still writes any user path with no `--force` (F-A7 open, low
  impact for a CLI).** `bin/entviz.py` no longer exists (src-layout), so F-A8 is
  moot.
- **Degenerate min==max blank-map case is handled** (ring + concentric dot,
  `pipeline.py:415`); reachable only with a single used ftok (a 1-token input
  forced to a 2×2 grid). Good.
- **Color-bar red letter contrast:** red `#ff3f2f` sits at Oklab L ≈ 0.657, so
  the `<0.6 → white` rule gives it a **black** letter `r`. On a red band this is
  the documented intended behavior, but black-on-red is the lowest-contrast
  band/letter pair in the set; verify it stays legible at small sizes (perceptual,
  unverified here). `pipeline.py:905`.
- **No `viewBox`-less path remains** and **no `mix-blend-mode`** anywhere
  (asserted by `test_v6_blank_map.py`); both prior gaps closed.
- **SVG injection is safe** on every path probed (hostile input text → base64url
  fallback; hostile SSH comment → escaped `&lt;script&gt;` in the bottom label).
  lxml `.text =` escaping holds. Still no dedicated hostile-input injection test
  in the suite — worth adding for regression insurance.

---

## Residual Unknowns

Static analysis + byte-level probing cannot settle these:

1. **Does the 80-bit non-injective middle (F1) matter perceptually for a
   read-aloud comparison of bech32/base36 inputs?** Smallest experiment:
   construct two >512-bit bech32 inputs whose digests differ only in the dropped
   nibbles (a short grind on a reduced-round proxy, or just synthesize digests),
   render both, and have a person read the middle cells aloud — confirm they are
   identical. This validates whether F1 is a paper cut or a real read-aloud
   defeat.
2. **CVD discrimination of the unchanged gold/red palette** (F3) — still needs
   confirmation with CVD observers or Ishihara-calibrated simulation; the ΔE
   math says collapse, unverified with humans.
3. **Does splitting the head with a blank (F5) measurably slow recognition?** A
   small timing study (head-as-contiguous-block vs head-split-by-blank) would
   settle whether F5's recommendation is worth the code.
4. **Black-on-red color-bar letter legibility at 12pt and below** — render and
   inspect; the contrast ratio is the lowest in the set.
5. **The habituated-landmark perceptual budget (~25–40 bits)** remains the
   single most important unmeasured quantity, as in the prior review; v6's
   color-bar letters and varying large-input blanks should *raise* it, but only
   a user study confirms by how much.

---

## Recommended Next Steps for the Maintainer

Ranked by bang-for-buck.

1. **Fix the spec's per-alphabet middle-entropy claim and the false
   "non-power-of-2 never reaches the path" statement (F1).** Cheapest, highest
   value: correct text + one regression test. Decide whether to also make the
   5-bit middle injective in code (render all 24 bits).
2. **Update the stale v5 separator-blank comments in `pipeline.py` and
   `entropy.py` (F7).** Zero behavior risk; prevents the next auditor from
   chasing a phantom layout. One commit.
3. **Add a hostile-input SVG-injection regression test** (input
   `'<script>alert(1)</script>'` and a hostile SSH comment) asserting the output
   contains `&lt;script` and never `<script`. Implementation is safe today;
   this freezes it.
4. **Add a CVD ΔE snapshot test and decide F3** — either re-tune the palette
   (breaking change, flag it) or downgrade the spec's CVD claim and lean on the
   now-lettered color bar + blank map + text.
5. **Tighten `EOS_REGEX` (F6)** so short odd-length hex fragments aren't
   mislabeled EOS; add the `parse('badcafe') is not EOS` test.
6. **Document a recommended comparison surface and a `fingerprint of` legend
   (F4).** README-level, no code.
7. **Consider constraining large-input blanks away from the head/tail token runs
   (F5)** if the recognition cost is judged to outweigh the CRC gain.
8. **Update `docs/threat-model.md`** with the two extensions in this report's
   threat-model section (broadened T5; displayed-fingerprint correlation
   sub-case of T1).

Constructed/measured collision and near-collision seeds are saved at
`/tmp/entviz-collision-candidates.txt` for use as regression fixtures.
