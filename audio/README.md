# Audio recordings (not included in v2.7)

v2.7 ships the audio system but **no recordings**. Nothing was invented or generated.
Until you add verified files, the site uses the visitor's browser text-to-speech and labels it
"Device voice (text-to-speech), not a recording".

## How to add a recording
1. Get an MP3 from a reciter or organisation that gives you written permission or a clear open licence.
2. Save the complete recitation as an MP3 and name it after its key, e.g. `sub.mp3`. Keep the full wording: a short dhikr may need only a few seconds, while a longer verse or supplication needs the time required to recite it fully. Never trim or shorten a Qur’anic verse or supplication to meet a file-size target.
   The list of keys is in `ASSETS-NEEDED.json` (28 dhikr, 99 names, 5 routine items).
3. Put the file in this `audio/` folder.
4. Add an entry to `manifest.json`, for example:

```
"sub": { "file": "/audio/sub.mp3", "reciter": "Name", "source": "Where it came from",
         "license": "e.g. CC BY 4.0 / written permission", "verified": true }
```
5. Upload to GitHub. The site only plays entries where `file`, `reciter`, `source`, `license` are filled and `verified` is true.
