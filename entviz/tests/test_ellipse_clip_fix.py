"""
Pins the fix for the SVG clip-path-on-transformed-element quirk.

Bug: when an SVG element has both `transform="rotate(…)"` and
`clip-path="url(#…)"`, the clipPath is resolved in the element's
*post-transform* user space — i.e., the clip rectangle rotates with
the element. The intent is for the clip to stay in screen space.

Fix: put the `clip-path` on a parent <g> with no transform; put the
`transform` on the <ellipse> inside the group. Then the clip resolves
in the group's coordinate space (unrotated), and the ellipse rotates
inside the clipped region.
"""
from lxml import etree

from entviz.pipeline import render


def test_ellipse_is_inside_a_clipping_group():
    # Render any input large enough to produce an ellipse overlay.
    svg = etree.fromstring(render("deadbeefdeadbeef" * 8).encode())
    ellipses = svg.xpath('//*[local-name()="ellipse"]')
    assert ellipses, "no ellipse rendered for the large input"
    ellipse = ellipses[0]

    # The ellipse must NOT carry clip-path directly.
    assert ellipse.get("clip-path") is None, (
        "ellipse element still has clip-path directly; the rotated clip-rect "
        "bug will reappear. Move clip-path to a parent <g>."
    )

    # Its parent must be a <g> with clip-path set.
    parent = ellipse.getparent()
    assert parent.tag.endswith("}g"), (
        f"ellipse parent is {parent.tag}, expected a <g>"
    )
    assert (parent.get("clip-path") or "").startswith("url(#"), (
        "ellipse's parent <g> does not carry clip-path"
    )


def test_ellipse_still_has_rotation_transform():
    svg = etree.fromstring(render("deadbeefdeadbeef" * 8).encode())
    ellipse = svg.xpath('//*[local-name()="ellipse"]')[0]
    transform = ellipse.get("transform") or ""
    assert transform.startswith("rotate("), (
        f"ellipse transform is {transform!r}; expected rotate(...)"
    )
