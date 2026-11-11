# Tasbih Digital Counter — Netlify ZIP

This is a static HTML website. It is configured to publish from the ZIP root and keeps the existing Netlify subdomain canonical URLs:

`https://tasbihdigitalcounter.netlify.app/`

## Deploy
1. Extract this ZIP on your computer.
2. Open Netlify and choose the manual deploy / drag-and-drop option.
3. Drag the extracted folder whose top level contains `index.html`, `sitemap.xml`, `robots.txt` and `netlify.toml`. Do not upload the ZIP file itself as a single nested file.
4. After deployment, open the homepage and test the counter, the after-salah mode and the bedtime mode.

The source repository can remain on GitHub; this ZIP is a static deploy package. The canonical tags, sitemap and robots.txt intentionally retain the `tasbihdigitalcounter.netlify.app` address.

## Important
- `keyword-research/` contains the consolidated keyword exports and mapping notes. It is research material, not a public-facing site section.
- No AdSense publisher code is included because no approved publisher ID/snippet was supplied.
- Islamic date entries are estimates; check local moon-sighting announcements. Religious content should be reviewed by a knowledgeable person before publication.

## SEO keyword prioritisation (v3)
This build uses a low-KD-first strategy without removing harder terms: KD 0–14 are primary opportunities, KD 15–29 are secondary, KD 30–49 are supporting, and KD 50+ are long-term. See `keyword-research/low-kd-page-priority-plan.csv` and `keyword-research/target-keyword-map.csv`. KD is an external estimate, not a Google ranking factor or guarantee.


## v4 visual, sharing and install updates
- Added `icon-192.png` and `icon-512.png` in the existing brand style and referenced them in the web app manifest. The Arabic symbol is rasterized with an Arabic-capable font to avoid missing-glyph squares.
- Added a 1200×630 `og-default.png`; all HTML pages now include Open Graph image and Twitter large-image metadata.
- Corrected `content.css` so it is valid external CSS (no embedded `<style>` tags) and aligned content typography with the homepage.
- On small screens, content-page navigation stays on one horizontally scrollable row below the one-line logo.
- Dark-mode counter button uses a deeper green for stronger white-text contrast. The service worker is registered from every page for visitors who land directly on a guide.
- Desktop layout reserves empty left/right rails for future approved AdSense units. No AdSense code or fake ads have been inserted.

## Future sidebar ad placements
The desktop rails are marked with `data-ad-placement="left"` and `data-ad-placement="right"` in the HTML. Add responsive AdSense code inside those `<aside>` elements only after the site is approved and you have the correct ad-unit code. Remove `aria-hidden="true"` from a rail when placing an ad in it so assistive technology can access the ad.
