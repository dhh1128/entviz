# v14 — label redesign + checksum validation (locked design)

_Design approved 2026-07-09. Builds on the v13 characterization. Mechanically a
SPEC_VERSION bump v13→v14 (label output + new error vectors are spec-observable;
the version-match gate requires a distinct version)._

## Why

v13 cleanly separated the axes (encoding/scheme/role/qualifiers/size_basis/
size_bits) but the visible LABEL strings are still hand-fused per-parser
(`CESR Ed25519 nt pubkey:`, `hex(64):`, `txt(56)->b64url:`, `ETH: 0x...`). v14
makes the label a **pure projection of the v13 fields** through one consistent
grammar, and fixes a real correctness gap: bound checksums are shown in the
label but mostly NOT verified.

## Scope: this is TEXT + validation, not pixels

Label glyphs are excluded from the Tier-B raster, so **golden.png files do NOT
change**. Only the Tier-A `labels` field changes, plus new error vectors. Same
5-impl coordination as v13; smaller surface.

## New label grammar (top strip)

```
[fingerprint of ]PRIMARY[, MOD][, MOD…][, SIZE]
```

- Slot separator: **`, ` (comma-space)**. No trailing `:`, no trailing `...`.
- The label is composed from the **characterization fields**, NOT the old
  `Parsed.type` string. Add a `render_label(characterization) -> (top, bottom)`
  projection; every impl implements the same function over the shared fields.

**PRIMARY** (always present):
- Self-describing prefix schemes (did / urn / gitoid / swhid): the self-framing
  prefix itself, no body echo, no `...`: `did:key`, `urn:isbn`,
  `gitoid:blob:sha256`, `swh:1:rev`.
- Other schemes: the short scheme name: `ETH`, `BTC`, `LTC`, `BCH`, `ADA`,
  `XRP`, `XLM`, `EOS`, `UUID`, `ULID`, `LEI`, `snowflake`, `SSH`, `CESR`,
  `CIDv0`, `CIDv1`.
- `scheme == null`:
  - `size_basis == utf8` (UTF-8 fallback) → **`text`**.
  - `size_basis == decoded` (bare encoding) → the `encoding` name (`hex`,
    `base32`, `base58`, `bech32`, `b64`, `b64url`, `crockford32`, `decimal`).

**MOD** (zero or more, comma-joined; silent-default / loud-departure):
- CESR: the primitive with the redundant role word dropped — strip a trailing
  ` pubkey`: `Ed25519 nt pubkey`→`Ed25519 nt`, `Ed25519 pubkey`→`Ed25519`,
  `Blake3-256`→`Blake3-256`. (role=key/digest is implied by the primitive.)
- SSH: `qualifiers.algorithm` (`ed25519`, `rsa`, `ecdsa-nistp256`, `dss`).
- CID: `qualifiers.codec` always (`dag-pb`/`raw`/`dag-cbor`); `qualifiers.hash`
  only on departure from `sha2-256`. CIDv0 → no MOD (dag-pb/sha2-256 by defn).
- Blockchains: `qualifiers.network` only on departure (`testnet`); mainnet
  silent. **DROP variant** (legacy/segwit) entirely.
- multihash: `qualifiers.hash` only on departure from `sha2-256`.
- Everything else (UUID/ULID/ETH/XRP/XLM/EOS/LEI/snowflake, bare encodings):
  no MOD.

**SIZE** (zero or one):
- `scheme == null` → show, unit follows `size_basis`:
  `decoded → "<size_bits>-bit"`, `utf8 → "<size_bits/8>-byte"`.
  (bare `hex, 256-bit`; `text, 56-byte`)
- `scheme in {ssh, multihash}` → `<size_bits>-bit` (key/hash size genuinely
  varies).
- **All other schemes → omit** (fixed or pinned: UUID=128, ETH=160,
  snowflake=64, LEI, CESR per-primitive, CID pinned by hash; and DID/URN where
  a bit/byte size is a category error for a structured identifier).

