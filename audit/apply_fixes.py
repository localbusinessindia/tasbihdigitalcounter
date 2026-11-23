#!/usr/bin/env python3
"""Records the exact source transformations applied during the audit (kept for traceability).
Run once against a pristine copy of the original project: python3 apply_fixes.py <site_dir>
"""
import glob, json, os, re, sys
from PIL import Image
SITE = os.path.abspath(sys.argv[1]); TODAY = '2026-11-14'
def rd(p): return open(os.path.join(SITE, p), encoding='utf8').read()
def wr(p, s): open(os.path.join(SITE, p), 'w', encoding='utf8').write(s)
def sub1(s, old, new, label):
    assert s.count(old) == 1, f'{label}: expected exactly 1 match, found {s.count(old)}'
    return s.replace(old, new)

pages = [f for f in os.listdir(SITE) if f.endswith('.html') and not f.startswith('google')]
for p in pages:
    s = rd(p)
    # 1. internal links -> canonical clean URLs (avoids a 301 hop per click)
    s = re.sub(r'href="((?!google)[a-z0-9-]+)\.html"', lambda m: 'href="/' + m.group(1) + '"', s)
    s = s.replace('href="content.css"', 'href="/content.css"')
    s = s.replace("register('sw.js')", "register('/sw.js')")
    # 2. charset declaration first in <head>
    s2 = re.sub(r'<meta charset="utf-8"\s*/?>', '', s, count=1, flags=re.I)
    assert s2 != s, p
    s = re.sub(r'<head>\s*', '<head>\n<meta charset="utf-8">\n', s2, count=1)
    # 3. FAQPage JSON-LD removal (not eligible for rich results on this site type; index copy did not mirror visible text)
    def fix_ld(m):
        d = json.loads(m.group(1))
        g = [x for x in d.get('@graph', [d]) if x.get('@type') != 'FAQPage']
        for x in g:
            if x.get('@type') == 'WebApplication' and 'description' not in x:
                x['description'] = 'Free online tasbih, tasbeeh and dhikr counter with 33, 66, 99, 100 and custom goals, guided after-salah and bedtime routines, and local progress saving.'
        d['@graph'] = g
        return '<script type="application/ld+json">' + json.dumps(d, ensure_ascii=False, separators=(',', ':')) + '</script>'
    s = re.sub(r'<script type="application/ld\+json">(.*?)</script>', fix_ld, s, flags=re.S)
    # 4. keyboard-reachable scroll containers for tables
    s = s.replace('<div class="table-wrap">', '<div class="table-wrap" tabindex="0" role="region" aria-label="Table (scrolls sideways on small screens)">')
    s = s.replace('<div class="tw">', '<div class="tw" tabindex="0" role="region" aria-label="Table (scrolls sideways on small screens)">')
    wr(p, s)
# 404 page: same charset fix + viewport-fit parity
s = rd('404.html'); s = re.sub(r'<meta charset="utf-8">', '', s, count=1); s = s.replace('<html lang="en"><head>', '<html lang="en"><head>\n<meta charset="utf-8">', 1); wr('404.html', s)

# ---- index.html behavioural/a11y fixes
s = rd('index.html')
s = sub1(s, "@media(prefers-reduced-motion:reduce)", "main a{color:var(--ac)}\n@media(prefers-reduced-motion:reduce)", 'link colour')
s = sub1(s, '<label><button onclick="this.nextElementSibling.click()">Import backup</button><input accept=".json" hidden="" id="imp" type="file"/></label>',
         '<button id="impbtn" type="button">Import backup</button><input accept=".json,application/json" aria-label="Choose a backup file to import" hidden id="imp" type="file">', 'import control')
