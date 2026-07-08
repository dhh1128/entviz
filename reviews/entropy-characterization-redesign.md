# Entropy characterization redesign — locked decisions + staged plan

_Design session 2026-07-07. Status: design locked, awaiting Stage 0 execution._

## Problem

The parser's output type — `Parsed(type, alphabet, prefix, core, suffix, prefix_semantic)`
— conflates several orthogonal facts:

- `type` is a single opaque **display label** that fuses (a) scheme/namespace,
  (b) semantic role of the bits, (c) network/variant, and (d) size. Downstream
  consumers (the React component, pills) have to string-parse the label back
  apart. This is the React pain and the direct blocker for promoting
  `entropyType` (tick 3ek3).
- `prefix` carries three different roles — presentation framing to strip,
  identity discriminator to fold, self-describing scheme text to show —
  patched by the `prefix_semantic` boolean. That boolean is the smoking gun of
  the overload. This is the "confusion in the prefix."

Root cause: **the output type is a label, not a model.** The label should be
*derived from* a structured characterization, not *be* it.

## The sharpened model (lean but explicit)

An input is characterized along independent axes; the label is derived:

```
Characterization:
  encoding    : Alphabet            # how it's written; drives tokenization (already clean)
  scheme      : str | None          # which recognizer fired; None = bare encoding
  role        : Role | None         # CLOSED enum; asserted only when the GENERIC recognizer determines it
  qualifiers  : dict                # network / variant / algorithm / version — independently-varying facets
  size_basis  : {decoded, utf8}     # how size_bits is measured (see Wrinkle 1); scheme-driven
  size_bits   : int                 # value size in bits; REPORTING only; NOT the truncation basis (see below)
  parts       : [Part(text, bind)]  # bind ∈ {none, fold, core}; replaces prefix + prefix_semantic
  # label is DERIVED and stays byte-identical for now
```

- `Role` is a **closed enum**: `key | signature | digest | address | identifier`
  (plus `null`). Asserted only where the format self-declares it (CESR
  `B/C/D/E`, SSH algorithm, CID codec, multihash fn, blockchain address). For
  arbitrary text it is `null` — entviz does not guess. This is *more honest*
  than implying a role via a label string.
- `entropyType` (tick 3ek3) becomes a defined derived field: `scheme ?? encoding`.
  Canonical across all five impls, not re-derived per impl.

### `bind` dissolves the "prefix" overload

Normalization cuts the input into ordered **parts**; each part declares a
`bind` mode — how it enters the fingerprint — independently of whether it is
displayed:

- **`core`** — in the hashed core text; rendered in cells. (CESR derivation
  code, LEI LOU code, any in-alphabet leading discriminator stay here.)
- **`fold`** — identity-bearing but a different alphabet/framing from the body;
  kept as a prefix, hashed as `prefix ‖ core`, shown in the label, not in
  cells. (SWHID/gitoid object-type, `did:<method>:`, `urn:<nid>:`.)
- **`none`** — carries no identity bits; binds nothing. Shown in the label when
  it aids recognition (`0x`, a multibase selector, a base58check checksum
  suffix) or dropped entirely when it is a free annotation (SSH comment, DID
  URL tail).

"Presentation prefix", "identity prefix", and "self-describing scheme text"
become three `bind` values; *display* becomes an orthogonal property. The
`prefix_semantic` boolean disappears.

## Locked decisions

1. **Lean-but-explicit model** (above): `encoding`, `scheme`, `role`,
   `qualifiers`, `size_bits`, `parts` — resist field explosion.
2. **Model-only + byte-identical labels first.** Enrich the parse output and
   `model.json` additively; keep the derived label string byte-identical.
   Fingerprint unchanged → goldens/PNG/SVG unchanged → Tier B untouched.
   Pills / label-evolution are a separate fast-follow.
3. **`role` is a closed enum** (`key|signature|digest|address|identifier|null`).
4. **Sequence:** model sharpening → 3ek3 (`entropyType`) → 7srp (dev API docs)
   → announce.

