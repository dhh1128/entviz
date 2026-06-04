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
        ("Bitcoin legacy",  "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"),
        ("Bitcoin (Satoshi genesis)", "1NSUpdRFAbn3Y2ZjN8nfNfJTpVTMo6gxa6"),
        ("Ripple",          "rEb8TK3gBgk5auZkwc6sHnwrGVJH8DuaLh"),
    ]),
    ("Bech32 addresses", [
        ("Bitcoin SegWit P2WPKH",       "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4"),
        ("Bitcoin SegWit P2WSH",        "bc1qrp33g0q5c5txsp9arysrx4k6zdkfs4nce4xj0gdcccefvpysxf3qccfmv3"),
        ("Litecoin (ltc1)",             "ltc1qhw6dgkk52v9eqzukju7vrqpw0jt4wll6e6n4q5"),
        ("Bitcoin Cash CashAddr",       "bitcoincash:qpm2qsznhks23z7629mms6s4cwef74vcwvy22gdx6a"),
        ("Cardano Shelley",
         "addr1q9c0sj9wp29txqlt0qkc4cz76d5szl4xqgmgpw70ay9zkmskq7stm5kkjjjvrjz9p3kgxx0plzkphkn2yepg6w2zjphshtm0rl"),
        ("Cosmos Hub (checksum-validated, HRP in label)",
         "cosmos1qqqsyqcyq5rqwzqfpg9scrgwpugpzysnrk363e"),
        ("Osmosis (same generic bech32 parser)",
         "osmo1qqqsyqcyq5rqwzqfpg9scrgwpugpzysntdz28t"),
    ]),
    ("SSH public keys", [
        ("ssh-ed25519 (with comment)",
         "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDtJVH9hM+2DyhmgRZBfeIDoVqCTbXY+0nKlS5pTkkXY user@example.com"),
        ("ssh-rsa 3072-bit (with comment)",
         "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQDSD+oM4kLidAptE5pjRA8OBIWNysc9reQJjK"
         "egek2jATA3bSvKdq/wdQtpbihEx5OlKMo//V/8QpAIjCSsBaMb6G/e/D5kC9wCjnYJ"
         "J68+34L+H5Fx1Ofuiz3BidgssINw/qbV0u1vrCop+ggs6lkl+pIwa+9kPriD9xdowC"
         "OQABMVl4todcojY8gZK/Zs5XTwKi9Z8MRS/37FEPxlvpRExMmQU8v2tnP/TDqhR13N"
         "SyCZWqiH2ojMNDm2jWR+W65gIjFz4kNsu4EaSNOfKY4U7VRBLXg7om3pvIoarhBFMZ"
         "vTPQ9FqJU/08BJ/A1tCjCIAY0+zGAAvfRHQt5R2wZXl83n9Xh+9IukW5r/pynpdLx1"
         "+WyAOKLxIUKflTWaIcYKBqmfaxz64Gm2lDbF0+9r/0Xf//P8TFDWFo9bo4loIukgjt"
         "wQmp8Kn6ngEKj8gS3vLApZ3wN18q3emtglyQEmO+9VXckK4NPOqAzwOu7rQbr7oEPS"
         "6HrnY3PKe9JD570= alice@workstation"),
        ("ecdsa-sha2-nistp256 (no comment)",
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
        ("SWHID qualified (origin/lines → suffix)",
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
    # KERI / CESR primitives. An AID is a CESR key (D transferable, B
    # non-transferable); a SAID is a CESR self-addressing digest (E =
    # Blake3-256). The label reports the cryptographic primitive, not the
    # contextual AID/SAID role. See this.i:mult1c0d.
    ("KERI / CESR primitives (AIDs, SAIDs, keys, signatures)", [
        ("AID — transferable (D, Ed25519)",     "DKxy2sgzfplyr_tgwIxS19f2OchFHtLwPWD3v4oYimBx"),
        ("AID — non-transferable (B, Ed25519)", "BKxy2sgzfplyr_tgwIxS19f2OchFHtLwPWD3v4oYimBx"),
        ("SAID — Blake3-256 digest (E)",        "EBfdlu8R27Fbx_ehrqwImnK_8Cm79sqbAQ4caaZG_LFv"),
        ("Ed25519 signature (0B)",
         "0BLwV6fEpOzY9iHsR2bAlKvU5eDoNyX8hGrQ1a_kJuT4dCnMxW7gFqP0Z-jItS3cBmLwV6fEpOzY9iHsR2bAlKvU"),
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
    entry_seq = 0
    for title, samples in SAMPLES:
        rows = []
        for sample in samples:
            entry_seq += 1
            if len(sample) == 2:
                label, entropy = sample
                kwargs = {}
            elif isinstance(sample[2], dict):
                label, entropy, kwargs = sample
            else:
                label, entropy, target_ar = sample
                kwargs = {"target_ar": target_ar}
            filename = f"{entry_seq:02d}-{_slugify(label)}.svg"
            svg_path = os.path.join(args.svg_dir, filename)
            try:
                svg = render(entropy, **kwargs)
                with open(svg_path, 'w', encoding='utf-8') as f:
                    f.write(svg)
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
        sections.append(SECTION.format(title=html.escape(title), rows="".join(rows)))

    os.makedirs(html_dir, exist_ok=True)
    with open(args.html_out, 'w', encoding='utf-8') as f:
        title = html.escape(f"Entviz {SPEC_VERSION}, generated by lib v{__version__}")
        f.write(PAGE.format(body="".join(sections), title=title))
    print(f"wrote {args.html_out}")
    print(f"wrote {entry_seq} SVGs under {args.svg_dir}")


if __name__ == '__main__':
    main()
