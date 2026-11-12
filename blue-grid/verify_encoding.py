#!/usr/bin/env python3
"""Prove the byte-packed measurement layers decoded losslessly.

The distance fields and the history layer smuggle real quantities through an
8-bit PNG channel. If Earth Engine's visualize() stretched them, or the
thumbnail resampled them, every distance the tool reports would be wrong and
entirely plausible. Nothing else in the pipeline would notice.

The decisive test is cross-consistency rather than eyeballing: distance to a
feature must be zero wherever that feature's own mask is set. Two layers built
by separate code paths have to agree, or something moved.

    ./verify_encoding.py bengaluru
"""
import sys
import numpy as np
from PIL import Image

city = sys.argv[1] if len(sys.argv) > 1 else 'bengaluru'
fails = []

# Must match the CITIES table in index.html and the BOUNDS table in
# validate.py. Only the routing checks need it: they walk MERIT's own grid,
# which is defined in degrees, and the pixel grid alone cannot locate it.
BOUNDS = {
    'bengaluru': (77.63, 12.90, 77.75, 12.97),
    'chennai':   (80.180, 12.900, 80.280, 12.985),
}


def load(name, required=True):
    try:
        return np.asarray(Image.open(f'data/{city}/{name}.png').convert('RGBA'))
    except (FileNotFoundError, OSError):
        if required:
            sys.exit(f'missing or unreadable data/{city}/{name}.png')
        return None


def check(ok, msg):
    print(('  PASS  ' if ok else '  FAIL  ') + msg)
    if not ok:
        fails.append(msg)


buf = load('buffers')
hist = load('history', required=False)
hyd = load('hydro', required=False)
rtg = load('routing', required=False)
present, historic, flowpath = load('present'), load('historic'), load('flowpath')

print(f"\nbuffers.png {buf.shape[1]}x{buf.shape[0]}"
      + (f"   history.png {hist.shape[1]}x{hist.shape[0]}" if hist is not None
         else "   history.png ABSENT") + "\n")

# Every layer is georeferenced by stretching it across the same AOI rectangle,
# so a layer with different pixel dimensions is on a different grid and every
# lookup into it lands on the wrong ground. This is silent: the numbers stay
# plausible. Check it before anything else.
ref_shape = historic.shape[:2]
for nm, im in [('buffers', buf), ('present', present), ('flowpath', flowpath)] + \
              ([('history', hist)] if hist is not None else []) + \
              ([('hydro', hyd)] if hyd is not None else []) + \
              ([('routing', rtg)] if rtg is not None else []):
    check(im.shape[:2] == ref_shape,
          f'{nm} is {im.shape[1]}x{im.shape[0]}, historic is {ref_shape[1]}x{ref_shape[0]}')
if fails:
    print('\nGeometry mismatch - layers are on different grids. Fix the export '
          'before trusting anything below.')
    sys.exit(1)

# Alpha must be binary on a measurement layer. A browser stores canvas pixels
# premultiplied by alpha and un-premultiplies them on getImageData, so any
# fractional alpha quantisation-damages every channel under it: at alpha 17 a
# stored 6 returns 0. PIL does not premultiply, so this corruption is invisible
# to every check that reads the file directly - including the rest of this
# script. It has to be tested for explicitly.
# A thin rind of antialiased pixels along the clip boundary is unavoidable and
# harmless, because the sampler's alpha floor discards them anyway. A layer
# whose interior carries fractional alpha is a different thing entirely.
for nm, im in [('buffers', buf)] \
              + ([('history', hist)] if hist is not None else []) \
              + ([('hydro', hyd)] if hyd is not None else []) \
              + ([('routing', rtg)] if rtg is not None else []):
    a = im[..., 3]
    fr = (a > 0) & (a < 255)
    share = float(fr.mean())
    levels = np.unique(a[fr])
    check(share < 0.01,
          f'{nm} alpha is effectively binary '
          f'({100*share:.2f}% fractional, {levels.size} levels)'
          + ('' if share < 0.01 else
             f' e.g. {list(levels[:5])} - canvas premultiplication will corrupt '
             f'every channel under these pixels in the browser'))

inside = buf[..., 3] == 255          # alpha 255 marks the study area
print(f'study area covers {100 * inside.mean():.1f}% of the frame\n')

