#!/usr/bin/env python3
"""Browser-level audit (Chromium via Playwright) against a LOCAL Netlify-emulating server.
Usage: python3 browser_tests.py <site_dir> <out.json> [port]
Lab/emulated results only: no real devices, no Firefox/WebKit (not installed here), no live deployment.
"""
import http.client, json, os, re, statistics, subprocess, sys, time, traceback
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.abspath(sys.argv[1]); OUT = sys.argv[2]; PORT = int(sys.argv[3]) if len(sys.argv) > 3 else 8802
BASE = f'http://127.0.0.1:{PORT}'
AXE = os.path.join(HERE, 'node_modules/axe-core/axe.min.js')
R = []
def rec(cid, title, status, detail='', evidence=None):
    R.append({'id': cid, 'title': title, 'status': status, 'detail': detail, 'evidence': evidence or []})
    print(f'{status:7} {cid:5} {title}' + (f'  [{len(evidence or [])}]' if evidence else ''), flush=True)

def run(cid, title):
    def deco(fn):
        try:
            ev, detail = fn()
            rec(cid, title, 'FAIL' if ev else 'PASS', detail, ev)
        except Exception as e:
            rec(cid, title, 'FAIL', 'HARNESS/TEST ERROR: ' + repr(e)[:300], [traceback.format_exc()[-600:]])
        return fn
    return deco

