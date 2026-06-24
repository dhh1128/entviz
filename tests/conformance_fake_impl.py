"""A configurable fake external implementation for runner tests.

Behaves like a real ``--impl-cmd`` (reads one vector's ``input.json`` on stdin,
writes an SVG on stdout, exits non-zero to reject), but with knobs to simulate
the failure modes the runner enhancements must catch:

* ``--reject-if-contains S`` — exit non-zero when the entropy contains ``S``
  (a port that lacks a parser, e.g. js for ``did:peer:2``).
* ``--corrupt-if-contains S`` — render but mangle a model-bearing attribute when
  the entropy contains ``S`` (a Tier-A mismatch on that vector).
* ``--version-override V`` — stamp ``data-entviz-version="V"`` (spec mismatch).

Default (no flags) it is a faithful proxy for the reference renderer.
"""
import argparse
import json
import re
import sys

sys.path.insert(0, "src")
from entviz.pipeline import render  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reject-if-contains", default=None)
    ap.add_argument("--corrupt-if-contains", default=None)
    ap.add_argument("--version-override", default=None)
    args = ap.parse_args()

    inp = json.load(sys.stdin)
    entropy = inp["entropy"]
    p = inp["params"]

    if args.reject_if_contains and args.reject_if_contains in entropy:
        sys.exit(1)

    svg = render(entropy, target_ar=p["target_ar"],
                 font_size_pt=p["font_size_pt"], note=p["note"])

    if args.corrupt_if_contains and args.corrupt_if_contains in entropy:
        # Perturb a model-bearing attribute so Tier A diffs against the golden.
        svg = re.sub(r'data-input-bytes="(\d+)"',
                     lambda m: f'data-input-bytes="{int(m.group(1)) + 1}"',
                     svg, count=1)

    if args.version_override:
        svg = re.sub(r'data-entviz-version="[^"]*"',
                     f'data-entviz-version="{args.version_override}"', svg, count=1)

    sys.stdout.write(svg)


if __name__ == "__main__":
    main()
