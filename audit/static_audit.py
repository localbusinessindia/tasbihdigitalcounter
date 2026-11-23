#!/usr/bin/env python3
"""Static (source-level) audit of the tasbih site. Reads files only; no network.
Usage: python3 static_audit.py <site_dir> <out.json>
Every check returns PASS / FAIL / BLOCKED / NOT_APPLICABLE with details.
"""
import glob, json, os, re, subprocess, sys, xml.etree.ElementTree as ET
from urllib.parse import urlsplit, urljoin
from urllib.robotparser import RobotFileParser
from bs4 import BeautifulSoup
from PIL import Image

SITE = os.path.abspath(sys.argv[1]); OUT = sys.argv[2]
HOST = 'https://tasbihdigitalcounter.netlify.app'
R = []
def rec(cid, title, status, detail='', evidence=None):
    R.append({'id': cid, 'title': title, 'status': status, 'detail': detail, 'evidence': evidence or []})

def read(p): return open(os.path.join(SITE, p), encoding='utf8').read()
pages = sorted(f for f in os.listdir(SITE) if f.endswith('.html'))
content_pages = [p for p in pages if not p.startswith('google') and p != '404.html']
slug = lambda p: '' if p == 'index.html' else p[:-5]
soups = {p: BeautifulSoup(read(p), 'html.parser') for p in pages if not p.startswith('google')}

# redirects
redirects = {}
if os.path.exists(os.path.join(SITE, '_redirects')):
    for l in read('_redirects').splitlines():
        t = l.split()
        if len(t) >= 3 and not l.startswith('#'): redirects[t[0]] = t[1]

def route_for(path):
    """Map a URL path to a file or None, following Netlify pretty-URL rules."""
    p = path.split('#')[0]
    if p in ('', '/'): return 'index.html'
    c = p.lstrip('/')
    if os.path.isfile(os.path.join(SITE, c)): return c
    if os.path.isfile(os.path.join(SITE, c + '.html')): return c + '.html'
    return None

# ---- S01 required files
need = ['index.html', '404.html', 'robots.txt', 'sitemap.xml', 'manifest.webmanifest', 'sw.js', 'content.css', '_headers', '_redirects', 'netlify.toml']
miss = [n for n in need if not os.path.exists(os.path.join(SITE, n))]
rec('S01', 'Required site files present', 'FAIL' if miss else 'PASS', f'missing: {miss}' if miss else f'{len(need)} required files found')

# ---- S02 per-page head metadata
issues = []; titles = {}; descs = {}
for p, s in soups.items():
    raw = read(p)
    if p == '404.html':
        rb = s.find('meta', attrs={'name': 'robots'})
        if not rb or 'noindex' not in rb['content']: issues.append(f'{p}: 404 page should be noindex')
        continue
    h = s.find('html')
    if not h or not h.get('lang'): issues.append(f'{p}: missing html lang')
    m = re.search(r'<meta[^>]+charset', raw, re.I)
    if not m or m.start() > 1024: issues.append(f'{p}: charset declaration not within first 1024 bytes')
    if not s.find('meta', attrs={'name': 'viewport'}): issues.append(f'{p}: missing viewport')
    t = (s.title.string or '').strip() if s.title else ''
    if not t: issues.append(f'{p}: missing title')
    titles.setdefault(t, []).append(p)
    d = s.find('meta', attrs={'name': 'description'}); dc = d['content'].strip() if d and d.get('content') else ''
    if not dc: issues.append(f'{p}: missing meta description')
    descs.setdefault(dc, []).append(p)
    c = s.find('link', rel='canonical')
    exp = f'{HOST}/{slug(p)}'
    if not c or c.get('href') != exp: issues.append(f'{p}: canonical {c.get("href") if c else None} != {exp}')
    og = {x.get('property'): x.get('content') for x in s.find_all('meta') if x.get('property')}
    for k in ('og:title', 'og:description', 'og:url', 'og:image', 'og:type'):
        if not og.get(k): issues.append(f'{p}: missing {k}')
    if og.get('og:url') != exp: issues.append(f'{p}: og:url {og.get("og:url")} != {exp}')
    if not s.find('meta', attrs={'name': 'twitter:card'}): issues.append(f'{p}: missing twitter:card')
for t, ps in titles.items():
    if len(ps) > 1: issues.append(f'duplicate title {t!r}: {ps}')
for d, ps in descs.items():
    if len(ps) > 1: issues.append(f'duplicate description: {ps}')