s = sub1(s, 'class="small" style="text-align:center;margin:16px 0 0"', 'style="text-align:center;margin:16px 0 0;color:var(--mu);font-size:.88rem"', 'undefined .small')
# state loading + validation
s = sub1(s, "try{Object.assign(S,JSON.parse(localStorage.getItem('tdc')||'{}'))}catch(e){}",
"""function clean(o){
 if(!o||typeof o!=='object'||Array.isArray(o))throw new Error('bad backup');
 const R={},n=(v,max)=>Number.isFinite(v)&&v>=0?Math.min(Math.floor(v),max):null,dre=/^\\d{4}-\\d{1,2}-\\d{1,2}$/;
 for(const k of['life','today','streak']){const v=n(o[k],1e9);if(v!==null)R[k]=v}
 {const v=n(o.goal,1e5);if(v!==null)R.goal=v}
 for(const k of['sun','sleep','vib','snd','wake'])if(k in o)R[k]=o[k]?1:0;
 if(o.sun&&o.sleep){R.sun=1;R.sleep=0}
 if(['auto','light','dark'].includes(o.theme))R.theme=o.theme;
 for(const k of['day','last'])if(typeof o[k]==='string'&&(o[k]===''||dre.test(o[k])))R[k]=o[k];
 if(o.c&&typeof o.c==='object'&&!Array.isArray(o.c)){R.c={};for(const k of Object.keys(o.c)){const v=n(o.c[k],1e9);if(/^(?:[a-z]{3}|c\\d{1,16})$/.test(k)&&v!==null)R.c[k]=v}}
 if(Array.isArray(o.custom))R.custom=o.custom.filter(x=>Array.isArray(x)&&typeof x[0]==='string'&&/^c\\d{1,16}$/.test(x[0])&&typeof x[2]==='string'&&x[2].trim()).slice(0,200).map(x=>[x[0],'',x[2].trim().slice(0,60),'',0]);
 if(typeof o.cur==='string')R.cur=o.cur;
 return R}
try{Object.assign(S,clean(JSON.parse(localStorage.getItem('tdc')||'{}')))}catch(e){}
if(!D.some(x=>x[0]===S.cur)&&!S.custom.some(x=>x[0]===S.cur))S.cur='sub';""", 'localStorage load')
s = sub1(s, "function fill(){$('#dsel').innerHTML=D.concat(S.custom).map(x=>`<option value=\"${x[0]}\">${x[2].replace(/</g,'&lt;')}</option>`).join('');$('#dsel').value=S.cur}",
"function fill(){const sel=$('#dsel');sel.textContent='';D.concat(S.custom).forEach(x=>{const o=document.createElement('option');o.value=x[0];o.textContent=x[2];sel.appendChild(o)});sel.value=S.cur}", 'fill')
s = sub1(s, "$('#st').textContent=S.today;$('#sl').textContent=S.life;$('#ss').textContent=S.streak;",
"$('#st').textContent=S.today;$('#sl').textContent=S.life;$('#ss').textContent=(S.last===dstr()||S.last===dstr(-1))?S.streak:0;\n $('#tap').setAttribute('aria-label','Count '+n+(g?' of '+g:', no limit')+'. Tap to add one');", 'streak+label')
s = sub1(s, "document.addEventListener('keydown',e=>{if((e.key==' '||e.key=='Enter')&&!/^(SELECT|INPUT|TEXTAREA|BUTTON)$/.test(e.target.tagName)){e.preventDefault();tap()}});",
"document.addEventListener('keydown',e=>{if(e.repeat||e.ctrlKey||e.metaKey||e.altKey)return;if((e.key==' '||e.key=='Enter')&&!/^(SELECT|INPUT|TEXTAREA|BUTTON|A|SUMMARY)$/.test(e.target.tagName)&&!e.target.isContentEditable){e.preventDefault();tap()}});", 'keydown')
s = sub1(s, "$('#exp').onclick=()=>{const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(S)],{type:'application/json'}));a.download='tasbih-backup.json';a.click()};",
"$('#exp').onclick=()=>{const a=document.createElement('a'),u=URL.createObjectURL(new Blob([JSON.stringify(S)],{type:'application/json'}));a.href=u;a.download='tasbih-backup.json';document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(u),1500)};", 'export')
s = sub1(s, "$('#imp').onchange=e=>{const f=e.target.files[0];if(f)f.text().then(t=>{try{Object.assign(S,JSON.parse(t));fill();render()}catch(x){alert('This file is not a valid backup.')}})};",
"$('#impbtn').onclick=()=>$('#imp').click();\n$('#imp').onchange=e=>{const f=e.target.files[0];if(!f)return;if(f.size>1e6){alert('This file is too large to be a backup.');e.target.value='';return}f.text().then(t=>{try{const c=clean(JSON.parse(t));Object.assign(S,c);if(!D.some(x=>x[0]===S.cur)&&!S.custom.some(x=>x[0]===S.cur))S.cur='sub';fill();render();$('#msg').textContent='Backup imported.'}catch(x){alert('This file is not a valid backup.')}e.target.value=''})};", 'import')
wr('index.html', s)

