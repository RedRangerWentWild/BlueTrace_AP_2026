"""The parts of BlueTrace's screening logic the database scripts need, ported from
blue-grid/index.html so that rows written by Python are the rows the app would
produce. Standard library + Pillow (for reading the PNG layers) only.

Reference data is parsed out of index.html and data/corpus.json at import time,
never retyped, so the scripts fail loudly if the app changes underneath them.

    CITIES, RULESETS, OUTCOME_TITLE, OUTCOME_RANK, CODE_CHUNK, CODE_OUTCOME, PARAMS
    decide_(m, rule)           decide()            (index.html line 2802)
    fnv1a(s)                   fnv1a()             (line 3603)
    metres_between(...)        metresBetween()     (line 1556)
    sig2(x)                    sig2()              (line 2446)
    Layers(city)               makeSampler() / sampleCh() / sample() / readSite() /
                               traceDownstream()   (lines 1712-1795, 2541, 2658)
    canonical(...), cert_ref(...)                  the certificate reference (line 3650)
"""
import json
import math
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
APP = ROOT / 'blue-grid'
HTML = (APP / 'index.html').read_text(encoding='utf-8')
CORPUS = json.loads((APP / 'data' / 'corpus.json').read_text(encoding='utf-8'))


def js_unescape(s):
    return re.sub(r'\\u([0-9a-fA-F]{4})', lambda m: chr(int(m.group(1), 16)), s)


def js_round(x):
    """Math.round: halves go up, unlike Python's round()."""
    return math.floor(x + 0.5)


def block(name):
    """Source text of the top-level `var NAME = {...};` in index.html."""
    m = re.search(r'^var ' + name + r' = \{', HTML, flags=re.M)
    if not m:
        sys.exit('cannot find var %s in index.html' % name)
    i, depth = m.end() - 1, 0
    for j in range(i, len(HTML)):
        if HTML[j] == '{':
            depth += 1
        elif HTML[j] == '}':
            depth -= 1
            if depth == 0:
                return HTML[i:j + 1]
    sys.exit('unterminated %s' % name)


# ------------------------------------------------------------------ reference data
CITIES = {}
for _key, _body in re.findall(r"\n  (\w+): \{(.*?)\n  \}", block('CITIES'), flags=re.S):
    CITIES[_key] = {
        'label': re.search(r"label: '([^']*)'", _body).group(1),
        'sub': re.search(r"sub: '([^']*)'", _body).group(1),
        'bounds': [float(x) for x in re.search(r"bounds: \[([^\]]*)\]", _body).group(1).split(',')],
        'zones': re.search(r"zones: '([^']*)'", _body).group(1),
        'hotspots': [dict(name=n, lon=float(lo), lat=float(la), px=int(p)) for n, lo, la, p in
                     re.findall(r"\{name:'([^']*)',\s*lon:([\d.]+), lat:([\d.]+), px:(\d+)\}", _body)],
    }

RULESETS = {}
for _rid, _label, _lake, _drain in re.findall(
        r"(\w+):\s*\{id:'\w+', label:'([^']*)',\s*lakeM:(\d+), drainM:(\d+)", block('RULESETS')):
    RULESETS[_rid] = dict(id=_rid, label=js_unescape(_label), lakeM=int(_lake), drainM=int(_drain))

OUTCOME_TITLE = dict(re.findall(r"(\w+):\s*\{c:'\w+',\s*t:'([^']*)'", block('OUTCOME')))
OUTCOME_RANK = {'REJECT': 3, 'REFER': 2, 'CONDITIONS': 1, 'NO_OBJECTION': 0}   # decide(): rank = {...}

CODE_CHUNK = dict(re.findall(r"'([a-z.-]+)':\s*'([a-z0-9.-]+)'", block('CODE_CHUNK')))

