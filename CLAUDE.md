# Project memory for Claude

Pāli text-to-speech: Pāli (IAST) is converted to Kannada script with Aksharamukha and spoken by
Microsoft's Kannada neural voices via `edge-tts` (kn-IN-GaganNeural / kn-IN-SapnaNeural).
Owner is new to GitHub: give very step-by-step instructions, use the GitHub website (no terminal),
keep answers short, direct, with a confidence score; brainstorm before big changes.
Owner's rule: whenever starting a new chat would save tokens, say so, and update this file first
(so the new chat can continue from it).

## Status (2026-11-02)
- v2 merged (PR #4). v2.1 = ññ test (branch `claude/pensive-archimedes-hdsrmw`, PR #5 pending).
- PR #1 and #2 merged. macOS is the focus; Windows installer is still broken (copies a missing
  `pali_tts.py` from `windows/`, calls `pyinstaller` directly). Android/iOS untouched.
- Teacher confirmed the Mac DMG installs and works.

## macOS architecture (v2, branch claude/pensive-archimedes-hdsrmw, 2026-11-02)
- `pali_tts.py`: Tkinter window titled "Read Pāli Aloud": text box, 5-step speed slider
  0.33x/0.67x/1x/1.33x/1.67x = edge-tts -75/-50/-25/+0/+25% (old steps ×4/3; old 1.5x/1.75x
  dropped), Read: Pāli / English / Both, Pāli voice Male/Female, English voice combobox
  (`say -v ?`, en_* voices), Dark mode checkbox (aqua: `MacWindowStyle appearance darkaqua`;
  follows system until toggled), Save audio to Downloads, Play/Pause/Resume (SIGSTOP/SIGCONT on
  `afplay`), Stop, Space = play/pause, elapsed/total time. Settings in
  `~/Library/Application Support/PaliTTS/settings.json` (keys rate, voice, save, mode, en_voice,
  dark). Pāli only → one edge-tts MP3. English/Both → `split_segments()` (line-based English
  detection), Pāli parts via edge-tts (concurrent), English via `say`, all `afconvert` → WAV
  24 kHz mono, joined with 0.4 s gaps (`join_wavs`), saved as M4A (no MP3 encoder on macOS).
  Quotes are deleted from Pāli (`clean_pali`), dashes → space. Transliteration: local
  `aksharamukha` (`ast.Str` shim), online API fallback. Sets SSL_CERT_FILE from certifi.
- `Install Pali TTS.command`: builds `/Applications/Read Pāli Aloud.app` (or ~/Applications if
  not writable; all-users → sudo): python binary copied to `Contents/MacOS/python3` and runtime
  `lib` to `Contents/lib` so the Dock shows the app name/icon; launcher `Contents/MacOS/ReadPaliAloud`;
  icon `assets/AppIcon.icns` (DMG `.assets/`). Service workflow runs the launcher; shortcut
  Ctrl+Cmd+P via `defaults write pbs NSServicesStatus` key
  `(null) - Read Pali Aloud - runWorkflowAsService` = `@^p`. Removes old ~/Library/Scripts/PaliTTS.
- `.github/workflows/build_macos.yml`: `uv` 0.12.21 installs python-build-standalone 3.13
  (Tk 9.0.4) for arm64 + x86_64; pip installs `requirements-macos.txt` wheels; slims; reports
  min macOS (arm64 11, Intel 10.15); tests Intel under Rosetta; builds `PaliTTS-macOS.dmg`;
  installs from a quarantined DMG; tests say/afconvert/join; screenshots + OCRs the window
  (light, dark-by-toggle, system dark, opened via `open`, via Services; prints window owner
  name = Dock name); uploads artifacts; Release on `v*` tag or published Release.
- DMG is unsigned: first open needs System Settings → Privacy & Security → Open Anyway.
- `assets/AppIcon.png` (1024, made from the owner's image, outline square only).

## Next: Windows installer (plan, not started; owner tests on own Windows PC)
Current `windows/` is v1-era and broken: needs Python + AutoHotkey preinstalled, bat calls
`pyinstaller` directly, copies a missing `pali_tts.py`, uses Win+P (clashes with Windows'
display shortcut), `playsound` cannot pause. Proposed:
- Build on GitHub Actions `windows-latest`: PyInstaller (one-folder) of the shared `pali_tts.py`
  (v2) + icon (`assets/AppIcon.png` → .ico), then Inno Setup → `PaliTTS-Setup.exe` (Start menu
  entry "Read Pāli Aloud" with icon, uninstaller, per-user install, no admin). Upload artifact.
- Ctrl+Alt+P without AutoHotkey: small resident helper started at login (ctypes
  `RegisterHotKey`), sends Ctrl+C, reads clipboard, opens the window with the text.
- Playback with pause/resume/position: Windows MCI (`winmm.mciSendStringW` via ctypes) for MP3.
- English voice on Windows: SAPI (System.Speech) later; first get Pāli working.
- Unsigned exe: SmartScreen → "More info" → "Run anyway".
- CI can smoke-test install + screenshot; audio still needs the owner's PC.

## Environment gotchas (cloud sessions)
- Microsoft TTS (speech.platform.bing.com) is unreachable from the sandbox and returns 403 to
  GitHub runners: audio can't be tested automatically; ask the owner to test on a Mac.
- raw.githubusercontent.com works (SuttaCentral data: `suttacentral/bilara-data`, branch
  `published`); suttacentral.net API and Actions artifact downloads are blocked → read CI logs.
- Filenames of the deck exports use decomposed Unicode (ī = i + U+0304): use globs.

## Teacher feedback status
Done in v2 (needs the teacher to test on a Mac): 2 quotes, 3 speeds, 4 title, 5 .app, 6 Mac
shortcut, 7 English (selected text only; Mac voices), plus dark mode.
Still open:
1. `aññaṁ` sounds like "abbaṁ" (Aksharamukha ಅಞ್ಞಂ; voice mispronounces ಞ್ಞ). v2.1 adds an
   "ññ test" button: `NYA_VARIANTS` = 1 ಞ್ಞ (old) 2 ನ್ಯ 3 ಞ್ಯ 4 ನ್ನ್ಯ 5 ನ್ಞ 6 ಞ್ಞ್ಯ, read on
   `NYA_TEST_WORDS` (aññaṃ, paññā, saññā, rañño, kataññū, aññatra), each after "Number N"
   (Mac `say`); chosen number saved as setting `nya` and applied in `to_kannada`. Waiting for the
   teacher's pick → then make it the default (and use it on Windows).
6b. Ctrl+Alt+P on Windows (Windows installer still broken).
7b. English voice on Windows/Android: use each system's local voices when we get there.

## Bhikkhunī Pātimokkha side task
- `BiPv8.xlsx` (560 rows) made by `tools/update_bip.py` (AnkiConnect, or `--txt` exports).
  Excel columns: order, noID, Alt Pali, Alt English, Alt Audio, Pali, English, Audio ←
  export fields 11, 1, 4 (or 3 if empty), 19, 18, 3, 7, 10. New range notes keep source IDs
  (`BI VIN PAT SK 51-55`).
- Checked the "for Bhikkhunī" deck against SuttaCentral `pli-tv-bi-pm`: 13 Pāli differences
  (PK 2/3/5, SA 1/16/CONCL, NP 15, PC 36, ND 4, PJ 2/5/6, PC 20) + SA 7–9 English missing
  "immediate … sending away and". Owner said to park this for now.
