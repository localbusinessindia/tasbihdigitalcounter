# Tasbih Digital Counter — Version 2.3

## Changes in this package
- Added editable daily goal (1–100,000), daily-goal progress, and a local best-day count.
- Added Focus Mode with a visible exit control.
- Added two selectable bedtime sequences: 34-33-33 and 33-33-34, with deep links from the homepage and bedtime guide.
- Added target selection when creating a custom dhikr (0 means no fixed target).
- Added a shareable PNG progress card; native file sharing is used when supported, otherwise the image downloads.
- Added Android Chrome and iOS Safari Add to Home Screen instructions.
- Bumped the service-worker cache to v10 so returning visitors can receive updated files.
- Preserved the existing site pages, clean URLs, counter, backup/import, local storage, SEO metadata, and Netlify configuration.

## Important limitations / owner actions
- At the time of this release, the contact page did not have an owner-supplied email. Version 2.7 now routes public feedback through the project GitHub Issues page instead.
- Browser vibration, native sharing, Wake Lock, and PWA installation depend on the actual device/browser and must be tested on physical devices.
- The automated audit files describe the prior audited build. Re-run the audit suite after this update; do not treat old PASS results as certification of this version.
- Religious text and citations have not been independently reviewed by a qualified scholar. The two bedtime orders are presented as separate reported variants; verify wording and references before publication.
- No audio recitation or complete translated language packs were added in this release.
