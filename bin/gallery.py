"""
Generate an HTML gallery of v4 entvizes across a curated set of input
types and avalanche pairs. SVGs are written as standalone files under
docs/assets/gallery/ and referenced from docs/gallery.html.

Run from the repo root:
    python bin/gallery.py
"""
import argparse
import html
import os
import re
import shutil
import sys

# Allow running directly from the source tree.
HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, REPO_ROOT)

from entviz.pipeline import render


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
        ("IPFS CID v1",         "bafybeigdyrzt5sfp7udm7hu76uh7y26nf3efuylqabf3oclgtqy55fbzdi"),
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
]


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>entviz v4 gallery</title>
<style>
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    margin: 2em;
    color: #222;
    background: #fafafa;
  }}
  h1 {{ margin-bottom: 0; }}
  .sub {{ color: #666; margin-top: 0.25em; margin-bottom: 2em; }}
  h2 {{ border-bottom: 1px solid #ccc; padding-bottom: 0.25em; margin-top: 2.5em; }}
  .row {{
    display: flex;
    align-items: center;
    gap: 1.5em;
    padding: 1em 0;
    border-bottom: 1px dotted #ddd;
  }}
  .meta {{ flex: 0 0 28em; }}
  .input {{
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 0.85em;
    color: #555;
    word-break: break-all;
    background: #f0f0f0;
    padding: 0.4em 0.6em;
    border-radius: 4px;
    line-height: 1.4;
  }}
  .viz {{ flex: 0 0 auto; }}
  .viz img {{ display: block; }}
</style>
</head>
<body>
<h1>entviz v4 gallery</h1>
<p class="sub">24-box surround, nucleus-color fill, digest-histogram color bar. Rendered at 12pt unless noted.</p>
{body}
</body>
</html>
"""

SECTION = """
<h2>{title}</h2>
{rows}
"""

ROW = """
<div class="row">
  <div class="meta">
    <div class="input">{input}</div>
  </div>
  <div class="viz"><img src="{svg_path}" alt="entviz of {alt}"></div>
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
                row_html = ROW.format(
                    input=html.escape(entropy),
                    svg_path=html.escape(rel_path, quote=True),
                    alt=html.escape(label, quote=True),
                )
            except Exception as e:
                # Parser corner cases (e.g. hex-multihash trying to decode
                # an unrelated hex blob) shouldn't abort the whole gallery.
                err = (f'<div style="color:#900;font-family:monospace;'
                       f'padding:0.5em;background:#fee;border-radius:4px;">'
                       f'render failed: {html.escape(str(e))}</div>')
                row_html = (
                    f'<div class="row"><div class="meta">'
                    f'<div class="input">{html.escape(entropy)}</div></div>'
                    f'<div class="viz">{err}</div></div>'
                )
            rows.append(row_html)
        sections.append(SECTION.format(title=html.escape(title), rows="".join(rows)))

    os.makedirs(html_dir, exist_ok=True)
    with open(args.html_out, 'w', encoding='utf-8') as f:
        f.write(PAGE.format(body="".join(sections)))
    print(f"wrote {args.html_out}")
    print(f"wrote {entry_seq} SVGs under {args.svg_dir}")


if __name__ == '__main__':
    main()