srv = subprocess.Popen([sys.executable, os.path.join(HERE, 'serve.py'), SITE, str(PORT)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.0)

def fetch_url(path, method='GET'):
    c = http.client.HTTPConnection('127.0.0.1', PORT, timeout=10)
    c.request(method, path); r = c.getresponse(); body = r.read()
    return r.status, dict(r.getheaders()), body

sitemap = re.findall(r'<loc>([^<]+)</loc>', open(os.path.join(SITE, 'sitemap.xml'), encoding='utf8').read())
routes = [urlsplit(u).path or '/' for u in sitemap]

try:
    # ---------- HTTP layer (emulated) ----------
    @run('B01', 'Every sitemap URL returns 200 directly (no redirect), .html aliases 301 once, unknown path 404')
    def _():
        ev = []
        for r in routes:
            s, h, _b = fetch_url(r)
            if s != 200: ev.append(f'{r} -> {s}')
        for r in routes:
            if r == '/': continue
            s, h, _b = fetch_url(r + '.html')
            if s != 301 or urlsplit(h.get('Location', '')).path != r: ev.append(f'{r}.html -> {s} {h.get("Location")}')
        s, h, b = fetch_url('/definitely-not-a-page')
        if s != 404 or b'noindex' not in b: ev.append(f'404 behaviour: {s}')
        s, h, _b = fetch_url('/index.html')
        if s != 301: ev.append(f'/index.html -> {s}')
        for u in ('/README.md', '/README-DEPLOY.md', '/AUDIT-RESULTS.md', '/audit/serve.py', '/audit/results/browser_after.json', '/.env.example'):
            s, h, _b = fetch_url(u)
            if s != 404: ev.append(f'{u} is publicly reachable ({s}); project/audit files must not be published')
        return ev, f'{len(routes)} sitemap routes; server is an emulation of Netlify rules, not Netlify itself'

    @run('B02', 'Service-worker precache URLs all return 200 with no redirect')
    def _():
        sw = open(os.path.join(SITE, 'sw.js'), encoding='utf8').read()
        urls = re.findall(r'["\'](/[^"\']*)["\']', sw.split('PRECACHE_URLS')[1].split('];')[0])
        ev = []
        for u in urls:
            s, h, _b = fetch_url(u)
            if s != 200: ev.append(f'{u} -> {s}')
        return ev, f'{len(urls)} URLs'

    @run('B03', 'Response headers: nosniff, referrer-policy, CSP, HSTS, frame protection, caching rules on key URLs')
    def _():
        ev = []
        for u in ('/', '/about', '/icon-192.png', '/sw.js'):
            s, h, _b = fetch_url(u)
            hl = {k.lower(): v for k, v in h.items()}
            for k in ('x-content-type-options', 'referrer-policy', 'content-security-policy', 'strict-transport-security'):
                if k not in hl: ev.append(f'{u}: missing {k}')
            if 'frame-ancestors' not in hl.get('content-security-policy', '') and 'x-frame-options' not in hl: ev.append(f'{u}: no frame protection')
        s, h, _b = fetch_url('/icon-192.png')
        if 'immutable' in h.get('Cache-Control', ''): ev.append('/icon-192.png is immutable (not fingerprinted)')
        s, h, _b = fetch_url('/sw.js')
        if 'max-age=0' not in h.get('Cache-Control', ''): ev.append('/sw.js must be revalidated')
        return ev, 'headers come from _headers as interpreted by the local emulator; real Netlify headers are BLOCKED (no live access)'

    with sync_playwright() as pw:
        launch_opts = {'args': ['--no-sandbox']}
        if os.environ.get('CHROMIUM_PATH'): launch_opts['executable_path'] = os.environ['CHROMIUM_PATH']
        br = pw.chromium.launch(**launch_opts)
        def ctx(**kw):
            kw.setdefault('service_workers', 'block'); kw.setdefault('viewport', {'width': 1366, 'height': 768})
            return br.new_context(**kw)

        # ---------- console / network health on every page ----------
        @run('B04', 'No console errors, page errors, CSP violations or failed requests on any route')
        def _():
            c = ctx(); ev = []
            for r in routes + ['/definitely-not-a-page']:
                p = c.new_page(); errs = []
                p.on('console', lambda m, errs=errs, r=r: errs.append(m.text) if m.type in ('error', 'warning') and 'blocked by Playwright' not in m.text and not (r == '/definitely-not-a-page' and '404' in m.text) else None)
                p.on('pageerror', lambda e, errs=errs: errs.append('pageerror: ' + str(e)))
                p.on('requestfailed', lambda q, errs=errs: errs.append('requestfailed ' + q.url))
                p.on('response', lambda rs, errs=errs, r=r: errs.append(f'HTTP {rs.status} {rs.url}') if rs.status >= 400 and r != '/definitely-not-a-page' else None)
                p.goto(BASE + r); p.wait_for_load_state('networkidle')
                ev += [f'{r}: {e}' for e in errs]; p.close()
            c.close(); return ev, f'{len(routes)+1} routes loaded in Chromium'

        # ---------- homepage functional tests ----------
        def home(c=None, url='/', **kw):
            c = c or ctx(**kw); p = c.new_page(); p.on('dialog', lambda d: d.accept()); p.goto(BASE + url); return c, p
        num = lambda p: int(p.inner_text('#n'))

        @run('B05', 'Counter core: tap, undo, reset, goal buttons, dhikr select, ring progress, persistence')
        def _():
            c, p = home(); ev = []
            for _i in range(5): p.click('#tap')
            if num(p) != 5: ev.append(f'5 taps -> {num(p)}')
            p.click('#minus')
            if num(p) != 4: ev.append('undo failed')
            p.click('#minus'); p.click('#minus'); p.click('#minus'); p.click('#minus'); p.click('#minus')
            if num(p) != 0: ev.append(f'undo below zero -> {num(p)}')
            if p.inner_text('#st') != '0' and int(p.inner_text('#st')) < 0: ev.append('negative today')
            for g in ('33', '66', '99', '100'):
                p.click(f'#goals [data-g="{g}"]')
                if p.inner_text('#g') != f'of {g}': ev.append(f'goal {g} -> {p.inner_text("#g")}')
            p.click('#goals [data-g="0"]')
            if p.inner_text('#g') != 'no limit': ev.append('infinity goal label')
            p.select_option('#dsel', 'ast')
            if p.inner_text('#tr') != 'Astaghfirullah' or p.inner_text('#g') != 'of 100': ev.append('select dhikr did not set text/goal')
            for _i in range(25): p.click('#tap')
            p.wait_for_timeout(500)
            off = float(p.evaluate("getComputedStyle(document.querySelector('#ring')).strokeDashoffset.replace('px','')"))
            if abs(off - 565.5 * 0.75) > 2: ev.append(f'ring offset {off} expected ~{565.5*.75:.1f} at 25/100')
            p.reload()
            if num(p) != 25 or p.input_value('#dsel') != 'ast': ev.append('state not persisted across reload')
            p.click('#reset')
            if num(p) != 0: ev.append('reset failed')
            c.close(); return ev, ''

        @run('B06', 'Goal completion + custom goal: input validation (valid, 0, text, negative, >100000, cancel)')
        def _():
            ev = []; c = ctx(); p = c.new_page()
            def setgoal(val):
                p.once('dialog', lambda d: d.accept(val) if val is not None else d.dismiss()); p.click('#cg')
            p.goto(BASE); setgoal('7'); 
            if p.inner_text('#g') != 'of 7': ev.append('custom goal 7 not applied')
            for _i in range(7): p.click('#tap')
            if 'Goal reached' not in p.inner_text('#msg'): ev.append(f'no completion message: {p.inner_text("#msg")!r}')
            for bad in ('0', 'abc', '-5', '100001', '', None):
                before = p.inner_text('#g'); setgoal(bad)
                if p.inner_text('#g') != before: ev.append(f'invalid goal {bad!r} changed goal to {p.inner_text("#g")}')
            setgoal('100000')
            if p.inner_text('#g') != 'of 100000': ev.append('upper boundary 100000 rejected')
            c.close(); return ev, ''

        @run('B07', 'After-salah 33-33-34 and bedtime 34-33-33 routines: sequence, goals, completion, deep links')
        def _():
            ev = []
            for url, seq, label in (('/?routine=after-salah', [('SubhanAllah', 33), ('Alhamdulillah', 33), ('Allahu Akbar', 34)], 'After-salah'),
                                    ('/?routine=bedtime', [('Allahu Akbar', 34), ('SubhanAllah', 33), ('Alhamdulillah', 33)], 'Bedtime')):
                c, p = home(url=url)
                for i, (name, n) in enumerate(seq):
                    if p.inner_text('#tr') != name or p.inner_text('#g') != f'of {n}': ev.append(f'{label} step {i}: {p.inner_text("#tr")} {p.inner_text("#g")} expected {name} of {n}')
                    p.evaluate("n=>{const b=document.querySelector('#tap');for(let i=0;i<n;i++)b.click()}", n)
                if 'complete' not in p.inner_text('#msg').lower(): ev.append(f'{label}: no completion msg: {p.inner_text("#msg")!r}')
                if p.get_attribute('#sun', 'aria-pressed') != 'false' or p.get_attribute('#sleep', 'aria-pressed') != 'false': ev.append(f'{label}: mode buttons not released')
                c.close()
            c, p = home(url='/?dhikr=ast&goal=100')
            if p.inner_text('#tr') != 'Astaghfirullah' or p.inner_text('#g') != 'of 100': ev.append('?dhikr=ast&goal=100 deep link')
            c.close(); c, p = home(url='/?dhikr=bogus&goal=-3&routine=zzz')
            if p.inner_text('#tr') != 'SubhanAllah': ev.append('bogus query params changed state')
            c.close(); return ev, ''

        @run('B08', 'Export backup downloads valid JSON; import restores it; invalid / hostile backups are rejected or sanitised and do not break the app')
        def _():
            ev = []; c = ctx(); p = c.new_page(); errs = []
            p.on('pageerror', lambda e: errs.append(str(e))); p.on('dialog', lambda d: d.accept()); p.goto(BASE)
            for _i in range(3): p.click('#tap')
            with p.expect_download() as dl: p.click('#exp')
            path = dl.value.path(); data = json.load(open(path))
            if data.get('c', {}).get('sub') != 3: ev.append(f'export content wrong: {data.get("c")}')
            p.click('#reset')
            p.set_input_files('#imp', files=[{'name': 'b.json', 'mimeType': 'application/json', 'buffer': json.dumps(data).encode()}])
            p.wait_for_timeout(200)
            if num(p) != 3: ev.append(f'import did not restore count (got {num(p)})')
            hostile = [
              {'custom': 'abc'}, {'c': None}, {'goal': 'x', 'life': 'y'}, {'cur': {'a': 1}}, [1, 2], 'str', {'custom': [['q" onfocus="window.__xss=1" x="', '', 'evil', '', 0]], 'cur': 'q" onfocus="window.__xss=1" x="'},
              {'custom': [['c1', '', '<img src=x onerror=window.__xss=1>', '', 0]], 'cur': 'c1'}]
            for i, h in enumerate(hostile):
                p.set_input_files('#imp', files=[{'name': f'h{i}.json', 'mimeType': 'application/json', 'buffer': json.dumps(h).encode()}]); p.wait_for_timeout(120)
                if p.evaluate("[...document.querySelectorAll('#dsel option')].some(o=>[...o.attributes].some(a=>a.name.startsWith('on')))"): ev.append(f'payload {i}: imported id injected an event-handler attribute into <option>')
                if p.evaluate("document.querySelector('#dsel img')"): ev.append(f'payload {i}: imported name injected an <img> element')
            p.set_input_files('#imp', files=[{'name': 'bad.json', 'mimeType': 'application/json', 'buffer': b'not json{'}]); p.wait_for_timeout(120)
            if p.evaluate('window.__xss'): ev.append('XSS flag set by imported data')
            p.reload(); p.wait_for_timeout(200)
            try:
                p.click('#tap'); 
            except Exception as e: ev.append('app unusable after hostile import: ' + str(e)[:100])
            if errs: ev.append('uncaught page errors after hostile imports: ' + '; '.join(sorted(set(errs))[:3]))
            c.close(); return ev, 'hostile payloads: wrong types, arrays, strings, attribute-injection ids, markup in names'

        @run('B09', 'Custom dhikr: add, select, count; markup in names rendered as text')
        def _():
            ev = []; c = ctx(); p = c.new_page(); p.goto(BASE)
            q = ['<b>My</b> dhikr & "x"', '33']; p.on('dialog', lambda d: d.accept(q.pop(0) if q else '')); p.click('#add')
            if p.inner_text('#tr') != '<b>My</b> dhikr & "x"': ev.append(f'name shown as {p.inner_text("#tr")!r}')
            if p.evaluate("document.querySelectorAll('#dsel b').length"): ev.append('markup injected into select')
            p.click('#tap')
            if num(p) != 1: ev.append('custom dhikr cannot be counted')
            before = p.locator('#dsel option').count(); q.append('   '); p.click('#add')
            if p.locator('#dsel option').count() != before: ev.append(f'blank name created an entry ({p.locator("#dsel option").count()} options)')
            c.close(); return ev, ''

        @run('B10', 'Keyboard: Enter on links/summary is NOT hijacked by the counter; Space/Enter on page counts; key-repeat ignored')
        def _():
            ev = []; c, p = home()
            p.focus('a[href*="routine=bedtime"]')
            try:
                with p.expect_navigation(timeout=3000): p.keyboard.press('Enter')
            except Exception: pass
            if 'routine=bedtime' not in p.url: ev.append('Enter on "Start the bedtime counter" link did not navigate (counter hijacked the key)')
            elif p.inner_text('#tr') != 'Allahu Akbar': ev.append('bedtime deep link navigated but routine did not start')
            c.close(); c, p = home()
            before = num(p); p.focus('summary'); p.keyboard.press('Enter')
            if num(p) != before: ev.append('Enter on FAQ <summary> incremented the counter')
            if not p.evaluate("document.querySelector('details').open"): ev.append('Enter on <summary> did not toggle the FAQ')
            c.close(); c, p = home(); p.focus('body'); p.keyboard.press(' ')
            if num(p) != 1: ev.append('Space on page body should count once')
            p.evaluate("document.dispatchEvent(new KeyboardEvent('keydown',{key:' ',repeat:true,bubbles:true}))")
            if num(p) != 1: ev.append('auto-repeat keydown counted')
            c.close(); return ev, ''

        @run('B11', 'Settings toggles: theme cycle, vibration, sound, keep-awake report state accurately without errors')
        def _():
            ev = []; c = ctx(); p = c.new_page(); errs = []; p.on('pageerror', lambda e: errs.append(str(e))); p.goto(BASE)
            seen = []
            for _i in range(3): p.click('#theme'); seen.append(p.evaluate("document.documentElement.getAttribute('data-theme')"))
            if seen != ['light', 'dark', None]: ev.append(f'theme cycle {seen}')
            for sel in ('#snd', '#wake'):
                a = p.get_attribute(sel, 'aria-pressed'); p.click(sel); b = p.get_attribute(sel, 'aria-pressed')
                if a == b: ev.append(f'{sel} aria-pressed did not change')
            if p.evaluate("typeof navigator.vibrate") == 'function':
                p.click('#vib'); 
                if not p.inner_text('#deviceNote').strip(): ev.append('vibration note empty')
            if errs: ev.append('page errors: ' + '; '.join(errs))
            c.close(); return ev, 'actual vibration hardware cannot be verified in headless Chromium'

        @run('B12', 'Day-streak display does not show a stale streak after a missed day')
        def _():
            c = ctx(); p = c.new_page(); p.goto(BASE)
            p.evaluate("localStorage.setItem('tdc',JSON.stringify({streak:5,last:'2020-1-1',life:50,today:3,day:'2020-1-1'}))"); p.reload()
            shown = p.inner_text('#ss'); c.close()
            return ([f'streak shows {shown} although last activity was in 2020'] if shown != '0' else []), ''

        @run('B13', 'Counter button exposes the current count to assistive tech')
        def _():
            c, p = home(); 
            for _i in range(3): p.click('#tap')
            lab = p.get_attribute('#tap', 'aria-label'); c.close()
            return ([f'aria-label is {lab!r}; does not convey count/goal'] if not re.search(r'3', lab or '') else []), ''

        @run('B14', 'Import control is valid, labelled and keyboard operable (button, not nested in label)')
        def _():
            c, p = home(); ev = []
            if p.evaluate("!!document.querySelector('label button')"): ev.append('<button> nested inside <label> with a file input (invalid HTML, ambiguous name)')
            if not p.evaluate("(()=>{const i=document.querySelector('#imp');return !!(i.getAttribute('aria-label')||document.querySelector('label[for=imp]'))})()"): ev.append('file input has no accessible name')
            c.close(); return ev, ''

        @run('B15', 'Performance stress: 2000 rapid taps counted exactly and handler stays fast')
        def _():
            c, p = home(); ev = []
            t = p.evaluate("(()=>{const b=document.querySelector('#tap');const t0=performance.now();for(let i=0;i<2000;i++)b.click();return performance.now()-t0})()")
            if num(p) != 2000: ev.append(f'count {num(p)} != 2000')
            if t > 4000: ev.append(f'2000 taps took {t:.0f} ms')
            c.close(); return ev, f'2000 synthetic taps in {t:.0f} ms (headless lab, not field data)'

        # ---------- guide pages ----------
        @run('B16', 'islamic-dates table matches the browser Umm al-Qura calendar and weekdays')
        def _():
            c = ctx(); p = c.new_page(); p.goto(BASE + '/islamic-dates'); ev = []
            MON = {'Muharram': 1, 'Safar': 2, 'Rabi al-Awwal': 3, 'Rabi al-Thani': 4, 'Jumada al-Awwal': 5, 'Jumada al-Thani': 6, 'Rajab': 7, "Sha'ban": 8, 'Ramadan': 9, 'Shawwal': 10, "Dhul Qa'dah": 11, 'Dhul Hijjah': 12}
            rows = p.evaluate("[...document.querySelectorAll('table tbody tr')].map(r=>[...r.cells].map(c=>c.innerText))")
            for name, hij, greg in rows:
                wd, d, mon, y = re.match(r'(\w+), (\d+) (\w+) (\d{4})', greg).groups()
                after = 'after sunset' in greg
                got = p.evaluate("""([d,mon,y,add])=>{const dt=new Date(`${d} ${mon} ${y} 12:00:00 UTC`);const w=dt.toLocaleDateString('en-US',{weekday:'long',timeZone:'UTC'});
                  dt.setUTCDate(dt.getUTCDate()+add);const pr=new Intl.DateTimeFormat('en-u-ca-islamic-umalqura',{day:'numeric',month:'numeric',year:'numeric',timeZone:'UTC'}).formatToParts(dt);
                  const g=t=>+pr.find(x=>x.type===t).value;return {w,d:g('day'),m:g('month'),y:g('year')}}""", [d, mon, y, 1 if after else 0])
                if got['w'] != wd: ev.append(f'{name}: {greg} is actually a {got["w"]}')
                hd, hm, hy = re.match(r"(\d+) (.+) (\d+) AH", hij).groups()
                if (got['d'], got['m'], got['y']) != (int(hd), MON[hm], int(hy)): ev.append(f'{name}: page says {hij} on {greg}; Umm al-Qura (browser Intl) gives {got["d"]}/{got["m"]}/{got["y"]}')
            c.close(); return ev, f'{len(rows)} rows compared (evening events compared against next civil day); Intl Umm al-Qura in Chromium {br.version}'

        @run('B17', 'Offline/PWA: service worker installs, precached pages load offline, error pages are not cached')
        def _():
            ev = []; c = br.new_context(viewport={'width': 1366, 'height': 768}); p = c.new_page(); p.goto(BASE + '/')
            p.evaluate('navigator.serviceWorker.ready.then(()=>1)'); p.wait_for_timeout(1500)
            p.goto(BASE + '/no-such-page-xyz'); p.wait_for_timeout(500)
            keys = p.evaluate("caches.keys().then(async ks=>{const out=[];for(const k of ks){const c=await caches.open(k);out.push(...(await c.keys()).map(r=>new URL(r.url).pathname))}return out})")
            if '/no-such-page-xyz' in keys: ev.append('service worker cached a 404 response as a page')
            if not keys: ev.append('cache empty: SW did not install')
            c.set_offline(True)
            for r in ('/', '/about', '/subhanallah', '/islamic-dates'):
                try:
                    p.goto(BASE + r, timeout=5000)
                    if p.locator('h1').count() == 0 or 'not found' in p.inner_text('h1').lower(): ev.append(f'offline {r}: no content')
                except Exception as e: ev.append(f'offline {r}: {str(e)[:80]}')
            try:
                p.goto(BASE + '/'); p.click('#tap'); 
                if num(p) < 1: ev.append('offline counter did not count')
            except Exception as e: ev.append('offline counting: ' + str(e)[:80])
            c.close(); return ev, 'Chromium only'

        # ---------- responsive ----------
        VP = [(320, 568), (375, 812), (430, 932), (768, 1024), (1366, 768), (1920, 1080), (812, 375)]
        @run('B18', 'No horizontal overflow / clipped content on any page at 320, 375, 430, 768, 1366, 1920 and 812x375 landscape')
        def _():
            ev = []
            for (w, h) in VP:
                c = ctx(viewport={'width': w, 'height': h}); p = c.new_page()
                for r in routes + ['/definitely-not-a-page']:
                    p.goto(BASE + r)
                    o = p.evaluate("""()=>{const W=document.documentElement.clientWidth;const bad=[];
                      for(const e of document.querySelectorAll('body *')){const r=e.getBoundingClientRect();if(!r.width||getComputedStyle(e).position==='fixed')continue;
                        if(r.right>W+1||r.left<-1){let a=e,inside=false;while((a=a.parentElement)){const o=getComputedStyle(a).overflowX;if((o==='auto'||o==='scroll'||o==='hidden')&&a!==document.body&&a!==document.documentElement){inside=true;break}}
                          if(!inside&&!getComputedStyle(e).visibility.includes('hidden')&&getComputedStyle(e).left!=='-9999px')bad.push(e.tagName+'.'+e.className+' '+Math.round(r.left)+'..'+Math.round(r.right))}}
                      return {sw:document.documentElement.scrollWidth,W,bad:bad.slice(0,3)}}""")
                    if o['sw'] > o['W'] + 1 or o['bad']: ev.append(f'{w}x{h} {r}: scrollWidth {o["sw"]} > {o["W"]}; {o["bad"]}')
                c.close()
            return ev, f'{len(routes)+1} pages x {len(VP)} viewports (Chromium viewport emulation, not physical devices)'

        @run('B19', 'Home counter workflow completable at 320x568 and 375x812: tap button fully inside viewport after scroll, >=44px')
        def _():
            ev = []
            for (w, h) in ((320, 568), (375, 812)):
                c = ctx(viewport={'width': w, 'height': h}, has_touch=True, is_mobile=True); p = c.new_page(); p.goto(BASE)
                bb = p.locator('#tap').bounding_box()
                if bb['width'] < 44 or bb['height'] < 44: ev.append(f'{w}: tap target {bb["width"]:.0f}x{bb["height"]:.0f}')
                p.tap('#tap'); p.tap('#tap')
                if num(p) != 2: ev.append(f'{w}: touch taps -> {num(p)}')
                if bb['x'] < 0 or bb['x'] + bb['width'] > w: ev.append(f'{w}: tap button outside viewport horizontally')
                for sel in ('#minus', '#reset', '#sun', '#sleep', '#exp', '#cg'):
                    b = p.locator(sel).bounding_box()
                    if b['height'] < 24 or b['width'] < 24: ev.append(f'{w}: {sel} target {b["width"]:.0f}x{b["height"]:.0f} < 24px (WCAG 2.5.8)')
                c.close()
            return ev, 'emulated touch'

        # ---------- accessibility (axe) ----------
        AX = open(AXE, encoding='utf8').read() if os.path.exists(AXE) else None
        def axe(p, tags):
            p.evaluate("document.getAnimations().forEach(a=>{try{a.finish()}catch(e){a.cancel()}})")
            p.add_script_tag(content=AX)
            return p.evaluate("(tags)=>axe.run(document,{runOnly:{type:'tag',values:tags},resultTypes:['violations']}).then(r=>r.violations.map(v=>({id:v.id,impact:v.impact,n:v.nodes.length,t:v.nodes.slice(0,2).map(n=>n.target.join(' ')+' :: '+(n.failureSummary||'').split('\\n').slice(1,2).join(' ').slice(0,120))})))", tags)
        if AX:
            @run('B20', 'axe-core WCAG 2.0/2.1/2.2 A+AA: zero violations on all pages (light, desktop + 375px mobile)')
            def _():
                ev = []
                for (w, h) in ((1366, 768), (375, 812)):
                    c = ctx(viewport={'width': w, 'height': h}, color_scheme='light'); p = c.new_page()
                    for r in routes:
                        p.goto(BASE + r)
                        for v in axe(p, ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa']): ev.append(f'{w}px {r}: {v["id"]} ({v["impact"]}, {v["n"]} nodes) {v["t"]}')
                    c.close()
                return ev, 'automated scan only; not proof of full WCAG compliance'

            @run('B21', 'axe-core WCAG A+AA in dark mode (OS dark and manual dark toggle) on all pages')
            def _():
                ev = []
                c = ctx(color_scheme='dark'); p = c.new_page()
                for r in routes:
                    p.goto(BASE + r)
                    for v in axe(p, ['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa']): ev.append(f'dark {r}: {v["id"]} ({v["n"]} nodes) {v["t"]}')
                c.close()
                c = ctx(color_scheme='light'); p = c.new_page(); p.goto(BASE); p.click('#theme'); p.click('#theme')
                for v in axe(p, ['wcag2a', 'wcag2aa', 'wcag21aa']): ev.append(f'home manual dark: {v["id"]} ({v["n"]}) {v["t"]}')
                # after-count states
                p.click('#goals [data-g="33"]'); p.click('#sun')
                for v in axe(p, ['wcag2aa']): ev.append(f'home manual dark + routine on: {v["id"]} ({v["n"]}) {v["t"]}')
                c.close(); return ev, ''

            @run('B22', 'axe-core best-practice rules (advisory; failures listed, not blocking)')
            def _():
                c = ctx(); p = c.new_page(); ev = []
                for r in routes:
                    p.goto(BASE + r)
                    for v in axe(p, ['best-practice']): ev.append(f'{r}: {v["id"]} ({v["impact"]}, {v["n"]}) {v["t"]}')
                c.close(); R_adv = ev
                return [], 'advisory findings: ' + ('; '.join(sorted({e.split(": ")[1].split(" ")[0] for e in ev})) or 'none')
        else:
            rec('B20', 'axe-core accessibility scan', 'BLOCKED', 'axe-core not installed (npm install in audit/)')

        @run('B23', 'Keyboard: every interactive element on the home page is reachable by Tab and has a visible focus indicator')
        def _():
            c = ctx(); p = c.new_page()
            p.add_init_script("window.__seen=new Set();document.addEventListener('focusin',e=>window.__seen.add(e.target),true)")
            p.goto(BASE); ev = []
            vis = p.evaluate("[...document.querySelectorAll('a[href],button:not([disabled]),select,summary,input:not([hidden])')].filter(e=>e.offsetParent!==null&&getComputedStyle(e).visibility!=='hidden'&&(e.tagName==='SUMMARY'||!e.closest('details:not([open])'))).length")
            for _i in range(vis + 6):
                p.keyboard.press('Tab')
                info = p.evaluate("(()=>{const e=document.activeElement;if(!e||e===document.body)return null;const s=getComputedStyle(e);return {k:e.tagName+'#'+e.id+' '+(e.getAttribute('href')||e.textContent.trim().slice(0,20)),ol:s.outlineStyle,ow:parseFloat(s.outlineWidth),bs:s.boxShadow}})()")
                if info and (info['ol'] == 'none' or info['ow'] == 0) and info['bs'] == 'none': ev.append(f'no focus indicator on {info["k"]}')
            n = p.evaluate('window.__seen.size')
            if n < vis: ev.append(f'Tab reached {n} of {vis} interactive elements')
            c.close(); return sorted(set(ev)), f'{n} focusable elements reached of {vis} visible'

        @run('B24', 'prefers-reduced-motion disables animations/transitions')
        def _():
            c = ctx(reduced_motion='reduce'); p = c.new_page(); p.goto(BASE); ev = []
            d = p.evaluate("(()=>{let m=0;for(const e of document.querySelectorAll('*')){const s=getComputedStyle(e);for(const v of (s.animationDuration+','+s.transitionDuration).split(',')){const n=parseFloat(v)*(v.includes('ms')?0.001:1);if(n>m)m=n}}return m})()")
            if d > 0.02: ev.append(f'longest animation/transition duration {d}s under reduced motion')
            c.close(); return ev, ''

        # ---------- v2.6 features ----------
        import struct
        def wav_bytes():
            n = 80000; data = b'\x00\x00' * n
            return b'RIFF' + struct.pack('<I', 36 + len(data)) + b'WAVEfmt ' + struct.pack('<IHHIIHH', 16, 1, 1, 8000, 16000, 2, 16) + b'data' + struct.pack('<I', len(data)) + data
        def rp_click_all(p, n):
            for _i in range(n): p.evaluate("(()=>{const b=document.getElementById('rpTap');if(b&&!b.disabled)b.click()})()")

        @run('B26', 'Routine player: after-salah 33-33-34 steps, pause/resume, previous/next, restore after reload, completion, stats updated')
        def _():
            ev = []; c, p = home(url='/?play=after-salah'); p.wait_for_selector('#rpSel')
            if p.input_value('#rpSel') != 'after-salah': ev.append('deep link did not select after-salah')
            p.click('text=Start routine')
            if 'Step 1 of 3' not in p.inner_text('#routine-player'): ev.append('step 1 not shown')
            rp_click_all(p, 33)
            if 'Step 2 of 3' not in p.inner_text('#routine-player'): ev.append('did not advance to step 2 after 33')
            rp_click_all(p, 5)
            p.click('#routine-player >> text=Pause')
            if not p.is_disabled('#rpTap'): ev.append('tap not disabled while paused')
            p.click('#routine-player >> text=Resume')
            if p.is_disabled('#rpTap'): ev.append('tap still disabled after resume')
            p.click('text=Previous')
            if 'Step 1 of 3' not in p.inner_text('#routine-player'): ev.append('Previous did not go back')
            p.click('text=Next')
            p.reload(); p.wait_for_selector('#routine-player')
            if 'Unfinished routine' not in p.inner_text('#routine-player'): ev.append('no restore banner after reload')
            p.click('#routine-player >> text=Resume')
            if 'Step 2 of 3' not in p.inner_text('#routine-player') or '5 of 33' not in p.inner_text('#routine-player').replace('\n', ' '): ev.append('restored place/count wrong: ' + p.inner_text('#rpTap').replace('\n', ' '))
            rp_click_all(p, 28 + 34)
            if 'Routine complete' not in p.inner_text('#routine-player'): ev.append('no completion screen')
            p.reload(); p.wait_for_selector('#routine-player')
            if 'Unfinished routine' in p.inner_text('#routine-player'): ev.append('completed routine still offered for restore')
            if int(p.inner_text('#st')) != 100: ev.append('daily total is ' + p.inner_text('#st') + ' (expected 100)')
            c.close(); return ev, ''

        @run('B27', 'Bedtime routine player: both narrated orders (34-33-33 and 33-33-34)')
        def _():
            ev = []
            for rid, first, goals in (('bedtime-34', 'Allahu Akbar', [34, 33, 33]), ('bedtime-33', 'SubhanAllah', [33, 33, 34])):
                c, p = home(url='/?play=' + rid); p.wait_for_selector('#rpSel'); p.click('text=Start routine')
                for k, g in enumerate(goals):
                    t = p.inner_text('#routine-player').replace('\n', ' ')
                    if f'Step {k+1} of 3' not in t or f'of {g}' not in t: ev.append(f'{rid} step {k+1}: {t[:120]}')
                    if k == 0 and first not in t: ev.append(f'{rid} first phrase is not {first}')
                    rp_click_all(p, g)
                if 'Routine complete' not in p.inner_text('#routine-player'): ev.append(rid + ' did not complete')
                c.close()
            return ev, ''

        @run('B28', 'Morning/evening routine player: 6 starter steps, no invented Arabic text, completes')
        def _():
            ev = []
            for rid in ('morning', 'evening'):
                c, p = home(url='/?play=' + rid); p.wait_for_selector('#rpSel'); p.click('text=Start routine')
                t = p.inner_text('#routine-player')
                if 'Ayat al-Kursi' not in t or 'Qur’an 2:255' not in t: ev.append(rid + ': first step wrong')
                total = 0
                for g in (1, 3, 3, 3, 100, 1): rp_click_all(p, g); total += g
                if 'Routine complete' not in p.inner_text('#routine-player'): ev.append(rid + ' did not complete after 111 taps')
                c.close()
            return ev, ''

        @run('B29', 'Custom routine creator: validation, save, run, persistence, delete, markup shown as text')
        def _():
            ev = []; c, p = home(); p.wait_for_selector('#routine-player')
            p.click('text=Create my own routine')
            p.click('text=Save routine')
            if 'enter a routine name' not in p.inner_text('#rpLive').lower(): ev.append('empty name not rejected')
            p.fill('#rpName', '<b>Mine</b> set'); p.click('text=Save routine')
            if 'at least one step' not in p.inner_text('#rpLive'): ev.append('empty routine not rejected')
            p.fill('#rpCnt', '0'); p.click('text=Add step')
            if 'whole number' not in p.inner_text('#rpLive'): ev.append('bad target accepted')
            p.fill('#rpCnt', '2'); p.click('text=Add step'); p.select_option('#rpDh', 'alh'); p.fill('#rpCnt', '3'); p.click('text=Add step')
            p.click('text=Save routine')
            if p.evaluate("document.querySelectorAll('#routine-player b').length"): ev.append('markup injected in routine name')
            p.reload(); p.wait_for_selector('#rpSel')
            if '<b>Mine</b> set' not in p.inner_text('#rpSel'): ev.append('custom routine not persisted as text')
            p.select_option('#rpSel', 'custom:0'); p.click('text=Start routine'); rp_click_all(p, 5)
            if 'Routine complete' not in p.inner_text('#routine-player'): ev.append('custom routine did not complete')
            p.click('text=Back to counter'); p.select_option('#rpSel', 'custom:0'); p.click('text=Delete this routine')
            if p.locator('#rpSel option[value="custom:0"]').count(): ev.append('custom routine not deleted')
            c.close(); return ev, ''

        @run('B30', '99 Names tools: search, favourites, learned, random, learning mode, persistence')
        def _():
            ev = []; c, p = home(url='/99-names-of-allah'); p.wait_for_selector('#nmSearch')
            if p.locator('.tw tr:not([hidden])').count() != 100: ev.append('not 99 rows + header')
            p.fill('#nmSearch', 'rahim'); n = p.locator('.tw tr:not([hidden])').count() - 1
            if n < 1 or n > 3: ev.append(f'search "rahim" shows {n} rows')
            p.fill('#nmSearch', 'zzzz')
            if p.locator('.tw tr:not([hidden])').count() != 1: ev.append('no-match search should hide all rows')
            p.fill('#nmSearch', '')
            p.locator('.tw tr').nth(3).locator('button[aria-label^="Favourite"]').click()
            p.locator('.tw tr').nth(5).locator('input[type=checkbox]').check()
            p.reload(); p.wait_for_selector('#nmSearch')
            if p.locator('.tw tr').nth(3).locator('button[aria-label^="Favourite"]').inner_text() != '★': ev.append('favourite not persisted')
            if not p.locator('.tw tr').nth(5).locator('input[type=checkbox]').is_checked(): ev.append('learned not persisted')
            if 'Learned: 1 of 99' not in p.inner_text('#nmProg'): ev.append('progress text: ' + p.inner_text('#nmProg'))
            p.click('text=Show favourites only')
            if p.locator('.tw tr:not([hidden])').count() != 2: ev.append('favourites-only filter wrong')
            p.click('text=Showing favourites')
            p.click('text=Random name')
            if p.locator('.names-card:not([hidden])').count() != 1: ev.append('random name card missing')
            p.click('text=Learning mode'); p.click('text=Show meaning'); p.click('text=I knew it')
            if 'Learned: 2 of 99' not in p.inner_text('#nmProg'): ev.append('learning mode did not record progress: ' + p.inner_text('#nmProg'))
            p.once('dialog', lambda d: d.accept()); p.click('text=Reset my progress')
            if 'Learned: 0 of 99' not in p.inner_text('#nmProg'): ev.append('reset failed')
            c.close(); return ev, ''

        @run('B31', 'Audio: no recordings shipped; fallback is labelled "not a recording"; verified manifest entry plays with credit; unverified entry ignored; pause/resume/stop')
        def _():
            ev = []
            m = json.load(open(os.path.join(SITE, 'audio/manifest.json'), encoding='utf8'))
            if m.get('items'): ev.append('manifest lists recordings but none are shipped in v2.6')
            c, p = home(url='/subhanallah'); p.wait_for_selector('.voice-play')
            p.click('.voice-play >> nth=0'); p.wait_for_timeout(400)
            st = p.inner_text('#voiceStatus')
            if 'Recording:' in st: ev.append('claimed a recording with none available: ' + st)
            if not any(k in st for k in ('not a recording', 'No verified recording', 'not available')): ev.append('fallback not labelled: ' + st)
            if 'Device voice' in st and 'text-to-speech' not in st: ev.append('TTS not labelled')
            c.close()
            c = ctx(); p = c.new_page(); p.on('dialog', lambda d: d.accept())
            good = {'version': 1, 'items': {'sub': {'file': '/audio/sub.mp3', 'reciter': 'Test Reciter', 'source': 'Test Source', 'license': 'Test Licence', 'verified': True},
                                         'sbh': {'file': '/audio/sbh.mp3', 'reciter': 'X', 'source': 'Y', 'license': 'Z', 'verified': False}}}
            p.route('**/audio/manifest.json', lambda r: r.fulfill(status=200, content_type='application/json', body=json.dumps(good)))
            p.route('**/audio/*.mp3', lambda r: r.fulfill(status=200, content_type='audio/wav', body=wav_bytes()))
            p.goto(BASE + '/subhanallah'); p.wait_for_selector('.voice-play')
            p.click('.voice-play >> nth=0'); p.wait_for_timeout(800)
            st = p.inner_text('#voiceStatus')
            if 'Recording: Test Reciter' not in st: ev.append('verified recording not played/credited: ' + st)
            if p.inner_text('#voicePause') != 'Pause': ev.append('pause button state')
            p.click('#voicePause')
            if p.inner_text('#voicePause') != 'Resume': ev.append('pause did not switch to Resume')
            p.click('#voicePause'); p.click('#voiceStop')
            if not p.is_disabled('#voicePause'): ev.append('stop did not reset controls')
            p.click('.voice-play >> nth=1'); p.wait_for_timeout(500)
            st = p.inner_text('#voiceStatus')
            if 'Recording:' in st: ev.append('unverified manifest entry was used: ' + st)
            c.close(); return ev, 'recording test uses a generated silent WAV served by the test only'

        @run('B32', 'Article-to-counter: Start links select the dhikr + target, back-to-guide link, custom target form, unsafe "from" ignored, step reset')
        def _():
            ev = []
            for page, g in (('subhanallah', 33), ('alhamdulillah', 33), ('allahu-akbar', 34)):
                c, p = home(url='/' + page); p.click('a[href^="/?dhikr="]'); p.wait_for_selector('#tap')
                if f'of {g}' not in p.inner_text('#g'): ev.append(f'{page}: goal {p.inner_text("#g")}')
                if p.get_attribute('#backGuide', 'href') != '/' + page or p.is_hidden('#backGuide'): ev.append(page + ': no back-to-guide link')
                c.close()
            c, p = home(url='/astaghfirullah'); p.fill('form[data-start-form] input', '50'); p.click('form[data-start-form] button'); p.wait_for_selector('#tap')
            if 'of 50' not in p.inner_text('#g') or 'Astaghfirullah' not in p.inner_text('#tr'): ev.append('astaghfirullah custom target: ' + p.inner_text('#g'))
            p.goto(BASE + '/astaghfirullah'); p.fill('form[data-start-form] input', ''); p.click('form[data-start-form] button'); p.wait_for_selector('#tap')
            if 'no limit' not in p.inner_text('#g'): ev.append('astaghfirullah no-limit: ' + p.inner_text('#g'))
            p.goto(BASE + '/astaghfirullah'); p.fill('form[data-start-form] input', '-5'); p.click('form[data-start-form] button')
            if '/?dhikr=' in p.url: ev.append('invalid target was accepted')
            p.goto(BASE + '/salawat-durood'); p.fill('form[data-start-form] input', '10'); p.click('form[data-start-form] button'); p.wait_for_selector('#tap')
            if 'of 10' not in p.inner_text('#g'): ev.append('salawat target')
            p.evaluate("(()=>{const s=JSON.parse(localStorage.getItem('tdc'));s.step=5;localStorage.setItem('tdc',JSON.stringify(s))})()")
            p.goto(BASE + '/?dhikr=sub&goal=33&from=/subhanallah'); p.wait_for_selector('#tap')
            if p.input_value('#stepSel') != '1': ev.append('step not reset by deep link')
            for bad in ('//evil.com', 'javascript:alert(1)', '/a/b', 'https://evil.com'):
                p.goto(BASE + '/?dhikr=sub&from=' + bad)
                if p.is_visible('#backGuide'): ev.append('unsafe from accepted: ' + bad)
            p.goto(BASE + '/99-names-of-allah'); p.click('a[href^="/?study=names"]'); p.wait_for_selector('#tap')
            if 'no limit' not in p.inner_text('#g'): ev.append('99 names study has a target')
            c.close(); return ev, ''

        @run('B33', 'Language pages: lang/dir, canonical, hreflang cluster, switcher links, translated UI, counting works')
        def _():
            ev = []
            for l, d in (('ar', 'rtl'), ('ur', 'rtl'), ('id', 'ltr'), ('tr', 'ltr')):
                c, p = home(url='/' + l)
                if p.get_attribute('html', 'lang') != l or p.get_attribute('html', 'dir') != d: ev.append(l + ': lang/dir wrong')
                if p.get_attribute('link[rel=canonical]', 'href') != 'https://tasbihdigitalcounter.netlify.app/' + l: ev.append(l + ': canonical')
                if p.locator('link[rel=alternate][hreflang]').count() != 6: ev.append(l + ': hreflang count ' + str(p.locator('link[rel=alternate][hreflang]').count()))
                if p.locator('nav.lang-switch a').count() != 8: ev.append(l + ': switcher links ' + str(p.locator('nav.lang-switch a').count()))
                before = p.inner_text('#minus'); p.click('#tap')
                if p.inner_text('#n') != '1': ev.append(l + ': tap failed')
                if before in ('Undo −1',): ev.append(l + ': UI not translated')
                c.close()
            c, p = home(url='/')
            if p.locator('link[rel=alternate][hreflang]').count() != 6 or p.locator('nav.lang-switch a').count() != 8: ev.append('en: hreflang/switcher')
            c.close(); return ev, 'checks structure and counting; translation accuracy needs a native-speaker review'

        # ---------- performance (lab) ----------
        @run('B25', 'Lab performance (mobile-emulated, 4x CPU throttle, median of 3): LCP<=2.5s, CLS<=0.1, tap-to-next-paint<=200ms')
        def _():
            ev = []; info = []
            for url in ('/', '/subhanallah', '/99-names-of-allah'):
                L, C, T, F = [], [], [], []
                for _i in range(3):
                    c = ctx(viewport={'width': 375, 'height': 812}, device_scale_factor=2, has_touch=True, is_mobile=True)
                    p = c.new_page(); cdp = c.new_cdp_session(p); cdp.send('Emulation.setCPUThrottlingRate', {'rate': 4})
                    p.add_init_script("""window.__m={lcp:0,cls:0};
                      new PerformanceObserver(l=>{for(const e of l.getEntries())window.__m.lcp=e.startTime}).observe({type:'largest-contentful-paint',buffered:true});
                      new PerformanceObserver(l=>{for(const e of l.getEntries())if(!e.hadRecentInput)window.__m.cls+=e.value}).observe({type:'layout-shift',buffered:true});""")
                    p.goto(BASE + url); p.wait_for_load_state('networkidle'); p.wait_for_timeout(600)
                    tap = 0
                    if url == '/':
                        tap = max(p.evaluate("async()=>{const b=document.querySelector('#tap');const t=performance.now();b.click();await new Promise(r=>requestAnimationFrame(()=>setTimeout(r)));return performance.now()-t}") for _j in range(15))
                    m = p.evaluate('window.__m'); ttfb = p.evaluate("performance.getEntriesByType('navigation')[0].responseStart")
                    L.append(m['lcp']); C.append(m['cls']); T.append(tap); F.append(ttfb); c.close()
                lcp, cls, tp, ttfb = statistics.median(L), statistics.median(C), statistics.median(T), statistics.median(F)
                info.append(f'{url}: LCP {lcp:.0f}ms CLS {cls:.3f}' + (f' worst tap->paint {tp:.0f}ms' if tp else '') + f' TTFB {ttfb:.0f}ms')
                if lcp > 2500: ev.append(f'{url}: LCP {lcp:.0f}ms')
                if cls > 0.1: ev.append(f'{url}: CLS {cls:.3f}')
                if tp > 200: ev.append(f'{url}: tap->next paint {tp:.0f}ms')
            return ev, ' | '.join(info) + ' | local loopback server, headless Chromium; lab data only, NOT field/CrUX data; INP approximated by tap-to-next-paint'
        br.close()
finally:
    srv.terminate()
    json.dump(R, open(OUT, 'w'), indent=1, ensure_ascii=False)
