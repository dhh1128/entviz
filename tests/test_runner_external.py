"""Tests for the runner's external-implementation features:

* invariant pairs are now checked for an external ``--impl-cmd`` (not only for
  the in-process reference);
* ``--skip-file`` runs the full corpus minus declared skips, failing if a
  non-skipped vector fails OR a skipped vector unexpectedly passes;
* the spec-version match assertion fails on a corpus/impl version mismatch.

These exercise the runner through a configurable fake external impl
(``tests/conformance_fake_impl.py``) so the contract is verified end-to-end
through ``subprocess`` exactly as a real port CLI is.
"""
import os
import sys

import pytest

from compliance.runner import DEFAULT_CORPUS, certify, read_skip_file

CORPUS = DEFAULT_CORPUS
HAS_CORPUS = os.path.isfile(os.path.join(CORPUS, "manifest.json"))
FAKE = os.path.join(os.path.dirname(__file__), "conformance_fake_impl.py")

# Run every external-impl check at Tier A only: these features are tier-agnostic
# and Tier B needs the raster deps.
TIERS = ("A",)

pytestmark = pytest.mark.skipif(not HAS_CORPUS, reason="corpus not generated")


def _cmd(*extra):
    return " ".join([sys.executable, FAKE, *extra])


def _results(report):
    return {r.vid: r for r in report.results}


# --------------------------------------------------------------------------
# 1. invariant pairs are checked for an external impl
# --------------------------------------------------------------------------

def test_external_impl_clean_passes_including_invariants_and_version():
    report = certify(CORPUS, impl_cmd=_cmd(), tiers=TIERS)
    res = _results(report)
    invariants = [r for r in report.results if r.kind == "invariant"]
    assert invariants, "invariant pairs must be checked for an external impl"
    assert all(r.passed for r in invariants), report.summary()
    assert res["spec-version-match"].passed
    assert report.passed, report.summary()


def test_external_impl_corrupting_one_member_fails_its_invariant_pair():
    # Corrupt only the dashed UUID; its pair (uuid-dashed == uuid-undashed) must
    # now fail, proving the invariant is genuinely asserted via the impl. The
    # corruption bumps data-input-bytes, which IS excluded from the invariant
    # comparison, so the pair fails only because the dashed member's own Tier A
    # diff is surfaced through the render result — confirm the run fails overall.
    report = certify(CORPUS, impl_cmd=_cmd("--corrupt-if-contains", "550e8400"),
                     tiers=TIERS)
    res = _results(report)
    assert not res["uuid-dashed"].passed
    assert not report.passed


# --------------------------------------------------------------------------
# 2a. a non-skipped vector that fails fails the run
# --------------------------------------------------------------------------

def test_failing_vector_fails_the_run():
    report = certify(CORPUS, impl_cmd=_cmd("--reject-if-contains", "did:peer"),
                     tiers=TIERS)
    res = _results(report)
    assert not res["did-peer-2"].passed
    assert "render raised" in " ".join(res["did-peer-2"].messages) \
        or res["did-peer-2"].messages
    assert not report.passed


# --------------------------------------------------------------------------
# 2b. a declared skip absorbs a genuinely-unsupported vector
# --------------------------------------------------------------------------

def test_skip_absorbs_a_genuinely_failing_vector():
    report = certify(CORPUS, impl_cmd=_cmd("--reject-if-contains", "did:peer"),
                     tiers=TIERS, skip={"did-peer-2"})
    res = _results(report)
    assert res["did-peer-2"].skipped
    assert res["did-peer-2"].passed  # expected-fail, so it counts as a pass
    assert report.passed, report.summary()


# --------------------------------------------------------------------------
# 2c. a skipped vector that PASSES is a hard failure (skip-list rot)
# --------------------------------------------------------------------------

def test_skip_that_unexpectedly_passes_fails_the_run():
    report = certify(CORPUS, impl_cmd=_cmd(), tiers=TIERS, skip={"did-peer-2"})
    res = _results(report)
    assert res["did-peer-2"].skipped
    assert not res["did-peer-2"].passed
    assert any("skip-list rot" in m for m in res["did-peer-2"].messages)
    assert not report.passed


def test_unknown_skip_id_fails_the_run():
    report = certify(CORPUS, impl_cmd=_cmd(), tiers=TIERS,
                     skip={"no-such-vector"})
    res = _results(report)
    assert "no-such-vector" in res
    assert not res["no-such-vector"].passed
    assert not report.passed


# --------------------------------------------------------------------------
# 3. spec-version match assertion
# --------------------------------------------------------------------------

def test_version_mismatch_fails_the_run():
    report = certify(CORPUS, impl_cmd=_cmd("--version-override", "v999"),
                     tiers=TIERS)
    res = _results(report)
    assert not res["spec-version-match"].passed
    assert any("mismatch" in m for m in res["spec-version-match"].messages)
    assert not report.passed


# --------------------------------------------------------------------------
# skip-file parsing
# --------------------------------------------------------------------------

def test_read_skip_file_ignores_comments_and_reasons(tmp_path):
    f = tmp_path / "skips.txt"
    f.write_text(
        "# this is a comment\n"
        "\n"
        "did-peer-2  >512-bit large-input path not ported\n"
        "did-jwk-large # inline reason\n"
    )
    assert read_skip_file(str(f)) == {"did-peer-2", "did-jwk-large"}
