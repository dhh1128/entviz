# entviz threat model

This document is the explicit frame against which entviz's design, code, and
human-factor decisions should be evaluated. It exists so that security and
usability findings can be discussed as concrete answers to "does the system
defend against attacker X with capability Y trying to achieve outcome Z?"
rather than as abstract risk lists.

The initial version of this model was drafted by the adversarial review of
2026-05-27 (see `reviews/adversarial-2026-05-27.md`); update it whenever a
finding changes the assumed attacker capabilities or the boundary of what
entviz is responsible for defending.

---

## Assets

**Primary.** The user's belief that two entropy values are equal (or that they
are not equal). entviz exists exclusively to support this single human
security judgment. Everything else in the design serves it.

**Secondary.** The integrity of a rendered SVG when embedded in a third-party
HTML document — i.e., that the displayed entviz cannot be silently altered
(content-wise) or made to influence the embedding page (script injection,
style bleed) merely by existing on the same page.

---

## Trust boundaries

**entviz trusts:**

* The input bytes, after the spec-defined normalization step has been applied.
* The display device's color and resolution fidelity within the spec's stated
  envelope (16M colors, ≥256 colors, ≥256 greys).
* The user's font stack to render a monospace family with reasonable glyph
  shapes for the alphabets in use.
* The browser (or other SVG renderer) to honor `clip-path`, `mix-blend-mode`,
  and standard SVG semantics.
* The user to read both label strips (top and bottom) and to understand the
  truncation marker `^…$ ` when it appears.
* The user's attention during comparison — i.e., that the user is genuinely
  looking, not glancing.

**entviz does not trust:**

* Attacker-controlled HTML or CSS surrounding an embedded SVG.
* The user to remember exact pixel-level details across sessions; entviz is
  for comparison against a present reference, not for recall.
* The input source to canonicalize bytes before passing them in (entviz
  normalizes); but the user is trusted to paste *the* value they meant to
  compare.

---

## User note (out-of-band caption)

The optional `--note` caption (see `spec.md` "User note" and
`this.i:usrn0te1`) is an annotation supplied by **whoever runs the
renderer**, not by the input string. It is deliberately *out-of-band* so it
adds no attacker capability:

* It **never enters the entropy core or the fingerprint**, so it cannot
  affect any comparison channel; it is outside the comparison surface. A
  *mismatched* note only makes two entvizes look more different (the safe
  direction), so it cannot be used to forge a false match (the primary win
  condition).
* In the security-relevant flow — a defender renders a value received from
  an untrusted party — the attacker controls the bytes but not the flag, so
  cannot inject a note. An attacker who instead hands over a *pre-rendered*
  SVG already has full control of the rendering surface (**T2**) and could
  draw anything; the note grants nothing new.
* The residual risk is mild human *false-reassurance* from an
  attacker-chosen caption in a rendering the attacker controlled. It is
  bounded by aggressive sanitization (ASCII alphanumeric, single token,
  ≤8 chars, strict-reject-on-violation — no control/bidi/homoglyph
  characters, no whitespace to fake authoritative phrases), by rendering the
  note in quiet gray (`#808080`) in the *bottom* strip (never on the trusted
  top type-label), and by a `data-user-note` attribute that keeps it
  structurally distinct from algorithm-derived suffix content. An in-band
  caption syntax was rejected because, on the arbitrary-text fallback path,
  no delimiter is safe to reserve and it would overload the trusted label
  channel (see `this.i:usrn0te1`).

---

## Attacker tiers

These are the assumed adversary capability classes. A finding should always
name which tier(s) it applies to.

* **T1.** Can choose one of the two compared values and grind it offline.
  Compute is cheap; SHA-512 is fast; an attacker can iterate millions to
  billions of candidate inputs looking for one whose entviz best matches a
  target.
* **T2.** Can control the rendering surface for one or both entvizes —
  surrounding CSS is in scope, font substitution, scale, screenshot vs. live
  render, print vs. screen.
* **T3.** Can manipulate the input string at the encoding layer: change case
  for case-insensitive alphabets, add or remove a leading prefix, exploit
  alphabet ambiguity (a string valid in more than one parser), attach
  trailing junk that the parser may silently drop, or present a value in a
  **non-canonical or alternate encoding** that decodes to the same bytes
  (base64/base58/bech32 malleability, alternate alphabets, padding/trailing
  bits). The last of these is structurally defused by hashing **text, not
  decoded bytes** — see *Fingerprint hashes text (encoding-layer defense)*
  below.
* **T4.** Can manipulate the user's environment: induce a CVD-simulating
  filter, force a monochrome display, force a small viewport, substitute a
  hostile or narrow-glyph font.
* **T5.** Can construct long inputs (>512 bits) whose displayed **head**
  (first 8 tokens) and **tail** (last 8 tokens) match a
  target. In v6 the 4 middle cells additionally display a **96-bit hex readout
  of a second, domain-separated SHA-512** of the whole input, so T5 must also
  produce a 96-bit (injective, uniform across alphabets) partial preimage of
  that second digest to match the text channel — and, because every gestalt
  channel binds the full input through the *primary* fingerprint, must
  independently match the gestalt as well.
  *(v6 note, closing adversarial-2026-06-02 F2: the displayed middle is
  derived from a digest that is **domain-separated** from the primary
  fingerprint, so matching the middle text does NOT also match the color bar
  or surround "for free" — the middle-text preimage and the gestalt match are
  independent requirements. The first v6 draft read the middle from primary
  digest bytes that also drove those channels, making the two correlated; that
  is no longer the case.)*