## Resolution A — `size_bits` two-branch definition (spec-ready)

> **`size_bits` (value size, presentation-independent).** The characterization
> carries a single size measure, `size_bits`, **always a whole multiple of 8**,
> computed from the **core** — never the input string, never a folded identity
> prefix. It is defined by one of two branches according to whether the core is
> an *encoding of an underlying byte string* or is *inherently text*:
>
> - **Encoding cores** — the core is a serialization of binary under a declared
>   alphabet (hex, base32, bech32, base64, base64url, base58, base36,
>   crockford32, decimal). `size_bits = (decoded byte length of the core) × 8`.
>   For the power-of-2-density alphabets (hex = 4, base32/bech32/crockford32 = 5,
>   base64/base64url = 6 bits/char) this equals
>   `floor(core_char_count × bits_per_char / 8) × 8`; base64 `=` padding is
>   stripped before counting and any sub-byte final-group bits are zero and drop
>   out. For the non-power-of-2 alphabets (base58, base36, decimal)
>   implementations MUST decode the core to its integer value and take its
>   minimal byte length — they MUST NOT use the tokenizer's `bits_per_char`,
>   which is a token-packing convention (base58 = 6) that overstates true
>   density (base58 ≈ 5.86).
> - **Text cores** — the core is inherently text with no underlying binary: a
>   DID method-specific-id, a URN namespace-specific string, or the UTF-8
>   fallback. The text *is* the value, so
>   `size_bits = (UTF-8 byte length of the core text) × 8`. For the UTF-8
>   fallback this equals the original input's byte length (the value shown as
>   `txt(N)`).
>
> The branch is selected by an explicit **`size_basis ∈ {decoded, utf8}`** field
> set by the parser, driven by **scheme** — did / urn / UTF-8-fallback are
> `utf8`, everything else is `decoded`. It MUST NOT be inferred from `alphabet`
> (a DID msi and a real base64url value both declare `base64url`) nor from the
> content's appearance (a `did:jwk` msi is base64url-encoded JSON but is a text
> core, because entviz never decodes a DID msi).
>
> `size_bits` measures the **serialized value entviz renders**, not the
> underlying cryptographic material. A CESR `E` (Blake3-256) primitive reports
> `size_bits = 264` — 33 core bytes including the derivation-code alignment
> byte — not the 256 bits of the digest it carries. The semantic-material size,
> when known, is conveyed by `qualifiers` (e.g. `algorithm`), never by
> `size_bits`.
>
> **`size_bits` is a reporting field only — it is NOT the >512-bit truncation
> basis.** The large-input (head/middle/tail) trigger MUST keep using the
> existing tokenization byte length (`len(core) × bits_per_char // 8`),
> unchanged. The two measures coincide for encoding cores but diverge for text
> cores (a 65–86-char text core truncates under `size_bits` but not under the
> tokenization basis); re-pointing the trigger at `size_bits` would move the
> truncation boundary and break goldens. Keep them distinct and named
> distinctly.

## Resolution B — approximation + exclusion caveats (spec-ready)

> Where an encoding core is a **substring** of a larger checksummed value (a
> base58check body whose version and checksum are split into `prefix`/`suffix`),
> the decoded substring is not independently byte-aligned, so `size_bits` is
> **approximate**. This is accepted: `size_bits` feeds only the label and the
> coarse `>512`-bit threshold, neither of which needs bit-exact precision.
>
> A **folded identity prefix** (`bind = fold`: SWHID/gitoid scheme,
> `did:<method>:`, `urn:<nid>:`) is **not** counted in `size_bits`: it binds
> the fingerprint but is not part of the rendered core.

## Pressure-test findings (rounds 2 & 3, 17 corpus cases)

Tested against the parser oracle on: cesr-said-e, btc-legacy, cid-v1,
did-ethr-network, gitoid-blob-sha256, text-lorem, urn-isbn/oid/uuid,
snowflake-19, ssh-ed25519, cid-v0, did-key-ed25519, lei-bloomberg, stellar,
eth-checksummed, did-peer-2, did-jwk-large, bitcoincash, did-web,
urn-nss-slash, did-pkh, did-webvh. Every derived label reproduced the corpus
bytes. Findings folded into the model above:

