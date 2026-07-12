"""Tests for the entropy characterization model.

Asserts the structured characterization fields (encoding / scheme / role /
qualifiers / size_basis / size_bits / parts+bind / entropy_type) for the worked
ground-truth cases in reviews/entropy-characterization-redesign.md, verified
against the parser oracle. These pin the model so the four ports must reproduce
identical values. See docs/spec.md -> *Entropy characterization* and
this.i:ch4rmod3l / s1zeb1ts.
"""
import pytest

from entviz.characterize import characterize

# Corpus entropy strings for the worked cases (exact, from compliance/corpus.py).
E = {
    "cesr-said-e": "EBfdlu8R27Fbx_ehrqwImnK_8Cm79sqbAQ4caaZG_LFv",
    "btc-legacy": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
    "cid-v1": "bafybeigdyrzt5sfp7udm7hu76uh7y26nf3efuylqabf3oclgtqy55fbzdi",
    "cid-v0": "QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG",
    "did-ethr-network": "did:ethr:0x5:0xf3beac30c498d9e26865f34fcaa57dbb935b0d74",
    "did-key-ed25519": "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK",
    "did-peer-2": (
        "did:peer:2.Ez6LSt4Jscr227NFyuzKHT85haVE4AFVXm1tDwYeZ5xenxMmW."
        "Vz6MkfvwnoNS6Cto38MEMbqdnypVDN7gS4oAMaHFkjAUse5JE"
    ),
    "gitoid-blob-sha256": (
        "gitoid:blob:sha256:"
        "473a0f4c3be8a93681a267e3b1e9a7dcda1185436fe141f7749120a303721813"
    ),
    "urn-isbn": "urn:isbn:0451450523",
    "snowflake-19": "1234567890987654321",
    "ssh-ed25519": (
        "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDtJVH9hM+2DyhmgRZBfeIDoV"
        "qCTbXY+0nKlS5pTkkXY user@example.com"
    ),
    "lei-bloomberg": "5493001KJTIIGC8Y1R12",
    "stellar": "GCKFBEIYTKP5RDBQMUTAPDCDHF2TR4LPNRGW4JBQQTQUYZP4LDKP3SGM",
    "eth-checksummed": "0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed",
    "bitcoincash": "bitcoincash:qpm2qsznhks23z7629mms6s4cwef74vcwvy22gdx6a",
    "text-lorem": "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
}


def _binds(c):
    return [p["bind"] for p in c["parts"]]


def _texts(c):
    return [p["text"] for p in c["parts"]]


# --- exact scheme / role / size_basis / size_bits per worked case ---------
# (scheme, role, size_basis, size_bits)
WORKED = {
    "cesr-said-e": ("cesr", "digest", "decoded", 264),
    "btc-legacy": ("btc", "address", "decoded", 168),
    "cid-v1": ("cid", "identifier", "decoded", 288),
    "cid-v0": ("cid", "identifier", "decoded", 264),
    "did-ethr-network": ("did", "identifier", "utf8", 368),
    "did-key-ed25519": ("did", "identifier", "utf8", 384),
    "did-peer-2": ("did", "identifier", "utf8", 808),
    "gitoid-blob-sha256": ("gitoid", "digest", "decoded", 256),
    "urn-isbn": ("urn", "identifier", "utf8", 80),
    "snowflake-19": ("snowflake", "identifier", "decoded", 64),
    "ssh-ed25519": ("ssh", "key", "decoded", 264),
    "lei-bloomberg": ("lei", "identifier", "decoded", 96),
    "stellar": ("stellar", "address", "decoded", 272),
    "eth-checksummed": ("eth", "address", "decoded", 160),
    "bitcoincash": ("bch", "address", "decoded", 208),
    "text-lorem": (None, None, "utf8", 448),
}


@pytest.mark.parametrize("vid,expected", WORKED.items())
def test_worked_scheme_role_size(vid, expected):
    scheme, role, size_basis, size_bits = expected
    c = characterize(E[vid])
    assert c["scheme"] == scheme, c
    assert c["role"] == role, c
    assert c["size_basis"] == size_basis, c
    assert c["size_bits"] == size_bits, c


def test_size_bits_is_multiple_of_8():
    for vid in WORKED:
        assert characterize(E[vid])["size_bits"] % 8 == 0


def test_role_is_closed_enum_or_none():
    allowed = {None, "key", "signature", "digest", "address", "identifier"}
    for vid in E:
        assert characterize(E[vid])["role"] in allowed


def test_entropy_type_is_scheme_or_encoding():
    for vid in E:
        c = characterize(E[vid])
        assert c["entropy_type"] == (c["scheme"] if c["scheme"] is not None else c["encoding"])


# --- qualifiers ------------------------------------------------------------

def test_cesr_qualifiers():
    c = characterize(E["cesr-said-e"])
    assert c["qualifiers"] == {"algorithm": "Blake3-256"}


def test_did_ethr_qualifiers():
    c = characterize(E["did-ethr-network"])
    assert c["qualifiers"] == {"method": "ethr", "network": "0x5"}


def test_urn_isbn_qualifiers():
    c = characterize(E["urn-isbn"])
    assert c["qualifiers"] == {"nid": "isbn"}


