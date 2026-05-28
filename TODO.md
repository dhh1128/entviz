# Entviz Project To-Do List

This list tracks the remaining tasks to complete the Entviz reference implementation, based on the algorithm specification in `docs/spec.md`.

## 1. Core Algorithm Implementation

### Entropy Processing
- [x] Input normalization and type detection (`entropy.py`).
- [ ] Tokenization of normalized entropy into 24-bit quants.
- [ ] Implement repetition of low-order bits for tokens < 24 bits.

### Grid & Cell Layout
- [x] Basic Rect and Cell geometry (`layout.py`).
- [ ] Implement target aspect ratio grid selection logic.
- [ ] Implement token-to-cell assignment (left-to-right, top-to-bottom).
- [ ] Implement median token detection for blank cell insertion.
- [ ] Implement quartile token detection for CRC marks.
- [ ] Implement blank cell shifting logic (max 3 shifts).

### Visual Selection Logic
- [ ] Implement background color selection from median token.
- [ ] Implement edge shape array selection from second quartile token.
- [ ] Implement `shape_shift` and `color_shift` state tracking.

## 2. Rendering (SVG)

### Cell Rendering
- [ ] Implement Nucleus background color calculation (RGB + HLS for text contrast).
- [ ] Implement edge color and shape selection with XOR shifting.
- [ ] Implement SVG generation for all 8 edge shapes (triangles, hooks, boxes, etc.).
- [ ] Implement rotation and compression logic for edge shapes based on edge index.
- [ ] Implement quartile CRC mark rendering (circles in corners).

### Grid Rendering
- [ ] Implement overall SVG assembly (bounding box, font scaling).
- [ ] Add support for embedding the text channel (font rendering in nucleus).

## 3. Tooling & DX

### CLI Improvements
- [ ] Update `bin/entviz.py` to actually generate and save/output an SVG.
- [ ] Add option to output as a data URI or raw SVG text.
- [ ] Add "Thoughts About Comparing" features (legend, toggles for channels).

### Testing
- [ ] Add tests for aspect ratio selection.
- [ ] Add tests for blank cell shifting logic.
- [ ] Add tests for SVG shape generation (visual snapshots or path validation).
- [ ] Add end-to-end tests: entropy string in -> SVG out.

### Refactoring & Intent
- [ ] Audit `cell_shapes.py` and `shapes.py` for naming quality and metaphor consistency.
- [ ] Update `this.i` as implementation decisions are made (especially SVG library choice).