_dec = HTML[HTML.index('function decide(m, rule)'):HTML.index('var CODE_CHUNK')]
CODE_OUTCOME = {}
for _d, _code in re.findall(r"d:'(\w+)',\s*codes?:\[?'([a-z.-]+)'", _dec):
    if CODE_OUTCOME.get(_code, _d) != _d:
        sys.exit('decide() returns %s with two outcomes' % _code)
    CODE_OUTCOME[_code] = _d
if set(CODE_OUTCOME) != set(CODE_CHUNK):
    sys.exit('decide() and CODE_CHUNK disagree: %s' % (set(CODE_OUTCOME) ^ set(CODE_CHUNK)))

# The numbers the app computes with: the bootstrap block in index.html (between
# "// @params" and "// @end-params"), overridden by every value the corpus
# declares - exactly what reconcileParams() does (line 2784): the corpus wins.
_pblock = HTML[HTML.index('// @params'):HTML.index('// @end-params')]
PARAMS = {k: float(v) for k, v in re.findall(r'^\s*(\w+):\s*([\d.]+),?', _pblock, flags=re.M)}
PARAMS.update({k: v['v'] for k, v in CORPUS['params'].items()})
UNCERTAINTY_M = PARAMS.get('uncertaintyM', 20)


# ------------------------------------------------------------------ arithmetic helpers
def sig2(x):
    """sig2(): two significant figures."""
    if x is None or not math.isfinite(x):
        return None
    if x == 0:
        return 0
    return float('%.2g' % x)


def metres_between(lon1, lat1, lon2, lat2):
    """metresBetween(): equirectangular metres."""
    dx = (lon2 - lon1) * 111320 * math.cos(lat1 * math.pi / 180)
    dy = (lat2 - lat1) * 110574
    return math.sqrt(dx * dx + dy * dy)


def fnv1a(s):
    """fnv1a(): 32-bit FNV-1a, upper-case hex."""
    h = 0x811c9dc5
    for ch in s:
        h ^= ord(ch)
        h = (h + (h << 1) + (h << 4) + (h << 7) + (h << 8) + (h << 24)) & 0xFFFFFFFF
    return '%08X' % h


def _js(v):
    """Array.join() writes null as an empty string."""
    return '' if v is None else str(v)


def canonical(city, lat, lon, plot_m, rule, m, verdict, iso, corpus_version, generator, chunk_ids):
    """The canonical record a certificate's digest is computed over (line 3650)."""
    return '|'.join(_js(v) for v in [
        city, '%.6f' % lat, '%.6f' % lon, plot_m, rule['id'], rule['lakeM'], rule['drainM'],
        m['distPresent'], m['distHistoric'], m['distDrain'], m['lastWaterYear'], m['occurrence'], m['handM'],
        verdict, iso, corpus_version, generator, ','.join(chunk_ids)])


def cert_ref(iso, seq, canon):
    """'BT/BLR/<date>/<4-digit number>-<digest>' (the app writes BLR for every city)."""
    return 'BT/BLR/' + iso[:10].replace('-', '') + '/' + str(seq).zfill(4) + '-' + fnv1a(canon)


