# How to publish version 2.7 (GitHub + Netlify)

## A. Upload the complete website to GitHub
1. Unzip `tasbih-digital-counter-v2_7.zip` on your computer.
2. Open https://github.com/localbusinessindia/tasbihdigitalcounter and sign in.
3. Open the repository's main branch. Choose **Add file > Upload files**.
4. Open the unzipped folder and select everything inside it, including folders such as `audio` and `audit` (select the contents, not the parent folder).
5. Drag the selected files into GitHub. Wait for the uploads to finish.
6. In the commit message, write `Version 2.7` and choose **Commit directly to the main branch**, then click **Commit changes**.

Uploading the complete folder matters because v2.7 includes new files such as `99-names-of-allah.pdf`. Do not upload only the changed HTML files.

## B. Netlify deployment
If your Netlify site is connected to this GitHub repository and branch, the new commit should trigger a deploy. Open Netlify > your site > **Deploys** and confirm the newest deploy says **Published**. The local audit in this ZIP is not a live Netlify test.

## C. Check the published site
1. Open https://tasbihdigitalcounter.netlify.app/ on your phone.
2. Open the 99 Names guide and test **Download 99 Names PDF**.
3. Try the counter, Undo, Reset, vibration/sound settings and a guided routine.
4. Open the Contact page and test the GitHub Issues link.
5. Use the post-deploy checklist in `POST-DEPLOY-CHECKLIST.md`.

If you see an older version, refresh the page after the new deploy is Published. The service worker cache was bumped in v2.7.

## Items still requiring owner or specialist input
- **Authentic audio:** no recitation MP3 files are included. Add only recordings with documented permission/open licence and complete reciter/source/licence details; see `audio/README.md`.
- **Religious review:** Arabic, transliteration, translations, hadith citations and devotional routines still need a qualified review before being presented as scholar-verified.
- **Native-language review:** Arabic, Urdu, Indonesian and Turkish UI pages need native-speaker proofreading.
- **Physical-device checks:** vibration, sound, offline behaviour and PDF opening should be tested on a real Android phone and at least one other browser/device. Automated headless tests cannot prove hardware behaviour.
- **Live technical checks:** verify Netlify headers, external links, Lighthouse/field Core Web Vitals and Search Console after publishing.

No contact email is fabricated. The Contact page now links to the project's public GitHub Issues page; visitors should not post private information there.
