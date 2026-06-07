"""Generate the conformance corpus from the reference Python implementation.

Writes, under ``compliance/corpus/`` (override with ``--out``):

* ``manifest.json`` — spec/lib versions, the pinned rasterizer + tolerances,
  and the list of render/error/invariant vectors.
* ``<id>/input.json`` — the implementation contract for one vector: entropy,
  params, and whether it must render or be rejected. This is what an external
  implementation reads on stdin.
* ``<id>/model.json`` — the golden Tier-A render model (render vectors only).
* ``<id>/golden.svg`` — the reference SVG (render vectors only).
* ``<id>/golden.png`` — the golden Tier-B raster, text stripped (render only).

Run: ``PYTHONPATH=src:. python -m compliance.generate``
"""
from __future__ import annotations

import argparse
import json
import os
import shutil

from entviz import SPEC_VERSION, __version__
from entviz.pipeline import render

from . import raster
from .corpus import ERROR_VECTORS, INVARIANT_PAIRS, RENDER_VECTORS
from .model import extract_model

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUT = os.path.join(HERE, "corpus")


def _input_json(vid: str, entropy: str, kwargs: dict, expect: str) -> dict:
    params = {
        "target_ar": kwargs.get("target_ar", 1.0),
        "font_size_pt": kwargs.get("font_size_pt", 12),
        "note": kwargs.get("note"),
    }
    return {"id": vid, "entropy": entropy, "params": params, "expect": expect}


def generate(out_dir: str = DEFAULT_OUT) -> dict:
    if os.path.isdir(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir, exist_ok=True)

    render_ids = []
    for vid, entropy, kwargs in RENDER_VECTORS:
        d = os.path.join(out_dir, vid)
        os.makedirs(d, exist_ok=True)
        svg = render(entropy, **kwargs)
        model = extract_model(svg)
        png = raster.rasterize(svg)
        with open(os.path.join(d, "input.json"), "w") as f:
            json.dump(_input_json(vid, entropy, kwargs, "render"), f, indent=2)
        with open(os.path.join(d, "model.json"), "w") as f:
            json.dump(model, f, indent=2, sort_keys=True)
        with open(os.path.join(d, "golden.svg"), "w") as f:
            f.write(svg)
        with open(os.path.join(d, "golden.png"), "wb") as f:
            f.write(png)
        render_ids.append(vid)

    error_ids = []
    for vid, entropy, kwargs, category in ERROR_VECTORS:
        d = os.path.join(out_dir, vid)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "input.json"), "w") as f:
            json.dump(_input_json(vid, entropy, kwargs, category), f, indent=2)
        error_ids.append(vid)

    manifest = {
        "spec_version": SPEC_VERSION,
        "lib_version": __version__,
        "rasterizer": raster.rasterizer_id(),
        "raster_scale": raster.DEFAULT_SCALE,
        "channel_tol": raster.DEFAULT_CHANNEL_TOL,
        "pixel_fraction": raster.DEFAULT_PIXEL_FRACTION,
        "render_vectors": render_ids,
        "error_vectors": error_ids,
        "invariant_pairs": [list(p) for p in INVARIANT_PAIRS],
    }
    with open(os.path.join(out_dir, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    return manifest


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=DEFAULT_OUT)
    args = ap.parse_args()
    m = generate(args.out)
    print(f"corpus {m['spec_version']} (lib {m['lib_version']}) "
          f"rasterizer={m['rasterizer']}")
    print(f"  {len(m['render_vectors'])} render vectors, "
          f"{len(m['error_vectors'])} error vectors, "
          f"{len(m['invariant_pairs'])} invariant pairs")
    print(f"  -> {args.out}")


if __name__ == "__main__":
    main()