# ------------------------------------------------------------------ decide()
def decide_(m, rule):
    """decide() from index.html, with the same branches, order and sentences.
    Returns (verdict, [(code, text), ...])."""
    if m['distPresent'] is None or m['distHistoric'] is None:
        return 'REFER', [('refer.outside-study-area',
                          'This plot lies outside the mapped study area. No satellite evidence exists for it.')]
    occ = None if m['occurrence'] is None else '%d%%' % m['occurrence']
    if m['distPresent'] == 0:
        return 'REJECT', [('reject.inside-live-water',
            'The plot footprint falls inside an existing surface water body'
            + (', recorded as water in ' + occ + ' of observations since 1984.' if occ else '.'))]
    if m['distHistoric'] == 0:
        when = ('last recorded as water in %d' % m['lastWaterYear']) if m['lastWaterYear'] \
               else 'recorded as water before 2000'
        built = (m['encroached'] or 0) > .1
        if (m['occurrence'] or 0) >= 50:
            w = ['The plot sits on a former water body, ' + when + ', water in ' + occ + ' of observations.']
            if built:
                w.append('Construction is already present on this footprint.')
            return 'REJECT', [('reject.former-water-high-occurrence', ' '.join(w))]
        at_channel = m['handM'] is not None and m['handM'] <= PARAMS['handDeepM']
        if built:
            return 'REJECT', [('reject.construction-on-former-bed', ' '.join([
                'The plot sits on a former water body, ' + when + ', and construction '
                + 'already stands on that footprint.',
                ('Water occurrence reads ' + occ + ' of observations, which is low '
                 + 'because the record spans the period in which the bed was lost: a '
                 + 'tank drained part-way through 1984–2021 is dry for the remainder '
                 + 'of it. The low share is evidence of the loss, not evidence against it.')
                if occ else 'How often it held water is not recorded at this pixel.']))]
        if at_channel:
            return 'REFER', [('refer.intermittent-water', ' '.join([
                'The plot sits on land recorded as water ' + ('only ' + occ + ' of the time, ' if occ else '')
                + when + ', and stands at the level of the channel it drains into.',
                'Low occurrence on a bed at channel level does not resolve to a wet '
                + 'season: it is equally the signature of a tank lost during the record. '
                + 'Establish the boundary against the notified tank schedule.']))]
        return 'REFER', [('refer.intermittent-water',
            ('The plot sits on land recorded as water only ' + occ + ' of the time, ' + when
             + '. At 30 m resolution intermittent water cannot be distinguished from a wet season.')
            if occ else
            ('The plot sits on land recorded as water, ' + when + '. How often it held water is not '
             + 'recorded at this pixel, so the record cannot distinguish a tank from a field that '
             + 'floods in a wet year.'))]
    R = []
    dp, dh, dd = m['distPresent'], m['distHistoric'], m['distDrain']
    lake, drain = rule['lakeM'], rule['drainM']
    if dp < lake - UNCERTAINTY_M:
        R.append(('REJECT', 'reject.inside-buffer', 'The plot lies %d m from the present water edge, '
                  'inside the %d m buffer.' % (dp, lake)))
    elif abs(dp - lake) <= UNCERTAINTY_M:
        R.append(('REFER', 'refer.buffer-within-uncertainty', 'The plot lies %d m from the present water edge. '
                  'At ±%d m that cannot be resolved against the %d m buffer. Ground survey required.'
                  % (dp, UNCERTAINTY_M, lake)))
    if dp - dh > 30 and dh < lake:
        R.append(('REFER', 'refer.shoreline-disagreement', 'Measured from today’s water edge the plot is %d'
                  ' m away and clears the %d m buffer. Measured from the 1984–99 edge it is %d m away, '
                  'inside it. The shoreline has retreated %d m here, so the buffer measured today is drawn '
                  'from a boundary that encroachment created. Verify against the notified lake boundary.'
                  % (dp, lake, dh, dp - dh)))
    # JavaScript compares a null distance as 0, so a missing drain distance counts as "near"
    if (dd if dd is not None else 0) < drain + UNCERTAINTY_M:
        R.append(('REFER', 'refer.near-drainage', 'The plot lies about %s m from a terrain-derived '
                  'drainage line, against a %d m buffer. Drain order is not resolved at the 90 m source '
                  'resolution — check the BBMP rajakaluve alignment for this survey number.'
                  % (_js(dd) if dd is not None else 'null', drain)))
    if m['handM'] is not None and m['handM'] <= 1:
        R.append(('CONDITIONS', 'conditions.low-ground', 'The plot stands %d m above the nearest drainage '
                  'line. On-site retention and a plinth condition should be imposed.' % m['handM']))
    if not R:
        return 'NO_OBJECTION', [('no-objection.nothing-found', ' '.join([
            'No recorded water body, buffer breach or drainage line within %d m of this plot.' % UNCERTAINTY_M,
            'Absence of evidence at 30 m resolution is not evidence of absence: tanks under roughly '
            'half a hectare do not appear in this record.']))]
    top = R[0]
    for r in R[1:]:
        if OUTCOME_RANK[r[0]] > OUTCOME_RANK[top[0]]:
            top = r
    return top[0], [(code, text) for _, code, text in R]


