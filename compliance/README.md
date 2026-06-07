# entviz conformance suite

A language-agnostic, three-tier checker that certifies an entviz implementation
against the algorithm in [`../docs/spec.md`](../docs/spec.md) (see its
**Conformance** section). The reference Python implementation generates a fixed
**corpus** of golden artifacts; any implementation — the reference, `entviz-rs`,
`entviz-js` — is certified by reproducing them.

## Tiers

| Tier | What it proves | How |
|---|---|---|
| **A — render model** | The algorithm computed the right *values*; localizes failures | Recover the abstract render model from the SVG's normative `data-*` attributes + normative geometry ([`model.py`](model.py)) and compare field-for-field to the golden `model.json` |
| **B — canonical raster** | What a human *sees*: layering, color, position, size, occlusion | Rasterize with one pinned rasterizer (text stripped) and pixel-compare to the golden `golden.png` ([`raster.py`](raster.py)) |
| **C — browser smoke** | Deployment sanity on the real target | Out of scope for this offline harness (headless browser) |

Text glyphs are excluded from Tier B (cross-platform glyph shape is a non-goal —
see the spec's font-fallback clause); text content/position/size/color is proven
by Tier A instead.

## Layout

```
compliance/
  model.py      # Tier A: extract_model(svg) -> dict; diff_models / models_equal
  raster.py     # Tier B: strip_text, rasterize, compare_png (pinned rasterizer)
  corpus.py     # RENDER_VECTORS, ERROR_VECTORS, INVARIANT_PAIRS
  generate.py   # build the corpus from the reference impl
  runner.py     # certify(render_fn | --impl-cmd) at the chosen tiers
  corpus/       # generated goldens: <id>/{input.json, model.json, golden.svg, golden.png}
```

## Usage

```sh
# (Re)generate the corpus from the reference implementation:
PYTHONPATH=src:. python -m compliance.generate

# Certify the reference (Tier A + B):
PYTHONPATH=src:. python -m compliance.runner

# Certify an external implementation:
PYTHONPATH=src:. python -m compliance.runner --impl-cmd './my-entviz'
```

## The implementation contract (external impls)

For each corpus vector the checker pipes that vector's `input.json` to the
implementation command on **stdin**:

```json
{ "id": "hex-256", "entropy": "0123…", 
  "params": { "target_ar": 1.0, "font_size_pt": 12, "note": null },
  "expect": "render" }
```

The implementation MUST:

* for `"expect": "render"` — write the entviz **SVG to stdout** and exit `0`;
* for any other `expect` (an error category) — **exit non-zero** (reject).

The corpus drift guard (`tests/test_compliance.py::test_committed_corpus_matches_reference`)
keeps the committed goldens in sync with the reference renderer, exactly like the
figure drift guard: if a change alters rendered output, regenerate the corpus and
commit it.