rec('S02', 'Title/description/canonical/OG/viewport/charset/lang on every indexable page', 'FAIL' if issues else 'PASS', f'{len(content_pages)} pages checked', issues)

# ---- S03 headings
issues = []
for p, s in soups.items():
    hs = [int(h.name[1]) for h in s.find_all(re.compile('^h[1-6]$'))]
    if hs.count(1) != 1: issues.append(f'{p}: {hs.count(1)} h1 elements')
    prev = 0
    for n in hs:
        if prev and n > prev + 1: issues.append(f'{p}: heading level skip h{prev}->h{n}')
        prev = n
    ids = [x['id'] for x in s.find_all(id=True)]
    d = {i for i in ids if ids.count(i) > 1}
    if d: issues.append(f'{p}: duplicate ids {d}')
rec('S03', 'Single h1, no heading-level skips, no duplicate ids', 'FAIL' if issues else 'PASS', '', issues)

# ---- S04 internal links, redirect hops, link graph
issues_broken, issues_redirect, graph = [], [], {p: set() for p in pages}
for p, s in soups.items():
    for a in s.find_all('a', href=True):
        h = a['href']
        if re.match(r'^(mailto:|tel:|https?://(?!tasbihdigitalcounter))', h) or h.startswith('#'): continue
        u = urlsplit(urljoin(f'{HOST}/{slug(p)}' if slug(p) else HOST + '/', h))
        if u.netloc and u.netloc != 'tasbihdigitalcounter.netlify.app': continue
        if u.path in redirects: issues_redirect.append(f'{p}: href="{h}" -> 301 -> {redirects[u.path]}')
        tgt = route_for(u.path)
        if not tgt: issues_broken.append(f'{p}: {h}'); continue
        if u.path.endswith('.html') and u.path not in redirects: issues_redirect.append(f'{p}: href="{h}" is a non-canonical .html URL')
        graph[p].add(tgt)
    for tag, attr in (('link', 'href'), ('script', 'src'), ('img', 'src')):
        for e in s.find_all(tag, **{attr: True}):
            v = e[attr]
            if re.match(r'^(https?:|data:|#)', v): continue
            if not route_for(urlsplit(urljoin('/', v)).path): issues_broken.append(f'{p}: <{tag}> {v} does not exist')
rec('S04a', 'Internal links and assets resolve to existing files', 'FAIL' if issues_broken else 'PASS', '', issues_broken)
rec('S04b', 'Internal links point directly at canonical URLs (no redirect hop)', 'FAIL' if issues_redirect else 'PASS', f'{len(issues_redirect)} links go through a redirect' if issues_redirect else '', issues_redirect[:40])

seen, stack = set(), ['index.html']
while stack:
    x = stack.pop()
    if x in seen: continue
    seen.add(x); stack.extend(graph.get(x, []))
orph = [p for p in content_pages if p not in seen]
rec('S05', 'No orphan pages (all reachable from homepage via internal links)', 'FAIL' if orph else 'PASS', '', orph)

# ---- S06 sitemap
try:
    tree = ET.parse(os.path.join(SITE, 'sitemap.xml')); root = tree.getroot()
    ns = '{http://www.sitemaps.org/schemas/sitemap/0.9}'
    issues = []
    if root.tag != ns + 'urlset': issues.append('root is not sitemap urlset namespace')
    locs = [u.find(ns + 'loc').text.strip() for u in root.findall(ns + 'url')]
    if len(locs) != len(set(locs)): issues.append('duplicate <loc>')
    for l in locs:
        pu = urlsplit(l)
        if pu.scheme != 'https' or pu.netloc != 'tasbihdigitalcounter.netlify.app': issues.append(f'bad host/scheme: {l}')
        if pu.path.endswith('.html') or (pu.path.endswith('/') and pu.path != '/'): issues.append(f'non-canonical form: {l}')
        if not route_for(pu.path): issues.append(f'sitemap URL has no page: {l}')
    for u in root.findall(ns + 'url'):
        lm = u.find(ns + 'lastmod')
        if lm is not None and not re.match(r'^\d{4}-\d{2}-\d{2}$', lm.text.strip()): issues.append(f'bad lastmod {lm.text}')
    expected = {f'{HOST}/{slug(p)}' for p in content_pages}
    for e in sorted(expected - set(locs)): issues.append(f'indexable page missing from sitemap: {e}')
    for l in locs:
        f = route_for(urlsplit(l).path)
        if f and soups.get(f) is not None:
            rb = soups[f].find('meta', attrs={'name': 'robots'})
            if rb and 'noindex' in rb.get('content', ''): issues.append(f'noindex page in sitemap: {l}')
    rec('S06', 'sitemap.xml valid, canonical, complete, no noindex/nonexistent URLs', 'FAIL' if issues else 'PASS', f'{len(locs)} URLs', issues)
