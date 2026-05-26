"""Generate sample entvizes with random nucleus colors and per-edge gradients.

Each edge shape is filled with a linear gradient that runs from the nucleus
color (at the edge attaching the nucleus) to a "putative" color picked from
{gold, blue, red, black} (at the far side of the edge rect). The gradient is
defined in the shape's nominal (24x8) coord space; SVG's `<use>` transform
rotates/translates the gradient along with the shape, so the same gradient
direction (vertical, y=8 -> y=0) works for every edge except brick on side
edges (which uses the brkv 8x16 def without rotation, so it gets a custom
horizontal gradient).
"""

import random

ARR0 = ['fin', 'fng', 'brk', 'inf']
ARR1 = ['wav', 'hole', 'kel', 'mnd']

# (bbox_center_x, bbox_center_y, bbox_width, bbox_height)
SHAPE_BBOX = {
    'fin': (4, 4, 8, 8),
    'fng': (16, 4, 16, 8),
    'brk': (12, 4, 24, 8),
    'inf': (12, 4, 16, 8),
    'wav': (16, 4, 16, 8),
    'kel': (6, 4, 12, 8),
    'mnd': (12, 4, 16, 8),
}

# Edge rect position within a 64x32 cell: (x, y, w, h)
EDGE_RECTS = {
    0: (8, 0, 24, 8),
    1: (32, 0, 24, 8),
    2: (56, 8, 8, 16),
    3: (32, 24, 24, 8),
    4: (8, 24, 24, 8),
    5: (0, 8, 8, 16),
}

# Putative colors from entviz spec (no white)
PUTATIVE = ['#ffd966', '#2f3fbf', '#ffdf2f', '#000000']  # gold, blue, red, black

_gid_counter = [0]

def fmt(x):
    return f'{x:g}'

def random_nucleus_color(rng):
    r = rng.randint(80, 200)
    g = rng.randint(80, 200)
    b = rng.randint(80, 200)
    return f'#{r:02x}{g:02x}{b:02x}'

def make_gradient(nucleus_color, putative_color, shape_name, edge_idx):
    """Returns (gradient_id, gradient_def_string).

    Standard direction (in shape-nominal coords): y=8 (nucleus side) -> y=0
    (outer side). The `<use>` transform rotates this gradient to match each
    edge's orientation.

    Exception: brick on side edges uses brkv (no rotation), so the gradient
    must be horizontal in brkv's own 8x16 local coords.
    """
    _gid_counter[0] += 1
    gid = f'g{_gid_counter[0]}'
    if shape_name == 'brk' and edge_idx in (2, 5):
        # brkv local coords are 8 wide x 16 tall
        if edge_idx == 2:
            x1, y1, x2, y2 = 0, 8, 8, 8  # nucleus on left of brkv -> right
        else:
            x1, y1, x2, y2 = 8, 8, 0, 8  # nucleus on right of brkv -> left
    else:
        x1, y1, x2, y2 = 12, 8, 12, 0
    g = (f'<linearGradient id="{gid}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
         f'gradientUnits="userSpaceOnUse">'
         f'<stop offset="0" stop-color="{nucleus_color}"/>'
         f'<stop offset="1" stop-color="{putative_color}"/></linearGradient>')
    return gid, g

def shape_use_str(shape_name, edge_idx, fill_url):
    if shape_name == 'hole':
        return ''
    ex, ey, _, _ = EDGE_RECTS[edge_idx]
    if shape_name == 'brk' and edge_idx in (2, 5):
        return f'<use href="#brkv" x="{ex}" y="{ey}" fill="{fill_url}"/>'
    bcx, bcy, bw, bh = SHAPE_BBOX[shape_name]
    if edge_idx in (0, 1):
        return f'<use href="#{shape_name}" transform="translate({ex} {ey})" fill="{fill_url}"/>'
    if edge_idx == 2:
        dx, dy = bh / 2 - bcx, bw / 2 - bcy
        return (f'<use href="#{shape_name}" transform="translate({ex} {ey}) '
                f'translate({fmt(dx)} {fmt(dy)}) rotate(90 {bcx} {bcy})" fill="{fill_url}"/>')
    if edge_idx in (3, 4):
        return (f'<use href="#{shape_name}" transform="translate({ex} {ey}) '
                f'rotate(180 12 4)" fill="{fill_url}"/>')
    # edge 5
    dx, dy = bh / 2 - bcx, 16 - bw / 2 - bcy
    return (f'<use href="#{shape_name}" transform="translate({ex} {ey}) '
            f'translate({fmt(dx)} {fmt(dy)}) rotate(-90 {bcx} {bcy})" fill="{fill_url}"/>')

