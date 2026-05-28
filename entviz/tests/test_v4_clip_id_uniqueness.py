"""
v4 clip-path id uniqueness: each render() emits a clipPath id salted
with first 16 hex chars of the fingerprint + grid dimensions, so multiple
entvizes embedded in one HTML document don't collide. Browsers resolve
url(#…) to the first matching id document-wide, so without this fix,
every entviz after the first is clipped to the first one's grid rect.

Salt width was 8 hex chars (32 bits) through v4 and was widened to 16
hex chars (64 bits) following adversarial review F-A3 — birthday-bound
collision moved from ~65k to ~4 billion entvizes on a single page.
"""
import re

from entviz.pipeline import render


def test_clip_id_includes_fingerprint_prefix():
    svg = render("0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef")
    m = re.search(r'<clipPath id="([^"]+)"', svg)
    assert m
    cid = m.group(1)
    # Expect format: grid-clip-{16 hex chars}-{cols}x{rows}
    assert re.match(r'grid-clip-[0-9a-f]{16}-\d+x\d+$', cid), f"clip id {cid!r}"


def test_different_inputs_produce_different_clip_ids():
    a = render("aaaa")
    b = render("bbbb")
    a_id = re.search(r'<clipPath id="([^"]+)"', a).group(1)
    b_id = re.search(r'<clipPath id="([^"]+)"', b).group(1)
    assert a_id != b_id


def test_same_input_different_aspect_ratio_produces_different_clip_ids():
    """The grid dimensions are part of the salt, so the same input at
    different aspect ratios gets different ids (the gallery scenario)."""
    a = render("0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
               target_ar=1.0)
    b = render("0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
               target_ar=2.0)
    a_id = re.search(r'<clipPath id="([^"]+)"', a).group(1)
    b_id = re.search(r'<clipPath id="([^"]+)"', b).group(1)
    assert a_id != b_id


def test_render_is_deterministic_for_clip_id():
    """The clip id is a deterministic function of input + target_ar."""
    a = render("hello world")
    b = render("hello world")
    a_id = re.search(r'<clipPath id="([^"]+)"', a).group(1)
    b_id = re.search(r'<clipPath id="([^"]+)"', b).group(1)
    assert a_id == b_id


def test_ellipse_g_references_the_local_clip_id():
    """The g wrapping the ellipse uses url(#...) pointing at the same id
    declared in this SVG's defs."""
    svg = render("0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef")
    clip_id = re.search(r'<clipPath id="([^"]+)"', svg).group(1)
    # g[clip-path] reference
    m = re.search(r'<g clip-path="url\(#([^)]+)\)"', svg)
    assert m
    assert m.group(1) == clip_id
