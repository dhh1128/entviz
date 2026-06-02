from lxml import etree

def circle(svg, where, fill_color: str="blue"):
    center = where.center
    return etree.SubElement(svg, 'circle', cx=f"{center.x}", cy=f"{center.y}", r=f"{where.size.width / 2}", fill=fill_color)

def rect(svg, where, fill_color):
    return etree.SubElement(svg, 'rect', x=f"{where.left}", y=f"{where.top}", width=f"{where.size.width}", height=f"{where.size.height}", fill=fill_color)

def canvas(size) -> etree.Element:
    # viewBox mirrors width/height so consumers that override `width` or
    # `height` (e.g. `width="100%"` for responsive embedding) get
    # content-box scaling driven by the viewport-to-viewBox ratio rather
    # than raw attribute substitution. Without viewBox, percentage-width
    # SVGs collapse to 0 height in many browsers. See review F-A4.
    w = f"{size.width}"
    h = f"{size.height}"
    return etree.Element(
        'svg',
        width=w, height=h,
        viewBox=f"0 0 {w} {h}",
        xmlns="http://www.w3.org/2000/svg",
    )
