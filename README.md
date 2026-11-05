# Read Pāli Aloud (Pāḷi TTS)

*Made by Āyasmā Paññādhammika · free software under the [GNU AGPL 3.0 or later](LICENSE)*

Reads Pāḷi text aloud. Pāḷi in Roman script (IAST) is converted to Kannada script with
[Aksharamukha](https://aksharamukha.appspot.com) and spoken by Microsoft's Kannada neural voices
(`kn-IN-GaganNeural` male / `kn-IN-SapnaNeural` female, via `edge-tts`, needs internet), or
offline by the Piper Kannada voice ([micahchoo/piper-kn](https://huggingface.co/micahchoo/piper-kn)) or the Mac's Soumya. Lines in
other languages (English, Chinese, Malay…) can be read by the computer's own voices.

**Current version: 2.10** — download the installers from
[Releases](https://github.com/DiamondNg/Pali-TTS-for-Andriod/releases) (or the latest
[Actions](https://github.com/DiamondNg/Pali-TTS-for-Andriod/actions) run → Artifacts).
**iPhone / iPad:** install the ready-made shortcut —
[Read Pāli Aloud (iCloud)](https://www.icloud.com/shortcuts/2997ad258cce49daaa635fb4d4fc0c76),
then see [`ios/README_iOS_Shortcut.txt`](ios/README_iOS_Shortcut.txt) (download the Kannada voice
and pick it in Speak Text).

## Status

| Platform | State | How it is used |
|----------|-------|----------------|
| **macOS** 11+ (Apple Silicon), 10.15+ (Intel) | Working (v2.x, tested by the teacher) | Select text → **Shift‑Cmd‑Y**, or right‑click → Services → *Read Pali Aloud*; or open the app and paste |
| **Windows** 10/11 | Working (v2.4+, tested by the owner) | Tray app: select text → **Ctrl+Shift+Y**, or the floating **▶ Read Pāli** button; or open the window and paste |
| **Android** | App (Kotlin + Chaquopy); APK from Releases/CI | `android/` |
| **iOS** (iPhone / iPad) | Working Shortcut (v2.10, tested by owner 2026-11-05) | Select Pāḷi → Share → *Read Pali Aloud*; or right-click → Services on Mac. Guide + `.shortcut`: `ios/` |

## Features (macOS and Windows)

- Speed slider for Pāḷi (0.33x–2x) and a separate one for translations (0.75x–3x).
- **Read:** Pāḷi / Translation / Both. Pāḷi lines are detected automatically; translation lines
  in any language use the computer's own voices ("Auto (by language)" picks one per line).
  Detection uses a list of all 145,000 Pāli word forms of the Suttas and Vinaya, so Pāli typed
  without diacritics (*evam me sutam*) is recognised too; in line-by-line Pāli/translation text,
  short lines follow the alternating pattern. A line with Pāli followed by its translation is
  cut where the language changes.
- Pāḷi voice: Male / Female · Microsoft (online); **Male · Piper (offline**, bundled; Mac needs
  macOS 13+); on Mac also **Female · Soumya (offline**, the Mac's own Kannada voice). ññ is spelled the way the teacher chose (ನ್ನ್ಯ); quotes are removed.
- Play / Pause / Resume / Stop, Space = play/pause, elapsed/total time.
- Save audio as MP3 to Downloads, or to a folder you choose ("Change folder…").
- Dark mode; all settings, the window size and dark mode are remembered.
- Help button in the window.
- Windows only: runs in the tray, starts with Windows (optional), reads the selection
  without using the clipboard.

## Installing

- **macOS:** open `Read Pāli Aloud v<version>.dmg` → double-click `Install Pali TTS.command`.
  Unsigned: the first time, System Settings → Privacy & Security → *Open Anyway*. See
  [`README_Mac.txt`](README_Mac.txt).
- **Windows:** run `Read Pāli Aloud v<version>.exe`. Unsigned: *More info* → *Run anyway*. See
  [`windows/README_Windows.txt`](windows/README_Windows.txt).

## In progress / ideas

- The offline voices were chosen with the test kit in
  [`tools/offline_voices/`](tools/offline_voices/README.md) (Piper, eSpeak NG, Soumya).
- Mobile apps (Android / iOS).

## Repository layout

```
pali_core.py                 text part shared by all platforms (Pāḷi detection, transliteration,
                             Microsoft voices); only changes here rebuild Android
pali_words.py                Pāli word list (145,000 forms) for language detection (tools/build_pali_words.py)
pali_tts.py                  desktop app (Tkinter window, local voices, playback)
Install Pali TTS.command     macOS installer (builds the .app and the Service, shipped in the DMG)
README_Mac.txt               macOS instructions
windows/                     Windows entry point, tray app, hotkey, UI Automation, Inno Setup script
tools/offline_voices/        offline Kannada voice test kit (Mac)
.github/scripts/             CI helpers: GUI tests, Piper model download (Hugging Face), slimming
tools/                       icon maker, other tools
android/                     Android app (Kotlin + Chaquopy; MP3 via LAME, android/app/src/main/cpp)
ios/                         iOS Shortcut guide (README_iOS_Shortcut.txt) + exported .shortcut
.github/workflows/           builds and tests: build_macos.yml (DMG), build_windows.yml (installer),
                             build_android.yml (APK)
```

## Building

GitHub Actions builds everything: a push builds the DMG and the Windows installer (with automatic
tests); a `v*` tag or a published Release attaches them to the Release. The version is
`APP_VERSION` in `pali_tts.py`; for a Release the builds take the version from the Release tag
(tag `v2.10` → "Read Pāli Aloud v2.10.dmg / .exe / .apk" and "2.10" in Help), so the names always
match the Release.

A v2.10 Release can bundle all four platforms: the macOS **.dmg**, the Windows **.exe**, the
Android **.apk** (all built by CI), and the iOS **.shortcut** (exported from the Shortcuts app on
an iPhone/iPad and uploaded to the Release by hand — CI cannot build or sign an iOS Shortcut).
See `ios/README_iOS_Shortcut.txt` → "Sharing / distributing this shortcut".

## Credits and licences

Read Pāli Aloud — Copyright © 2026 Āyasmā Paññādhammika. Free software: you can share and change
it under the [GNU Affero General Public License 3.0 or later](LICENSE) (AGPL, the same
licence as Aksharamukha). It comes with no warranty.

Included software and data:
- **Offline Piper voice** `kn_IN-syspin_male-medium` by micahchoo
  ([huggingface.co/micahchoo/piper-kn](https://huggingface.co/micahchoo/piper-kn)), trained on the
  SYSPIN Kannada male speaker — licensed under
  [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Bundled unchanged.
- [Piper](https://github.com/OHF-voice/piper1-gpl) speech engine (`piper-tts`) and
  [eSpeak NG](https://github.com/espeak-ng/espeak-ng) (Piper uses it to turn Kannada letters into
  speech sounds before the voice speaks; only its Kannada/English rules are bundled): GNU GPL 3.0
  or later.
- Pāli word list (`pali_words.py`, all 145,000 word forms, made by `tools/build_pali_words.py`): from
  [SuttaCentral bilara-data](https://github.com/suttacentral/bilara-data) (Mahāsaṅgīti Pāli,
  Sujato/Brahmali translations), CC0.
- [Aksharamukha](https://github.com/virtualvinodh/aksharamukha) (Pāḷi → Kannada script):
  GNU AGPL 3.0.
- [edge-tts](https://github.com/rany2/edge-tts) (Microsoft online voices) and lameenc (MP3):
  LGPL 3.0; LAME 3.100 (MP3 on Android): LGPL 2.0 or later; onnxruntime, miniaudio, comtypes: MIT; certifi: MPL 2.0; Python: PSF licence.

## Network domains (filtered networks)

- `speech.platform.bing.com` (Microsoft voices, WSS 443; not needed for the offline voices)
- `aksharamukha-plugin.appspot.com` (fallback transliteration, HTTPS 443)
