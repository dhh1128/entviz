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
    assert p.type == ""               # no type: the self-describing prefix is the label
    assert p.alphabet is HEX
    assert p.prefix == "swh:1:rev:"
    assert p.core == SHA1
    assert p.suffix is None


def test_swhid_content_directory_release_snapshot_types():
    for ty in ("cnt", "dir", "rel", "snp"):
        p = parse_swhid(f"swh:1:{ty}:" + SHA1)
        assert p is not None, ty
        assert p.type == ""                    # no echoing type
        assert p.prefix == f"swh:1:{ty}:"      # object type carried by the prefix
        assert p.core == SHA1


def test_swhid_hex_normalized_lowercase():
    p = parse_swhid("SWH:1:REV:" + SHA1.upper())
    assert p is not None
    assert p.prefix == "swh:1:rev:"   # scheme + type lowercased
    assert p.core == SHA1             # hex lowercased


def test_swhid_qualifiers_recognized_but_dropped():
    # A qualified SWHID still parses (recognized via its core), but the
    # qualifier tail is a FREE annotation: it varies independently of the
    # value, so it is dropped — not entered into the core, not surfaced as a
    # suffix. See this.i:sufxbind.
    p = parse_swhid("swh:1:cnt:" + SHA1 + ";origin=https://example.org;lines=1-18")
    assert p is not None
    assert p.core == SHA1
    assert p.suffix is None
    assert compute_fingerprint(p.core) == compute_fingerprint(SHA1)


def test_swhid_qualifier_does_not_affect_rendering():
    # Two SWHIDs differing only in a free qualifier are the same value, so
    # the visual entviz must be identical (only the informational
    # data-input-bytes metadata reflects the literal input length).
    import re
    from entviz.pipeline import render
    norm = lambda s: re.sub(r' data-input-bytes="\d+"', "", s)
    a = render("swh:1:cnt:" + SHA1 + ";origin=https://a.example")
    b = render("swh:1:cnt:" + SHA1 + ";lines=1-200;origin=https://much-longer.example/x")
    assert norm(a) == norm(b)


def test_swhid_rejects_unknown_type_and_bad_length():
    assert parse_swhid("swh:1:xxx:" + SHA1) is None      # bogus object type
    assert parse_swhid("swh:1:rev:" + SHA1[:-1]) is None  # 39 hex
    assert parse_swhid("swh:2:rev:" + SHA1) is None       # wrong scheme version
    assert parse_swhid("swh:1:rev:" + SHA256) is None     # SWHID v1 is sha1 only


def test_swhid_dispatches_through_parse():
    p = parse("swh:1:rev:" + SHA1)
    assert p.type == ""
    assert p.core == SHA1


# ---- gitoid ------------------------------------------------------------


def test_gitoid_blob_sha1():
    p = parse_gitoid("gitoid:blob:sha1:" + SHA1)
    assert p is not None
    assert p.type == ""               # no type: the self-describing prefix is the label
    assert p.alphabet is HEX
    assert p.prefix == "gitoid:blob:sha1:"
    assert p.core == SHA1
    assert p.suffix is None


def test_gitoid_commit_sha256():
    p = parse_gitoid("gitoid:commit:sha256:" + SHA256)
    assert p is not None
    assert p.type == ""
    assert p.prefix == "gitoid:commit:sha256:"
    assert p.core == SHA256


def test_gitoid_all_object_types():
    for obj in ("blob", "tree", "commit", "tag"):
        p = parse_gitoid(f"gitoid:{obj}:sha1:" + SHA1)
        assert p is not None, obj
        assert p.type == ""                      # no echoing type
        assert p.prefix == f"gitoid:{obj}:sha1:"  # obj carried by the prefix


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
    assert p.type == ""
    assert p.core == SHA256


# ---- fundamentals unchanged -------------------------------------------


def test_no_type_label_renders_self_describing_prefix_alone():
    # The top label must show the prefix on its own, with no echoing type
    # ("SWHID"/"git object") in front of it. See this.i:lbldedup.
    from entviz.pipeline import render
    svg = render("swh:1:rev:" + SHA1)
    assert "swh:1:rev:..." in svg
    assert "SWHID" not in svg
    svg2 = render("gitoid:blob:sha256:" + SHA256)
    assert "gitoid:blob:sha256:..." in svg2
    assert "git object" not in svg2


def test_prefix_excluded_from_fingerprint_matches_bare_hex():
    # The whole point: swh:1:rev:<h>, gitoid:commit:sha1:<h>, and bare <h>
    # all visualize the SAME entropy — only the label differs.
    bare = compute_fingerprint(SHA1)
    assert compute_fingerprint(parse("swh:1:rev:" + SHA1).core) == bare
    assert compute_fingerprint(parse("gitoid:commit:sha1:" + SHA1).core) == bare
