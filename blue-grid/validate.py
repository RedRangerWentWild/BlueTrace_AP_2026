#!/usr/bin/env python3
"""Score water detection against the JRC reference on held-out ground.

What this measures, precisely: how well an independent spectral method
reproduces JRC Global Surface Water's own per-year classification over the
same pixels in the same years (2003-2007).

What it does NOT measure: accuracy against surveyed ground truth. There is no
labelled encroachment dataset for this catchment, so no such number exists.
Anyone reporting one has either found labels worth citing or invented them.

Threshold selection happens on training blocks only. Blocks are contiguous
tiles, not random pixels, because neighbouring pixels of the same lake are not
independent samples and a pixel-wise split would inflate every score here.

    ./validate.py bengaluru
    ./validate.py bengaluru --blocks 8x6 --holdout 13
"""
import argparse, math, sys
import numpy as np
from PIL import Image

BOUNDS = {
    'bengaluru': (77.63, 12.90, 77.75, 12.97),
    'chennai':   (80.180, 12.900, 80.280, 12.985),
}

ap = argparse.ArgumentParser()
ap.add_argument('city')
ap.add_argument('--blocks', default='6x4', help='grid of blocks, COLSxROWS')
ap.add_argument('--holdout', type=int, default=8, help='how many blocks to hold out')
ap.add_argument('--seed', type=int, default=0)
ap.add_argument('--seeds', type=int, default=1,
                help='re-run over this many held-out draws and report the spread')
ap.add_argument('--bounds', help='west,south,east,north if the city is not in the table')
ap.add_argument('--routing', action='store_true',
                help='score the downstream trace against the flow-path mask '
                     'instead of scoring MNDWI against JRC')
a = ap.parse_args()

W, S, E, N = (tuple(float(x) for x in a.bounds.split(','))
              if a.bounds else BOUNDS.get(a.city, ()) or sys.exit(f'unknown city {a.city!r}'))

def load(name):
    try:
        return Image.open(f'data/{a.city}/{name}.png').convert('RGBA')
    except FileNotFoundError:
        sys.exit(f'missing data/{a.city}/{name}.png — add the benchmark exports from '
                 f'gee_blue_grid.js to urls/{a.city}.txt and re-run ./fetch_layers.sh {a.city}')