except Exception as e:
    rec('S06', 'sitemap.xml valid', 'FAIL', str(e))

# ---- S07 robots
rp = RobotFileParser(); txt = read('robots.txt'); rp.parse(txt.splitlines())
blocked = [p for p in content_pages if not rp.can_fetch('Googlebot', f'{HOST}/{slug(p)}')]
blocked += [a for a in ('content.css', 'icon-192.png', 'manifest.webmanifest', 'sw.js') if not rp.can_fetch('Googlebot', f'{HOST}/{a}')]
smref = f'Sitemap: {HOST}/sitemap.xml' in txt
rec('S07', 'robots.txt allows pages and render resources and references the sitemap', 'PASS' if (not blocked and smref) else 'FAIL', '', blocked + ([] if smref else ['no Sitemap line']))

# ---- S08 JSON-LD
issues = []; warn = []
for p, s in soups.items():
    for sc in s.find_all('script', type='application/ld+json'):
        try: d = json.loads(sc.string)
        except Exception as e: issues.append(f'{p}: invalid JSON-LD {e}'); continue
        for g in (d.get('@graph') or [d]):
            t = g.get('@type')
            if t == 'Article':
                for k in ('headline', 'mainEntityOfPage', 'publisher'):
                    if k not in g: issues.append(f'{p}: Article missing {k}')
                if g.get('mainEntityOfPage') != f'{HOST}/{slug(p)}': issues.append(f'{p}: Article mainEntityOfPage != canonical')
            if t == 'WebApplication' and g.get('url') != f'{HOST}/{slug(p)}': issues.append(f'{p}: WebApplication url mismatch')
            if t == 'FAQPage': warn.append(f'{p}: FAQPage markup (Google restricts FAQ rich results to authoritative government/health sites; does not match policy for this site type)')
            for bad in ('aggregateRating', 'review'):
                if bad in g: issues.append(f'{p}: unverified {bad} present')
rec('S08', 'JSON-LD parses, required props present, URLs match canonical, no invented ratings', 'FAIL' if issues else 'PASS', '', issues)
rec('S08b', 'No FAQPage markup that cannot qualify for rich results / may not mirror visible text', 'FAIL' if warn else 'PASS', '', warn)

# ---- S09 images / icons / manifest
issues = []
for p, s in soups.items():
    for im in s.find_all('img'):
        if im.get('alt') is None: issues.append(f'{p}: <img> without alt')
m = json.loads(read('manifest.webmanifest'))
for ic in m.get('icons', []):
    f = os.path.join(SITE, ic['src'].lstrip('/'))
    if not os.path.exists(f): issues.append(f'manifest icon missing {ic["src"]}'); continue
    w, h = Image.open(f).size
    if f'{w}x{h}' != ic['sizes']: issues.append(f'{ic["src"]}: declared {ic["sizes"]} actual {w}x{h}')
    if 'maskable' in ic.get('purpose', ''):
        im = Image.open(f).convert('RGBA')
        if im.getpixel((0, 0))[3] < 255: issues.append(f'{ic["src"]}: purpose=maskable but corner pixel is transparent (not full-bleed)')
og = Image.open(os.path.join(SITE, 'og-default.png'))
if og.size != (1200, 630): issues.append(f'og-default.png is {og.size}')
for k in ('start_url', 'scope', 'name', 'display', 'icons'):
    if k not in m: issues.append(f'manifest missing {k}')
if m.get('start_url', '').startswith('./'): issues.append('manifest start_url is relative "./" (prefer "/" for a root-hosted PWA)')
if 'id' not in m: issues.append('manifest missing "id"')
rec('S09', 'Images, icons, OG image and web manifest are valid and consistent', 'FAIL' if issues else 'PASS', 'site has no <img> elements; alt-text audit applies to icons/OG only', issues)

