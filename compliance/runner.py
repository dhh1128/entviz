"""Run an entviz implementation against the conformance corpus.

Two ways to supply the implementation under test:

* **In-process** (the reference, or any importable Python callable): pass a
  ``render_fn(entropy, *, target_ar, font_size_pt, note) -> svg_str`` that
  raises on rejected inputs.
* **External / language-agnostic** (``--impl-cmd``): a shell command that reads
  one vector's ``input.json`` on **stdin** and writes the SVG to **stdout** for
  a render vector, or exits **non-zero** for an error vector. This is the
  contract entviz-rs and entviz-js are certified through.

Each render vector is checked at Tier A (render-model equality vs. the golden
model) and Tier B (canonical raster vs. the golden PNG, text excluded). Error
vectors are checked for rejection. Invariant pairs are checked for
model equality.

Run the reference self-certification:
    PYTHONPATH=src:. python -m compliance.runner
External impl:
    PYTHONPATH=src:. python -m compliance.runner --impl-cmd './entviz-cli'
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field

from lxml import etree

from . import raster
from .model import diff_models, extract_model, validate_closed_profile

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CORPUS = os.path.join(HERE, "corpus")

# Model keys excluded from the invariant-pair comparison: they are non-pixel
# metadata that may legitimately differ between two inputs that share a
# visualization. `input_bytes` is the raw input length; the rest are the
# reporting-only entropy characterization (spec v13). See the invariant-pair
# loop below.
_CHARACTERIZATION_KEYS = frozenset({
    "encoding", "scheme", "role", "qualifiers",
    "size_basis", "size_bits", "parts", "entropy_type",
})
_INVARIANT_EXCLUDED_KEYS = frozenset({"input_bytes"}) | _CHARACTERIZATION_KEYS


@dataclass
class VectorResult:
    vid: str
    kind: str            # "render" | "error" | "invariant" | "version" | "skip"
    tier_a: bool | None = None
    tier_b: bool | None = None
    passed: bool = False
    skipped: bool = False  # declared in a --skip-file: expected NOT to pass
    messages: list[str] = field(default_factory=list)


@dataclass
class Report:
    results: list[VectorResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(r.passed for r in self.results)

    def summary(self) -> str:
        n = len(self.results)
        ok = sum(1 for r in self.results if r.passed)
        nskip = sum(1 for r in self.results if r.skipped)
        head = f"{ok}/{n} vectors passed"
        if nskip:
            head += f" ({nskip} skipped / expected-fail)"
        lines = [head]
        for r in self.results:
            if not r.passed:
                lines.append(f"  FAIL [{r.kind}] {r.vid}")
                for m in r.messages[:8]:
                    lines.append(f"        {m}")
        return "\n".join(lines)


def reference_render(entropy, *, target_ar=1.0, font_size_pt=12, note=None):
    from entviz.pipeline import render
    return render(entropy, target_ar=target_ar, font_size_pt=font_size_pt, note=note)


def _load(corpus_dir, vid, name):
    with open(os.path.join(corpus_dir, vid, name)) as f:
        return f.read()


def _run_external(cmd: str, input_json: dict):
    """Returns (svg_or_None, rejected_bool). rejected when exit code != 0."""
    proc = subprocess.run(
        cmd, shell=True, input=json.dumps(input_json).encode("utf-8"),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        return None, True
    return proc.stdout.decode("utf-8"), False


def _svg_spec_version(svg: str | bytes) -> str | None:
    """The implementation's declared spec version (root ``data-entviz-version``).

    Read from the SVG root attribute with a light parse so it works at any tier
    (Tier B alone does not extract the full render model)."""
    if isinstance(svg, str):
        svg = svg.encode("utf-8")
    try:
        return etree.fromstring(svg).get("data-entviz-version")
    except etree.XMLSyntaxError:
        return None


def read_skip_file(path: str) -> set[str]:
    """Parse a skip file into a set of vector ids.

    Each non-blank, non-``#``-comment line names one vector id to skip; any text
    after the id on the same line (whitespace- or ``#``-separated) is a free-form
    reason and is ignored. Skipped vectors are run anyway and EXPECTED to fail —
    a skipped vector that passes is a hard error (the skip list has rotted)."""
    skip: set[str] = set()
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            skip.add(line.split()[0])
    return skip


def certify(corpus_dir: str = DEFAULT_CORPUS, *, render_fn=reference_render,
            impl_cmd: str | None = None, tiers=("A", "B"),
            only: set[str] | None = None,
            skip: set[str] | None = None) -> Report:
    """Certify an implementation against the corpus.

    `only`, if given, restricts certification to that set of vector ids — used
    to certify an implementation against the subset of vectors whose parsers it
    has ported (the remainder are reported separately as out of scope, not as
    failures). Invariant pairs are checked only when both members are in scope.

    `skip`, if given, is a set of vector ids the implementation is NOT expected
    to handle (e.g. a port that omits a parser). Unlike `only`, skipped vectors
    are still RUN: a skipped vector is expected to FAIL, and a skipped vector
    that PASSES is itself a hard failure — that keeps a skip list from rotting
    and silently shrinking coverage as a port catches up. Invariant pairs with a
    skipped member are dropped (the pair cannot be asserted when one side is out
    of the port's scope).
    """
    with open(os.path.join(corpus_dir, "manifest.json")) as f:
        manifest = json.load(f)
    report = Report()
    models: dict[str, dict] = {}
    skip = skip or set()
    # The implementation's declared spec version, captured from the first SVG it
    # produces, for the corpus-vs-impl version-match assertion below.
    impl_version: str | None = None

    def in_scope(vid):
        return only is None or vid in only

    for vid in manifest["render_vectors"]:
        if not in_scope(vid):
            continue
        res = VectorResult(vid=vid, kind="render")
        inp = json.loads(_load(corpus_dir, vid, "input.json"))
        p = inp["params"]
        try:
            if impl_cmd:
                svg, rejected = _run_external(impl_cmd, inp)
                if rejected or svg is None:
                    raise RuntimeError("implementation rejected a render vector")
            else:
                svg = render_fn(inp["entropy"], target_ar=p["target_ar"],
                                font_size_pt=p["font_size_pt"], note=p["note"])
        except Exception as e:  # noqa: BLE001
            res.messages.append(f"render raised: {e!r}")
            report.results.append(res)
            continue

        if impl_version is None:
            impl_version = _svg_spec_version(svg)

        # Tier A
        if "A" in tiers:
            golden = json.loads(_load(corpus_dir, vid, "model.json"))
            actual = extract_model(svg)
            models[vid] = actual
            d = diff_models(golden, actual)
            # Closed profile: the SVG must contain ONLY the enumerated entviz
            # channels — no overlaid logo, copyright, or other extra content.
            profile_viol = validate_closed_profile(svg)
            res.tier_a = not d and not profile_viol
            if d:
                res.messages.extend(d)
            if profile_viol:
                res.messages.extend(f"closed-profile: {m}" for m in profile_viol)
        # Tier B
        if "B" in tiers:
            golden_png = open(os.path.join(corpus_dir, vid, "golden.png"), "rb").read()
            try:
                actual_png = raster.rasterize(
                    svg, scale=manifest["raster_scale"])
                rd = raster.compare_png(
                    golden_png, actual_png,
                    channel_tol=manifest["channel_tol"],
                    pixel_fraction=manifest["pixel_fraction"])
                res.tier_b = rd.ok
                if not rd.ok:
                    res.messages.append(
                        f"raster diff: {rd.diff_pixels} px "
                        f"({rd.fraction:.4%}) max={rd.max_channel_diff} {rd.note}")
            except Exception as e:  # noqa: BLE001
                res.tier_b = False
                res.messages.append(f"rasterize failed: {e!r}")

        res.passed = (res.tier_a is not False) and (res.tier_b is not False)
        report.results.append(res)

    # Error vectors: must be rejected.
    for vid in manifest["error_vectors"]:
        if not in_scope(vid):
            continue
        res = VectorResult(vid=vid, kind="error")
        inp = json.loads(_load(corpus_dir, vid, "input.json"))
        p = inp["params"]
        rejected = False
        try:
            if impl_cmd:
                _, rejected = _run_external(impl_cmd, inp)
            else:
                render_fn(inp["entropy"], target_ar=p["target_ar"],
                          font_size_pt=p["font_size_pt"], note=p["note"])
                rejected = False
        except Exception:  # noqa: BLE001
            rejected = True
        res.passed = rejected
        if not rejected:
            res.messages.append(f"expected rejection ({inp['expect']}), got an SVG")
        report.results.append(res)

    # Invariant pairs: identical render models (only meaningful with Tier A).
    # Both members were rendered through the SAME implementation above — the
    # reference in-process, or the external --impl-cmd — and their models
    # extracted by the single authoritative model.py; this asserts the impl maps
    # both members to the same entviz. A pair with a skipped member is dropped:
    # the invariant cannot be asserted when one side is outside the port's scope.
    if "A" in tiers:
        for a, b in manifest.get("invariant_pairs", []):
            if not (in_scope(a) and in_scope(b)):
                continue
            if a in skip or b in skip:
                continue
            res = VectorResult(vid=f"{a}=={b}", kind="invariant")
            if a in models and b in models:
                # The invariant is that the VISUALIZATION is identical. The raw
                # input-length metadata (data-input-bytes) legitimately differs
                # (e.g. a dashed vs undashed UUID is 36 vs 32 chars) without any
                # change to the entviz, so it is excluded from this comparison.
                # The reporting-only entropy characterization (spec v13) is
                # likewise excluded: two inputs can share an entviz yet differ in
                # scheme/size_bits/parts (e.g. avalanche-a hex vs uuid-dashed),
                # and a URN's dropped r-/q-/f-components change its input bytes
                # but not its visualization. Both are non-pixel metadata.
                ma = {k: v for k, v in models[a].items()
                      if k not in _INVARIANT_EXCLUDED_KEYS}
                mb = {k: v for k, v in models[b].items()
                      if k not in _INVARIANT_EXCLUDED_KEYS}
                d = diff_models(ma, mb)
                res.passed = not d
                if d:
                    res.messages.extend(d[:8])
            else:
                res.passed = False
                res.messages.append("missing model for invariant pair")
            report.results.append(res)

    # Skip-file post-processing: a skipped vector is EXPECTED to fail. Invert its
    # verdict — a skipped vector that failed counts as a pass (expected), and a
    # skipped vector that PASSED is a hard failure (the skip list has rotted and
    # must be trimmed). Skips are applied to render/error vectors only.
    processed_vids = {r.vid for r in report.results if r.kind in ("render", "error")}
    for res in report.results:
        if res.kind in ("render", "error") and res.vid in skip:
            res.skipped = True
            if res.passed:
                res.passed = False
                res.messages.insert(0,
                    "skip-list rot: this vector is in the skip file but the "
                    "implementation PASSED it — remove it from the skip file")
            else:
                res.passed = True
    # A skip id that matches no in-scope vector is itself an error (typo, or the
    # vector was renamed/removed): fail so skip lists stay honest.
    for vid in sorted(skip - processed_vids):
        res = VectorResult(vid=vid, kind="skip", skipped=True)
        res.messages.append(
            "skip file references an unknown vector id (typo, or the vector was "
            "renamed/removed from the corpus)")
        report.results.append(res)

    # Spec-version match: the corpus and the implementation must agree on the
    # spec version, guarding against pinning the wrong corpus to a port (the
    # corpus stamps spec_version; the impl stamps it as data-entviz-version on
    # every render). Mismatch fails loudly.
    corpus_version = manifest.get("spec_version")
    vres = VectorResult(vid="spec-version-match", kind="version")
    if impl_version is None:
        vres.messages.append(
            "could not determine the implementation's spec version "
            "(no render vector produced output)")
    elif corpus_version is None:
        vres.messages.append("corpus manifest declares no spec_version")
    elif impl_version != corpus_version:
        vres.messages.append(
            f"spec-version mismatch: corpus={corpus_version!r} but the "
            f"implementation renders data-entviz-version={impl_version!r} "
            "(wrong corpus pinned, or the port is out of date)")
    else:
        vres.passed = True
    report.results.append(vres)

    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corpus", default=DEFAULT_CORPUS)
    ap.add_argument("--impl-cmd", default=None,
                    help="external impl: reads input.json on stdin, writes SVG on stdout")
    ap.add_argument("--tiers", default="AB", help="subset of A,B to run (default AB)")
    ap.add_argument("--only", default=None,
                    help="comma-separated vector ids to certify (subset)")
    ap.add_argument("--skip-file", default=None,
                    help="path to a file of vector ids the impl need not handle "
                         "(expected-fail); a skipped vector that passes fails the run")
    args = ap.parse_args()
    tiers = tuple(t for t in ("A", "B") if t in args.tiers.upper())
    only = set(args.only.split(",")) if args.only else None
    skip = read_skip_file(args.skip_file) if args.skip_file else None
    report = certify(args.corpus, impl_cmd=args.impl_cmd, tiers=tiers, only=only,
                     skip=skip)
    print(report.summary())
    sys.exit(0 if report.passed else 1)


if __name__ == "__main__":
    main()
