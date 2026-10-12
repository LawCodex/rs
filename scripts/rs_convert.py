#!/usr/bin/env python3
"""Convert archived Pravno-informacioni sistem RS pages (fetched by rs_fetch.py) to Markdown.

Usage: rs_convert.py RAW_DIR OUT_DIR
"""
import datetime, json, os, re, sys, unicodedata
from bs4 import BeautifulSoup, NavigableString, Tag, Comment, Doctype, Declaration, ProcessingInstruction

SKIP_STR = (Comment, Doctype, Declaration, ProcessingInstruction)

RAW, OUT = sys.argv[1], sys.argv[2]
TODAY = datetime.date.today().isoformat()

CYR = dict(zip('абвгдђежзијклљмнњопрстћуфхцчџш',
               ['a', 'b', 'v', 'g', 'd', 'dj', 'e', 'z', 'z', 'i', 'j', 'k', 'l', 'lj', 'm', 'n', 'nj', 'o', 'p',
                'r', 's', 't', 'c', 'u', 'f', 'h', 'c', 'c', 'dz', 's']))
MONTHS = {}
for i, names in enumerate([('јануар', 'januar'), ('фебруар', 'februar'), ('март', 'mart'), ('април', 'april'),
                           ('мај', 'maj'), ('јун', 'jun'), ('јул', 'jul'), ('август', 'avgust'),
                           ('септемб', 'septemb'), ('октоб', 'oktob'), ('новемб', 'novemb'), ('децемб', 'decemb')], 1):
    for n in names:
        MONTHS[n] = i

# type detection from the title (Cyrillic or Latin)
TYPES = [  # (regex on lowercased latinised title, type, directory)
    (r'^ustavni zakon', 'constitutional_act', 'ustav'),
    (r'^ustav ', 'constitution', 'ustav'),
    (r'^(krivicni |gradjanski |carinski |porodicni |zakonik)', 'code', 'zakoni'),
    (r'^zakonik', 'code', 'zakoni'),
    (r'^zakon', 'act', 'zakoni'),
    (r'^uredba', 'decree', 'uredbe'),
    (r'^pravilnik', 'regulation', 'pravilnici'),
    (r'^odluka', 'decision', 'odluke'),
    (r'^naredba', 'order', 'naredbe'),
    (r'^uputstvo', 'instruction', 'uputstva'),
    (r'^poslovnik', 'rules_of_procedure', 'poslovnici'),
    (r'^statut', 'statute', 'statuti'),
]


def lat(s):
    out = []
    for ch in s:
        lo = ch.lower()
        if lo in CYR:
            t = CYR[lo]
            out.append(t.capitalize() if ch != lo else t)
        else:
            out.append(ch)
    return ''.join(out)


def slug(s, n=80):
    s = lat(s).lower().replace('đ', 'dj')
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    s = re.sub(r'[^a-z0-9]+', '-', s).strip('-')
    return s[:n].rstrip('-')


def norm(t):
    t = t.replace('\xa0', ' ').replace('​', '').replace('﻿', '')
    return re.sub(r'[ \t\r\n]+', ' ', t).strip()


BLOCK = {'p', 'div', 'table', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'center', 'blockquote', 'section'}
ART_RE = re.compile(r'^(Члан|Član|Чл\.|Čl\.)\s*\d+[a-zа-я]?\.?\s*\**$', re.I)
BOLD_CLASSES = {'bold', 'v2-bold-1', 'italik', 'v2-italik-1', 'unbold-change', 'spacija', 'naslov'}


def inline(el):
    """Text of an inline element, keeping <sup>/<sub> lightly."""
    parts = []
    for c in el.descendants:
        if isinstance(c, NavigableString):
            if isinstance(c, SKIP_STR) or c.parent.name in ('script', 'style'):
                continue
            if c.parent.name == 'sup':
                parts.append('^' + str(c) + '^' if str(c).strip() else str(c))
            else:
                parts.append(str(c))
        elif c.name == 'br':
            parts.append('\x00')
    txt = ''.join(parts)
    lines = [norm(x) for x in txt.split('\x00')]
    return '  \n'.join(x for x in lines if x)


