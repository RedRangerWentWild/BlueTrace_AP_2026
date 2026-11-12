#!/usr/bin/env python3
"""Find the densest clusters of encroachment in an exported layer.

At catchment zoom the encroached layer covers a fraction of a percent of the
frame, so it cannot carry a demo on its own. Rather than exaggerate the layer,
this finds where it actually concentrates and prints coordinates to fly to.

    ./hotspots.py bengaluru
    ./hotspots.py chennai --layer floodprone

Paste the printed block into the CITIES table in index.html.
"""
import sys, argparse
from collections import Counter
from PIL import Image

BOUNDS = {                      # west, south, east, north — must match gee_blue_grid.js
    'bengaluru': (77.63, 12.90, 77.75, 12.97),
    'chennai':   (80.180, 12.900, 80.280, 12.985),
}

ap = argparse.ArgumentParser()
ap.add_argument('city')
ap.add_argument('--layer', default='encroached')
ap.add_argument('--top', type=int, default=4)
ap.add_argument('--grid', type=int, default=64, help='cells across; smaller = coarser clusters')
ap.add_argument('--bounds', help='west,south,east,north if the city is not in the table')
a = ap.parse_args()

if a.bounds:
    W, S, E, N = (float(x) for x in a.bounds.split(','))
elif a.city in BOUNDS:
    W, S, E, N = BOUNDS[a.city]
else:
    sys.exit(f'unknown city {a.city!r} — pass --bounds west,south,east,north')

path = f'data/{a.city}/{a.layer}.png'
try:
    im = Image.open(path).convert('RGBA')
except FileNotFoundError:
    sys.exit(f'missing {path} — run gee_blue_grid.js then ./fetch_layers.sh {a.city}')

px = im.getchannel('A').load()
GX = a.grid
GY = max(1, round(GX * (N - S) / (E - W)))   # keep cells roughly square on the ground

cells = Counter()
for y in range(im.height):
    for x in range(im.width):
        if px[x, y]:
            cells[(x * GX // im.width, y * GY // im.height)] += 1

if not cells:
    sys.exit(f'{path} has no visible pixels — nothing was flagged in this area')

total = sum(cells.values())
print(f'{path}: {total} flagged pixels, {len(cells)} occupied cells\n')
print('    hotspots: [')
for (cx, cy), c in cells.most_common(a.top):
    lon = W + (cx + 0.5) / GX * (E - W)
    lat = N - (cy + 0.5) / GY * (N - S)
    print(f"      {{name:'Site {lat:.4f}, {lon:.4f}', lon:{lon:.4f}, lat:{lat:.4f}, px:{c}}},")
print('    ]')
print('\nRename each site before demoing — a place name reads far better than a coordinate.')
