# entviz

[![CI](https://github.com/dhh1128/entviz/actions/workflows/ci.yml/badge.svg)](https://github.com/dhh1128/entviz/actions/workflows/ci.yml)

Entviz is a tool for visualizing high-entropy values (like cryptographic keys, UUIDs, or blockchain addresses) into a grid of colored shapes and text, making it easy for humans to compare them.

## Comparing two entvizes

> **Note:** This is interim guidance. A dedicated comparison UI (a React
> component that aligns two entvizes and highlights differences) is planned;
> until then, follow the manual procedure below.

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

### Cutting a release

```bash
uv run python scripts/release.py --patch -m "what changed"
```

See [scripts/release.py](scripts/release.py) for bump options and the versioning convention.

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

## Methodology & AI Collaboration

This repository follows a specific methodology for high-quality software development, especially when collaborating with AI:

- **AI Behavioral Rules:** See [AGENTS.md](AGENTS.md) for mandatory rules on comprehension, TDD, and intent tracking.
- **Intent Layer:** We track design decisions and goals in [this.i](this.i).
- **TDD:** Strict Test-Driven Development is required for all changes.