def table_md(t):
    rows = t.find_all('tr')
    simple = rows and not t.find(attrs={'colspan': True}) and not t.find(attrs={'rowspan': True}) \
        and not t.find('table')
    if simple:
        cells = [[inline(c).replace('|', '\\|').replace('  \n', ' ') for c in r.find_all(['td', 'th'])] for r in rows]
        w = max(len(r) for r in cells)
        if w == 0:
            return ''
        cells = [r + [''] * (w - len(r)) for r in cells]
        out = ['| ' + ' | '.join(cells[0]) + ' |', '|' + '---|' * w]
        out += ['| ' + ' | '.join(r) + ' |' for r in cells[1:]]
        return '\n'.join(out)
    # complex: keep minimal HTML
    t = BeautifulSoup(str(t), 'lxml').find('table')
    for e in t.find_all(True):
        keep = {k: v for k, v in e.attrs.items() if k in ('colspan', 'rowspan')}
        e.attrs = keep
        if e.name in ('span', 'font', 'a', 'o:p', 'b', 'i', 'strong', 'em'):
            e.unwrap()
    for e in t.find_all(['p', 'div']):
        e.insert_after(NavigableString(' '))
        e.unwrap()
    for e in t.find_all('img'):
        e.decompose()
    h = str(t)
    h = re.sub(r'\s+', ' ', h)
    h = h.replace('<tr>', '\n<tr>').replace('</table>', '\n</table>')
    return h


def blocks(el):
    """Yield (kind, element) leaves of block structure."""
    for c in el.children:
        if isinstance(c, NavigableString):
            if not isinstance(c, SKIP_STR) and norm(str(c)):
                yield ('text', c)
            continue
        if not isinstance(c, Tag) or c.name in ('script', 'style', 'meta', 'link', 'title', 'head', 'img'):
            continue
        if c.name == 'table':
            yield ('table', c)
        elif c.find(lambda x: isinstance(x, Tag) and x.name in BLOCK):
            yield from blocks(c)
        else:
            yield ('p', c)


def body_md(article):
    out = []
    started_articles = False
    for kind, e in blocks(article):
        if kind == 'table':
            md = table_md(e)
            if md:
                out.append(md)
            continue
        txt = norm(str(e)) if kind == 'text' else inline(e)
        if not txt:
            continue
        cls = set(e.get('class') or []) if kind == 'p' else set()
        flat = txt.replace('  \n', ' ')
        if ART_RE.match(flat):
            out.append('#### ' + flat)
            started_articles = True
        elif 'hide-change' in cls or flat.startswith('*Службени гласник') or flat.startswith('*Službeni glasnik'):
            out.append('*' + flat.strip('*').strip() + '*' if not flat.startswith('*') else '_' + flat + '_')
        elif (len(flat) <= 160 and re.search(r'[A-ZА-ЯЂЈЉЊЋЏČĆŽŠĐ]', flat)
              and not re.search(r'[a-zа-яђјљњћџčćžšđ]', flat) and not re.match(r'^[\d\W]+$', flat)):
            out.append('### ' + flat)
        elif cls & BOLD_CLASSES and len(flat) <= 250:
            out.append('**' + flat + '**')
        else:
            # escape leading markdown markers
            if re.match(r'^(#|>|\d+\. |[-+*] )', txt):
                txt = '\\' + txt
            out.append(txt)
    return '\n\n'.join(out)


def parse_date(s):
    m = re.search(r'(\d{1,2})\.\s*([^\W\d_]+)\s+(\d{4})', s.lower())
    if not m:
        return None
    for k, v in MONTHS.items():
        if m.group(2).startswith(k):
            try:
                return datetime.date(int(m.group(3)), v, int(m.group(1))).isoformat()
            except ValueError:
                return None
    return None


def yq(s):
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'