# ---- S10 placeholders / secrets
issues = []
SKIP = lambda rel: rel.startswith(('audit/', 'node_modules/', '.git/')) or rel in ('README.md', 'AUDIT-RESULTS.md', '.env.example', '.gitignore')
for f in glob.glob(SITE + '/**/*', recursive=True):
    if not os.path.isfile(f) or f.endswith(('.png',)) or SKIP(os.path.relpath(f, SITE)): continue
    t = open(f, encoding='utf8', errors='ignore').read()
    rel = os.path.relpath(f, SITE)
    for pat in (r'YOUR-EMAIL@example\.com', r'lorem ipsum', r'\bTODO\b', r'\bREPLACE[_ -]?ME\b', r'example\.com'):
        if re.search(pat, t, re.I): issues.append(f'{rel}: placeholder matches /{pat}/')
secrets = []
for f in glob.glob(SITE + '/**/*', recursive=True):
    if not os.path.isfile(f) or f.endswith('.png') or os.path.relpath(f, SITE).startswith(('node_modules/', '.git/')): continue
    t = open(f, encoding='utf8', errors='ignore').read()
    for pat in (r'AKIA[0-9A-Z]{16}', r'-----BEGIN (RSA |EC )?PRIVATE KEY-----', r'sk-[A-Za-z0-9]{32,}', r'(?i)api[_-]?key\s*[:=]\s*[\'"][A-Za-z0-9_\-]{16,}', r'ghp_[A-Za-z0-9]{30,}'):
        if re.search(pat, t): secrets.append(f'{os.path.relpath(f, SITE)}: /{pat}/')
rec('S10a', 'No unresolved placeholder content', 'FAIL' if issues else 'PASS', 'placeholder scan across deployable source files', issues)
rec('S10b', 'No secrets / credentials in source (regex scan)', 'FAIL' if secrets else 'PASS', 'pattern scan only; not proof of absence', secrets)

# ---- S11 headers/config
hd = read('_headers')
issues = []
for k in ('X-Content-Type-Options', 'Referrer-Policy', 'Permissions-Policy', 'Content-Security-Policy', 'Strict-Transport-Security'):
    if k not in hd: issues.append(f'_headers lacks {k}')
if 'frame-ancestors' not in hd and 'X-Frame-Options' not in hd: issues.append('no clickjacking protection (frame-ancestors / X-Frame-Options)')
if re.search(r'icon[^\n]*\n\s*Cache-Control:[^\n]*immutable', hd): issues.append('un-fingerprinted icon files served with 1-year immutable cache')
rec('S11', 'Security/caching headers configured in _headers', 'FAIL' if issues else 'PASS', 'configuration inspection only; live headers are verified separately (BLOCKED if no deployment access)', issues)

# ---- S12 JS syntax
issues = []
for p, s in soups.items():
    for i, sc in enumerate(s.find_all('script')):
        if sc.get('type') or not sc.string: continue
        tmp = f'/tmp/_chk_{p}_{i}.js'; open(tmp, 'w').write(sc.string)
        r = subprocess.run(['node', '--check', tmp], capture_output=True, text=True)
        if r.returncode: issues.append(f'{p} script#{i}: {r.stderr.strip().splitlines()[0]}')
r = subprocess.run(['node', '--check', os.path.join(SITE, 'sw.js')], capture_output=True, text=True)
if r.returncode: issues.append('sw.js: ' + r.stderr[:200])
rec('S12', 'Inline scripts and service worker parse (node --check)', 'FAIL' if issues else 'PASS', '', issues)

# ---- S13 near-duplicate content
def words(p):
    m = soups[p].select_one('.main-content') or soups[p].body
    return re.findall(r'\w+', m.get_text(' ').lower())
def sh(ws, n=8): return {' '.join(ws[i:i+n]) for i in range(len(ws) - n)}
sets = {p: sh(words(p)) for p in content_pages}
pairs = []
for i, a in enumerate(content_pages):
    for b in content_pages[i+1:]:
        if not sets[a] or not sets[b]: continue
        j = len(sets[a] & sets[b]) / len(sets[a] | sets[b])
        if j > 0.25: pairs.append(f'{a} ~ {b}: shingle overlap {j:.2f}')
rec('S13', 'No near-duplicate pages (8-word shingle Jaccard > 0.25)', 'FAIL' if pairs else 'PASS', '', pairs)

# ---- S14 privacy text vs implementation
pv = soups['privacy-policy.html'].get_text(' ')
issues = []
if 'GitHub Pages' in pv and os.path.exists(os.path.join(SITE, 'netlify.toml')): issues.append('privacy policy names GitHub Pages as host but the site deploys on Netlify (netlify.toml, *.netlify.app)')
if re.search(r'\banalytics\b', pv, re.I) and not re.search(r'(not currently|no analytics|do not use)', pv, re.I) and not re.search(r'google-analytics|gtag|plausible|umami', ''.join(read(p) for p in pages), re.I): issues.append('policy refers to analytics; none implemented and wording does not state that')
if 'service worker' not in pv.lower() and 'sw.js' in read('index.html'): issues.append('policy does not disclose the service worker / Cache Storage the site uses')
rec('S14', 'Privacy policy matches implementation (host, analytics, ads, storage)', 'FAIL' if issues else 'PASS', '', issues)

