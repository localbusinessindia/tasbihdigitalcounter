# Version 2.7 audit notes

## How to read these results
- Current v2.7 source checks were run against the package in this ZIP. S17 checks the generated PDF with PyPDF and verifies all 99 English transliterations against the source table; S18 checks the Contact and PDF links.
- B01-B03 were rerun against the local Netlify-emulating HTTP server for v2.7. B01 checked 27 sitemap routes; B02 checked 45 precache URLs; B03 inspected the configured headers through the local emulator.
- B04-B33 are the previously completed v2.6 headless-Chromium regression results, retained as a baseline because the current environment could not run the interactive browser suite against the local server. They are not claimed as a fresh v2.7 browser run. Playwright-managed Chromium was not installed; system Chromium could render the PDF from inline HTML, but local test-server navigation was blocked by the runtime.
- The PDF was rendered to five page images and visually inspected. The Arabic text, table layout and all 99 entries were visible in the rendered pages.
- Current v2.7 static results: 19 PASS, 0 FAIL, 2 BLOCKED. S15 is BLOCKED because the HTML validator package was not cached and npm registry access is unavailable in this build environment. S16 is BLOCKED because outbound external-link checks are not allowed here.

## v2.7 changes verified in source
- Contact page no longer contains a fake email address; it links to the public GitHub Issues page and warns users not to post private information.
- 99 Names PDF is a real five-page PDF generated from the existing 99-row source table. It includes Arabic, transliteration and concise English meanings. All 99 transliteration names were found in extracted PDF text.
- The PDF is included in the service-worker precache and the service-worker cache was bumped to v14. The local HTTP route test confirms precache URLs return 200.
- Three practical guides were expanded with original non-prescriptive advice about local backups, device alerts, choosing a counter method and maintaining a sustainable habit.
- The digital-vs-physical guide now describes the optional device text-to-speech aid accurately and does not imply that a verified MP3 is shipped.

## Remaining owner / specialist actions
1. **Authentic recitation audio** – no MP3 recordings are included. Add only recordings with documented permission or an open licence, plus reciter, source and licence attribution. The current optional device TTS is not a recorded recitation and may pronounce Arabic incorrectly.
2. **Religious review** – Arabic text, transliterations, translations, hadith references, the 99 Names glosses and devotional routines still need review by a qualified person. The current audits do not establish religious correctness.
3. **Native-language review** – Arabic, Urdu, Indonesian and Turkish interface text needs proofreading by native speakers. Automated tests verify page structure and counter operation, not translation quality.
4. **Physical-device testing** – test vibration, sound, offline use, PDF opening and keyboard/accessibility behaviour on a real Android phone and other browsers/devices. Headless Chromium cannot verify hardware vibration or real-world audio.
5. **Live deployment checks** – after uploading, confirm Netlify reports Published; test the live PDF download, HTTPS/security headers, external source links, redirects and 404 behaviour. Run Lighthouse and check field Core Web Vitals when data becomes available. Submit the sitemap in Search Console and verify indexing separately.
6. **Advertising** – AdSense scripts are not installed. When approved/ready, update CSP and privacy/consent disclosures together before enabling ads.

## Known technical trade-off
- The current Content Security Policy permits inline script/style because the homepage contains inline code. Moving that code into external files would allow a tighter policy, but this is a separate refactor and was not required for this version.
