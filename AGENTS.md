# AI Behavioral Rules & Orientation

All AI agents (including Gemini, Claude, and GitHub Copilot) working on the `entviz` project MUST adhere to these rules. These rules are designed to ensure that code is a byproduct of comprehension, not a replacement for it.

## 1. Core Principles

- **Comprehension is the primary output, not code.** You must genuinely understand the *why* before writing the *how*.
- **Intent is a first-class artifact.** Every major decision, tradeoff, and goal must be recorded in `this.i`.
- **The "How" of interaction determines skill.** Use AI for conceptual inquiry and reasoning. Avoid blind code delegation.
- **True TDD.** Never modify code without a failing test, and never leave code in a state where tests do not pass.

## 2. The Intent Layer (`this.i`)

We maintain a file named `this.i` in the root of the repository. This file uses a structured, hierarchical format to track the project's purpose.

- **Structure:** Use the indented YAML-like format (see `this.i` for current state).
- **Updates:** Every time you make a significant design decision or identify a new constraint/tech debt, update `this.i`.
- **IDs:** Assign unique, 8-character alphanumeric IDs (e.g., `r4nk2mp8`) to every goal, decision, or constraint.
- **Intent Checks:** Before starting any implementation task, perform an "intent check": read `this.i` and `docs/index.md` to ensure your plan aligns with the established vision.

## 3. Engineering Discipline

### TDD (Test Driven Development)
1. **Red:** Write a test that fails for the new feature or bug fix.
2. **Green:** Write the minimal code to make the test pass.
3. **Refactor:** Clean up the code while keeping the tests green.

### Naming & Metaphor
Code is a human language.
- **High-Quality Names:** Avoid generic names like `Manager` or `data`. Use names that reflect the semantics (e.g., `Nucleus`, `Edge`, `Quant`).
- **Metaphorical Integrity:** Adhere to the project's visual metaphors (Cells, Nucleus, Edge, CRC). If a new concept is introduced, find a consistent metaphor for it.
- **Refactoring:** If you find a name that is misleading or weak, refactor it immediately.

## 4. Operational Workflow

1. **Research & Strategy:** Use `grep_search` and `read_file` to understand the context.
2. **Intent Update:** If the task involves a design choice, update `this.i` first.
3. **Implementation (TDD):** Create a test, verify failure, implement, verify success.
4. **Validation:** Run all project tests to ensure no regressions.

## 5. Navigation

- [README.md](README.md) - Developer onboarding.
- [docs/index.md](docs/index.md) - Algorithm specification.
- [this.i](this.i) - The "Why" behind the project.
- [CLAUDE.md](CLAUDE.md) - Summary for Claude.
- [GEMINI.md](GEMINI.md) - Summary for Gemini.