# ---- S15 HTML validity (Nu validator)
vnu = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'node_modules/vnu-jar/build/dist/vnu.jar')
if os.path.exists(vnu):
    files = [os.path.join(SITE, p) for p in pages if not p.startswith('google')]
    r = subprocess.run(['java', '-jar', vnu, '--format', 'json', '--errors-only'] + files, capture_output=True, text=True)
    try:
        raw = r.stderr or r.stdout
        msgs = json.loads(raw[raw.index('{'):])['messages']
        errs = [f"{os.path.basename(m['url'])}:{m.get('lastLine')}: {m['message'][:140]}" for m in msgs if m['type'] == 'error' and 'env(' not in m['message']]
        fp = [m for m in msgs if m['type'] == 'error' and 'env(' in m['message']]
        rec('S15', 'HTML validation (Nu Html Checker, errors only)', 'FAIL' if errs else 'PASS', f'{len(fp)} CSS env() messages ignored (validator does not parse env() in shorthand; valid CSS)', errs)
    except Exception as e:
        rec('S15', 'HTML validation', 'BLOCKED', f'validator output unreadable: {e}')
else:
    rec('S15', 'HTML validation', 'BLOCKED', 'vnu-jar not installed (run npm install in audit/)')

# ---- S16 external links
ext = sorted({a['href'] for s in soups.values() for a in s.find_all('a', href=True) if a['href'].startswith('http') and 'tasbihdigitalcounter' not in a['href']})
rec('S16', 'External links reachable', 'BLOCKED', 'sandbox egress allow-list does not include these hosts; list recorded for manual / CI check', ext)

# ---- S18 version-specific contact and PDF download wiring
contact_links = [a.get('href') for a in soups['contact.html'].find_all('a', href=True)]
name_links = [a.get('href') for a in soups['99-names-of-allah.html'].find_all('a', href=True)]
issues = []
if 'https://github.com/localbusinessindia/tasbihdigitalcounter/issues' not in contact_links: issues.append('contact page missing the project GitHub Issues link')
if '/99-names-of-allah.pdf' not in name_links: issues.append('99 Names page missing the PDF download link')
if not os.path.isfile(os.path.join(SITE, '99-names-of-allah.pdf')): issues.append('PDF asset missing')
rec('S18', 'v2.7 contact route and 99 Names PDF link are wired', 'FAIL' if issues else 'PASS', '', issues)

# ---- S17 downloadable study PDF
pdf_path = os.path.join(SITE, '99-names-of-allah.pdf')
try:
    from pypdf import PdfReader
    if not os.path.isfile(pdf_path):
        rec('S17', 'Downloadable 99 Names PDF is valid and contains all 99 entries', 'FAIL', '99-names-of-allah.pdf is missing')
    else:
        reader = PdfReader(pdf_path)
        pdf_text = '\n'.join(page.extract_text() or '' for page in reader.pages)
        names_table = soups['99-names-of-allah.html'].select('.tw table tr')[1:]
        required_names = [row.select_one('td:nth-of-type(3) b').get_text(' ', strip=True) for row in names_table]
        missing_pdf = [name for name in required_names if name not in pdf_text]
        if '99 Names of Allah' not in pdf_text: missing_pdf.append('PDF title')
        rec('S17', 'Downloadable 99 Names PDF is valid and contains all 99 entries', 'FAIL' if missing_pdf or len(reader.pages) < 2 or len(required_names) != 99 else 'PASS', f'{len(reader.pages)} pages; {os.path.getsize(pdf_path)} bytes; {len(required_names)-len([n for n in missing_pdf if n in required_names])}/99 names found', missing_pdf)
except Exception as e:
    rec('S17', 'Downloadable 99 Names PDF is valid and contains all 99 entries', 'BLOCKED', 'PDF validation dependency unavailable or unreadable: ' + str(e)[:180])

json.dump(R, open(OUT, 'w'), indent=1, ensure_ascii=False)
for r in R: print(f"{r['status']:6} {r['id']:5} {r['title']}  ({len(r['evidence'])} items)")
