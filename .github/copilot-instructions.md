# GitHub Copilot Instructions — entviz

**STOP!** Before making any changes, read [AGENTS.md](AGENTS.md) at the root of this repository.
It contains the mandatory AI orientation and behavioral rules for this project, including:

- **Comprehension First:** Demonstrate understanding of *why* before writing *how*.
- **Intent Layer:** Maintain and update [this.i](this.i) for all design decisions.
- **Strict TDD:** Never modify code without a failing test.
- **Naming & Metaphor:** Treat code as human language; prioritize high-quality names.

**The short version:** Never modify code without first verifying the existing tests pass, and never leave code in a state where the tests do not pass. Ensure all logic adheres to the Entviz algorithm specification in [docs/index.md](docs/index.md).