# 1. A distance field is graded. A mask is not. Telling them apart catches a
#    visualize() call that collapsed the range.
for ch, name in [(0, 'R  distance to water today'),
                 (1, 'G  distance to 1984-99 water'),
                 (2, 'B  distance to drainage line')]:
    v = buf[..., ch][inside]
    uniq = len(np.unique(v))
    check(uniq > 30, f'{name}: {uniq} distinct values, range {v.min()}-{v.max()}'
          + ('' if uniq > 30 else '   <-- looks like a mask, not a distance'))

# 2. The decisive one. Distance must read zero exactly where the feature's own
#    mask is set, and those two layers were produced by different code paths.
for ch, mask, name in [(0, present, 'present water'),
                       (1, historic, '1984-99 water'),
                       (2, flowpath, 'drainage line')]:
    on = (mask[..., 3] > 128) & inside
    if not on.any():
        check(False, f'{name}: mask is empty, cannot cross-check')
        continue
    d = buf[..., ch][on]
    frac = float((d <= 10).mean())
    ok = frac > 0.95
    check(ok, f'{name}: {100*frac:.1f}% of mask pixels read <= 10 m '
              f'(median {np.median(d):.0f} m)')
    if not ok:
        # A mirrored or rotated export keeps every value and every count
        # intact, so only a positional test can see it. Naming the specific
        # transform turns a mystifying failure into a one-line fix.
        zero = buf[..., ch] == 0
        for label, cand in [('flipped vertically', np.flipud(zero)),
                            ('flipped horizontally', np.fliplr(zero)),
                            ('rotated 180', np.flipud(np.fliplr(zero)))]:
            hit = float((on & cand).sum()) / max(1, on.sum())
            if hit > 0.9:
                print(f'          ^ the layer appears to be {label}: '
                      f'{100*hit:.0f}% of mask pixels match after that transform')

# 3. Distance has to grow with distance.
on = (historic[..., 3] > 128) & inside
off = (historic[..., 3] <= 128) & inside
if on.any() and off.any():
    check(buf[..., 1][off].mean() > buf[..., 1][on].mean(),
          f'G rises outside the 1984-99 mask ({buf[...,1][off].mean():.0f} m) '
          f'versus inside it ({buf[...,1][on].mean():.0f} m)')

if hist is None:
    print('\n  history layer absent - skipping year and occurrence checks')
else:
    yc = hist[..., 0][inside]
    yrs = yc[yc > 0]
    if yrs.size:
        lo, hi = 1983 + int(yrs.min()), 1983 + int(yrs.max())
        check(1984 <= lo and hi <= 2021,
              f'last-water year decodes to {lo}-{hi} (expected inside 1984-2021)')
        print(f'          {100*(yc>0).mean():.1f}% of the study area held water at some point')
    else:
        check(False, 'no non-zero year codes at all')

    occ = hist[..., 1][inside]
    check(occ.max() <= 100, f'JRC occurrence peaks at {occ.max()} (must not exceed 100)')

    if on.any():
        med = float(np.median(hist[..., 1][on]))
        check(med > 20, f'median occurrence inside the 1984-99 mask is {med:.0f}%')

# hydro.png is the one layer not read as a straight byte: its red channel is a
# log packing of upstream drainage area. A scaling law is a second thing that
# can be wrong, so it gets its own cross-check against the flow-path mask that
# was built from the same band by a different code path.
if hyd is None:
    print('\n  hydro layer absent - skipping upstream-area checks')
