# Read Pāli Aloud (Pāḷi TTS)

Reads Pāḷi text aloud. Pāḷi in Roman script (IAST) is converted to Kannada script with
[Aksharamukha](https://aksharamukha.appspot.com) and spoken by Microsoft's Kannada neural voices
(`kn-IN-GaganNeural` male / `kn-IN-SapnaNeural` female, via `edge-tts`, needs internet). Lines in
other languages (English, Chinese, Malay…) can be read by the computer's own voices.

**Current version: 2.6** — download the installers from
[Releases](https://github.com/DiamondNg/Pali-TTS-for-Andriod/releases) (or the latest
[Actions](https://github.com/DiamondNg/Pali-TTS-for-Andriod/actions) run → Artifacts).

## Status

| Platform | State | How it is used |
|----------|-------|----------------|
| **macOS** 11+ (Apple Silicon), 10.15+ (Intel) | Working (v2.x, tested by the teacher) | Select text → **Shift‑Cmd‑Y**, or right‑click → Services → *Read Pali Aloud*; or open the app and paste |
| **Windows** 10/11 | Working (v2.4+, tested by the owner) | Tray app: select text → **Ctrl+Shift+Y**, or the floating **▶ Read Pāli** button; or open the window and paste |
| **Android** | Old prototype (Kivy) | `android/` |
| **iOS** | Shortcuts recipe | `ios/README_iOS_Shortcut.txt` |

## Features (macOS and Windows)

- Speed slider for Pāḷi (0.33x–1.67x) and a separate one for translations (0.75x–3x).
- **Read:** Pāḷi / Translation / Both. Pāḷi lines are detected automatically; translation lines
  in any language use the computer's own voices ("Auto (by language)" picks one per line).
- Pāḷi voice: Male or Female. ññ is spelled the way the teacher chose (ನ್ನ್ಯ); quotes are removed.
- Play / Pause / Resume / Stop, Space = play/pause, elapsed/total time.
- Save audio to Downloads as MP3.
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

- **Offline Kannada voices** (no internet needed): being evaluated with a small test kit,
  see [`tools/offline_voices/README.md`](tools/offline_voices/README.md) — Piper (neural),
  eSpeak NG (rule-based) and the Mac's own Kannada voice *Soumya*.
- Mobile apps (Android / iOS).

## Repository layout

```
pali_tts.py                  shared app (Tkinter window, Pāḷi detection, transliteration, voices)
Install Pali TTS.command     macOS installer (builds the .app and the Service, shipped in the DMG)
README_Mac.txt               macOS instructions
windows/                     Windows entry point, tray app, hotkey, UI Automation, Inno Setup script
tools/offline_voices/        offline Kannada voice test kit (Mac)
tools/                       icon maker, other tools
android/, ios/               early mobile versions
.github/workflows/           builds and tests: build_macos.yml (DMG), build_windows.yml (installer),
                             build_android.yml (APK)
```

## Building

GitHub Actions builds everything: a push builds the DMG and the Windows installer (with automatic
tests); a `v*` tag or a published Release attaches them to the Release. The version is
`APP_VERSION` in `pali_tts.py`.

## Network domains (filtered networks)

- `speech.platform.bing.com` (Microsoft voices, WSS 443)
- `aksharamukha-plugin.appspot.com` (fallback transliteration, HTTPS 443)