def generate_cell(array, cell_x, cell_y, rng):
    """Returns (cell_svg_str, list_of_gradient_defs)."""
    gdefs = []
    nuc = random_nucleus_color(rng)
    parts = [f'<g transform="translate({cell_x} {cell_y})">',
             f'<rect x="8" y="8" width="48" height="16" fill="{nuc}"/>']
    for e in range(6):
        shape = rng.choice(array)
        if shape == 'hole':
            continue
        putative = rng.choice(PUTATIVE)
        gid, g = make_gradient(nuc, putative, shape, e)
        gdefs.append(g)
        s = shape_use_str(shape, e, f'url(#{gid})')
        if s:
            parts.append(s)
    parts.append('</g>')
    return '\n'.join(parts), gdefs

def generate_entviz(array, ev_x, ev_y, rng):
    # Skip one randomly-chosen cell (never the first one).
    skip = rng.randint(1, 11)
    gdefs = []
    parts = [f'<g transform="translate({ev_x} {ev_y})">']
    for row in range(4):
        for col in range(3):
            idx = row * 3 + col
            if idx == skip:
                continue
            cell, cgdefs = generate_cell(array, col * 64, row * 32, rng)
            parts.append(cell)
            gdefs.extend(cgdefs)
    parts.append('</g>')
    return '\n'.join(parts), gdefs

random.seed(7)

ev_w, ev_h = 192, 128
gap = 18
margin = 20
header_h = 22

svg_w = 2 * margin + 4 * ev_w + 3 * gap
svg_h = 2 * margin + 2 * header_h + 2 * ev_h + gap

shape_defs = '''<path id="fin" d="M 0,8 H 8 A 8,8 0 0 0 0,0 Z"/>
<path id="fng" d="M 8,0 H 24 C 21,1 17,3 16,6 C 10,5 9,2 8,0 Z"/>
<rect id="brk" width="24" height="8" rx="2"/>
<rect id="brkv" width="8" height="16" rx="2"/>
<path id="inf" d="M 8,0 C 6,0 4,2 4,4 S 6,8 8,8 S 14,0 16,0 S 20,2 20,4 S 18,8 16,8 S 10,0 8,0 Z"/>
<path id="wav" d="M 8,8 H 24 C 22,8 22,2 20,2 S 18,6 16,6 S 14,4 12,4 S 10,8 8,8 Z"/>
<path id="kel" d="M 12,0 C 8,0 6,2 5,4 C 5,7 4,8 0,8 V 0 Z"/>
<path id="mnd" d="M 4,8 H 20 A 8,8 0 0 0 4,8 Z"/>'''

body = []
all_gdefs = []

body.append(f'<text x="{svg_w/2}" y="{margin + header_h - 6}" font-family="sans-serif" '
            f'font-size="12" text-anchor="middle" fill="#666">array 0: fin / fang / brick / inf</text>')
for i in range(4):
    ev_x = margin + i * (ev_w + gap)
    ev_y = margin + header_h
    ev_str, ev_gdefs = generate_entviz(ARR0, ev_x, ev_y, random)
    body.append(ev_str)
    all_gdefs.extend(ev_gdefs)

y2 = margin + header_h + ev_h + gap
body.append(f'<text x="{svg_w/2}" y="{y2 + header_h - 6}" font-family="sans-serif" '
            f'font-size="12" text-anchor="middle" fill="#666">array 1: wave / hole / keel / mound</text>')
for i in range(4):
    ev_x = margin + i * (ev_w + gap)
    ev_y = y2 + header_h
    ev_str, ev_gdefs = generate_entviz(ARR1, ev_x, ev_y, random)
    body.append(ev_str)
    all_gdefs.extend(ev_gdefs)

out = ['<?xml version="1.0" encoding="UTF-8" standalone="no"?>',
       f'<svg width="{svg_w}" height="{svg_h}" xmlns="http://www.w3.org/2000/svg">',
       '<defs>',
       shape_defs,
       *all_gdefs,
       '</defs>',
       f'<rect width="{svg_w}" height="{svg_h}" fill="white"/>',
       *body,
       '</svg>']

with open('/home/daniel/code/entviz/gen2.svg', 'w') as f:
    f.write('\n'.join(out))
print(f'SVG: {svg_w}x{svg_h}, gradients: {len(all_gdefs)}')