**Terminal `fingerprint of ` marker**: unchanged (bold dark-red prefix for
>512-bit truncated inputs).

## Bottom strip: unchanged (but now trustworthy)

`...<suffix>` (bound, now-VERIFIED checksum) then ` (<note>)` for the user note.
Keep both. Showing the checksum is exactly why validation below is required.

## Checksum validation (correctness fix — required, since we show it)

Rule: **a parser may surface a bound checksum as a suffix only if it VERIFIED
it.** On an invalid checksum where the structure clearly matches the scheme
(right prefix / length / reserved bytes), **REJECT** (raise a checksum error →
the input is an error vector), matching the existing EIP-55 behavior.

- **base58check** (BTC legacy, LTC legacy, ADA Byron): decode base58, verify the
  4-byte double-SHA256 checksum; reject on mismatch. (Today: NOT verified —
  a corrupted address renders as valid with the bad checksum shown.)
- **bech32** (BTC segwit `bc1`, LTC `ltc1`, generic cosmos/…, BCH): verify the
  BIP-173/BIP-350 polymod on ALL bech32 paths, including the specific bc1/ltc1
  parsers (today the specific parsers skip it). Reject on mismatch.
- **LEI** MOD 97-10: already verified but currently FALLS THROUGH to a generic
  encoding; change to **REJECT** (structure — 20 base36 + `00` reserved — is a
  clear match).
- **Ethereum EIP-55**: already rejects. Unchanged.
- Accepted tradeoff (document in spec): a base58 blob that structurally matches
  a base58check address but has a bad checksum is rejected, not rendered as bare
  base58. That is the intended "no entviz from an invalid checksum" behavior.

**New error vectors** (corpus `expect: error`), proving rejection across all 5
impls: `err-btc-legacy-bad-checksum`, `err-btc-segwit-bad-checksum`,
`err-lei-bad-checksum`, plus `err-ltc-bad-checksum` / `err-cardano-bad-checksum`
/ `err-cosmos-bad-checksum` as coverage allows. (Today only
`err-eip55-bad-checksum` exists.)

## Before → after (grounded)

| current | v14 |
|---|---|
| `ETH: 0x...` | `ETH` |
| `BTC SegWit: bc1...` | `BTC` |
| `BTC legacy: 1...` + `...vfNa` | `BTC` + `...vfNa` |
| `UUID:` | `UUID` |
| `LEI:` + `...12` | `LEI` + `...12` |
| `snowflake:` | `snowflake` |
| `CESR Ed25519 nt pubkey:` | `CESR, Ed25519 nt` |
| `CESR Ed25519 pubkey:` | `CESR, Ed25519` |
| `CESR Blake3-256:` | `CESR, Blake3-256` |
| `SSH ed25519: AAAA...` | `SSH, ed25519, 264-bit` |
| `CIDv1 dag-pb: b...` | `CIDv1, dag-pb` |
| `did:key:...` | `did:key` |
| `urn:isbn:...` | `urn:isbn` |
| `hex(64):` | `hex, 256-bit` |
| `fingerprint of b64(119):` | `fingerprint of b64, 712-bit` |
| `txt(56)->b64url:` | `text, 56-byte` |

## Rollout

Stage 0 (entviz): spec (grammar + checksum normative text + change-log) +
`render_label(characterization)` + checksum verification/rejection + new error
vectors + regen corpus (labels change, PNGs unchanged) + tests + SPEC_VERSION
v13→v14, version 0.13.0→0.14.0. Then ports rs/go/java on `main`; **js on
`feat/disclosure-lifecycle-ux`** (its v13 lives there, not on main). Docs +
port-CI corpus-pin bump `v0.13.0→v0.14.0` after tagging. Local commits only;
user pushes. Publishing on the entviz `v0.14.0` tag (as with v0.13.0).