def routing_mode():
    """Score the downstream trace against an independently derived flow path.

    What this measures, precisely: how often cells the D8 trace walks through
    coincide with the flow-path mask, which is built from a different code path
    (upa > 2 km2 AND hnd < 2 m, thresholded in Earth Engine) over the same two
    bands. Two methods agreeing is worth something. One method agreeing with
    itself is not, and that is the trap here — both come from MERIT Hydro, so
    this is cross-method agreement within one source, not independent
    corroboration.

    What it does NOT measure: whether water actually goes where the trace says.
    There is no surveyed drain network for this catchment, so no such number
    exists, and the figure below is not an accuracy. The baseline is printed
    beside it for exactly that reason: agreement means nothing until you know
    what agreement a random walk would have scored.
    """
    rtg = load('routing')
    hyd, flow, buf = load('hydro'), load('flowpath'), load('buffers')
    if not (rtg.size == hyd.size == flow.size == buf.size):
        sys.exit(f'size mismatch: routing {rtg.size} hydro {hyd.size} '
                 f'flowpath {flow.size} buffers {buf.size}')

    d8 = np.asarray(rtg)[..., 0]
    upa = np.asarray(hyd)[..., 0].astype(np.int16)
    onflow = np.asarray(flow)[..., 3] > 128
    inside = np.asarray(buf)[..., 3] == 255
    H, W_ = d8.shape

    # Walk MERIT's own grid, as verify_encoding.py and the client both do. The
    # export is an arbitrary 2048 px across the AOI, so a 3 arc-second cell is
    # about 14.15 px and never a whole number of them; stepping a rounded 14
    # drifts off the grid and revisits cells the trace never entered. The grid
    # is centre-registered — centres on integer multiples of 1/1200 of a
    # degree — which was measured off the export rather than assumed.
    MERIT_DEG = 1.0 / 1200
    DXY = {1: (1, 0), 2: (1, 1), 3: (0, 1), 4: (-1, 1),
           5: (-1, 0), 6: (-1, -1), 7: (0, -1), 8: (1, -1)}

    def to_px(ix, iy):
        lon, lat = ix * MERIT_DEG, iy * MERIT_DEG
        return (int(round((lon - W) / (E - W) * W_)),
                int(round((N - lat) / (N - S) * H)))

    def walk(x0, y0):
        lon = W + (x0 + 0.5) / W_ * (E - W)
        lat = N - (y0 + 0.5) / H * (N - S)
        ix, iy = int(round(lon / MERIT_DEG)), int(round(lat / MERIT_DEG))
        seen, out = set(), []
        for _ in range(200):
            if (ix, iy) in seen:
                break
            seen.add((ix, iy))
            x, y = to_px(ix, iy)
            if not (0 <= x < W_ and 0 <= y < H) or not inside[y, x]:
                break
            out.append((x, y))
            c = int(d8[y, x])
            if c not in DXY:
                break
            dx, dy = DXY[c]
            ix, iy = ix + dx, iy - dy      # y is southward, latitude is not
        return out

    GX, GY = (int(v) for v in a.blocks.lower().split('x'))
    ys_ix = (np.arange(H) * GY) // H
    xs_ix = (np.arange(W_) * GX) // W_
    block_id = ys_ix[:, None] * GX + xs_ix[None, :]

    seed_ys, seed_xs = np.nonzero(inside & np.isin(d8, list(DXY)))
    if seed_xs.size == 0:
        sys.exit('no pixel inside the study area carries a direction — check '
                 'section 14 of gee_blue_grid.js')

    base = float(onflow[inside].mean())
    print(f'\nrouting agreement — {a.city}')
    print(f'  traced route   MERIT Hydro flow direction, 3 arc-second cells')
    print(f'  compared with  flow-path mask (upa > 2 km2 and hnd < 2 m)')
    print(f'  blocks         {GX}x{GY} contiguous tiles\n')

    per_seed = []
    for sd in range(max(1, a.seeds)):
        rng = np.random.default_rng(sd)
        pick = rng.choice(seed_xs.size, size=min(1500, seed_xs.size), replace=False)
        hits = np.zeros(GX * GY, np.int64)
        tot = np.zeros(GX * GY, np.int64)
        grew = []
        for i in pick:
            path = walk(int(seed_xs[i]), int(seed_ys[i]))
            for (x, y) in path:
                b = block_id[y, x]
                tot[b] += 1
                hits[b] += bool(onflow[y, x])
            # Upstream area at the end of a route against its start. Water runs
            # into larger catchments, so a direction field that is right sends
            # routes up this ratio and one that is transposed does not. It is
            # reported as a share rather than a pass, because a handful of
            # routes starting on a ridge legitimately end up going nowhere.
            if len(path) >= 3:
                grew.append(int(upa[path[-1][1], path[-1][0]])
                            >= int(upa[path[0][1], path[0][0]]))
        live = tot >= 100
        if not live.any():
            continue
        frac = hits[live] / tot[live]
        per_seed.append((float(np.median(frac)), float(frac.min()),
                         float(frac.max()), int(live.sum()), int(tot.sum())))
        print(f'    seed {sd:<3} per-block agreement median {np.median(frac):.3f}'
              f'   range {frac.min():.3f}-{frac.max():.3f}'
              f'   ({int(live.sum())} blocks, {int(tot.sum())} traced cells)'
              + (f'   {100*np.mean(grew):.0f}% end in a catchment no smaller '
                 f'than they started in' if grew else ''))

    if per_seed:
        meds = [p[0] for p in per_seed]
        print(f'\n    across {len(per_seed)} draws: median agreement '
              f'{min(meds):.3f} to {max(meds):.3f}')
    print(f'    baseline: {base:.3f} of all study-area cells lie on the mask')
    if per_seed and max(meds) <= base:
        print('\n    The routes do no better than picking cells at random.')
        print('    That is a finding about the direction field, not a score.')

    print('\n  This is agreement between two readings of MERIT Hydro, not')
    print('  corroboration by an independent source, and it is not an accuracy.')
    print('  Blocks are contiguous tiles, and a downstream cell is not')
    print('  independent of the upstream cell that routed into it, so even the')
    print('  block spread above is the optimistic version.')
    print('\n  No surveyed drain network exists for this catchment. Anyone')
    print('  reporting how often these routes are right has invented it.\n')


if a.routing:
    routing_mode()
    sys.exit(0)


ref_im, mn_im = load('ref2005'), load('mndwi2005')
if ref_im.size != mn_im.size:
    sys.exit(f'size mismatch: ref {ref_im.size} vs mndwi {mn_im.size}')

ref_a = np.asarray(ref_im)
mn_a = np.asarray(mn_im)

truth = ref_a[..., 0] > 127                      # white = water in the reference
valid = mn_a[..., 3] > 0                         # cloud-masked pixels carry no evidence
mndwi = mn_a[..., 0].astype(np.float32) / 255.0 * 2.0 - 1.0   # grey ramp back to -1..1

H, Wd = truth.shape
GX, GY = (int(v) for v in a.blocks.lower().split('x'))
if a.holdout >= GX * GY:
    sys.exit(f'--holdout {a.holdout} must be fewer than the {GX*GY} blocks available')

# Ground area, for reporting how much land the held-out set actually covers.
mid = math.radians((S + N) / 2)
km2_total = (E - W) * 111.320 * math.cos(mid) * (N - S) * 110.574

ys = np.arange(H) * GY // H
xs = np.arange(Wd) * GX // Wd
block_id = ys[:, None] * GX + xs[None, :]

rng = np.random.default_rng(a.seed)
test_blocks = set(rng.choice(GX * GY, size=a.holdout, replace=False).tolist())
is_test = np.isin(block_id, list(test_blocks))

train_sel = valid & ~is_test
test_sel = valid & is_test
if not test_sel.any():
    sys.exit('no valid pixels in the held-out blocks — try a different --seed')

