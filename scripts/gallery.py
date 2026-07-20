"""
Generate an HTML gallery of entvizes across a curated set of input
types and avalanche pairs. SVGs are written as standalone files under
docs/assets/gallery/ and referenced from docs/gallery.html.

The page title pulls both version axes from the entviz package
(SPEC_VERSION + __version__ — the same values the renderer stamps onto
every SVG), so the gallery's declared versions can never drift from the
library that produced the images.

Run from the repo root via uv (which puts the editable package on the
path):
    uv run python scripts/gallery.py
"""
import argparse
import html
import os
import re
import shutil

from entviz import SPEC_VERSION, __version__
from entviz.pipeline import render

# Repo root is the parent of this scripts/ directory; output paths default
# under docs/ relative to it.
REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))


SAMPLES = [
    ("UUIDs", [
        ("Random UUID v4",          "550e8400-e29b-41d4-a716-446655440000"),
        ("Nil UUID",                "00000000-0000-0000-0000-000000000000"),
        ("Max UUID",                "ffffffff-ffff-ffff-ffff-ffffffffffff"),
        ("Sequential, ends in …01", "00000000-0000-0000-0000-000000000001"),
    ]),
    ("Avalanche: single-character differences", [
        ("UUID A",                  "550e8400-e29b-41d4-a716-446655440000"),
        ("UUID A with last char flipped", "550e8400-e29b-41d4-a716-446655440001"),
        ("UUID A with mid char flipped",  "550e8400-e29b-41d5-a716-446655440000"),
        ("UUID A with first char flipped","450e8400-e29b-41d4-a716-446655440000"),
    ]),
    ("Hex of various sizes", [
        ("64-bit hex",  "a1b2c3d4e5f6a7b8"),
        ("128-bit hex", "0123456789abcdef0123456789abcdef"),
        ("256-bit hex", "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"),
        ("512-bit hex", "0123456789abcdef" * 8),
    ]),
    # One 256-bit input rendered at three reference font sizes. Geometry scales
    # linearly with font_size_pt, so this shows the same entviz small / nominal
    # / large. A sample tuple's 3rd element may be a dict of render() kwargs.
    ("Same 256-bit input at three font sizes", [
        ("6pt",  "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08", {"font_size_pt": 6}),
        ("12pt", "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08", {"font_size_pt": 12}),
        ("24pt", "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08", {"font_size_pt": 24}),
    ]),
    ("ULIDs (Crockford base32)", [
        ("Canonical ULID",                 "01ARZ3NDEKTSV4RRFFQ69G5FAV"),
        ("Lowercase ULID (normalized up)", "01arz3ndektsv4rrffq69g5fav"),
        ("ULID with I/L/O aliases",        "01ARZ3NDEKTSV4RRFFQ69G5FaIlO"[:26]),
    ]),
    ("Blockchain addresses", [
        ("Ethereum",        "0x742d35cc6634c0532925a3b844bc454e4438f44e"),
        # The Satoshi genesis coinbase address is 1A1zP1eP… (block 0's reward
        # output). The prior gallery used it under the plain "Bitcoin legacy"
        # label and paired it with a bogus, checksum-invalid "genesis" address
        # (1NSUpdRF…) that raised on render. Fixed: legacy now uses the canonical
        # Bitcoin-wiki example P2PKH, and the genesis entry uses the real
        # genesis address — both checksum-valid and distinct.
        ("Bitcoin legacy",  "1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2"),
        ("Bitcoin (Satoshi genesis)", "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"),
        ("Ripple",          "rEb8TK3gBgk5auZkwc6sHnwrGVJH8DuaLh"),
    ]),
    ("Bech32 addresses", [
        ("Bitcoin SegWit P2WPKH",       "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4"),
        ("Bitcoin SegWit P2WSH",        "bc1qrp33g0q5c5txsp9arysrx4k6zdkfs4nce4xj0gdcccefvpysxf3qccfmv3"),
        # v14: real checksum-valid ltc1 / Shelley addresses (the prior gallery
        # placeholders failed the now-enforced bech32 polymod and would raise).
        ("Litecoin (ltc1)",             "ltc1qw508d6qejxtdg4y5r3zarvary0c5xw7kgmn4n9"),
        ("Bitcoin Cash CashAddr",       "bitcoincash:qpm2qsznhks23z7629mms6s4cwef74vcwvy22gdx6a"),
        ("Cardano Shelley",
         "addr1qyqqzqsrqszsvpcgpy9qkrqdpc83qygjzv2p29shrqv35xmyv4nxw6rfdf4kcmtwdac8zunnw36hvamc09a8klra0elsr0jfpr"),
        ("Cosmos Hub (checksum-validated, HRP in label)",
         "cosmos1qqqsyqcyq5rqwzqfpg9scrgwpugpzysnrk363e"),
        ("Osmosis (same generic bech32 parser)",
         "osmo1qqqsyqcyq5rqwzqfpg9scrgwpugpzysntdz28t"),
    ]),
    ("SSH public keys", [
        ("ssh-ed25519 — label reads 264-bit: the 256-bit key plus one structural "
         "byte base64 alignment can't shed; input comment dropped from entviz",
         "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDtJVH9hM+2DyhmgRZBfeIDoVqCTbXY+0nKlS5pTkkXY user@example.com"),
        ("ssh-rsa (3072-bit key) — label reads 3096-bit: the modulus carries ~3 "
         "bytes of SSH mpint sign / length framing; input comment dropped from entviz",
         "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQDSD+oM4kLidAptE5pjRA8OBIWNysc9reQJjK"
         "egek2jATA3bSvKdq/wdQtpbihEx5OlKMo//V/8QpAIjCSsBaMb6G/e/D5kC9wCjnYJ"
         "J68+34L+H5Fx1Ofuiz3BidgssINw/qbV0u1vrCop+ggs6lkl+pIwa+9kPriD9xdowC"
         "OQABMVl4todcojY8gZK/Zs5XTwKi9Z8MRS/37FEPxlvpRExMmQU8v2tnP/TDqhR13N"
         "SyCZWqiH2ojMNDm2jWR+W65gIjFz4kNsu4EaSNOfKY4U7VRBLXg7om3pvIoarhBFMZ"
         "vTPQ9FqJU/08BJ/A1tCjCIAY0+zGAAvfRHQt5R2wZXl83n9Xh+9IukW5r/pynpdLx1"
         "+WyAOKLxIUKflTWaIcYKBqmfaxz64Gm2lDbF0+9r/0Xf//P8TFDWFo9bo4loIukgjt"
         "wQmp8Kn6ngEKj8gS3vLApZ3wN18q3emtglyQEmO+9VXckK4NPOqAzwOu7rQbr7oEPS"
         "6HrnY3PKe9JD570= alice@workstation"),
        ("ecdsa-sha2-nistp256 — label reads 528-bit: a P-256 public key is a "
         "~520-bit EC point (0x04‖X‖Y), not a 256-bit value; the 256 names the "
         "field, not the key encoding; no comment",
         "ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAABBBNSBA0Md9M/Cwp0J32Rvk/aiElw77t6l9YQbMmJSP4PfybRxeGP4fqsrIvr6ckdRms5N8Bp/kvug/iAgX6OK59E="),
    ]),
    ("Base32 addresses (RFC 4648)", [
        ("Stellar account",     "GCKFBEIYTKP5RDBQMUTAPDCDHF2TR4LPNRGW4JBQQTQUYZP4LDKP3SGM"),
        ("Stellar muxed account (M…)",
         "MA7QYNF7SOWQ3GLR2BGMZEHXAVIRZA4KVWLTJJFC7MGXUA74P7UJVAAAAAAAAAAAAAJLK"),
        ("IPFS CID v1",         "bafybeigdyrzt5sfp7udm7hu76uh7y26nf3efuylqabf3oclgtqy55fbzdi"),
    ]),
    # Git object hashes wrapped in their standardized prefix schemes. The
    # scheme is split off as a non-entropy prefix (excluded from the
    # fingerprint), so each renders the same entropy as the bare hash —
    # only the label differs. See this.i:g1tha5h0.
    ("Git object hashes (SWHID / gitoid)", [
        ("SWHID commit (rev)",    "swh:1:rev:309cf2674ee7a0749978cf8265ab91a60aea0f7d"),
        ("SWHID content (cnt)",   "swh:1:cnt:94a9ed024d3859793618152ea559a168bbcbb5e2"),
        ("SWHID qualified (origin/lines dropped — free annotation)",
         "swh:1:cnt:94a9ed024d3859793618152ea559a168bbcbb5e2"
         ";origin=https://github.com/torvalds/linux;lines=1-10"),
        ("gitoid blob sha1 (empty blob)",
         "gitoid:blob:sha1:e69de29bb2d1d6434b8b29ae775ad8c2e48c5391"),
        ("gitoid commit sha1",
         "gitoid:commit:sha1:309cf2674ee7a0749978cf8265ab91a60aea0f7d"),
        ("gitoid blob sha256 (empty blob)",
         "gitoid:blob:sha256:473a0f4c3be8a93681a267e3b1e9a7dcda1185436fe141f7749120a303721813"),
    ]),
    # Content addressing. CIDv1's self-describing interior is decoded to
    # name its content codec + hash function (label-only — the visualized
    # entropy is unchanged). See this.i:mult1c0d.
    ("Content addressing (IPFS CID / multicodec)", [
        ("CID v0 (dag-pb/sha2-256)",  "QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG"),
        ("CID v1 dag-pb/sha2-256",    "bafybeigdyrzt5sfp7udm7hu76uh7y26nf3efuylqabf3oclgtqy55fbzdi"),
        ("CID v1 raw/sha2-256",       "bafkreigh2akiscaildcqabsyg3dfr6chu3fgpregiymsck7e7aqa4s52zy"),
    ]),
    # KERI / CESR primitives. The two common AID forms are the
    # self-addressing transferable AID (`E`, Blake3-256 of the inception
    # event — the usual KERI identifier) and the basic non-transferable AID
    # (`B`, the Ed25519 key itself). A bare `D` is a transferable public
    # verification key, NOT normally an identifier — the spec table names it
    # "Ed25519 public verification key" with no "prefix"/AID qualifier — so
    # it is shown as a key, not "the transferable AID". The B/D pair shares
    # one body on purpose: it shows that the derivation code is
    # identity-bearing — same body, different code → different entviz now
    # that the code binds the fingerprint (this.i:s3mpr3fx). The label
    # reports the cryptographic primitive, not the contextual AID/SAID role.
    # See this.i:mult1c0d.
    ("KERI / CESR primitives (AIDs, SAIDs, keys, signatures)", [
        ("AID — self-addressing (E, Blake3-256)", "EBfdlu8R27Fbx_ehrqwImnK_8Cm79sqbAQ4caaZG_LFv"),
        ("AID — non-transferable (B, Ed25519)",   "BKxy2sgzfplyr_tgwIxS19f2OchFHtLwPWD3v4oYimBx"),
        ("Verification key (D, Ed25519)",         "DKxy2sgzfplyr_tgwIxS19f2OchFHtLwPWD3v4oYimBx"),
        ("Ed25519 signature (0B)",
         "0BLwV6fEpOzY9iHsR2bAlKvU5eDoNyX8hGrQ1a_kJuT4dCnMxW7gFqP0Z-jItS3cBmLwV6fEpOzY9iHsR2bAlKvU"),
        # Indexer table (issue #36): the indexed sigs a KEL actually carries —
        # controller/witness signatures. `A` + one index char (fs 88); the
        # code+index stay in the core so they drive the cells. Shown beside the
        # non-indexed 0B above to make the Matter-vs-Indexer distinction visible.
        ("Ed25519 indexed sig (A — KEL controller sig)",
         "ABCfhtCBiEx9ZZov6qDFWtAVn4bQgYhMfWWaL-qgxVrQFZ-G0IGITH1lmi_qoMVa0BWfhtCBiEx9ZZov6qDFWtAV"),
        ("secp256k1 indexed sig (C)",
         "CCCfhtCBiEx9ZZov6qDFWtAVn4bQgYhMfWWaL-qgxVrQFZ-G0IGITH1lmi_qoMVa0BWfhtCBiEx9ZZov6qDFWtAV"),
    ]),
    ("Snowflake IDs (Twitter/Discord/Mastodon)", [
        ("Discord docs example",         "80351110224678912"),
        ("Modern 19-digit snowflake",    "1234567890987654321"),
        ("Snowflake with neighbor seq",  "1234567890987654322"),
    ]),
    ("GLEIF LEI (ISO 17442, MOD 97-10 checksum)", [
        ("Bloomberg L.P.",                       "5493001KJTIIGC8Y1R12"),
        ("Goldman Sachs Group, Inc.",            "529900T8BM49AURSDO55"),
        ("JPMorgan Chase (lowercase input)",     "213800wavvops85n2205"),
    ]),
    ("Base64 / arbitrary text", [
        ("Short ASCII",       "hello world"),
        ("Lorem ipsum chunk", "Lorem ipsum dolor sit amet, consectetur adipiscing elit."),
        ("Base64 blob",       "SGVsbG8sIHRoaXMgaXMgYSB0ZXN0IG9mIHRoZSBlbnR2aXogYWxnb3JpdGhtIQ"),
    ]),
    ("Larger inputs (>512 bits → truncated text channel)", [
        ("RSA-style key fragment",
         "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAvkLpZUVjlW8zG3p" +
         "4G7m7Q1xQfP8aZ8WUEpiE8WxC8mTLg3aN8gqK2y1zGfKbXc9p2YtNvJ5h0sX"),
        ("1024-bit hex",        "0123456789abcdef" * 16),
    ]),
    ("Same input, different aspect ratios", [
        ("256-bit hex @ 1:1",  "deadbeefcafebabe1234567890abcdef0fedcba9876543210123456789abcdef", 1.0),
        ("256-bit hex @ 2:1",  "deadbeefcafebabe1234567890abcdef0fedcba9876543210123456789abcdef", 2.0),
        ("256-bit hex @ 1:2",  "deadbeefcafebabe1234567890abcdef0fedcba9876543210123456789abcdef", 0.5),
    ]),
    # The --note caption: an out-of-band, unverified, gray label on a bare
    # git hash that entviz can only detect as hex. It never touches the
    # fingerprint and is outside the comparison surface. See this.i:usrn0te1.
    ("User notes (--note caption on bare git hashes)", [
        ("git commit, SHA-1 — rendered with --note git",
         "309cf2674ee7a0749978cf8265ab91a60aea0f7d", {"note": "git"}),
        ("git commit, SHA-256 — rendered with --note git",
         "2c26b46b68ffc68ff99b453c1d30413413422d706483bfa0f98a5e886266e7ae", {"note": "git"}),
    ]),
    # v11: DIDs and URNs share one generic path — the scheme+namespace
    # (did:<method>: / urn:<nid>:) binds via prefix-fold, the body is kept
    # verbatim, and any DID URL / URN r-q-f component is dropped. See
    # docs/spec.md *Decentralized Identifiers* / *Uniform Resource Names*.
    ("Decentralized Identifiers (DID)", [
        ("did:key (Ed25519)",
         "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK"),
        ("did:web (domain)", "did:web:w3c-ccg.github.io"),
        ("did:web (colon path — segments are identity, kept)",
         "did:web:w3c-ccg.github.io:user:alice"),
        ("did:peer numalgo 2 (dotted body + purpose codes kept verbatim)",
         "did:peer:2.Ez6LSt4Jscr227NFyuzKHT85haVE4AFVXm1tDwYeZ5xenxMmW"
         ".Vz6MkfvwnoNS6Cto38MEMbqdnypVDN7gS4oAMaHFkjAUse5JE"),
        ("did:ethr (chain id in body)",
         "did:ethr:0x5:0xf3beac30c498d9e26865f34fcaa57dbb935b0d74"),
        ("did:ion (Sidetree SAID)",
         "did:ion:EiClkZMDxPKqC9c-umQfTkR8vvZ9JPhl_xLDI9Nfk38w5w"),
        ("did:webvh (self-certifying SCID : domain)",
         "did:webvh:QmQyDxVnosYTzHAMbzYDRZkVrD32ea9Sr2XNs8NkgMB5mn:domain.example"),
        ("did:keri (KERI autonomic identifier, CESR)",
         "did:keri:EBDCrJM9thBcC3hYZSzKGo-Iv53zQY9KIYEDhN0g5DnV"),
        ("did:webs (domain : path : KERI AID)",
         "did:webs:hook.testnet.gleif.org:7702:dws:ED1e8pD24aqd0dCZTQHaGpfcluPFD2ajGIY3ARgE5Yvr"),
        ("did:prism (Cardano / Hyperledger Identus, short form)",
         "did:prism:9b5118411248d9663b6ab15128fba8106511230ff654e7514cdcc4ce919bde9b"),
        ("did:cheqd (Cosmos; namespace + UUID, both kept)",
         "did:cheqd:mainnet:de9786cd-ec53-458c-857c-9342cf264f80"),
        ("did:dock (Substrate; SS58 base58)",
         "did:dock:5CEdyZkZnALDdCAp7crTRiaCq6KViprTM6kHUQCD8X6VqGPW"),
        ("did:ipid (IPFS; CIDv0 content address)",
         "did:ipid:QmeJGfbW6bhapSfyjV5kDq5wt3h2g46Pwj15pJBVvy7jM3"),
    ]),
    ("Uniform Resource Names (URN, RFC 8141)", [
        ("urn:isbn", "urn:isbn:0451450523"),
        ("urn:uuid (generic — not re-parsed as a bare UUID)",
         "urn:uuid:f81d4fae-7dec-11d0-a765-00a0c91e6bf6"),
        ("urn:oid (colons + dots kept in the NSS)",
         "urn:oid:2.16.840.1.113883.6.1"),
        ("urn:lex (NID lowercased; NSS case preserved)",
         "urn:lex:eu:council:directive:2010-19"),
    ]),
]


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    margin: 2em;
    color: #222;
    background: #fafafa;
  }}
  h1 {{ margin-bottom: 0; }}
  .sub {{ color: #666; margin-top: 0.25em; margin-bottom: 2em; }}
  h2 {{
    border-bottom: 1px solid #ccc;
    padding-bottom: 0.25em;
    margin-top: 2.5em;
    page-break-after: avoid;
  }}
  .cards {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 1.25em;
    align-items: start;
  }}
  .card {{
    border: 1px solid #ddd;
    border-radius: 8px;
    background: #fff;
    padding: 1em;
    display: flex;
    flex-direction: column;
    align-items: center;
    break-inside: avoid;
    page-break-inside: avoid;
  }}
  .card .viz {{ max-width: 100%; }}
  .card .viz img {{ display: block; max-width: 100%; height: auto; }}
  .card .label {{ font-weight: 600; margin: 0.75em 0 0.4em; text-align: center; }}
  .card .input {{
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 0.78em;
    color: #555;
    word-break: break-all;
    background: #f0f0f0;
    padding: 0.4em 0.6em;
    border-radius: 4px;
    line-height: 1.4;
    width: 100%;
    box-sizing: border-box;
  }}
  @media print {{
    body {{ margin: 0.5cm; background: #fff; }}
    .sub {{ margin-bottom: 1em; }}
    .cards {{ gap: 0.6em; }}
    .card {{ border-color: #bbb; }}
  }}
</style>
</head>
<body>
<h1>{title}</h1>
<p class="sub">24-box surround, nucleus-color fill, digest-histogram color bar, rounded blank-cell map, wider lettered color bar. Rendered at 12pt unless noted. (This page is laid out as printable cards.)</p>
{body}
</body>
</html>
"""

SECTION = """
<h2>{title}</h2>
<div class="cards">
{rows}
</div>
"""

CARD = """
<div class="card">
  <div class="viz"><img src="{svg_path}" alt="entviz of {alt}"></div>
  <div class="label">{label}</div>
  <div class="input">{input}</div>
</div>
"""


def _slugify(text: str) -> str:
    """Filesystem-safe slug for the SVG filename."""
    s = re.sub(r'[^a-zA-Z0-9._-]+', '-', text)[:60].strip('-')
    return s or 'entry'


def _parse_sample(sample):
    """Normalize a SAMPLES tuple to (label, entropy, render_kwargs).

    A sample is (label, entropy), (label, entropy, kwargs_dict), or
    (label, entropy, target_ar_float)."""
    if len(sample) == 2:
        return sample[0], sample[1], {}
    if isinstance(sample[2], dict):
        return sample[0], sample[1], sample[2]
    return sample[0], sample[1], {"target_ar": sample[2]}


def iter_entries():
    """Yield (section_title, filename, label, entropy, kwargs) for every gallery
    sample, in document order.

    Shared by main() and tests/test_gallery.py so the drift guard renders
    exactly the inputs the generator commits — the two cannot diverge."""
    entry_seq = 0
    for title, samples in SAMPLES:
        for sample in samples:
            entry_seq += 1
            label, entropy, kwargs = _parse_sample(sample)
            filename = f"{entry_seq:02d}-{_slugify(label)}.svg"
            yield title, filename, label, entropy, kwargs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--html-out', default=os.path.join(REPO_ROOT, 'docs', 'gallery.html'))
    ap.add_argument('--svg-dir', default=os.path.join(REPO_ROOT, 'docs', 'assets', 'gallery'))
    args = ap.parse_args()

    # Wipe the SVG output dir each run so renamed/removed entries don't
    # leave orphaned files behind.
    if os.path.isdir(args.svg_dir):
        shutil.rmtree(args.svg_dir)
    os.makedirs(args.svg_dir, exist_ok=True)

    # SVGs are referenced from the HTML via a path relative to the HTML
    # file's directory. Compute that once.
    html_dir = os.path.dirname(os.path.abspath(args.html_out))
    rel_svg_dir = os.path.relpath(args.svg_dir, html_dir).replace(os.sep, '/')

    sections = []
    cur_title = None
    rows = []
    n_svgs = 0
    for title, filename, label, entropy, kwargs in iter_entries():
        if title != cur_title:
            if cur_title is not None:
                sections.append(SECTION.format(title=html.escape(cur_title), rows="".join(rows)))
            cur_title, rows = title, []
        svg_path = os.path.join(args.svg_dir, filename)
        try:
            svg = render(entropy, **kwargs)
            with open(svg_path, 'w', encoding='utf-8') as f:
                f.write(svg)
            n_svgs += 1
            rel_path = f"{rel_svg_dir}/{filename}"
            row_html = CARD.format(
                input=html.escape(entropy),
                svg_path=html.escape(rel_path, quote=True),
                alt=html.escape(label, quote=True),
                label=html.escape(label),
            )
        except Exception as e:
            # Parser corner cases (e.g. hex-multihash trying to decode
            # an unrelated hex blob) shouldn't abort the whole gallery.
            err = (f'<div style="color:#900;font-family:monospace;'
                   f'padding:0.5em;background:#fee;border-radius:4px;">'
                   f'render failed: {html.escape(str(e))}</div>')
            row_html = (
                f'<div class="card"><div class="viz">{err}</div>'
                f'<div class="label">{html.escape(label)}</div>'
                f'<div class="input">{html.escape(entropy)}</div></div>'
            )
        rows.append(row_html)
    if cur_title is not None:
        sections.append(SECTION.format(title=html.escape(cur_title), rows="".join(rows)))

    os.makedirs(html_dir, exist_ok=True)
    with open(args.html_out, 'w', encoding='utf-8') as f:
        title = html.escape(f"Entviz {SPEC_VERSION}, generated by lib v{__version__}")
        f.write(PAGE.format(body="".join(sections), title=title))
    print(f"wrote {args.html_out}")
    print(f"wrote {n_svgs} SVGs under {args.svg_dir}")


if __name__ == '__main__':
    main()
