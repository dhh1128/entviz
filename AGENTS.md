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
- **Intent Checks:** Before starting any implementation task, perform an "intent check": read `this.i` and `docs/spec.md` to ensure your plan aligns with the established vision.

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
5. **Regenerate the gallery:** Any time a change can alter rendered output — anything in `src/entviz/` touching tokenization, geometry, color, layout, or SVG emission, or any spec change that flows into the renderer — regenerate the visual gallery with `uv run python scripts/gallery.py` and commit the updated `docs/gallery.html` and `docs/assets/gallery/*.svg` alongside the code. The gallery is the project's visual regression surface; stale SVGs hide rendering changes from review. Skip this step only for changes that provably cannot affect output (pure docs, comments, test-only edits). (Note: `scripts/release.py` regenerates the gallery automatically, since the gallery title embeds the library version.)
6. **Regenerate the documentation figures (paper + spec):** Every figure in `docs/assets/paper/` (the academic paper) and the channel/geometry/schematic figures in `docs/assets/` (the spec) is *generated* from the live renderer via the shared `scripts/figlib.py`, by `scripts/paper_figures.py` and `scripts/spec_figures.py` respectively (each wraps a real `render()` call or a gallery SVG, or is computed from `figlib.geometry()` — see [[paper-figure-house-style]]). They are **not** hand-drawn and must never be edited by hand. After any change that can alter rendered output (the same trigger as the gallery step) **or** after bumping `SPEC_VERSION`, re-run both generators (`PYTHONPATH=src .venv/bin/python scripts/paper_figures.py` and `… scripts/spec_figures.py`; deps: the `render` group) and commit the updated SVGs (and the paper's `*.png`). This is enforced: `tests/test_figures.py` regenerates every figure's SVG in-process and fails CI if it drifts from the committed file, if a figure's embedded `data-spec-version` no longer matches the current `SPEC_VERSION`, or if `figlib.geometry()` diverges from the renderer. When the version check fires on a spec bump, also **eyeball the hardcoded annotation labels** in the generators (e.g. "fingerprint bit *i* fills box *i*") against the new spec — the byte-diff catches pixel drift, but only a human catches a caption whose *meaning* went stale.

## 5. Defect Management (GitHub Issues)

This repo tracks defects as **GitHub Issues** on `dhh1128/entviz`, managed with the `gh` CLI (no issue tracker MCP server is used). Issues are enabled and the standard `bug` label exists.

**Logging a bug.** When a maintainer says "log a bug about X" (or an agent discovers a defect worth tracking), create the issue immediately — do not wait for further confirmation — and report the issue number and URL:

```
gh issue create --repo dhh1128/entviz --label bug \
  --title "<concise summary of the defect>" \
  --body "$(cat <<'EOF'
## Summary
<one-paragraph description>

## Steps to reproduce
1. ...

## Expected
<what should happen>

## Actual
<what happens instead>

## Environment
<version / OS / config relevant to the bug, if any>

## Notes
<logs, stack traces, suspected cause, related issues>
EOF
)"
```

Fill in every section you can; omit a section's body only when it genuinely does not apply. The only triage label is `bug` — no severity/priority labels. Use milestones or comments if prioritization is needed later.

**Fixing a bug.** When a maintainer says "let's fix bug X":

1. Resolve X to an issue: `gh issue list --repo dhh1128/entviz --label bug --state open --search "X"`, or `gh issue view <n>` if given a number. Confirm the match before proceeding.
2. Branch `fix/<issue#>-<short-slug>` off the default branch.
3. Fix it TDD-style per §3 (failing test first, then the minimal fix, then refactor).
4. If the fix can alter rendered output, regenerate the gallery per §4 step 5 and commit the updated SVGs alongside the code.
5. Reference `Fixes #<n>` in the commit message and/or PR body so the issue auto-closes when the change merges to the default branch.

**Finding bugs.** `gh issue list --repo dhh1128/entviz --label bug --state open` lists the open defect backlog; `gh issue view <n>` shows one.

## 6. Task tracking: `tick`

This repo tracks tasks, tech debt, and ideas in a local [`tick`](https://github.com/dhh1128/tick)
ledger (an orphan `tick` branch; the `tick` CLI is the interface). Reads are plain
files — do **not** use an external API for task tracking.

- **A tick mark is `~` + a digit-first 4-char id**, e.g. `~4mz3`. It pins a tick
  to a code location.
- **Before editing a file**, grep it for marks and read what they reference:
  `rg '~[2-7][a-z2-7]{3}' <file>` then `tick show <id>`. A mark means recorded
  context exists for that spot — read it first.
- **Search** existing ticks with `tick grep <text>`; **list** with `tick ls`.
- **Capture** new work with `tick add "<title>"` and place the printed `~<id>`
  mark at the relevant code spot.
- When your change **resolves** a tick, run `tick off <id>` and **delete the
  mark(s)** it reports still in the code.
- A tick that turns out to be a real design decision should **graduate** into
  `this.i` when closed (the ledger is the workshop; `this.i` is the showroom).

## 7. Navigation

- [README.md](README.md) - Developer onboarding.
- [docs/spec.md](docs/spec.md) - Algorithm specification (current: v6).
- [this.i](this.i) - The "Why" behind the project.
- [CLAUDE.md](CLAUDE.md) - Summary for Claude.
- [GEMINI.md](GEMINI.md) - Summary for Gemini.
