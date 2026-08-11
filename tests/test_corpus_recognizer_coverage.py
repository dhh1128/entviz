"""The corpus must exercise every recognizer — and this test names the ones it doesn't.

Twice now a coverage hole has been found by accident, by a port agent tripping
over it rather than by anything here:

* v16 added the first Cardano vectors and discovered that **two ports had no
  Cardano parser at all**. Invisible until a vector existed to notice.
* v17's correction pass discovered that the corpus has **no Litecoin-legacy
  vector** — the `litecoin` vector is the bech32 `ltc1` form — so both the Go
  and the Java agent had to generate their own fixture to test that path, and
  neither the reference nor any port had ever been checked against the other
  for it.

A recognizer with no corpus vector is a recognizer every implementation is free
to get wrong, or omit entirely, while certifying green. This file makes that
condition *visible and enforced* instead of latent.

Two layers, because one is not enough:

1. **Automatic, function level.** Every ``parse_*`` recognizer must be reached by
   some corpus vector. Catches a wholly new recognizer added with no vector.
2. **Curated, branch level.** Function granularity is too coarse — it reports
   ``parse_litecoin_address`` as covered because the *bech32* branch is, while the
   *legacy* branch beside it has never been run. So a hand-kept inventory names
   each recognizer branch and asserts the corpus reaches it.

`UNCOVERED` below is the current debt, written down rather than forgotten. It is
a list to shrink, and adding to it should require an argument.
"""
import glob
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, ".")

from entviz import entropy as E  # noqa: E402

CORPUS = Path(__file__).resolve().parent.parent / "compliance" / "corpus"


def _corpus_entropies():
    out = []
    for path in sorted(glob.glob(str(CORPUS / "*" / "input.json"))):
        with open(path, encoding="utf-8") as fh:
            out.append(json.load(fh)["entropy"])
    return out


ENTROPIES = _corpus_entropies()


# --- layer 1: every recognizer function is reached ----------------------------

# Recognizers with no corpus vector at all. Each entry is debt: the path exists,
# five implementations claim to support it, and nothing checks that they agree.
# Empty, and that is the intended steady state. Paid down 2026-08-11: adding a
# vector costs a corpus regeneration and a port re-pin, but nothing else — no
# code change, no spec text, no version bump — so there was never a good reason
# to carry it. If you add an entry here, say why it cannot simply be a vector.
UNCOVERED_FUNCTIONS: set[str] = set()


def _recognizer_names():
    return sorted(
        n for n in dir(E)
        if n.startswith("parse_") and callable(getattr(E, n))
    )


def _reached(name):
    fn = getattr(E, name)
    for entropy in ENTROPIES:
        try:
            if fn(entropy) is not None:
                return True
        except Exception:
            continue
    return False


def test_every_recognizer_function_is_exercised_or_declared_uncovered():
    unreached = {n for n in _recognizer_names() if not _reached(n)}
    surprises = unreached - UNCOVERED_FUNCTIONS
    assert not surprises, (
        f"recognizer(s) with no corpus vector and not declared in "
        f"UNCOVERED_FUNCTIONS: {sorted(surprises)}. Either add a corpus vector "
        f"(preferred — an unexercised recognizer is one every port may get "
        f"wrong while certifying green) or add it to the set with a reason."
    )


def test_the_uncovered_declaration_does_not_go_stale():
    # If a vector gets added, this list must shrink. A debt list that silently
    # over-reports is how the debt stops being read.
    fixed = {n for n in UNCOVERED_FUNCTIONS if _reached(n)}
    assert not fixed, (
        f"{sorted(fixed)} now HAS corpus coverage — remove it from "
        f"UNCOVERED_FUNCTIONS"
    )


# --- layer 2: every recognizer BRANCH is reached ------------------------------

# (branch name, a valid sample, the `Parsed.type` it must produce). Function
# coverage cannot see these: each of the first three lives beside a sibling
# branch that IS covered, so its function reports green while it never runs.
BRANCHES = [
    # parse_litecoin_address's legacy arm. The `litecoin` corpus vector is the
    # bech32 `ltc1` form, so this base58check arm has never been exercised.
    # Found by the entviz-go and entviz-java agents on the 0.17.2 pass, which
    # each had to generate this fixture themselves.
    ("litecoin-legacy", "LKDyUEtTR1HXamkiEphisSiBJu6o3ZPE34", "LTC legacy"),
    ("eos", "eosio.token", "EOS"),
    ("hex-multihash",
     "1220b1674191a88ec5cdd733e4240a81803105dc412d6c6708d53ab94fc248f4f553",
     "hex multihash"),
]

# Branch-level debt, same contract as UNCOVERED_FUNCTIONS. Also empty.
UNCOVERED_BRANCHES: set[str] = set()


@pytest.mark.parametrize("name,sample,expected_type", BRANCHES)
def test_the_branch_sample_really_is_what_it_claims(name, sample, expected_type):
    # The inventory is only worth having if its samples are honest, so check
    # them against the parser before trusting them to describe coverage.
    parsed = E.parse(sample)
    assert parsed is not None, f"{name}: sample does not parse at all"
    assert parsed.type == expected_type, (
        f"{name}: sample parses as {parsed.type!r}, not {expected_type!r}"
    )


@pytest.mark.parametrize("name,sample,expected_type", BRANCHES)
def test_every_branch_is_exercised_or_declared_uncovered(name, sample, expected_type):
    covered = False
    for entropy in ENTROPIES:
        try:
            parsed = E.parse(entropy)
        except Exception:
            continue
        if parsed is not None and parsed.type == expected_type:
            covered = True
            break
    if name in UNCOVERED_BRANCHES:
        assert not covered, (
            f"{name} now HAS a corpus vector — remove it from "
            f"UNCOVERED_BRANCHES"
        )
    else:
        assert covered, (
            f"{name} has no corpus vector producing type {expected_type!r}. Add "
            f"one, or declare it in UNCOVERED_BRANCHES with a reason."
        )
