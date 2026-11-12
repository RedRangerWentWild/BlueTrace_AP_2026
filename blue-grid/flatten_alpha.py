#!/usr/bin/env python3
"""Force alpha to opaque on the measurement layers.

A PNG stores colour un-premultiplied, so the bytes on disk are already correct.
A browser does not: it keeps canvas pixels premultiplied by alpha and
un-premultiplies them on getImageData, so any pixel exported at partial alpha
comes back with every channel quantisation-damaged. On the history layer that
lands exactly on the water pixels - occurrence 6 under alpha 17 decodes to 0,
a year code of 38 under alpha 166 decodes to 39, one year past the end of the
archive.

Rewriting alpha to 255 leaves RGB untouched and removes the round trip that
does the damage. The study-area test lives on the buffers layer, which keeps
its own alpha, so nothing here depends on transparency.

    ./flatten_alpha.py bengaluru
"""
import sys
import numpy as np
from PIL import Image

LAYERS = ('history', 'hydro', 'routing')  # measurement layers; buffers keeps alpha

city = sys.argv[1] if len(sys.argv) > 1 else 'bengaluru'
for name in LAYERS:
    path = f'data/{city}/{name}.png'
    try:
        im = Image.open(path).convert('RGBA')
    except FileNotFoundError:
        print(f'  skip  {name}: not downloaded')
        continue
    a = np.asarray(im)
    alpha = a[..., 3]
    frac = int(((alpha > 0) & (alpha < 255)).sum())
    if frac == 0 and alpha.min() == 255:
        print(f'  ok    {name}: already opaque')
        continue
    out = a.copy()
    out[..., 3] = 255
    Image.fromarray(out, 'RGBA').save(path)
    print(f'  fixed {name}: {frac:,} partially transparent pixels flattened')
