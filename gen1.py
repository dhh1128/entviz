import random

# Shape arrays (using internal def names)
ARR0 = ['fin', 'fng', 'brk', 'inf']
ARR1 = ['wav', 'hole', 'kel', 'mnd']

# Per-shape: (bbox_center_x, bbox_center_y, bbox_width, bbox_height)
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
    0: (8, 0, 24, 8),    # top-left half
    1: (32, 0, 24, 8),   # top-right half
    2: (56, 8, 8, 16),   # right side
    3: (32, 24, 24, 8),  # bottom-right half
    4: (8, 24, 24, 8),   # bottom-left half
    5: (0, 8, 8, 16),    # left side
}

def fmt(x):
    """Format number with no unnecessary decimals."""
    return f'{x:g}'

def shape_use_str(shape_name, edge_idx):
    if shape_name == 'hole':
        return ''
    ex, ey, ew, eh = EDGE_RECTS[edge_idx]
    # Brick on side edges uses brkv (8x16 vertical brick)
    if shape_name == 'brk' and edge_idx in (2, 5):
        return f'<use href="#brkv" x="{ex}" y="{ey}" fill="#ddd"/>'
    bcx, bcy, bw, bh = SHAPE_BBOX[shape_name]
    if edge_idx in (0, 1):
        return f'<use href="#{shape_name}" transform="translate({ex} {ey})" fill="#ddd"/>'
    elif edge_idx == 2:
        # 90° rotation, top-align in 8x16
        dx = bh/2 - bcx
        dy = bw/2 - bcy
        return f'<use href="#{shape_name}" transform="translate({ex} {ey}) translate({fmt(dx)} {fmt(dy)}) rotate(90 {bcx} {bcy})" fill="#ddd"/>'
    elif edge_idx in (3, 4):
        # 180° rotation, stays in 24x8
        return f'<use href="#{shape_name}" transform="translate({ex} {ey}) rotate(180 12 4)" fill="#ddd"/>'
    elif edge_idx == 5:
        # 270° rotation, bottom-align in 8x16
        dx = bh/2 - bcx
        dy = 16 - bw/2 - bcy
        return f'<use href="#{shape_name}" transform="translate({ex} {ey}) translate({fmt(dx)} {fmt(dy)}) rotate(-90 {bcx} {bcy})" fill="#ddd"/>'

def generate_cell(array, cell_x, cell_y, rng):
    parts = [f'<g transform="translate({cell_x} {cell_y})">']
    parts.append('<rect x="8" y="8" width="48" height="16" fill="#ccc"/>')
    for e in range(6):
        shape = rng.choice(array)
        s = shape_use_str(shape, e)
        if s:
            parts.append(s)
    parts.append('</g>')
    return '\n'.join(parts)

def generate_entviz(array, ev_x, ev_y, rng):
    # Skip one randomly-chosen cell (never the first one).
    skip = rng.randint(1, 11)
    parts = [f'<g transform="translate({ev_x} {ev_y})">']
    for row in range(4):
        for col in range(3):
            idx = row * 3 + col
            if idx == skip:
                continue
            parts.append(generate_cell(array, col * 64, row * 32, rng))
    parts.append('</g>')
    return '\n'.join(parts)

random.seed(7)

ev_w, ev_h = 192, 128
gap = 18
margin = 20
header_h = 22

svg_w = 2 * margin + 4 * ev_w + 3 * gap
svg_h = 2 * margin + 2 * header_h + 2 * ev_h + gap

defs = '''<defs>
  <path id="fin" d="M 0,8 H 8 A 8,8 0 0 0 0,0 Z"/>
  <path id="fng" d="M 8,0 H 24 C 21,1 17,3 16,6 C 10,5 9,2 8,0 Z"/>
  <rect id="brk" width="24" height="8" rx="2"/>
  <rect id="brkv" width="8" height="16" rx="2"/>
  <path id="inf" d="M 8,0 C 6,0 4,2 4,4 S 6,8 8,8 S 14,0 16,0 S 20,2 20,4 S 18,8 16,8 S 10,0 8,0 Z"/>
  <path id="wav" d="M 8,8 H 24 C 22,8 22,2 20,2 S 18,6 16,6 S 14,4 12,4 S 10,8 8,8 Z"/>
  <path id="kel" d="M 12,0 C 8,0 6,2 5,4 C 5,7 4,8 0,8 V 0 Z"/>
  <path id="mnd" d="M 4,8 H 20 A 8,8 0 0 0 4,8 Z"/>
</defs>'''

# Build SVG
out = []
out.append(f'<?xml version="1.0" encoding="UTF-8" standalone="no"?>')
out.append(f'<svg width="{svg_w}" height="{svg_h}" xmlns="http://www.w3.org/2000/svg">')
out.append(defs)
out.append(f'<rect width="{svg_w}" height="{svg_h}" fill="white"/>')

# Array 0 header + 4 entvizes
out.append(f'<text x="{svg_w/2}" y="{margin + header_h - 6}" font-family="sans-serif" font-size="12" text-anchor="middle" fill="#666">array 0: fin / fang / brick / inf</text>')
for i in range(4):
    ev_x = margin + i * (ev_w + gap)
    ev_y = margin + header_h
    out.append(generate_entviz(ARR0, ev_x, ev_y, random))

# Array 1 header + 4 entvizes
y2 = margin + header_h + ev_h + gap
out.append(f'<text x="{svg_w/2}" y="{y2 + header_h - 6}" font-family="sans-serif" font-size="12" text-anchor="middle" fill="#666">array 1: wave / hole / keel / mound</text>')
for i in range(4):
    ev_x = margin + i * (ev_w + gap)
    ev_y = y2 + header_h
    out.append(generate_entviz(ARR1, ev_x, ev_y, random))

out.append('</svg>')

with open('/home/daniel/code/entviz/gen1.svg', 'w') as f:
    f.write('\n'.join(out))
print(f'SVG: {svg_w}x{svg_h}')
