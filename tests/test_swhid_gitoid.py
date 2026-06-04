"""
SWHID and gitoid parsers.

Both are real, standardized prefix schemes that namespace a git-style
hash. Neither changes the fundamentals: the prefix is non-entropy framing
that is split off (and excluded from the fingerprint, which hashes the
`core` only), the core is plain lowercase hex tokenized by the HEX
alphabet, and the scheme's object-type word becomes the type label.

  * SWHID  (Software Heritage IDentifier, ISO/IEC 18670 track):
        swh:1:<type>:<40-hex-sha1>
    where <type> in {snp, rel, rev, dir, cnt}. A git *commit* is `rev`
    (revision). Lowercase hex is canonical.

  * gitoid (OmniBOR git object identifier):
        gitoid:<object-type>:<hash-algo>:<hex>
    where <object-type> in {blob, tree, commit, tag} and <hash-algo> in
    {sha1 (40 hex), sha256 (64 hex)}.

See `this.i:g1tha5h0` for why these are recognized but a bespoke `git:`
prefix is not.
"""
from entviz.entropy import parse, parse_swhid, parse_gitoid, HEX
from entviz.fingerprint import compute_fingerprint


SHA1 = "309cf2674ee7a0749978cf8265ab91a60aea0f7d"      # 40 hex
SHA256 = "fee53a18d32820613c0527aa79be5cb30173c823a9b448fa4817767cc84c6f03"  # 64 hex


# ---- SWHID -------------------------------------------------------------


def test_swhid_revision_is_a_commit():
    p = parse_swhid("swh:1:rev:" + SHA1)
    assert p is not None
    assert p.type == "SWHID rev"
    assert p.alphabet is HEX
    assert p.prefix == "swh:1:rev:"
    assert p.core == SHA1
    assert p.suffix is None


def test_swhid_content_directory_release_snapshot_types():
    for ty in ("cnt", "dir", "rel", "snp"):
        p = parse_swhid(f"swh:1:{ty}:" + SHA1)
        assert p is not None, ty
        assert p.type == f"SWHID {ty}"
        assert p.core == SHA1


def test_swhid_hex_normalized_lowercase():
    p = parse_swhid("SWH:1:REV:" + SHA1.upper())
    assert p is not None
    assert p.prefix == "swh:1:rev:"   # scheme + type lowercased
    assert p.core == SHA1             # hex lowercased


def test_swhid_qualifiers_captured_as_suffix_not_entropy():
    # A qualified SWHID carries addressing context after the core id.
    # The qualifiers are not entropy, so they must not enter the core
    # (and therefore must not change the fingerprint).
    p = parse_swhid("swh:1:cnt:" + SHA1 + ";origin=https://example.org;lines=1-18")
    assert p is not None
    assert p.core == SHA1
    assert p.suffix == "origin=https://example.org;lines=1-18"
    assert compute_fingerprint(p.core) == compute_fingerprint(SHA1)


def test_swhid_rejects_unknown_type_and_bad_length():
    assert parse_swhid("swh:1:xxx:" + SHA1) is None      # bogus object type
    assert parse_swhid("swh:1:rev:" + SHA1[:-1]) is None  # 39 hex
    assert parse_swhid("swh:2:rev:" + SHA1) is None       # wrong scheme version
    assert parse_swhid("swh:1:rev:" + SHA256) is None     # SWHID v1 is sha1 only


def test_swhid_dispatches_through_parse():
    p = parse("swh:1:rev:" + SHA1)
    assert p.type == "SWHID rev"
    assert p.core == SHA1


# ---- gitoid ------------------------------------------------------------


def test_gitoid_blob_sha1():
    p = parse_gitoid("gitoid:blob:sha1:" + SHA1)
    assert p is not None
    assert p.type == "gitoid blob sha1"
    assert p.alphabet is HEX
    assert p.prefix == "gitoid:blob:sha1:"
    assert p.core == SHA1
    assert p.suffix is None


def test_gitoid_commit_sha256():
    p = parse_gitoid("gitoid:commit:sha256:" + SHA256)
    assert p is not None
    assert p.type == "gitoid commit sha256"
    assert p.core == SHA256


def test_gitoid_all_object_types():
    for obj in ("blob", "tree", "commit", "tag"):
        p = parse_gitoid(f"gitoid:{obj}:sha1:" + SHA1)
        assert p is not None, obj
        assert p.type == f"gitoid {obj} sha1"


def test_gitoid_hex_normalized_lowercase():
    p = parse_gitoid("GITOID:BLOB:SHA1:" + SHA1.upper())
    assert p is not None
    assert p.prefix == "gitoid:blob:sha1:"
    assert p.core == SHA1


def test_gitoid_rejects_algo_length_mismatch():
    assert parse_gitoid("gitoid:blob:sha1:" + SHA256) is None    # sha1 must be 40
    assert parse_gitoid("gitoid:blob:sha256:" + SHA1) is None    # sha256 must be 64
    assert parse_gitoid("gitoid:blob:md5:" + SHA1) is None       # unknown algo
    assert parse_gitoid("gitoid:thing:sha1:" + SHA1) is None     # unknown object type


def test_gitoid_dispatches_through_parse():
    p = parse("gitoid:blob:sha256:" + SHA256)
    assert p.type == "gitoid blob sha256"
    assert p.core == SHA256


# ---- fundamentals unchanged -------------------------------------------


def test_prefix_excluded_from_fingerprint_matches_bare_hex():
    # The whole point: swh:1:rev:<h>, gitoid:commit:sha1:<h>, and bare <h>
    # all visualize the SAME entropy — only the label differs.
    bare = compute_fingerprint(SHA1)
    assert compute_fingerprint(parse("swh:1:rev:" + SHA1).core) == bare
    assert compute_fingerprint(parse("gitoid:commit:sha1:" + SHA1).core) == bare