**Wrinkle 1 — `size_basis` must be an explicit field.** URN NSS, DID msi, and
the UTF-8 fallback all declare `alphabet = base64url`, but so do CESR / SSH /
EOS / real base64url. `alphabet` alone can't decide the encoding-vs-text
`size_bits` branch. `did:jwk`'s msi is base64url-encoded JSON yet is a **text**
core — entviz never decodes a DID msi — proving the basis is driven by
**scheme** (did/urn/fallback → `utf8`), not by whether the content looks like
an encoding. Fix: explicit `size_basis ∈ {decoded, utf8}` on the model.

**Wrinkle 2 (CRITICAL for model-only) — `size_bits` ≠ the truncation basis.**
The >512-bit head/middle/tail trigger uses `_core_byte_length` =
`len(core) × bits_per_char // 8` (a token-count proxy), *uniformly, even for
text cores*. `size_bits`'s text branch (UTF-8 × 8) gives a **different** byte
count for text cores, so a text core of **65–86 chars** truncates under
`size_bits` but NOT under the current code. They are two distinct measures:
- `size_bits` — honest value size, **reporting only**, feeds the label `(N)`.
- tokenization byte length (`_core_byte_length`, **unchanged**) — pixel-
  affecting, decides truncation.
They coincide for encoding cores, diverge for text cores. The truncation check
MUST keep using `_core_byte_length` as-is; do NOT re-point it at `size_bits`,
or goldens move. (did-peer-2: size_bits 808 vs trunc-basis 600 — both truncate
here, but the divergence window is real.)

**Wrinkle 3 (principle) — `role` comes only from the *generic* recognizer.**
`did:key` → identifier (not `key`); `did:pkh` (contains an ETH address) →
identifier (not `address`); `urn:isbn` → identifier (not `book`). v11 does no
per-method/namespace decoding, so asserting a narrower role would need logic
the spec excludes — and an impl that special-cases it diverges. (Contrast SSH,
where the *generic* SSH recognizer legitimately decodes `ed25519` → role=key.)

**Wrinkle 4 (principle) — `bind` is a property of the *part at the recognizer's
granularity*, not of a character's abstract role.** The `z` multibase selector
is `bind=none` as a standalone value but `bind=core` inside a `did:key` msi —
no contradiction, they are different parts. Same for CIDv0's `Qm`. Without this
rule, "multibase selector is presentation" and "did:key keeps its `z`" read as
a conflict.

**Deferred observations (not blockers; out of scope for model-only):**
- *Checksum-splitting is parser-discretionary and inconsistent:* BTC/LEI/
  Cardano split their checksum into a shown `suffix` (`bind=none`); Stellar's
  CRC and CIDv0's `Qm` multihash header stay inside the core (`bind=core`). The
  `parts` list represents each faithfully but makes the inconsistency visible —
  candidate Stage 2 cleanup.
- *CIDv0's `Qm` is constant-format framing* (bind=none by "constant for the
  format", like `0x`), a subtler presentation call than a true multibase
  selector; record the rationale when writing the spec.
- *`urn:uuid:…` vs bare UUID intentionally differ* (size_bits 288 vs 128,
  different fingerprint): the `urn:` is folded identity and the NSS is kept
  verbatim with dashes. By design — the model surfaces it rather than hiding it.
- *`bitcoincash:` is presentation by the swap test* (swapping the HRP forces
  the bech32 body to re-encode) yet is shown in the label, with
  `qualifiers.network` recovered from the body — validates display ⊥ bind.

## Worked decomposition (verified against the live corpus)