def otsu(x):
    """Threshold maximising between-class variance, fitted on training pixels only."""
    hist, edges = np.histogram(x, bins=256, range=(-1, 1))
    centres = (edges[:-1] + edges[1:]) / 2
    w0 = np.cumsum(hist).astype(np.float64)
    w1 = w0[-1] - w0
    m0 = np.cumsum(hist * centres) / np.maximum(w0, 1)
    m1 = (np.sum(hist * centres) - np.cumsum(hist * centres)) / np.maximum(w1, 1)
    between = w0 * w1 * (m0 - m1) ** 2
    return float(centres[int(np.argmax(between))])

def score(pred, sel):
    p, t = pred[sel], truth[sel]
    tp = int(np.count_nonzero(p & t))
    fp = int(np.count_nonzero(p & ~t))
    fn = int(np.count_nonzero(~p & t))
    iou = tp / (tp + fp + fn) if tp + fp + fn else float('nan')
    prec = tp / (tp + fp) if tp + fp else float('nan')
    rec = tp / (tp + fn) if tp + fn else float('nan')
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else float('nan')
    return iou, f1, prec, rec, tp, fp, fn

t_otsu = otsu(mndwi[train_sel])
methods = [('MNDWI > 0', mndwi > 0.0), (f'Otsu/MNDWI ({t_otsu:+.3f})', mndwi > t_otsu)]

km2_test = km2_total * len(test_blocks) / (GX * GY)
print(f'\ncity            {a.city}')
print(f'reference       JRC GSW YearlyHistory, waterClass >= 2, 2003-2007')
print(f'prediction      Landsat 5 MNDWI, same years, same pixels')
print(f'blocks          {GX}x{GY} = {GX*GY}, {len(test_blocks)} held out '
      f'({km2_test:.1f} km2 of {km2_total:.1f} km2)')
print(f'valid pixels    {int(np.count_nonzero(test_sel)):,} in held-out blocks, '
      f'{100*truth[test_sel].mean():.2f}% water in reference\n')

print('  ' + '-' * 62)
print(f"  {'method':<22}{'IoU':>8}{'F1':>8}{'prec':>8}{'recall':>9}")
print('  ' + '-' * 62)
for name, pred in methods:
    iou, f1, prec, rec, *_ = score(pred, test_sel)
    print(f'  {name:<22}{iou:>8.3f}{f1:>8.3f}{prec:>8.3f}{rec:>9.3f}')
print('  ' + '-' * 62)

# Per-block spread matters more than the pooled figure: one large lake can
# carry an entire catchment's score and hide that most blocks are poor.
print('\n  per held-out block, MNDWI > 0:')
ious = []
for b in sorted(test_blocks):
    sel = valid & (block_id == b)
    if np.count_nonzero(sel) < 100 or not truth[sel].any():
        continue
    iou, *_ = score(mndwi > 0.0, sel)
    ious.append(iou)
    print(f'    block {b:<4} IoU {iou:.3f}   water {100*truth[sel].mean():5.2f}%')
if ious:
    print(f'\n    median {np.median(ious):.3f}   mean {np.mean(ious):.3f}   '
          f'sd {np.std(ious):.3f}   n={len(ious)}')

# One split is one sample. With 8 blocks held out of 24, which 8 they are moves
# the per-block median across a range wider than the difference between the two
# methods being compared, so quoting a single seed reports the draw rather than
# the method. Re-running over several seeds is the only way to see that, and
# seeing it is the point: the honest summary is the spread, not the best run.
if a.seeds > 1:
    print(f'\n  across {a.seeds} held-out draws:')
    pooled, medians = [], []
    for sd in range(a.seeds):
        rng2 = np.random.default_rng(sd)
        tb = set(rng2.choice(GX * GY, size=a.holdout, replace=False).tolist())
        tsel = valid & np.isin(block_id, list(tb))
        trsel = valid & ~np.isin(block_id, list(tb))
        if not tsel.any() or not trsel.any():
            continue
        pooled.append(score(mndwi > 0.0, tsel)[0])
        per = []
        for b in sorted(tb):
            sel = valid & (block_id == b)
            if np.count_nonzero(sel) < 100 or not truth[sel].any():
                continue
            per.append(score(mndwi > 0.0, sel)[0])
        if per:
            medians.append(float(np.median(per)))
        print(f'    seed {sd:<3} pooled IoU {pooled[-1]:.3f}   '
              f'per-block median {medians[-1] if medians else float("nan"):.3f}')
    if medians:
        print(f'\n    pooled IoU      {np.min(pooled):.3f} to {np.max(pooled):.3f}'
              f'   (median {np.median(pooled):.3f})')
        print(f'    per-block median {np.min(medians):.3f} to {np.max(medians):.3f}'
              f'   (median {np.median(medians):.3f})')
        print('\n    Report the range. A single seed is one draw, and the draw'
              '\n    moves the answer more than the choice of threshold does.')

print('\n  No learned model is scored here. This pipeline contains none —')
print('  every flag traces to a published dataset and a stated threshold.')
print()