def main():
    index = json.load(open(os.path.join(RAW, 'index.json')))
    acts = {}
    stats = {'repealed': 0, 'nocontent': 0, 'truncated': 0}
    for key, (orig, ts) in sorted(index.items()):
        fn = os.path.join(RAW, 'html', key + '.html')
        if not os.path.exists(fn):
            continue
        raw = open(fn, 'rb').read()
        html = raw.decode('utf-8', errors='replace')
        s = BeautifulSoup(html, 'lxml')
        th = s.find(id='actTitleHeader')
        art_div = s.find('div', id='actContentPrimaryScroll')
        article = art_div.find('article') if art_div else None
        if not th or not article or len(norm(article.get_text(' '))) < 200:
            stats['nocontent'] += 1
            continue
        header = norm(th.get_text(' '))
        name, _, cites = header.partition(':')
        name, cites = name.strip(), cites.strip()
        m = re.match(r'(\d+)/(\d{4})(?:-(\d+))?', cites)
        if m:
            issue, year, page = m.group(1), m.group(2), m.group(3) or '0'
        else:
            mk = re.match(r'eli_[a-z-]+_(\d{4})_(\d+)_(\d+)', key)
            if not mk:
                continue
            year, issue, page = mk.group(1), mk.group(2), mk.group(3)
        text_head = norm(article.get_text(' '))[:3000]
        repealed = bool(re.search(r'НАПОМЕНА[^.]{0,80}?(Закон|Уредба|Законик|Пропис|Акт)\w*\s+(је\s+)?преста(о|ла|ло)\s+(је\s+)?да\s+важи', text_head)) \
            or bool(re.search(r'NAPOMENA[^.]{0,80}?(Zakon|Uredba|Zakonik|Propis|Akt)\w*\s+(je\s+)?presta(o|la|lo)\s+(je\s+)?da\s+važi', text_head))
        if repealed:
            stats['repealed'] += 1
            continue
        ltitle = lat(name).lower()
        typ, d = 'other', 'ostalo'
        for rx, t, dd in TYPES:
            if re.match(rx, ltitle.replace('č', 'c').replace('ć', 'c').replace('đ', 'dj').replace('ž', 'z').replace('š', 's')):
                typ, d = t, dd
                break
        if typ == 'other':
            mk = re.match(r'eli_skupstina-zakon', key)
            if mk:
                typ, d = 'act', 'zakoni'
        k2 = (year, issue, page, slug(name, 60))
        rec = dict(key=key, orig=orig, ts=ts, name=name, cites=cites, year=year, issue=issue, page=page,
                   type=typ, dir=d, article=article, truncated=len(raw) >= 1048000 and not html.rstrip().endswith('</html>'))
        if k2 not in acts or ts > acts[k2]['ts']:
            acts[k2] = rec
        s.decompose() if False else None
    print(stats, len(acts), 'acts', file=sys.stderr)
    counts = {}
    for k2, r in sorted(acts.items()):
        md = body_md(r['article'])
        # dates
        cit = re.search(r'[„"“]\s*Службени\s+гласник\s+(РС|Републике Србије)\s*[”"“]?\s*,?\s*(бр(ој)?\.?)?\s*[^\n]{0,400}', md)
        date = parse_date(cit.group(0)) if cit else None
        last = None
        if cit:
            ds = re.findall(r'(\d{1,2}\.\s*[^\W\d_]+\s+\d{4})', cit.group(0).lower())
            if ds:
                last = parse_date(ds[-1])
        if r['dir'] == 'ustav':
            sub = 'ustav'
        else:
            sub = '%s/%s' % (r['dir'], r['year'])
        fn = '%s-%03d-%s-%s.md' % (r['year'], int(r['issue']), r['page'], slug(r['name'], 70))
        if r['dir'] == 'ustav':
            fn = '%s-%s' % (r['year'], slug(r['name'], 70)) + ('-%s' % r['issue'] if 'ustavni' in slug(r['name']) else '') + '.md'
        path = os.path.join(OUT, sub, fn)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if r['key'].startswith('eli_'):
            p = r['key'][4:].split('_')
            src = 'https://www.pravno-informacioni-sistem.rs/SlGlasnikPortal/eli/rep/sgrs/%s/%s/%s/%s/reg' % (p[0].replace('-', '/'), p[1], p[2], p[3])
        else:
            src = 'https://www.pravno-informacioni-sistem.rs/SlGlasnikPortal/reg/viewAct/' + r['key'][5:]
        arch = 'https://web.archive.org/web/%s/%s' % (r['ts'], r['orig'])
        snap = '%s-%s-%s' % (r['ts'][:4], r['ts'][4:6], r['ts'][6:8])
        fm = ['---', 'title: ' + yq(r['name']),
              'identifier: ' + yq('Službeni glasnik RS %s/%s' % (r['issue'], r['year'])),
              'citation: ' + yq(r['cites']),
              'type: ' + r['type'], 'jurisdiction: rs', 'language: sr']
        if date:
            fm.append('date: ' + date)
        if last:
            fm.append('last_amended: ' + last)
        # in force at the snapshot date; older snapshots may have been repealed since
        fm += ['status: ' + ('in_force' if snap >= '2024-01-01' else 'unknown'), 'text_version: consolidated',
               'source: ' + yq(src), 'archived_url: ' + yq(arch), 'snapshot_date: ' + snap,
               'retrieved: ' + TODAY]
        if r['truncated']:
            fm.append('note: "The archived page was truncated at 1 MB; the end of the text may be missing."')
        fm.append('---')
        open(path, 'w').write('\n'.join(fm) + '\n\n# ' + r['name'] + '\n\n' + md + '\n')
        counts[r['dir']] = counts.get(r['dir'], 0) + 1
    print(counts, file=sys.stderr)


if __name__ == '__main__':
    main()