| # | input (corpus id) | `scheme` | `role` | `qualifiers` | `parts` (bind) | `size_bits` | derived label (byte-identical target) |
|---|---|---|---|---|---|---|---|
| 1 | `EBfdlu8R…_LFv` (cesr-said-e) | `cesr` | `digest` | `{algorithm: Blake3-256}` | 44ch → core | **264** | `CESR Blake3-256:` |
| 2 | `1A1zP1…DivfNa` (btc-legacy) | `btc` | `address` | `{network: mainnet, variant: legacy}` | `1`→none · 29ch→core · `vfNa`→none | **~168\*** | top `BTC legacy: 1...` · bot `...vfNa` |
| 3 | `bafybei…bzdi` (cid-v1) | `cid` | `identifier` | `{version:1, codec: dag-pb, hash: sha2-256}` | `b`→none · 58ch→core | **288** | `CIDv1 dag-pb: b...` |
| 4 | `did:ethr:0x5:0xf3be…0d74` (did-ethr-network) | `did` | `identifier` | `{method: ethr, network: "0x5"}` | `did:ethr:`→fold · `0x5:0x…74`→core | **368†** | `did:ethr:...` (no type) |
| 5 | `gitoid:blob:sha256:473a…1813` (gitoid-blob-sha256) | `gitoid` | `digest` | `{object: blob, algorithm: sha256}` | `gitoid:blob:sha256:`→fold · 64hex→core | **256** | `gitoid:blob:sha256:...` (no type) |
| 6 | `Lorem ipsum…elit.` (text-lorem) | `text` | `null` | `{}` | b64url re-encoding→core | **448** | `txt(56)->b64url:` |

`*` base58 substring core → approximate (Resolution B).
`†` folded `did:ethr:` prefix excluded from `size_bits`; core UTF-8 = 46 bytes = 368 bits (Resolution B).

The derived label reproduces today's label byte-for-byte in every case, so no
golden moves.

## Staged implementation plan

**Stage 0 — freeze the model in spec + Python reference (the oracle).**
- Add the `Characterization` model, the Resolution A `size_bits` two-branch
  decode table, and the Resolution B caveats to `docs/spec.md` as normative.
- Enrich `Parsed` / parse output and `model.json` **additively** (new fields;
  keep existing fields). Keep label derivation byte-identical.
- Add `this.i` stanzas (drafted below under `ch4rmod3l`).
- **Precondition to verify:** the conformance checker must **tolerate additive
  Tier-A fields** in `model.json`. Confirm before landing; if strict, relax it
  first.
- No fingerprint change, no pixel change, no golden regen. TDD: extend
  `tests/test_entropy.py` to assert the new structured fields per corpus case.

**Stage 1 — port + certify (rs / js / go / java).**
- Mirror the structured fields in each port; re-certify Tier A+B against the
  corpus.
- Special item: reconcile **entviz-js**'s existing
  `classifyInput().entropyType` / `typeName` split into the canonical model —
  it is the impl that already drifted, so it is the reconciliation risk.

**Stage 2 — fast-follow (separate, visible change).**
- Promote `entropyType` to the spec (tick 3ek3, now just `scheme ?? encoding`).
- Build React pills over the structured fields.
- Optionally evolve labels to show `size_bits` uniformly (`hex ·160b`), which
  also fixes the current `hex(chars)` vs `txt(bytes)` label-unit inconsistency.

**Stage 3 — developer API docs (tick 7srp) against the frozen model → announce.**

## `this.i` stanzas to add at Stage 0

Insert as siblings after `sufxbind`:

- `ch4rmod3l` — Entropy Characterization Model: axes (encoding/scheme/role/
  qualifiers/size_bits), closed `Role` enum, `parts`+`bind` replacing
  `prefix`+`prefix_semantic`; links `[[s3mpr3fx]]`, `[[sufxbind]]`,
  `[[h4shtext]]`, `[[lbldedup]]`.
- `s1zeb1ts` — size_bits two-branch definition + base58 approximation +
  fold-prefix exclusion (Resolutions A/B); links `[[ch4rmod3l]]`,
  `[[h4shtext]]`.

(A concise `ch4rmod3l` node is added now at design-lock time; `s1zeb1ts`
detail folded into it. Expand at Stage 0.)
