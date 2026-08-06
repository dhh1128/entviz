"""The positional decode must stay EXACT while being fast (`this.i:f4std3c0`).

`size_bits` for base58/base36/decimal is defined normatively as "decode the core
to its integer value and take its minimal byte length" (docs/spec.md, Resolution
A). The implementation computes that with a balanced divide-and-conquer fold
rather than the O(n²) digit-at-a-time one. These tests pin the two properties
that matter: the fast fold returns exactly what the naive fold would, and the
cheap `ceil(len × log2(base) / 8)` estimate — which is what a reader reaching
for a speedup will try next — is *not* equivalent, so nobody swaps it in.
"""
import math

import pytest

from entviz.characterize import (
    _decoded_bytes_integer,
    _digits_to_int,
    _size_bits,
    characterize,
)
from entviz.entropy import BASE36, BASE58, DECIMAL, parse


def _naive(digits, base):
    n = 0
    for d in digits:
        n = n * base + d
    return n


@pytest.mark.parametrize("base", [58, 36, 10])
@pytest.mark.parametrize("length", [0, 1, 31, 32, 33, 64, 129, 1000])
def test_balanced_fold_equals_the_naive_fold(base, length):
    # Deterministic digits with a mix of leading zeros and full-range values;
    # leading zeros are the case the cheap estimate gets wrong, so they must be
    # exercised on both sides of the leaf threshold.
    digits = [(i * 7 + i // 3) % base for i in range(length)]
    assert _digits_to_int(digits, base) == _naive(digits, base)
    if length:
        zeros = [0] * (length // 2) + digits[length // 2:]
        assert _digits_to_int(zeros, base) == _naive(zeros, base)


def test_leading_zero_digits_survive_the_split():
    # A base58 core of all '1's decodes to 0 regardless of length. The split
    # must not turn that into something else.
    for n in (1, 32, 33, 100):
        assert _digits_to_int([0] * n, 58) == 0


@pytest.mark.parametrize("core,alphabet", [
    ("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", BASE58),
    ("rEb8TK3gBgk5auZkwc6sHnwrGVJH8DuaLh", BASE58),
    ("1" * 26, BASE58),
    ("5493001KJTIIGC8Y1R12", BASE36),
    ("123456789", DECIMAL),
])
def test_decoded_byte_length_matches_a_direct_computation(core, alphabet):
    chars = alphabet.chars
    n = _naive([chars.find(c) if chars.find(c) >= 0 else chars.lower().find(c.lower())
                for c in core], len(chars))
    expected = 1 if n == 0 else (n.bit_length() + 7) // 8
    assert _decoded_bytes_integer(core, alphabet) == expected


def test_the_cheap_estimate_is_not_equivalent_and_must_not_be_substituted():
    # Guard against a future "optimization" that swaps the exact decode for
    # ceil(len * log2(base) / 8). It disagrees whenever leading digits are zero.
    #
    # Use the core the parser ACTUALLY produces for a Bitcoin P2PKH address —
    # characterize() splits off the '1' version prefix and the 4-char
    # base58check suffix, so the core is the middle, not the whole string.
    # Asserting on the whole string instead (192 vs 200) is a true statement
    # about a call the pipeline never makes.
    address = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
    core = parse(address).core
    assert core == "A1zP1eP5QGefi2DMPTfTL5SLmv7Di"
    exact = _size_bits(core, BASE58, "decoded")
    estimate = math.ceil(len(core) * math.log2(58) / 8) * 8
    assert exact == 168
    assert estimate == 176
    assert exact != estimate
    # And end-to-end, so the figure quoted in this.i:f4std3c0 stays honest.
    assert characterize(address)["size_bits"] == 168