else:
    UPA_CEIL = 1000
    den = np.log10(1 + UPA_CEIL)

    def decode_upa(code):
        return 10 ** (code / 255.0 * den) - 1

    print()
    r = hyd[..., 0][inside]
    check(len(np.unique(r)) > 30,
          f'R  upstream area: {len(np.unique(r))} distinct codes, '
          f'{decode_upa(r.min()):.2f}-{decode_upa(r.max()):.0f} km2')

    # flowPath is upa > 2 km2 AND low ground, so every flow-path pixel must
    # decode above that threshold. The two were computed from the same band in
    # different sections; if the packing is wrong they stop agreeing.
    on_flow = (flowpath[..., 3] > 128) & inside
    if on_flow.any():
        upa = decode_upa(hyd[..., 0][on_flow].astype(float))
        frac = float((upa > 2).mean())
        # The mask is defined on MERIT's 90 m grid while upstream area is
        # exported on the 30 m grid, so the mask's edge pixels straddle cells
        # whose resampled area falls under the 2 km2 threshold. Agreement in
        # the high eighties is the expected consequence of that mismatch, not
        # a decoding fault.
        check(frac > 0.85,
              f'flow-path pixels decode above 2 km2: {100*frac:.1f}% '
              f'(median {np.median(upa):.1f} km2)')
    else:
        check(False, 'flow-path mask is empty, cannot cross-check upstream area')

    # A trunk channel is upa > 10 km2, and distance to it must be zero there.
    trunk = decode_upa(hyd[..., 0].astype(float)) > 10
    trunk_in = trunk & inside
    if trunk_in.any():
        g = hyd[..., 1][trunk_in]
        frac = float((g <= 10).mean())
        check(frac > 0.95,
              f'trunk-channel pixels read <= 10 m to a trunk channel: '
              f'{100*frac:.1f}% (median {np.median(g):.0f} m)')
    else:
        check(False, 'no pixel decodes above 10 km2 - the packing looks collapsed')

    check(hyd[..., 2][inside].min() == 0,
          f'B  elevation above the study-area minimum starts at '
          f'{hyd[..., 2][inside].min()} (must be 0 somewhere)')

# ---------------------------------------------------------------------------
# ROUTING - the flow-direction field
# ---------------------------------------------------------------------------
# Rule 1 above does not apply here and must not be reached for. A D8 direction
# channel legally holds eleven values, so "more than 30 distinct codes or it is
# a mask" would fail a perfectly good layer, and passing it would prove nothing
# anyway: a direction field can be entirely plausible and entirely wrong.
#
# What catches a wrong one is physics. Water runs downhill into larger and
# larger catchments, so upstream area along a correct route is non-decreasing.
# A transposed, flipped or averaged direction field breaks that immediately,
# while still producing routes that look like routes.
if rtg is not None and city not in BOUNDS:
    print(f'routing.png present but {city!r} is not in the BOUNDS table — '
          'add it to run the flow-direction checks.\n')
elif rtg is None:
    print('routing.png ABSENT - skipping the flow-direction checks. Run '
          'section 14 of gee_blue_grid.js to enable them.\n')
