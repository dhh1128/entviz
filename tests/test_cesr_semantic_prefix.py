"""
Identity-bearing prefixes must bind the fingerprint, and — when they share
the body's alphabet and sit contiguously — appear in the rendered cells too.

Unlike a *presentation* prefix (hex's `0x`, multibase's base selector — it
only says how the value is written, and is normalized away like case), an
*identity* prefix changes what the value IS. The "swap test" (docs/spec.md):
hold the body fixed; if another legal prefix could sit there and denote a
different value, the prefix is identity.

Two mechanisms, by alphabet:
  * Same alphabet + contiguous (CESR derivation code, LEI LOU): the prefix
    stays IN the core, so it is rendered in the cells AND bound by the
    fingerprint (which hashes the core *text* — see this.i:h4shtext).
  * Different alphabet / buried (SWHID & gitoid object-type, which are
    letters ahead of a hex body): kept in `prefix` with prefix_semantic=True,
    so it binds the fingerprint via the prefix-fold path but not the cells.

Also pins the table-correctness fixes: blinding factor is `a` (not `Z`,
which is Tag11), and the FN-DSA post-quantum codes parse.
"""
import re

from entviz.entropy import parse, parse_cesr, parse_lei
from entviz.fingerprint import compute_fingerprint
from entviz.pipeline import render

# A single 43-char base64url body shared by three derivation codes.
BODY43 = "Kxy2sgzfplyr_tgwIxS19f2OchFHtLwPWD3v4oYimBx"
assert len(BODY43) == 43

# A real LEI (Bloomberg L.P.) — passes the MOD 97-10 checksum.
LEI = "5493001KJTIIGC8Y1R12"

_CLIP_RE = re.compile(r'grid-clip-([0-9a-f]{16})-')


def _clip_digest16(svg: str) -> str:
    m = _CLIP_RE.search(svg)
    assert m, "no grid-clip id found in SVG"
    return m.group(1)


# ---- CESR: code lives in the core (cells + fingerprint) ----------------

def test_cesr_code_stays_in_core():
    # The derivation code is identity and base64url like the body, so it is
    # NOT split into a prefix — it stays at the front of the core and is
    # therefore rendered in cell 0.
    p = parse_cesr("D" + BODY43)
    assert p is not None
    assert p.prefix is None
    assert p.core == "D" + BODY43
    assert p.core.startswith("D")


def test_derivation_code_binds_fingerprint():
    # B / D / E over an identical body produce three DIFFERENT fingerprints,
    # each = SHA-512(code + body) (the whole primitive is the core). Before
    # the fix they were pixel-identical (fingerprint over the body alone).
    digests = {}
    for code in ("B", "D", "E"):
        s = code + BODY43
        clip = _clip_digest16(render(s))
        assert clip == compute_fingerprint(s).hex()[:16]
        digests[code] = clip
    assert len(set(digests.values())) == 3, "codes collide in fingerprint"


def test_derivation_code_appears_in_cell_text():
    # The code must reach the TEXT channel (cells), not just the gestalt —
    # short inputs have no fingerprint-middle cells, so the cells are the
    # only read-aloud carrier. cell 0's text begins with the code.
    svg = render("D" + BODY43)
    # The leading cell's text run begins with the code char.
    assert "DKxy" in svg, "code char not rendered into the leading cell"


# ---- Signal / presentation prefixes are unchanged ----------------------

def test_signal_prefix_is_not_semantic():
    p = parse("0x742d35cc6634c0532925a3b844bc454e4438f44e")
    assert p is not None
    assert p.prefix_semantic is False


def test_signal_prefix_fingerprint_over_core_only():
    eth = "0x742d35cc6634c0532925a3b844bc454e4438f44e"
    p = parse(eth)
    assert p.prefix_semantic is False
    clip = _clip_digest16(render(eth))
    assert clip == compute_fingerprint(p.core).hex()[:16]


# ---- LEI: the LOU issuer code lives in the core ------------------------

def test_lei_lou_stays_in_core():
    p = parse_lei(LEI)
    assert p is not None
    assert p.prefix is None
    # core = LOU + "00" + entity (everything but the 2-char checksum).
    assert p.core == LEI[:18]
    assert p.core.startswith("5493")  # the LOU
    assert p.suffix == LEI[18:]       # the MOD 97-10 checksum


def test_lei_lou_binds_fingerprint():
    # Two LEIs with the same entity body but a different LOU are different
    # registrations and must render differently. (Construct by swapping the
    # LOU; we compare via the core that feeds the fingerprint.)
    p = parse_lei(LEI)
    clip = _clip_digest16(render(LEI))
    assert clip == compute_fingerprint(p.core).hex()[:16]
    # The LOU is inside the hashed core, so a different LOU => different core.
    assert LEI[:4] in p.core


# ---- SWHID / gitoid: object-type folds into the fingerprint -----------

def test_swhid_object_type_binds_fingerprint():
    # Same git hash, different object type (cnt vs rev) = different object.
    h = "94a9ed024d3859793618152ea559a168bbcbb5e2"
    cnt = _clip_digest16(render(f"swh:1:cnt:{h}"))
    rev = _clip_digest16(render(f"swh:1:rev:{h}"))
    assert cnt != rev, "SWHID object-type must bind the fingerprint"


def test_gitoid_object_type_binds_fingerprint():
    h = "94a9ed024d3859793618152ea559a168bbcbb5e2"
    blob = _clip_digest16(render(f"gitoid:blob:sha1:{h}"))
    # A SWHID content over the same git hash must NOT collide with the gitoid.
    swhid = _clip_digest16(render(f"swh:1:cnt:{h}"))
    assert blob != swhid


# ---- Table-correctness fixes ------------------------------------------

def test_blinding_factor_is_lowercase_a():
    p = parse_cesr("a" + BODY43)
    assert p is not None
    assert "blinding" in p.type.lower()


def test_capital_Z_is_not_a_44char_primitive():
    # `Z` is Tag11 (12 chars), not a blinding factor.
    assert parse_cesr("Z" + BODY43) is None


def test_fndsa_post_quantum_codes_parse():
    for code in ("c", "d"):
        p = parse_cesr(code + BODY43)
        assert p is not None, f"{code} should parse"
        assert "FN-DSA" in p.type
