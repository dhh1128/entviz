"""Tests for the conformance suite (Tier A always; Tier B when the render
deps are installed) and a drift guard keeping the committed corpus in sync with
the reference renderer.

Mirrors the figure drift guard: if a change alters rendered output, the
committed golden render models go stale and this fails until the corpus is
regenerated (`PYTHONPATH=src:. python -m compliance.generate`).
"""
import json
import os

import pytest

from compliance import extract_model, diff_models
from compliance.corpus import ERROR_VECTORS, RENDER_VECTORS
from compliance.runner import DEFAULT_CORPUS, certify
from entviz import SPEC_VERSION
from entviz.pipeline import render

CORPUS = DEFAULT_CORPUS
HAS_CORPUS = os.path.isfile(os.path.join(CORPUS, "manifest.json"))


def _kw(kwargs):
    return {
        "target_ar": kwargs.get("target_ar", 1.0),
        "font_size_pt": kwargs.get("font_size_pt", 12),
        "note": kwargs.get("note"),
    }


def test_extract_model_is_deterministic():
    inp = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    a = extract_model(render(inp))
    b = extract_model(render(inp))
    assert diff_models(a, b) == []


def test_coordinates_are_compact_plain_decimals():
    # Numeric serialization (docs/spec.md): every numeric SVG attribute value is
    # a compact plain decimal -- no exponential notation, <= 3 fractional
    # digits, integers without a decimal point. Catches any coordinate that
    # slips past _normalize_numbers (the JS port had exactly such a bypass).
    import re as _re
    for inp in ("0123456789abcdef0123456789abcdef",
                "550e8400-e29b-41d4-a716-446655440000",
                "a" * 66):  # forces a blank-cell map + ellipse overlay
        svg = render(inp)
        for m in _re.finditer(r'="(-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)"', svg):
            v = m.group(1)
            assert "e" not in v.lower(), f"exponential notation: {v!r}"
            frac = v.split(".")[1] if "." in v else ""
            assert len(frac) <= 3, f"more than 3 fractional digits: {v!r}"
            assert not (frac and frac.endswith("0")), f"untrimmed trailing zero: {v!r}"


def test_diff_models_tolerates_subpixel_coordinate_noise():
    # Equivalence relation: coordinate/length/angle fields compare by value
    # within 0.05, so two implementations that round an unspecified-precision
    # coordinate to opposite sides of a boundary (12.345 vs 12.346) are equal,
    # but a real >= 0.05 geometry difference is still caught.
    base = {"ellipse": {"anchor": [10.0, 20.0], "rx": 12.345, "ry": 8.0, "rotation": 30.0}}
    near = {"ellipse": {"anchor": [10.0, 20.001], "rx": 12.346, "ry": 8.0, "rotation": 30.02}}
    far = {"ellipse": {"anchor": [10.0, 20.0], "rx": 12.5, "ry": 8.0, "rotation": 30.0}}
    assert diff_models(base, near) == []
    assert diff_models(base, far) != []


def test_extract_model_recovers_core_fields():
    m = extract_model(render("550e8400-e29b-41d4-a716-446655440000"))
    assert m["spec_version"] == SPEC_VERSION
    assert m["cols"] >= 2 and m["rows"] >= 2
    assert m["bg_color"].startswith("#")
    filled = [c for c in m["cells"].values() if not c["blank"]]
    assert filled, "expected at least one filled cell"
    c0 = filled[0]
    assert set(("text", "nucleus_bg", "fg", "surround_bits")) <= set(c0)
    assert 0 <= c0["surround_bits"] < (1 << 24)


@pytest.mark.parametrize("vid,entropy,kwargs,_cat", ERROR_VECTORS)
def test_error_vectors_are_rejected(vid, entropy, kwargs, _cat):
    with pytest.raises(Exception):
        render(entropy, **_kw(kwargs))


@pytest.mark.skipif(not HAS_CORPUS, reason="corpus not generated")
def test_committed_corpus_matches_reference():
    """Drift guard: every committed golden render model must match what the
    current reference renderer produces (Tier A, in-process — no raster deps)."""
    with open(os.path.join(CORPUS, "manifest.json")) as f:
        manifest = json.load(f)
    stale = []
    for vid, entropy, kwargs in RENDER_VECTORS:
        with open(os.path.join(CORPUS, vid, "model.json")) as f:
            golden = json.load(f)
        actual = extract_model(render(entropy, **_kw(kwargs)))
        d = diff_models(golden, actual)
        if d:
            stale.append((vid, d[:3]))
    assert not stale, (
        "committed corpus is stale; regenerate with "
        "`PYTHONPATH=src:. python -m compliance.generate`:\n"
        + "\n".join(f"  {vid}: {d}" for vid, d in stale))
    assert manifest["spec_version"] == SPEC_VERSION


@pytest.mark.skipif(not HAS_CORPUS, reason="corpus not generated")
def test_reference_certifies_tier_a():
    report = certify(CORPUS, tiers=("A",))
    assert report.passed, report.summary()


@pytest.mark.skipif(not HAS_CORPUS, reason="corpus not generated")
def test_reference_certifies_tier_b():
    pytest.importorskip("cairosvg")
    pytest.importorskip("PIL")
    report = certify(CORPUS, tiers=("A", "B"))
    assert report.passed, report.summary()
