# entviz

[![CI](https://github.com/dhh1128/entviz/actions/workflows/ci.yml/badge.svg)](https://github.com/dhh1128/entviz/actions/workflows/ci.yml)

Entviz is a tool for visualizing high-entropy values (like cryptographic keys, UUIDs, or blockchain addresses) into a grid of colored shapes and text, making it easy for humans to compare them.

## Developer Quickstart

### Prerequisites
- Python 3.x
- `pip`

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-repo/entviz.git
   cd entviz
   ```

2. (Optional) Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Running Tests

We use `pytest` for testing. Run all tests with:

```bash
pytest
```

### Running the CLI

The project includes a command-line interface in `bin/entviz.py`. You can run it like this:

```bash
python bin/entviz.py "your-entropy-string" --ar 1:1 --fs 12
```

## Project Structure

- `entviz/`: Core library logic.
  - `entropy.py`: Entropy parsing and normalization.
  - `layout.py`: Grid layout calculations.
  - `colors.py`: Color selection and conversion.
  - `shapes.py`: Edge shape definitions.
  - `app.py`: Main application logic and CLI entry point.
- `bin/`: Executable scripts.
- `docs/`: Detailed documentation and specifications.
- `assets/`: Images used in documentation.
- `entviz/tests/`: Unit tests.

## Documentation

For the full specification of the Entviz algorithm and design goals, see [docs/spec.md](docs/spec.md).

## Methodology & AI Collaboration

This repository follows a specific methodology for high-quality software development, especially when collaborating with AI:

- **AI Behavioral Rules:** See [AGENTS.md](AGENTS.md) for mandatory rules on comprehension, TDD, and intent tracking.
- **Intent Layer:** We track design decisions and goals in [this.i](this.i).
- **TDD:** Strict Test-Driven Development is required for all changes.
