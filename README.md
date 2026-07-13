# entviz

[![CI](https://github.com/dhh1128/entviz/actions/workflows/ci.yml/badge.svg)](https://github.com/dhh1128/entviz/actions/workflows/ci.yml)
[![Deploy Docs](https://github.com/dhh1128/entviz/actions/workflows/deploy-docs.yml/badge.svg)](https://github.com/dhh1128/entviz/actions/workflows/deploy-docs.yml)
[![Release](https://github.com/dhh1128/entviz/actions/workflows/release.yml/badge.svg)](https://github.com/dhh1128/entviz/actions/workflows/release.yml)
[![PyPI](https://img.shields.io/pypi/v/entviz)](https://pypi.org/project/entviz/)
[![Python versions](https://img.shields.io/pypi/pyversions/entviz)](https://pypi.org/project/entviz/)

Entviz is a tool for visualizing high-entropy values (like cryptographic keys, UUIDs, or blockchain addresses) into a grid of colored shapes and text, making it easy for humans to compare them. This is its reference implementation in Python; there are conformant implementations in Rust, TypeScript/JS + React, Java, and Go, plus a **[live browser playground](https://dhh1128.github.io/entviz-js/)** — see [Implementations](#implementations) below.

<figure markdown="span">
  ![An entviz rendering of this repository's root commit hash](assets/root-commit-entviz.svg){ width="320" }
  <figcaption>This repository itself, rendered as an entviz of its own root commit hash.</figcaption>
</figure>

## Implementations

entviz is a language-independent [specification](docs/spec.md); every implementation below passes the same shared conformance corpus. **[▶ Try it live in the browser](https://dhh1128.github.io/entviz-js/)** — the JS/React playground renders a value and compares two.

| Language | Repository | Package | API docs |
|---|---|---|---|
| **Python** (reference) | this repo | [PyPI `entviz`](https://pypi.org/project/entviz/) | [docs site](https://dhh1128.github.io/entviz/) |
| **Rust** | [entviz-rs](https://github.com/dhh1128/entviz-rs) | [crates.io `entviz`](https://crates.io/crates/entviz) | [docs.rs](https://docs.rs/entviz) |
| **TypeScript / JS** | [entviz-js](https://github.com/dhh1128/entviz-js) | [npm `@entviz/core`](https://www.npmjs.com/package/@entviz/core) | [TypeDoc](https://dhh1128.github.io/entviz-js/api/) |
| **React** | [entviz-js `packages/react`](https://github.com/dhh1128/entviz-js/tree/main/packages/react) | [npm `@entviz/react`](https://www.npmjs.com/package/@entviz/react) | — |
| **Java** | [entviz-java](https://github.com/dhh1128/entviz-java) | [Maven `io.github.dhh1128:entviz`](https://central.sonatype.com/artifact/io.github.dhh1128/entviz) | [javadoc.io](https://javadoc.io/doc/io.github.dhh1128/entviz) |
| **Go** | [entviz-go](https://github.com/dhh1128/entviz-go) | [pkg.go.dev](https://pkg.go.dev/github.com/dhh1128/entviz-go) | [pkg.go.dev](https://pkg.go.dev/github.com/dhh1128/entviz-go) |

## Install

```bash
pip install entviz      # or: uv add entviz
```

Render any value to an SVG on stdout:

```bash
entviz "550e8400-e29b-41d4-a716-446655440000" --ar 1:1 > id.svg
```

The library has one runtime dependency (`lxml`) and emits SVG only — no
rasterizer required.

## Comparing two entvizes

> **Tip:** For an interactive UI, the [`@entviz/react`](https://www.npmjs.com/package/@entviz/react)
> component and the **[live playground](https://dhh1128.github.io/entviz-js/)** let you render and
> compare two entvizes in the browser. The manual procedure below applies anywhere you have only the
> static SVGs.

entviz is built for **comparison**, not memorization. To check whether two
values are the same:

- **Render both the same way.** Same point size, same font, same background,
  shown **side by side** at the same scale. Differences in scale, zoom, font,
  or surrounding color can hide or fake a difference.
- **Reject on any visible difference.** The check is asymmetric: *any* visible
  difference in text, color bar, surround pattern, blank positions, ellipse,
  or quartile marks means the values are **different**. A match is **never
  proof** of identity — it only means no difference was found at the
  resolution you looked.
- **Compare every channel, not just one.** A habituated reader who checks only
  one landmark (e.g. the color bar) is the easiest to fool. Scan the text, the
  color bar (each band carries a letter `w/g/r/b/k`), the surround rings, the
  blank-cell positions, and the overlays.

### The `fingerprint of` marker

For inputs longer than 512 bits, the text channel can't show every character,
so the entviz is labeled **`fingerprint of <type>(<length>):`** in bold dark
red. On these entvizes:

- The **first 8 and last 8** text cells are real characters from the start and
  end of your value (use these to recognize and spot-check it).
- The **4 middle cells** (neutral background, framed) are a **hash readout** in
  hex — they are *not* characters from your value. Two different long inputs
  can therefore share many visible cells and still be different; trust the full
  picture, and remember that the whole input is bound into every color/shape
  channel through the fingerprint.

## Developer Quickstart

### Prerequisites
- [uv](https://docs.astral.sh/uv/) (manages the Python interpreter, virtualenv, and dependencies). uv will fetch a suitable Python (>=3.10) for you.

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/dhh1128/entviz.git
   cd entviz
   ```

2. Create the environment from the lockfile:
   ```bash
   uv sync
   ```

### Running Tests

```bash
uv run pytest
```

To prove the supported Python floor locally (CI runs the full 3.10/3.11/3.12 matrix):

```bash
uv run --python 3.10 pytest
```

### Running the CLI

`entviz` is installed as a console entry point:

```bash
uv run entviz "your-entropy-string" --ar 1:1 --fs 12
```

### Regenerating the gallery

```bash
uv run python scripts/gallery.py
```

### Regenerating the social preview card

The GitHub "social preview" image (the Open Graph card that unfurls when the
repo URL is shared on Slack, X, LinkedIn, etc.) is a reproducible asset. The
card embeds an *entviz of this repo's own root commit SHA* — the tool applied
to itself — which is the same entviz shown at the top of the docs.

```bash
uv run python scripts/social_card.py
```

This (re)writes three files into `docs/assets/`, alongside the other docs
images:

- `root-commit-entviz.svg` — the entviz of the root commit hash (also embedded
  at the top of [docs/index.md](docs/index.md));
- `social-card.svg` — the composed 1280×640 card (vector source of truth);
- `social-card.png` — the PNG you upload (under 1 MB).

The PNG is rendered with `cairosvg` (a dev dependency) using the DejaVu font
fallback baked into the font stack, so it reproduces without bundling fonts.

**Uploading it (one-time, manual):** GitHub → repo **Settings** → **General** →
**Social preview** → **Edit** → upload `docs/assets/social-card.png`.

**Reusing the template across repos:** the palette, layout, and typography are
shared family constants; only the `KNOBS` block at the top of
[scripts/social_card.py](scripts/social_card.py) (repo name, owner, tagline,
language, and the `MARK`) changes per repo. See the module docstring for details.

### Cutting a release

```bash
python3 scripts/release.py --patch -m "what changed"
```

The script is self-guarding: it switches to `main`, fast-forwards to
`origin/main`, refuses a dirty tree or unpushed local commits, runs the full
test suite, regenerates the gallery, then bumps the version, commits, and
pushes a `vX.Y.Z` tag. It is pure-stdlib, so it works from any directory (it
operates on the repo root regardless of `cwd`) — `python3 /path/to/entviz/scripts/release.py …`
is equivalent. (`uv` must be on `PATH`, since the script shells out to
`uv run` for the tests and gallery.)

The pushed tag triggers [`.github/workflows/release.yml`](.github/workflows/release.yml),
which re-runs the tests on the tagged commit, **publishes the sdist + wheel to
[PyPI](https://pypi.org/project/entviz/) via Trusted Publishing (OIDC — no API
token)**, and creates a GitHub Release with the same artifacts attached.

See [scripts/release.py](scripts/release.py) for bump options (`--minor`,
`--major`, `--set X.Y.Z`, `--no-bump`) and the versioning convention.

## Project Structure

- `src/entviz/`: Core library.
  - `entropy.py`: Entropy parsing and normalization.
  - `layout.py`: Grid layout calculations.
  - `colors.py`: Color selection and conversion.
  - `shapes.py`: Edge shape definitions.
  - `pipeline.py`: End-to-end render pipeline.
  - `app.py`: CLI entry point (`entviz`).
  - `__init__.py`: `SPEC_VERSION` (algorithm/spec) and `__version__` (library) — the single source of truth for both.
- `scripts/`: Maintenance tooling (`gallery.py`, `release.py`).
- `tests/`: Unit tests.
- `docs/`: Specification, gallery, and assets.

## Documentation

For the full specification of the Entviz algorithm and design goals, see [docs/spec.md](docs/spec.md).

For embedding entviz in an application — install + render + reading the
structured entropy characterization in each of the five languages — see the
[Developer Integration Guide](https://dhh1128.github.io/entviz/integration-guide/)
([source](docs/integration-guide.md)). The characterization re-expresses a
parsed value along independent axes and is emitted both as a `characterize()`
return value and as `data-*` attributes on the rendered SVG:

```python
from entviz.characterize import characterize

ch = characterize("550e8400-e29b-41d4-a716-446655440000")
# {"encoding": "hex", "scheme": "uuid", "role": "identifier", "qualifiers": {},
#  "size_basis": "decoded", "size_bits": 128, "parts": [...], "entropy_type": "uuid"}
```

## Methodology & AI Collaboration

This repository follows a specific methodology for high-quality software development, especially when collaborating with AI:

- **AI Behavioral Rules:** See [AGENTS.md](AGENTS.md) for mandatory rules on comprehension, TDD, and intent tracking.
- **Intent Layer:** We track design decisions and goals in [this.i](this.i).
- **TDD:** Strict Test-Driven Development is required for all changes.
