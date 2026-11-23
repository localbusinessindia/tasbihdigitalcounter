# Tasbih Digital Counter

Static website (plain HTML/CSS/JS, no build step, no runtime dependencies) deployed on Netlify at
`https://tasbihdigitalcounter.netlify.app/`.

## Layout
- `index.html` – the counter (inline CSS/JS) · `*.html` – guide and policy pages · `content.css` – shared guide styles
- `sw.js`, `manifest.webmanifest`, `icon*.png`, `og-default.png` – PWA / sharing assets
- `_headers`, `_redirects`, `netlify.toml` – Netlify config (security headers, clean-URL redirects, hides non-site files)
- `sitemap.xml`, `robots.txt` – SEO files (update `sitemap.xml` when you add a page)
- `99-names-of-allah.pdf` – downloadable study handout generated from the 99 Names page
- `audit/` – repeatable audit scripts and recorded results · `AUDIT-RESULTS.md` – what was actually tested

## Install / run locally
No install is needed to view the site. To serve it with Netlify-like clean URLs and headers:

    python3 audit/serve.py . 8000      # then open http://127.0.0.1:8000/

## Deploy
Drag the folder that contains `index.html` onto Netlify (or push to the connected repository).
`netlify.toml` publishes the repository root (`publish = "."`); `_redirects` makes `/audit/*`, `README*.md`
and `AUDIT-RESULTS.md` return 404 so project files are not public.
Environment variables: none (see `.env.example`).

## Repeat the audit
    pip install beautifulsoup4 lxml pillow playwright pypdf && playwright install chromium
    ./audit/run_all.sh

If Playwright cannot find its installed browser, set `CHROMIUM_PATH` to the Chromium executable. This runs: source checks (`audit/static_audit.py`: metadata, canonicals, links, sitemap, robots, JSON-LD,
manifest/icons, headers, JS syntax, HTML validation, placeholders, secrets, privacy-text consistency) and
Chromium checks (`audit/browser_tests.py`: every route, counter behaviour, import/export, keyboard, offline/PWA,
overflow at 7 viewports, axe-core WCAG A/AA in light and dark, lab performance), then regenerates `AUDIT-RESULTS.md`.
`audit/apply_fixes.py` records the source transformations made in the 2026-11-14 audit.

## Adding a page
1. Create `new-page.html` (copy a guide page; canonical `https://tasbihdigitalcounter.netlify.app/new-page`).
2. Link to it with a clean URL (`/new-page`, not `new-page.html`) from the homepage or a related guide.
3. Add it to `sitemap.xml` and to `PRECACHE_URLS` in `sw.js`, bump the `CACHE_NAME` version, add a `_redirects` line
   `/new-page.html /new-page 301!`, then run `./audit/run_all.sh`.

## Before enabling ads
`_headers` sets a Content-Security-Policy that only allows this site's own resources. Adding AdSense/analytics
requires extending `script-src`, `connect-src`, `img-src` and `frame-src` for the provider, and updating
`privacy-policy.html` (and a consent mechanism where required). Do this together.

## Remaining owner / specialist actions
- `contact.html` routes public feedback and corrections to the project GitHub Issues page; issues are public, so visitors should not submit private information.
- Religious content (translations, hadith references and devotional routines) still needs review by a qualified person.
- Arabic, Urdu, Indonesian and Turkish UI text needs native-speaker proofreading.
- Authentic recitation MP3 files are not bundled; see `audio/README.md` for the licensing and attribution requirements.
- Test vibration, audio, offline use and downloaded PDF on physical devices; then verify the live Netlify deployment and Search Console.