def test_cid_v1_qualifiers():
    c = characterize(E["cid-v1"])
    assert c["qualifiers"] == {"version": 1, "codec": "dag-pb", "hash": "sha2-256"}


def test_ssh_qualifiers():
    c = characterize(E["ssh-ed25519"])
    assert c["qualifiers"] == {"algorithm": "ed25519"}


def test_gitoid_qualifiers():
    c = characterize(E["gitoid-blob-sha256"])
    assert c["qualifiers"] == {"object": "blob", "algorithm": "sha256"}


def test_bitcoincash_qualifiers():
    c = characterize(E["bitcoincash"])
    assert c["qualifiers"].get("network") == "mainnet"


# --- parts + bind ----------------------------------------------------------

def test_cesr_parts_single_core():
    c = characterize(E["cesr-said-e"])
    assert _binds(c) == ["core"]
    assert _texts(c) == [E["cesr-said-e"]]


def test_btc_legacy_parts_none_core_none():
    # "1" -> none, 29-char body -> core, "vfNa" checksum -> none
    c = characterize(E["btc-legacy"])
    assert _binds(c) == ["none", "core", "none"]
    assert _texts(c)[0] == "1"
    assert _texts(c)[2] == "vfNa"


def test_cid_v1_prefix_is_none():
    c = characterize(E["cid-v1"])
    assert _binds(c) == ["none", "core"]
    assert _texts(c)[0] == "b"


def test_cid_v0_prefix_is_none():
    c = characterize(E["cid-v0"])
    assert _binds(c) == ["none", "core"]
    assert _texts(c)[0] == "Qm"


def test_did_ethr_fold_then_core():
    c = characterize(E["did-ethr-network"])
    assert _binds(c) == ["fold", "core"]
    assert _texts(c)[0] == "did:ethr:"


def test_did_key_z_stays_in_core():
    # The leading multibase "z" is bind=core inside a did:key msi (Wrinkle 4).
    c = characterize(E["did-key-ed25519"])
    assert _binds(c) == ["fold", "core"]
    core = _texts(c)[1]
    assert core.startswith("z6Mk")


def test_gitoid_fold_then_core():
    c = characterize(E["gitoid-blob-sha256"])
    assert _binds(c) == ["fold", "core"]
    assert _texts(c)[0] == "gitoid:blob:sha256:"


def test_urn_isbn_fold_then_core():
    c = characterize(E["urn-isbn"])
    assert _binds(c) == ["fold", "core"]
    assert _texts(c)[0] == "urn:isbn:"
    assert _texts(c)[1] == "0451450523"


def test_ssh_framing_prefix_is_none():
    c = characterize(E["ssh-ed25519"])
    assert _binds(c) == ["none", "core"]
    assert _texts(c)[0].startswith("AAAA")


def test_lei_in_core_lou_and_none_suffix():
    # The LOU code is in the core (bind=core), the MOD-97 check digits are a
    # none-bound shown suffix.
    c = characterize(E["lei-bloomberg"])
    assert _binds(c) == ["core", "none"]
    assert _texts(c)[1] == "12"


def test_stellar_prefix_is_none():
    c = characterize(E["stellar"])
    assert _binds(c) == ["none", "core"]
    assert _texts(c)[0] == "G"


def test_eth_prefix_is_none():
    c = characterize(E["eth-checksummed"])
    assert _binds(c) == ["none", "core"]
    assert _texts(c)[0] == "0x"


def test_bitcoincash_prefix_is_none():
    c = characterize(E["bitcoincash"])
    assert _binds(c) == ["none", "core"]
    assert _texts(c)[0] == "bitcoincash:"


def test_text_lorem_fallback_is_utf8_core_only():
    c = characterize(E["text-lorem"])
    assert c["scheme"] is None
    assert c["role"] is None
    assert c["size_basis"] == "utf8"
    assert c["encoding"] == "base64url"
    assert _binds(c) == ["core"]


# --- did:jwk: base64url JSON msi is STILL utf8 basis (Wrinkle 1) -----------

def test_did_jwk_is_utf8_despite_base64url_content():
    jwk = (
        "did:jwk:eyJjcnYiOiJQLTI1NiIsImt0eSI6IkVDIiwieCI6ImFjYklRaXVNcz"
        "NpOF91c3pFakoydHBUdFJNNEVVM3l6OTFQSDZDZEgyVjAiLCJ5IjoiX0tjeUxq"
        "OXZXTXB0bm1LdG00NkdxRHo4d2Y3NEk1TEtncmwyR3pIM25TRSJ9"
    )
    c = characterize(jwk)
    assert c["scheme"] == "did"
    assert c["role"] == "identifier"
    assert c["size_basis"] == "utf8"  # NOT decoded, despite base64url JSON msi


# --- did:pkh / did:key role stays identifier (Wrinkle 3) -------------------

def test_did_pkh_role_is_identifier_not_address():
    c = characterize("did:pkh:eip155:1:0xb9c5714089478a327f09197987f16f9e5d936e8a")
    assert c["scheme"] == "did"
    assert c["role"] == "identifier"  # NOT "address"


def test_did_key_role_is_identifier_not_key():
    c = characterize(E["did-key-ed25519"])
    assert c["role"] == "identifier"  # NOT "key"
