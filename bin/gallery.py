"""
Generate a single-file HTML gallery of v4 entvizes across a curated set
of input types and avalanche pairs. Inline SVGs, no external assets.

Run from the repo root:
    python bin/gallery.py -o gallery.html
"""
import argparse
import html
import os
import sys

# Allow running directly from the source tree.
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, '..')))

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
    ("Base32 addresses (RFC 4648)", [
        ("Stellar account",     "GCKFBEIYTKP5RDBQMUTAPDCDHF2TR4LPNRGW4JBQQTQUYZP4LDKP3SGM"),
        ("IPFS CID v1",         "bafybeigdyrzt5sfp7udm7hu76uh7y26nf3efuylqabf3oclgtqy55fbzdi"),
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
  .label {{ font-weight: 600; margin-bottom: 0.35em; }}
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
  .viz svg {{ display: block; }}
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
    <div class="label">{label}</div>
    <div class="input">{input}</div>
  </div>
  <div class="viz">{svg}</div>
</div>
"""


def _strip_xml_decl(svg: str) -> str:
    # Inline SVGs in HTML must not carry an XML prolog. Our render() already
    # uses xml_declaration=False but a stray BOM or leading whitespace would
    # also be ugly; strip defensively.
    return svg.lstrip().removeprefix('<?xml version="1.0"?>').lstrip()


def _uniquify_ids(svg: str, suffix: str) -> str:
    """
    Re-namespace every `id="…"` and matching `url(#…)` reference in the SVG
    by appending a per-entry suffix. Embedding multiple SVGs in one HTML
    document collides on shared IDs (clipPath, gradient, etc.) because the
    browser resolves url(#…) to the FIRST matching id in the entire HTML
    document — not the nearest enclosing SVG. Salting per entry isolates
    them.
    """
    import re
    suffix = f"-g{suffix}"
    svg = re.sub(r'id="([^"]+)"', lambda m: f'id="{m.group(1)}{suffix}"', svg)
    svg = re.sub(r'url\(#([^)]+)\)', lambda m: f'url(#{m.group(1)}{suffix})', svg)
    return svg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('-o', '--output', default='gallery.html')
    args = ap.parse_args()

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
            try:
                svg = render(entropy, **kwargs)
            except Exception as e:
                # Parser corner cases (e.g. hex-multihash trying to decode
                # an unrelated hex blob) shouldn't abort the whole gallery.
                svg = (f'<div style="color:#900;font-family:monospace;'
                       f'padding:0.5em;background:#fee;border-radius:4px;">'
                       f'render failed: {html.escape(str(e))}</div>')
            if svg.startswith('<svg'):
                svg_inline = _uniquify_ids(_strip_xml_decl(svg), str(entry_seq))
            else:
                svg_inline = svg
            rows.append(ROW.format(
                label=html.escape(label),
                input=html.escape(entropy),
                svg=svg_inline,
            ))
        sections.append(SECTION.format(title=html.escape(title), rows="".join(rows)))

    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(PAGE.format(body="".join(sections)))
    print(f"wrote {args.output}")


if __name__ == '__main__':
    main()