* **T6.** Habituated insider — the user has seen the "correct" entviz many
  times and now checks only one or two landmarks (color bar gestalt, blank
  positions, ellipse silhouette). The attacker only has to match those.

A realistic attacker frequently combines tiers (T1+T5+T6 is the canonical
worst case for a high-value compromise).

---

## Attacker win conditions

**Primary win.** Produce `A ≠ B` such that the user, comparing `entviz(A)`
and `entviz(B)` under realistic conditions, concludes they are the same. This
is the failure of *near-collision resistance* in the sense of Perrig & Song
(1999) and the entviz paper (2025); it is what any security claim made by
entviz must defend.

**Secondary wins.**

* Cause `entviz(A)` to render differently depending on environmental factors
  that should not matter (encoding form, alphabet classification, case for a
  case-insensitive alphabet, normalization form).
* Cause a stored entviz to render differently after being embedded in another
  document (the documented clip-path-id-collision case, or analogous bugs).
* Inject script or stylable content via the rendered SVG that affects the
  embedding page.
* DoS the renderer with a crafted input (uncaught exception, super-linear
  resource consumption).

**Not a win, but still worth tracking.** Make `entviz(A)` differ from
`entviz(A)` across two visually-similar but byte-distinct inputs that
*honestly* represent different values — this is the intended behavior of the
algorithm, not an attack, and the spec's avalanche guarantee depends on it.
Findings should not treat correct behavior as a defect.

---

## Out of scope

* Confidentiality of the input. entviz is a comparison aid, not a secrecy
  primitive.
* Compromise of the underlying cryptographic hash (SHA-512). If SHA-512 falls,
  entviz is a small part of a much larger problem.
* Defenses against a user who chooses not to look at the entviz at all, or
  who looks at only one of two entvizes being compared.
* Tampering with the user's clipboard, keyboard, or paste buffer.

---

## Fingerprint hashes text (encoding-layer defense)

The fingerprint is SHA-512 of the **canonical normalized text** of the entropy
(its UTF-8 bytes), **not** the value's decoded raw bytes (see `spec.md`,
*Why the fingerprint hashes text, not decoded bytes*). This is a deliberate
defense against the T3 encoding-layer attacker, on three counts:

* **No decoder-malleability collisions.** Hashing decoded bytes would insert a
  parser ahead of the hash, and many text encodings are malleable — distinct
  strings decode to identical bytes. Under byte-hashing those become *different
  text, identical gestalt*: a collision an attacker manufactures to make a
  tampered value's high-bandwidth channels match a target's (a **primary win**).
  Hashing the normalized text removes the lever: different text → different
  fingerprint. (Case and a few documented punctuation/dash conventions are the
  *only* normalizations applied, each narrow and specified.)
* **Fail-safe failure mode.** The cost is that two encodings of the *same* value
  render differently (a **secondary-win** "renders differently under encoding
  form"). This is an accepted, fail-safe outcome: it can only cause a *false
  negative* (a reader fails to notice two encodings match and investigates
  further), never a false "same." A verification tool should err this way.
* **Cross-implementation determinism.** Byte-decoding every alphabet identically
  across the certified implementations (base58 leading zeros, bech32 5-bit
  unpacking, base64 trailing-bit policy) is a large, divergence-prone surface;
  a mismatch would make the *same input* fingerprint differently per
  implementation. Text-hashing reduces the shared surface to case/punctuation
  normalization.

Identity-bearing prefixes (CESR derivation codes, LEI LOU, SWHID/gitoid
object-types) are still bound — by being present in the hashed *text* (kept in
the core, or folded in as `prefix ‖ core`), not by decoding. See `spec.md`'s
swap-test rule and `this.i:s3mpr3fx` / `this.i:h4shtext`.

---

## Accepted risks (per spec)

* **Cross-encoding non-invariance.** The same value in two encodings (hex vs.
  base64 of one digest; one CID in two multibases) renders as two different
  entvizes. This is intentional (see *Fingerprint hashes text* above): entviz
  protects *"this value in its canonical textual form."* Fail-safe; not a goal
  to remove.
* **Pure-text environments.** entviz is explicitly not designed for them; use
  randomart or similar instead.
* **Recall of all details.** The user is not expected to remember every cell
  of an entviz between sessions; comparison against a saved copy is the
  intended workflow.
* **Fine nucleus color gradations under reduced color depth.** The nucleus
  background is a hint channel, not a primary discriminator; subtle RGB
  differences below JND are acknowledged not to be reliable.

---

## How to apply this model

When evaluating a proposed change or filing a security/UX finding:

1. Name the asset that would be harmed.
2. Name the attacker tier(s) the change defends against or exposes.
3. Name the win condition the attacker would achieve.
4. State whether the change introduces a new trust assumption or relaxes an
   existing one.

A finding that does not map to one of these is either decoration or a bug
report for a different document (e.g., spec-improvement-notes, this.i).