else:
    print(f'\nrouting.png {rtg.shape[1]}x{rtg.shape[0]}')
    d8 = rtg[..., 0]

    # 4. Legality. Every code inside the study area is one this remap emits.
    #    This is what proves the 90 m -> 30 m reprojection stayed nearest: an
    #    average of two directions lands between the codes, not on one.
    codes = np.unique(d8[inside])
    illegal = [int(c) for c in codes if c > 10]
    check(not illegal,
          f'R  every direction code is in 0..10 '
          f'({codes.size} distinct: {[int(c) for c in codes[:12]]})'
          + ('' if not illegal else
             f' - found {illegal[:6]}, which means the reprojection averaged '
             f'directions instead of picking one'))

    # The flow field must actually flow. All-nodata passes every other check
    # below vacuously, because a trace of length zero never violates anything.
    flowing = np.isin(d8[inside], [1, 2, 3, 4, 5, 6, 7, 8])
    check(flowing.mean() > 0.5,
          f'R  {100*flowing.mean():.1f}% of the study area carries a direction '
          f'(the rest is mouth, depression or nodata)')

    # Walk MERIT's own grid, not this export's pixel grid. MERIT Hydro is 3
    # arc-seconds — exactly one 1200th of a degree — and the export is an
    # arbitrary 2048 px stretched across the AOI, so a cell is about 14.15
    # pixels and never a whole number of them. Stepping a rounded 14 px drifts
    # off the cell grid within a few steps and starts revisiting cells the
    # trace never actually entered, which reads as a loop that is not there.
    # On the first real export that produced 201 false loops out of 400.
    H, W = d8.shape
    W_DEG, S_DEG, E_DEG, N_DEG = BOUNDS[city]
    MERIT_DEG = 1.0 / 1200
    DXY = {1: (1, 0), 2: (1, 1), 3: (0, 1), 4: (-1, 1),
           5: (-1, 0), 6: (-1, -1), 7: (0, -1), 8: (1, -1)}
    MAXSTEPS = 200

    def to_px(ix, iy):
        """MERIT cell index -> pixel in this export, via the cell centre.

        Centre-registered: centres lie on integer multiples of 1/1200 of a
        degree. Measured off the export, not assumed — the half-multiple
        reading puts only 58% of sampled points back on their own code.
        """
        lon, lat = ix * MERIT_DEG, iy * MERIT_DEG
        x = int(round((lon - W_DEG) / (E_DEG - W_DEG) * W))
        y = int(round((N_DEG - lat) / (N_DEG - S_DEG) * H))
        return x, y

    def trace(x0, y0):
        """Follow the field from one pixel. Returns (pixel path, how it ended)."""
        lon = W_DEG + (x0 + 0.5) / W * (E_DEG - W_DEG)
        lat = N_DEG - (y0 + 0.5) / H * (N_DEG - S_DEG)
        ix, iy = int(round(lon / MERIT_DEG)), int(round(lat / MERIT_DEG))
        seen, path = set(), []
        for _ in range(MAXSTEPS):
            if (ix, iy) in seen:
                return path, 'loop'
            seen.add((ix, iy))
            x, y = to_px(ix, iy)
            if not (0 <= x < W and 0 <= y < H) or not inside[y, x]:
                return path, 'edge'
            path.append((x, y))
            c = int(d8[y, x])
            if c == 9:
                return path, 'mouth'
            if c == 10:
                return path, 'depression'
            if c not in DXY:
                return path, 'nodata'
            dx, dy = DXY[c]
            ix, iy = ix + dx, iy - dy      # y is southward, latitude is not
        return path, 'capped'

    rng = np.random.default_rng(0)
    ys, xs = np.nonzero(inside & np.isin(d8, [1, 2, 3, 4, 5, 6, 7, 8]))
    if xs.size == 0:
        check(False, 'no pixel inside the study area carries a direction')
    else:
        pick = rng.choice(xs.size, size=min(400, xs.size), replace=False)
        ends, paths = {}, []
        for i in pick:
            path, how = trace(int(xs[i]), int(ys[i]))
            ends[how] = ends.get(how, 0) + 1
            paths.append(path)

        # 5. Termination. A route ends somewhere real, or the field cycles.
        #    A visited-set catches the cycle here so the browser does not have
        #    to discover it at a demo.
        check(ends.get('loop', 0) == 0,
              f'traces terminate without cycling '
              f'({ends.get("loop", 0)} of {len(paths)} looped; '
              + ', '.join(f'{k} {v}' for k, v in sorted(ends.items())) + ')')

        # 6. The physical invariant. Upstream area is non-decreasing downstream.
        #    One code of tolerance per step: the direction field is 90 m data on
        #    a 30 m grid, so a step can land off-centre in the neighbouring cell
        #    and read its edge rather than its middle.
        if hyd is None:
            print('  SKIP  hydro.png absent - cannot check upstream area along '
                  'a route')
        else:
            upa = hyd[..., 0].astype(np.int16)
            drops, steps, grew = 0, 0, 0
            for path in paths:
                if len(path) < 3:
                    continue
                v = [int(upa[y, x]) for x, y in path]
                for a, b in zip(v, v[1:]):
                    steps += 1
                    if b < a - 1:
                        drops += 1
                if v[-1] > v[0]:
                    grew += 1
            if steps == 0:
                check(False, 'every trace was too short to test for monotonicity')
            else:
                share = drops / steps
                check(share < 0.05,
                      f'upstream area is non-decreasing downstream '
                      f'({100*share:.1f}% of {steps} steps fall by more than one '
                      f'code)' + ('' if share < 0.05 else
                      ' - the direction field is transposed, flipped or averaged'))
                long_paths = [p for p in paths if len(p) >= 3]
                frac = grew / max(1, len(long_paths))
                check(frac > 0.8,
                      f'traces end in a larger catchment than they started in '
                      f'({100*frac:.0f}% of {len(long_paths)} traces)')

print()
if fails:
    print(f'{len(fails)} CHECK(S) FAILED - do not trust any distance the tool reports.')
    sys.exit(1)
print('All checks passed. The bytes survived the round trip; distances are metres.')