# ------------------------------------------------------------------ the raster layers
D8_STEP = {1: (1, 0), 2: (1, 1), 3: (0, 1), 4: (-1, 1), 5: (-1, 0), 6: (-1, -1), 7: (0, -1), 8: (1, -1)}
D8_NAME = {(1, 0): 'E', (1, 1): 'SE', (0, 1): 'S', (-1, 1): 'SW', (-1, 0): 'W', (-1, -1): 'NW',
           (0, -1): 'N', (1, -1): 'NE'}      # x east, y south (line 2502)
D8_MOUTH, D8_DEPRESSION = 9, 10
MERIT_DEG = 1 / 1200
PROBE_METRES = 35
SAMPLE_MAX_W = 1024
UPA_DEN = math.log10(1 + PARAMS['upaCeilKm2'])


def decode_upa(code):
    """decodeUpa(): the log-packed upstream area in hydro.png's red channel."""
    return None if code is None else math.pow(10, (code / 255) * UPA_DEN) - 1


class Layers:
    """makeSampler() for one city: the four data layers pixel-exact, the encroached
    map layer at most SAMPLE_MAX_W wide (the browser smooths that downscale; here
    it is a bilinear resize, so `encroached` can differ by a few hundredths)."""

    def __init__(self, city):
        from PIL import Image
        self.b = CITIES[city]['bounds']
        self.s = {}
        for name, exact in (('buffers', True), ('history', True), ('hydro', True), ('routing', True),
                            ('encroached', False)):
            path = APP / 'data' / city / (name + '.png')
            if not path.exists():
                continue
            im = Image.open(path).convert('RGBA')
            if not exact:
                sc = min(1, SAMPLE_MAX_W / im.width)
                im = im.resize((max(1, js_round(im.width * sc)), max(1, js_round(im.height * sc))),
                               Image.BILINEAR)
            mid_lat = (self.b[1] + self.b[3]) / 2
            metres_wide = (self.b[2] - self.b[0]) * 111320 * math.cos(mid_lat * math.pi / 180)
            self.s[name] = dict(w=im.width, h=im.height, mpp=metres_wide / im.width, d=im.tobytes())

    def sample_ch(self, layer, lon, lat, ch, mode, radius_m=None, min_alpha=255):
        """sampleCh(): min or max of one channel over a disc, ignoring pixels outside the study area."""
        s, b = self.s.get(layer), self.b
        if s is None:
            return None
        x = js_round((lon - b[0]) / (b[2] - b[0]) * s['w'])
        y = js_round((b[3] - lat) / (b[3] - b[1]) * s['h'])
        rad = PROBE_METRES if radius_m is None else radius_m
        R = max(0, js_round(rad / s['mpp']))
        lo, best, w, h, d = mode == 'min', None, s['w'], s['h'], s['d']
        for dy in range(-R, R + 1):
            for dx in range(-R, R + 1):
                if dx * dx + dy * dy > R * R:
                    continue
                px, py = x + dx, y + dy
                if px < 0 or py < 0 or px >= w or py >= h:
                    continue
                i = (py * w + px) * 4
                if d[i + 3] < min_alpha:
                    continue
                v = d[i + ch]
                if best is None or (v < best if lo else v > best):
                    best = v
        return best

    def sample(self, layer, lon, lat):
        """sample(): the highest alpha within PROBE_METRES, as a fraction (used for `encroached`)."""
        s, b = self.s.get(layer), self.b
        if s is None:
            return 0
        x = js_round((lon - b[0]) / (b[2] - b[0]) * s['w'])
        y = js_round((b[3] - lat) / (b[3] - b[1]) * s['h'])
        R, best, w, h, d = max(1, js_round(PROBE_METRES / s['mpp'])), 0, s['w'], s['h'], s['d']
        for dy in range(-R, R + 1):
            for dx in range(-R, R + 1):
                if dx * dx + dy * dy > R * R:
                    continue
                px, py = x + dx, y + dy
                if px < 0 or py < 0 or px >= w or py >= h:
                    continue
                best = max(best, d[(py * w + px) * 4 + 3])
        return best / 255

    def read_site(self, lon, lat, plot_m):
        """readSite() plus the upstream area siteContext() reads (lines 2677-2678)."""
        r = max(6, plot_m / 2)
        yc = self.sample_ch('history', lon, lat, 0, 'max', r, 1)
        upa_code = self.sample_ch('hydro', lon, lat, 0, 'max', r, 1)
        return dict(
            distPresent=self.sample_ch('buffers', lon, lat, 0, 'min', r),
            distHistoric=self.sample_ch('buffers', lon, lat, 1, 'min', r),
            distDrain=self.sample_ch('buffers', lon, lat, 2, 'min', r),
            lastWaterYear=(1983 + yc) if yc else None,
            occurrence=self.sample_ch('history', lon, lat, 1, 'max', r, 1),
            handM=self.sample_ch('history', lon, lat, 2, 'min', r, 1),
            encroached=self.sample('encroached', lon, lat),
            upaKm2=None if upa_code is None else sig2(decode_upa(upa_code)))

    def trace(self, lon0, lat0):
        """traceDownstream(): returns (steps, ended_by). Each step is
        (direction, length_m, upa_km2 of the cell reached, hand_m of the cell reached)."""
        if 'routing' not in self.s:
            return [], None
        ix, iy = js_round(lon0 / MERIT_DEG), js_round(lat0 / MERIT_DEG)
        lon, lat = ix * MERIT_DEG, iy * MERIT_DEG
        seen, moves, cells, ended = set(), [], {}, 'capped'
        for n in range(int(PARAMS['routeMaxSteps'])):
            if (ix, iy) in seen:
                ended = 'loop'
                break
            seen.add((ix, iy))
            if self.sample_ch('buffers', lon, lat, 0, 'min', 0) is None:
                ended = 'edge'
                break
            upa_code = self.sample_ch('hydro', lon, lat, 0, 'max', 0, 1)
            upa = decode_upa(upa_code)
            hand = self.sample_ch('history', lon, lat, 2, 'min', 0, 1)
            hand_ok = hand is not None and hand < 255
            if n > 0:   # the origin is the plot itself, not ground that receives from it
                cells[n] = (sig2(upa) if upa is not None else None, hand if hand_ok else None)
            if upa is not None and upa > PARAMS['trunkUpaKm2'] and n > 0:
                ended = 'trunk'
                break
            code = self.sample_ch('routing', lon, lat, 0, 'max', 0)
            if code == D8_MOUTH:
                ended = 'mouth'
                break
            if code == D8_DEPRESSION:
                ended = 'depression'
                break
            step = D8_STEP.get(code)
            if not step:
                ended = 'nodata'
                break
            ix, iy = ix + step[0], iy - step[1]
            nlon, nlat = ix * MERIT_DEG, iy * MERIT_DEG
            moves.append((D8_NAME[step], metres_between(lon, lat, nlon, nlat)))
            lon, lat = nlon, nlat
        steps = []
        for k, (direction, length) in enumerate(moves, start=1):
            upa, hand = cells.get(k, (None, None))   # the cell a step arrives in may never be read
            steps.append((direction, round(length, 1), upa, hand))
        return steps, (ended if steps else None)
