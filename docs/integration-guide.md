# Developer Integration Guide

This guide is for developers **embedding entviz** in an application: rendering a
value to an SVG, reading its structured **entropy characterization**, and
showing the result in a UI. It is deliberately tight — for the normative details
of the algorithm, the render model, and the characterization, see the
[specification](spec.md).

## What entviz is

Entviz turns a high-entropy value — a cryptographic key, a signature, a digest,
a UUID, a blockchain address, a DID, a URN — into a compact SVG diagram whose
colors, shapes, surround patterns, and text a human can **compare at a glance**.
The core use case is *visual comparison*: render two values the same way, side by
side, and any visible difference means the values differ. (Entviz is a
recognition aid, never a substitute for a byte-for-byte equality check — a match
only means no difference was found at the resolution you looked.)

The same algorithm is implemented, and **certified against a shared conformance
corpus**, in five languages — [Python](https://github.com/dhh1128/entviz) (the
reference), [Rust](https://github.com/dhh1128/entviz-rs),
[Go](https://github.com/dhh1128/entviz-go),
[Java](https://github.com/dhh1128/entviz-java), and
[TypeScript/JavaScript](https://github.com/dhh1128/entviz-js) (with a
[React component](https://www.npmjs.com/package/@entviz/react)) — plus a
**[live browser playground](https://dhh1128.github.io/entviz-js/)**. The full
[directory of implementations](https://github.com/dhh1128/entviz#implementations)
lists every package and its API docs.

## Quickstart per language

Every implementation exposes a `render` entry point that takes an entropy string
(plus optional aspect ratio, font size, and note) and returns an **SVG string**.
All five also expose a public `characterize` function that returns the structured
[characterization](#the-characterization-model) directly. In **every**
implementation, the eight characterization fields are also emitted onto the root
`<svg>` as [`data-*` attributes](#consuming-the-fields), so a
consumer can read them off any rendered entviz without a separate call.

=== "Python"

    ```bash
    pip install entviz      # or: uv add entviz
    ```

    ```python
    from entviz.pipeline import render
    from entviz.characterize import characterize

    svg = render("550e8400-e29b-41d4-a716-446655440000")   # -> SVG string
    # render(entropy, target_ar=1.0, font_size_pt=12, note=None)

    ch = characterize("550e8400-e29b-41d4-a716-446655440000")
    # -> dict: {"encoding": "hex", "scheme": "uuid", "role": "identifier",
    #           "qualifiers": {}, "size_basis": "decoded", "size_bits": 128,
    #           "parts": [...], "entropy_type": "uuid"}
    ```

=== "Rust"

    ```toml
    # Cargo.toml
    [dependencies]
    entviz = "0.15"
    ```

    ```rust
    use entviz::render;
    use entviz::characterize::characterize;

    // render(entropy, target_ar, font_size_pt, note) -> Result<String, RenderError>
    let svg = render("550e8400-e29b-41d4-a716-446655440000", 1.0, 12.0, None)?;

    // characterize(entropy) -> Result<Characterization, ParseError>
    let ch = characterize("550e8400-e29b-41d4-a716-446655440000")?;
    assert_eq!(ch.scheme.as_deref(), Some("uuid"));
    assert_eq!(ch.role, Some("identifier"));
    assert_eq!(ch.size_bits, 128);
    ```

=== "Go"

    ```sh
    go get github.com/dhh1128/entviz-go
    ```

    ```go
    import entviz "github.com/dhh1128/entviz-go"

    // Render(entropy, targetAR, fontSizePt, note) -> (svg, error); note is *string.
    svg, err := entviz.Render("550e8400-e29b-41d4-a716-446655440000", 1.0, 12.0, nil)

    // Characterize(entropy) -> (*Characterization, error).
    ch, err := entviz.Characterize("550e8400-e29b-41d4-a716-446655440000")
    // ch.Scheme -> *"uuid", ch.Role -> *"identifier", ch.SizeBits -> 128
    // ch.QualifiersJSON() and ch.PartsJSON() give the compact-JSON forms.
    ```

=== "Java"

    ```xml
    <dependency>
      <groupId>io.github.dhh1128</groupId>
      <artifactId>entviz</artifactId>
      <version>0.15.0</version>
    </dependency>
    ```

    ```java
    import io.github.dhh1128.entviz.Entviz;
    import io.github.dhh1128.entviz.Characterization;
    import io.github.dhh1128.entviz.RenderOptions;

    // Defaults: aspect ratio 1.0, 12pt, no note.
    String svg = Entviz.render("550e8400-e29b-41d4-a716-446655440000");
    String wide = Entviz.render("550e8400-e29b-41d4-a716-446655440000",
            new RenderOptions(2.0, 12.0, "id"));

    // characterize(entropy) -> Characterization (record, public accessors).
    Characterization ch = Entviz.characterize("550e8400-e29b-41d4-a716-446655440000");
    // ch.scheme() -> "uuid", ch.role() -> "identifier", ch.sizeBits() -> 128
    // (scheme() and role() are null when absent); ch.qualifiers(), ch.parts().
    ```

=== "TypeScript / JavaScript"

    ```sh
    npm install @entviz/core          # add @entviz/react for the React component
    ```

    ```ts
    import { render, characterize } from "@entviz/core";

    const svg = render("550e8400-e29b-41d4-a716-446655440000");
    const svg2 = render("0123…", { targetAr: 2.0, fontSizePt: 16, note: "git" });

    const ch = characterize("550e8400-e29b-41d4-a716-446655440000");
    // -> { encoding: "hex", scheme: "uuid", role: "identifier", qualifiers: {},
    //      sizeBasis: "decoded", sizeBits: 128, parts: [...], entropyType: "uuid" }
    ```

    **React** — `@entviz/react` wraps the renderer in components (the fastest path
    for a UI; see [Using the React components](#using-the-react-components)):

    ```sh
    npm install @entviz/react @entviz/core react
    ```

    ```tsx
    import { Entviz } from "@entviz/react";

    // Render one value as a comparable SVG:
    <Entviz value="550e8400-e29b-41d4-a716-446655440000" targetAr={1.5} note="git" />
    ```

## The characterization model

The **entropy characterization** re-expresses the parser's recognition of an
input along independent axes, so consumers read structured fields instead of
string-parsing a display label. It is **reporting-only**: it changes no pixel, no
fingerprint input, and no label — it is metadata *about the input*. Every input
yields the same eight fields:

| Field | Description |
|---|---|
| `encoding` | The declared alphabet of the core (`hex`, `base58`, `bech32`, `base32`, `base64`, `base64url`, `base36`, `crockford32`, `decimal`) — the alphabet that drives tokenization. |
| `scheme` | The recognizer/namespace that fired (`cesr`, `btc`, `eth`, `cid`, `did`, `urn`, `ssh`, `uuid`, …), or `null` when only bare-encoding detection matched. |
| `role` | The semantic role of the bits, from the **closed enum** `{key, signature, digest, address, identifier}`, or `null` when undetermined. |
| `qualifiers` | An object of independently-varying facets the recognizer recovered, e.g. `{"network": "mainnet"}`, `{"algorithm": "ed25519"}`, `{"version": 1, "codec": "dag-pb", "hash": "sha2-256"}`; `{}` when none. |
| `size_basis` | `"decoded"` or `"utf8"` — how `size_bits` is measured. **Scheme-driven** (`did`/`urn`/UTF-8-fallback are `utf8`; everything else `decoded`), never inferred from the alphabet or content shape. |
| `size_bits` | Value size in bits, always a multiple of 8, computed from the **core** only. **Reporting-only** — see the caveat below. |
| `parts` | The ordered `[{text, bind}]` list the input was cut into, in reading order. `bind` ∈ `{none, fold, core}`. |
| `entropy_type` | Derived convenience field, equal to `scheme` when non-`null`, otherwise `encoding`. |

The closed `role` enum is exactly `key | signature | digest | address |
identifier` (plus `null`). `role` is asserted **only** where the generic
recognizer entviz already runs self-declares it — so a `did:key` is
`identifier` (not `key`), a `did:pkh` carrying an Ethereum address is
`identifier` (not `address`), and a `urn:isbn` is `identifier`. Entviz does not
guess.

`entropy_type` is defined as `scheme ?? encoding`. This is the canonical
promotion of the old per-implementation `entropyType` — one definition, identical
across all five ports, instead of a value each impl re-derived from a label
string.

!!! warning "`size_bits` is reporting-only"
    `size_bits` is **not** the truncation basis. The large-input (head/middle/
    tail) trigger for values over 512 bits uses the tokenizer's byte-length
    measure, which is unchanged and distinct from `size_bits`. Use `size_bits`
    for display and coarse "is this big?" decisions only; do not treat it as the
    truncation boundary. See [Resolution A](spec.md#resolution-a-size_bits-and-size_basis).

## The visible label

The text entviz draws is a **projection of the characterization fields**, not a
separately hand-fused string. The top strip follows one grammar —
`[+hash ]PRIMARY[, MOD][, SIZE][, PREFIX]`, joined with a comma-space and with no
trailing `:`:

* **PRIMARY** is the scheme name (`ETH`, `BTC`, `UUID`, `CESR`, `CIDv1`, `SSH`),
  or — for self-describing prefix schemes — the framing prefix itself (`did:key`,
  `urn:isbn`). When no scheme fired it is the encoding name (`hex`, `b64`) or
  `text` for the UTF-8 fallback.
* **MOD** carries the meaningful qualifiers (e.g. CESR primitive `Ed25519 nt`,
  SSH `ed25519` / `ecdsa-p256`, CID codec `dag-pb`) — shown only when they depart
  from the silent default.
* **SIZE** is shown in **bits** for decoded values (`hex, 256-bit`), in **bytes**
  for the `text` UTF-8 fallback (`text, 56-byte`), and **omitted** for structured
  identifiers whose size is fixed or a category error (DID, URN, UUID, ETH).
* **PREFIX** (v15) echoes the **literal front prefix stripped from the visualized
  core** (`0x`, `bc1`, `cosmos1`, Stellar `G`, the SSH header, …) so a reader can
  reconcile the pasted value against the cells, whose first character is
  otherwise silently different. Shown *in addition to* the type name
  (`ETH, 0x`; `ADA, addr1`; `bech32, cosmos1`); it is the only slot that
  truncates — a long prefix (in practice only SSH's structural header) is cut to
  `<head>...`. Folded identity prefixes (did/urn/gitoid/swhid) are not repeated;
  they are already the PRIMARY slot.

The `+hash ` marker (bold dark-red) replaces v14's `fingerprint of ` for inputs
over 512 bits, where the middle cells are a fingerprint readout rather than input
bytes — the value augmented with a hash, not a hash.

Examples: `ETH, 0x`, `UUID`, `CESR, Blake3-256`, `CESR, Ed25519 nt`,
`SSH, ed25519, 264-bit, AAAA...`, `CIDv1, dag-pb, b`, `hex, 256-bit`,
`text, 56-byte`, `did:key`, `urn:isbn`, `bech32, cosmos1`, `+hash b64, 712-bit`.

The bottom strip shows any **bound checksum** as `...<suffix>` (optionally
followed by ` (<note>)`). This checksum is **verified**: a parser surfaces it
only after checking it, so an input whose structure matches a scheme but whose
checksum is invalid is **rejected as an error**, never rendered with a bad
checksum on display. See the [specification](spec.md) for the normative grammar
and checksum rules.

## Consuming the fields

There are two equivalent ways to obtain the characterization.

### (a) Call `characterize()` directly

In all five languages, call the public `characterize` function shown in the
[quickstart](#quickstart-per-language). It returns the eight fields as a
structured object (a dict / struct / record / interface) — no string parsing.
This is the right choice when you have the raw value in hand and want the
characterization without rendering.

### (b) Read the `data-*` attributes off a rendered SVG

Every implementation emits the eight fields onto the **root `<svg>`** element, so
any consumer — in any language, including one that only receives the rendered SVG
— can recover them by reading attributes. This is also how the conformance
checker compares each implementation against its **own** characterization. The
attributes are:

| Attribute | Field | Serialization |
|---|---|---|
| `data-encoding` | `encoding` | string |
| `data-scheme` | `scheme` | string (empty string for `null`) |
| `data-role` | `role` | string (empty string for `null`) |
| `data-qualifiers` | `qualifiers` | compact JSON object |
| `data-size-basis` | `size_basis` | string |
| `data-size-bits` | `size_bits` | integer as a decimal string |
| `data-parts` | `parts` | compact JSON array |
| `data-entropy-type` | `entropy_type` | string |

These are advisory metadata that add no ink (the closed SVG profile explicitly
permits extra `data-*` attributes), so emitting them changes nothing a viewer
sees.

### Using the React components

For web and mobile UIs — the most common way to embed entviz —
[`@entviz/react`](https://www.npmjs.com/package/@entviz/react) wraps the core
renderer in ready-made components. **[Try them all in the live playground](https://dhh1128.github.io/entviz-js/)**,
then reach for:

* **`<Entviz>`** — render one value as a comparable SVG. Props: `value`,
  `targetAr`, `fontSizePt`, `note`, `title`, `style`, `onError` (see the
  [quickstart](#quickstart-per-language) above).
* **`<EntvizCompare>`** — render *two* values and surface any visible difference.
  This is the core comparison use case, built for you — the "dedicated comparison
  UI" the manual procedure below otherwise stands in for.
* **`<EntvizPill>`** — a compact badge driven by the **structured
  characterization**, not by parsing the label string (the exact pain the
  characterization removes). It shows a constant badge plus the trusted type and
  affords locate / expand / copy — **never an equality verdict** (recognition ≠
  verification).
* **`<EntvizVoiceCompare>`** — the read-aloud comparison flow (name the color-bar
  band letters in order) for verifying two values over a voice call.

Whatever you build, model it on the pill's principle: **drive presentation from
the structured fields, and never let a glance at a badge stand in for a real
comparison.** For full props and source, see the
[`@entviz/react` README](https://github.com/dhh1128/entviz-js/tree/main/packages/react)
and the [entviz-js repo](https://github.com/dhh1128/entviz-js).

## Conformance

Correctness is defined by the spec's [three conformance tiers](spec.md#the-three-conformance-tiers):

* **Tier A — render model.** The abstract render model recovered from the SVG's
  required attributes matches the golden model field-for-field (semantic
  correctness; localizes failures).
* **Tier B — canonical raster.** The SVG, rasterized by the single pinned
  reference rasterizer, matches the golden raster pixel-for-pixel outside text
  regions (visual correctness).
* **Tier C — browser smoke.** A subset is rendered in a headless browser and
  screenshot-compared with loose tolerance (deployment sanity; non-blocking).

All five implementations are certified against the **shared conformance corpus**
that lives in [`compliance/`](https://github.com/dhh1128/entviz/tree/main/compliance)
in the reference repo. The corpus also certifies that every implementation emits
an **identical characterization** for each input: the eight fields appear in each
input's golden `model.json`, and the checker recovers them from each
implementation's own `data-*` attributes and compares them. So `characterize()`
in any language, and the `data-*` attributes on any rendered SVG, agree by
construction.

## Comparing two entvizes

Entviz is built for **comparison**, not memorization. A human comparing two
entvizes should:

* **Render both the same way** — same point size, font, and background, shown
  side by side at the same scale. Differences in scale, zoom, or surrounding
  color can hide or fake a difference.
* **Reject on any visible difference.** The check is asymmetric: *any* visible
  difference in the text, color bar, surround pattern, blank positions, ellipse,
  or quartile marks means the values are **different**. A match is never proof of
  identity.
* **Compare every channel, not just one.** Scan the text, the color bar (each
  band carries a letter `w/g/r/b/k`, read aloud left to right), the surround
  rings, the blank-cell positions, and the overlays. A reader who habitually
  checks only one landmark is the easiest to fool.

The **read-aloud** convention — naming the color-bar band letters in order —
gives two people a channel for comparing entvizes over a voice call (and drives
`<EntvizVoiceCompare>`). For the full treatment of the perceptual channels and the
comparison model, see [The channels at a glance](spec.md#the-channels-at-a-glance)
in the spec.