# ---- privacy policy: accurate host, ads/analytics wording, storage disclosure
s = rd('privacy-policy.html')
s = sub1(s, 'our hosting provider (GitHub Pages) may log', 'our hosting provider (Netlify) may log', 'host')
s = sub1(s, '<p>If you are in the European Economic Area, the United Kingdom or Switzerland, you may be shown a consent message and can choose how cookies are used.</p>',
 '<p>No advertising or advertising cookies are active on the site at the time of this update. If ads are added, this policy will be updated first, and where the law requires it a consent choice will be offered before advertising cookies are set (for example in the European Economic Area, the United Kingdom and Switzerland).</p>', 'consent')
s = sub1(s, '<p>We may use privacy-respecting analytics to understand which pages are used. This data is aggregated and does not identify you.</p>',
 '<p>The site does not currently run analytics. If privacy-respecting, aggregated analytics are added in future, this policy will be updated first.</p>', 'analytics')
s = sub1(s, '<h2>Children</h2>', '<h2>Offline files (service worker)</h2><p>To let the counter and guides work offline, the site installs a service worker that stores copies of its own pages and images in your browser\'s cache storage. These copies contain no personal data and are replaced when the site is updated. Clearing this site\'s data in your browser removes them.</p>\n<h2>Children</h2>', 'sw disclosure')
s = sub1(s, '<p><em>Last updated: November 10, 2026</em></p>', f'<p><em>Last updated: November 14, 2026</em></p>', 'date')
wr('privacy-policy.html', s)

# ---- full-bleed maskable icon (original icon has transparent rounded corners)
im = Image.open(os.path.join(SITE, 'icon-512.png')).convert('RGBA'); bg = Image.new('RGBA', im.size, (15, 81, 50, 255)); bg.alpha_composite(im)
bg.convert('RGB').save(os.path.join(SITE, 'icon-maskable-512.png'), optimize=True)
m = json.loads(rd('manifest.webmanifest'))
m['id'] = '/'; m['start_url'] = '/'; m['scope'] = '/'; m['lang'] = 'en'; m['categories'] = ['lifestyle', 'utilities']
m['icons'][2]['src'] = '/icon-maskable-512.png'
wr('manifest.webmanifest', json.dumps(m, indent=2) + '\n')

# ---- sitemap lastmod (all pages changed in this audit)
s = rd('sitemap.xml'); s = re.sub(r'<lastmod>[^<]+</lastmod>', f'<lastmod>{TODAY}</lastmod>', s); wr('sitemap.xml', s)

# ---- service worker: bump cache, precache maskable icon, never cache non-OK navigations
s = rd('sw.js')
s = s.replace("tasbih-digital-counter-v8", "tasbih-digital-counter-v9").replace('"/icon-512.png", ', '"/icon-512.png", "/icon-maskable-512.png", ')
s = sub1(s, "event.respondWith(fetch(request).then(response => {\n      const copy = response.clone(); caches.open(CACHE_NAME).then(cache => cache.put(request, copy)); return response;",
            "event.respondWith(fetch(request).then(response => {\n      if (response.ok && !response.redirected) { const copy = response.clone(); caches.open(CACHE_NAME).then(cache => cache.put(request, copy)); } return response;", 'sw nav')
s = sub1(s, "event.respondWith(caches.match(request).then(cached => cached || fetch(request).then(response => {\n    const copy = response.clone(); caches.open(CACHE_NAME).then(cache => cache.put(request, copy)); return response;",
            "event.respondWith(caches.match(request).then(cached => cached || fetch(request).then(response => {\n    if (response.ok) { const copy = response.clone(); caches.open(CACHE_NAME).then(cache => cache.put(request, copy)); } return response;", 'sw assets')
wr('sw.js', s)

# ---- _headers
wr('_headers', """/*
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), microphone=(), geolocation=()
  Strict-Transport-Security: max-age=31536000
  Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; manifest-src 'self'; worker-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'
/sw.js
  Cache-Control: public, max-age=0, must-revalidate
/index.html
  Cache-Control: public, max-age=0, must-revalidate
/manifest.webmanifest
  Cache-Control: public, max-age=0, must-revalidate
/icon.svg
  Cache-Control: public, max-age=86400
/icon-192.png
  Cache-Control: public, max-age=86400
/icon-512.png
  Cache-Control: public, max-age=86400
/icon-maskable-512.png
  Cache-Control: public, max-age=86400
/og-default.png
  Cache-Control: public, max-age=86400
""")
print('fixes applied')
