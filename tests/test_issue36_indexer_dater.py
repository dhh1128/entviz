"""Issue #36 — the CESR recognizer must cover the Indexer table (indexed
signatures) and the Dater (datetime) Matter code, instead of dropping them to
the ``raw`` base64url fallback.

Scope decisions (see this.i:idxs1gs0 and docs/spec.md role principle):

* **Indexed signatures ARE in scope** — a 64-byte controller/witness signature
  is exactly the high-entropy cryptographic material entviz exists to compare
  (docs/spec.md:11 names "signatures"). Every IdrDex variant of one algorithm
  (current-only "crt", "big" dual-index) collapses to ONE label; the code+index
  chars stay in the core, so they still drive the cells. Role -> ``signature``.
* **The Dater is recognized only to LABEL it correctly, not to endorse
  visualizing a datetime as entropy.** A datetime is low-entropy and directly
  human-readable — the antithesis of entviz's purpose — so it is recognized
  (better than a wrong ``raw`` label) but carries NO role in the closed enum:
  ``role`` is ``None``, NOT the ``key`` default.

Vectors are authoritative — generated from keripy 1.1.33 (``keri.core.coring``
``Siger`` / ``Dater``), hardcoded here so the test has no keripy dependency.
"""
from entviz.entropy import parse, parse_cesr
from entviz.characterize import characterize, render_label

# (qb64, expected CESR label, expected characterize role) — one per length class
# and per algorithm, small + big variants.
INDEXED_SIGS = [
    # small (hs1/hs2), fs 88 / 156
    ("ABCfhtCBiEx9ZZov6qDFWtAVn4bQgYhMfWWaL-qgxVrQFZ-G0IGITH1lmi_qoMVa0BWfhtCBiEx9ZZov6qDFWtAV", "Ed25519 idx sig"),    # A  Ed25519_Sig      idx1
    ("BDCfhtCBiEx9ZZov6qDFWtAVn4bQgYhMfWWaL-qgxVrQFZ-G0IGITH1lmi_qoMVa0BWfhtCBiEx9ZZov6qDFWtAV", "Ed25519 idx sig"),    # B  Ed25519_Crt_Sig  idx3
    ("CCCfhtCBiEx9ZZov6qDFWtAVn4bQgYhMfWWaL-qgxVrQFZ-G0IGITH1lmi_qoMVa0BWfhtCBiEx9ZZov6qDFWtAV", "secp256k1 idx sig"),  # C  ECDSA_256k1_Sig  idx2
    ("EFCfhtCBiEx9ZZov6qDFWtAVn4bQgYhMfWWaL-qgxVrQFZ-G0IGITH1lmi_qoMVa0BWfhtCBiEx9ZZov6qDFWtAV", "secp256r1 idx sig"),  # E  ECDSA_256r1_Sig  idx5
    ("0ACCAQIDBAUGBwgJCgsMDQ4PEBESExQVFhcYGRobHB0eHyAhIiMkJSYnKCkqKywtLi8wMTIzNDU2Nzg5AQIDBAUGBwgJCgsMDQ4PEBESExQVFhcYGRobHB0eHyAhIiMkJSYnKCkqKywtLi8wMTIzNDU2Nzg5", "Ed448 idx sig"),  # 0A Ed448_Sig idx2
    # big (hs2), fs 92 / 160
    ("2AAFAFCfhtCBiEx9ZZov6qDFWtAVn4bQgYhMfWWaL-qgxVrQFZ-G0IGITH1lmi_qoMVa0BWfhtCBiEx9ZZov6qDFWtAV", "Ed25519 idx sig"),    # 2A Ed25519_Big_Sig    idx5
    ("2CABABCfhtCBiEx9ZZov6qDFWtAVn4bQgYhMfWWaL-qgxVrQFZ-G0IGITH1lmi_qoMVa0BWfhtCBiEx9ZZov6qDFWtAV", "secp256k1 idx sig"),  # 2C ECDSA_256k1_Big_Sig idx1
    ("2EAHAHCfhtCBiEx9ZZov6qDFWtAVn4bQgYhMfWWaL-qgxVrQFZ-G0IGITH1lmi_qoMVa0BWfhtCBiEx9ZZov6qDFWtAV", "secp256r1 idx sig"),  # 2E ECDSA_256r1_Big_Sig idx7
    ("3AAADAADAQIDBAUGBwgJCgsMDQ4PEBESExQVFhcYGRobHB0eHyAhIiMkJSYnKCkqKywtLi8wMTIzNDU2Nzg5AQIDBAUGBwgJCgsMDQ4PEBESExQVFhcYGRobHB0eHyAhIiMkJSYnKCkqKywtLi8wMTIzNDU2Nzg5", "Ed448 idx sig"),  # 3A Ed448_Big_Sig idx3
]

# keri.core.coring.Dater(dts="2020-08-22T17:50:09.988921+00:00").qb64
DATER = "1AAG2020-08-22T17c50c09d988921p00c00"


def test_indexed_sigs_recognized_not_raw():
    for qb64, label in INDEXED_SIGS:
        answer = parse_cesr(qb64)
        assert answer is not None, f"indexed sig fell through to raw: {qb64}"
        assert answer.type == f"CESR {label}", (qb64, answer.type)
        # The derivation code + index stay IN the core (rendered in cells and
        # hashed), like every other CESR primitive; nothing is split to prefix.
        assert answer.prefix is None
        assert answer.core == qb64


def test_indexed_sigs_dispatch_via_parse():
    for qb64, label in INDEXED_SIGS:
        answer = parse(qb64)
        assert answer is not None and answer.type == f"CESR {label}"


def test_indexed_sig_role_is_signature():
    for qb64, label in INDEXED_SIGS:
        ch = characterize(qb64)
        assert ch["scheme"] == "cesr", ch
        assert ch["role"] == "signature", ch
        assert ch["qualifiers"] == {"algorithm": label}, ch


def test_indexed_sig_label_projection():
    # Top strip reads "CESR, <algo> idx sig"; there is no " pubkey" to strip.
    top, _bottom = render_label(characterize(INDEXED_SIGS[0][0]))
    assert top == "CESR, Ed25519 idx sig", top


def test_matter_vs_indexer_disambiguation_by_length():
    # A 44-char 'A...' is the Matter Ed25519 SEED; an 88-char 'A...' is the
    # Indexer signature. Length must decide, not the leading char alone.
    seed = "A" + "A" * 43  # 44 chars, base64url
    assert parse_cesr(seed).type == "CESR Ed25519 seed"
    sig = INDEXED_SIGS[0][0]
    assert len(sig) == 88 and sig[0] == "A"
    assert parse_cesr(sig).type == "CESR Ed25519 idx sig"


def test_dater_recognized_not_raw():
    answer = parse_cesr(DATER)
    assert answer is not None, "Dater fell through to raw"
    assert answer.type == "CESR datetime", answer.type
    assert answer.core == DATER


def test_dater_role_is_none_not_key():
    ch = characterize(DATER)
    assert ch["scheme"] == "cesr", ch
    # A datetime is recognized but carries NO closed-enum role — it MUST NOT
    # default to "key" (the reason we special-case it).
    assert ch["role"] is None, ch
    assert ch["qualifiers"] == {"algorithm": "datetime"}, ch


def test_dater_label_projection():
    top, _bottom = render_label(characterize(DATER))
    assert top == "CESR, datetime", top
