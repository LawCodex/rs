#!/usr/bin/env python3
"""Fetch Serbian consolidated legislation from Internet Archive copies of the official
Pravno-informacioni sistem RS (www.pravno-informacioni-sistem.rs), which is not reachable
from outside Serbia (connection times out).

1. Query the Wayback CDX API for all captured pages under
   /SlGlasnikPortal/eli/rep/sgrs/{skupstina/zakon,skupstina/ustav,vlada/uredba}/.../reg
   and /SlGlasnikPortal/reg/viewAct/<uuid>.
2. For each distinct act keep the most recent capture and download the raw archived page
   (id_ mode, unmodified) into _raw/rs/html/.

Usage: rs_fetch.py [RAW_DIR]
"""
import json, os, re, sys, time
import requests

RAW = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), '..', '..', '_raw', 'rs')
UA = 'LawCodex/1.0 (+https://github.com/LawCodex)'
S = requests.Session(); S.headers['User-Agent'] = UA
CDX = 'https://web.archive.org/cdx/search/cdx'
PREFIXES = ['eli/rep/sgrs/skupstina/zakon/', 'eli/rep/sgrs/skupstina/ustav/',
            'eli/rep/sgrs/vlada/uredba/', 'eli/rep/sgrs/skupstina/zakonik/', 'reg/viewAct/']
DELAY = 1.5


def get(url, **kw):
    for i in range(6):
        try:
            r = S.get(url, timeout=120, **kw)
            if r.status_code in (429, 502, 503, 504):
                raise requests.RequestException('HTTP %d' % r.status_code)
            return r
        except requests.RequestException as e:
            w = 10 * 2 ** i
            print('  retry', url, e, 'wait', w, file=sys.stderr); time.sleep(w)
    return None


def cdx(prefix):
    fn = os.path.join(RAW, 'cdx_' + prefix.strip('/').replace('/', '_') + '.txt')
    if not os.path.exists(fn):
        r = get(CDX, params={'url': 'pravno-informacioni-sistem.rs/SlGlasnikPortal/' + prefix,
                             'matchType': 'prefix', 'fl': 'original,timestamp,statuscode,length',
                             'filter': 'statuscode:200'})
        open(fn, 'w').write(r.text)
    return open(fn).read().split('\n')


def key_of(orig):
    u = orig.replace('%20', '').replace(':80', '')
    m = re.search(r'/eli/rep/sgrs/([a-z]+/[a-z]+)/(\d{4})/(\d+)/(\d+)/reg(?:$|/?$)', u)
    if m:
        return 'eli_' + '_'.join(m.groups()).replace('/', '-')
    m = re.search(r'/reg/viewAct/([0-9a-f-]{36})$', u)
    if m:
        return 'uuid_' + m.group(1)
    return None


def main():
    os.makedirs(os.path.join(RAW, 'html'), exist_ok=True)
    best = {}
    for p in PREFIXES:
        for line in cdx(p):
            f = line.split()
            if len(f) < 4:
                continue
            k = key_of(f[0])
            if not k:
                continue
            if int(f[3]) < 8000:   # error/empty shells (compressed size)
                continue
            if k not in best or f[1] > best[k][1]:
                best[k] = (f[0], f[1])
    json.dump(best, open(os.path.join(RAW, 'index.json'), 'w'), indent=0)
    print(len(best), 'acts to fetch', file=sys.stderr)
    n = 0
    for k, (orig, ts) in sorted(best.items()):
        fn = os.path.join(RAW, 'html', k + '.html')
        if os.path.exists(fn):
            continue
        url = 'https://web.archive.org/web/%sid_/%s' % (ts, orig)
        r = get(url)
        if r is not None and r.status_code == 200:
            open(fn, 'wb').write(r.content)
            n += 1
        else:
            print('FAIL', k, url, r.status_code if r is not None else None, file=sys.stderr)
        time.sleep(DELAY)
    print('fetched', n, file=sys.stderr)


if __name__ == '__main__':
    main()
