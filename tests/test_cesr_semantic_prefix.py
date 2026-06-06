"""
CESR derivation codes are *semantic* prefixes, not mere signals.

Unlike hex's `0x` (a constant, removable signal — no other prefix could
precede the same 20 bytes and mean something else), a CESR derivation code
is drawn from a set of alternatives that each make the *same* trailing
body denote a *different* object: `B<43>` is a non-transferable key,
`D<43>` a transferable key, `E<43>` a Blake3-256 digest. The "swap test"
(docs/spec.md) classifies such a prefix as identity-bearing, so it MUST
bind the fingerprint.

These tests pin two things:
  1. parse_cesr flags its prefix as semantic; signal prefixes do not.
  2. render() folds a semantic prefix into the fingerprint input
     (prefix + core), so derivation-code-only differences avalanche
     across every fingerprint-driven channel — while a signal prefix
     leaves the fingerprint over the core alone (unchanged behavior).

Also pins the table-correctness fixes: blinding factor is `a` (not `Z`,
which is Tag11), and the FN-DSA post-quantum codes parse.
"""
import re

from entviz.entropy import parse, parse_cesr
from entviz.fingerprint import compute_fingerprint
from entviz.pipeline import render

# A single 43-char base64url body shared by three derivation codes.
BODY43 = "Kxy2sgzfplyr_tgwIxS19f2OchFHtLwPWD3v4oYimBx"
assert len(BODY43) == 43

_CLIP_RE = re.compile(r'grid-clip-([0-9a-f]{16})-')


def _clip_digest16(svg: str) -> str:
    m = _CLIP_RE.search(svg)
    assert m, "no grid-clip id found in SVG"
    return m.group(1)


def test_cesr_prefix_is_semantic():
    p = parse_cesr("D" + BODY43)
    assert p is not None
    assert p.prefix == "D"
    assert p.core == BODY43
    assert p.prefix_semantic is True


def test_signal_prefix_is_not_semantic():
    # Ethereum's 0x is a pure signal; default prefix_semantic is False.
    p = parse("0x742d35cc6634c0532925a3b844bc454e4438f44e")
    assert p is not None
    assert p.prefix_semantic is False


def test_derivation_code_binds_fingerprint():
    # B / D / E over an identical body must now produce three DIFFERENT
    # fingerprints, each equal to SHA-512(code + body). Before the fix they
    # were pixel-identical (fingerprint over the body alone).
    digests = {}
    for code in ("B", "D", "E"):
        s = code + BODY43
        clip = _clip_digest16(render(s))
        expected = compute_fingerprint(s).hex()[:16]
        assert clip == expected, f"{code}: code not folded into fingerprint"
        digests[code] = clip
    assert len(set(digests.values())) == 3, "codes collide in fingerprint"


def test_signal_prefix_fingerprint_over_core_only():
    # A non-semantic (signal) prefix leaves the fingerprint over the core
    # alone — 0x is not hashed.
    eth = "0x742d35cc6634c0532925a3b844bc454e4438f44e"
    p = parse(eth)
    assert p.prefix_semantic is False
    clip = _clip_digest16(render(eth))
    assert clip == compute_fingerprint(p.core).hex()[:16]


def test_blinding_factor_is_lowercase_a():
    p = parse_cesr("a" + BODY43)
    assert p is not None
    assert "blinding" in p.type.lower()


def test_capital_Z_is_not_a_44char_primitive():
    # `Z` is Tag11 (12 chars), not a blinding factor. A 44-char `Z...`
    # string is not a valid CESR primitive.
    assert parse_cesr("Z" + BODY43) is None


def test_fndsa_post_quantum_codes_parse():
    # FN-DSA (FIPS 206) seeds at the 44-char sweet spot.
    for code in ("c", "d"):
        p = parse_cesr(code + BODY43)
        assert p is not None, f"{code} should parse"
        assert "FN-DSA" in p.type
