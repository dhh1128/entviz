from lxml import etree

def circle(svg, where, fill_color: str="blue"):
    center = where.center
    return etree.SubElement(svg, 'circle', cx=f"{center.x}", cy=f"{center.y}", r=f"{where.size.width / 2}", fill=fill_color)

def rect(svg, where, fill_color):
    return etree.SubElement(svg, 'rect', x=f"{where.left}", y=f"{where.top}", width=f"{where.size.width}", height=f"{where.size.height}", fill=fill_color)

def canvas(size) -> etree.Element:
    return etree.Element('svg', width=f"{size.width}", height=f"{size.height}", xmlns="http://www.w3.org/2000/svg")
