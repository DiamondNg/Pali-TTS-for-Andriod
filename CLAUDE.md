# Project memory for Claude

Pāli text-to-speech: Pāli (IAST) is converted to Kannada script with Aksharamukha and spoken by
Microsoft's Kannada neural voices via `edge-tts` (kn-IN-GaganNeural / kn-IN-SapnaNeural).
Owner is new to GitHub: give very step-by-step instructions, use the GitHub website (no terminal),
keep answers short, direct, with a confidence score; brainstorm before big changes.
Owner's rule: whenever starting a new chat would save tokens, say so, and update this file first
(so the new chat can continue from it).

## Status (2026-11-03)
- v2.1 merged (PR #5). v2.2 on branch `claude/wonderful-babbage-9my24n` (no PR yet): ññ fixed to
  spelling 4, icon without white ring, first Windows installer.
- Teacher confirmed the Mac DMG installs and works. Mac shortcut changed to Ctrl+Cmd+O (owner,
  2026-11-03; `key_equivalent = "@^o"`, CI greps it); real keypress only testable by a person.
- v2.3 (same branch): "English" → "Translation" (any language): voice combobox lists ALL local
  voices (Mac `say -v ?`; Windows OneCore/WinRT + SAPI via embedded PowerShell 5.1 script
  `WIN_SPEECH_PS`), loaded in a background thread; settings `en_voice` (id) + `en_voice_label`.
  Windows Both/Translation: `miniaudio` decodes MP3/WAV → 24 kHz mono, saved as WAV.
- Detection `line_language()`: non-Latin script or English markers → translation; Latin line is
  Pāli if ≥70% words use only Pāli letters and ≤20% end in a consonant other than ṃ (catches
  Malay/Spanish/Italian, and Pāli without diacritics); 1–2-word lines join neighbours.
  Limit: short all-vowel-ending lines in other languages ("Saya suka kopi") → Pāli.
  DPD not needed now; a Pāli word list from DPD could improve detection later.
- v2.4 (same branch, PR for owner's v2.4 release): all saved audio is MP3 (`wav_to_mp3`, bundled
  `lameenc`, 64 kbps). Voice option "Auto (by language)" (default, id "auto"): `split_segments`
  tags translation lines with `guess_language()` (Unicode script ranges; Latin via marker words
  for ms/es/fr/de/it/pt/nl/tl, Vietnamese letters, else en); `pick_voice()` matches the voice
  label's language prefix (PREFERRED_REGION, ms↔id; Apple Eloquence voices last); English →
  system default voice. Separate "Translation speed" slider (owner: Pāli slider unchanged) `TRANSLATION_SPEEDS` 0.75–3x
  (owner dropped 3.5x: SAPI max ≈3x), setting `en_speed`; Mac `say -r 175×`, WinRT SpeakingRate,
  SAPI Rate = 10·log3(x). Pāli slider label is now "Pāli speed".

- v2.4 released (owner: works very well on Windows). v2.5 on branch `claude/focused-ride-ai96xi`
  (PR): shortcut Ctrl+Shift+Y (Win, `hotkey.py`) / Cmd+Shift+Y (Mac `@$y`; installer clears the
  Stickies "Make Sticky" service shortcut, same keys); tip line in window (`SHORTCUT`); window
  resizable, min = packed size, text box expands; settings `size` [w,h] saved; settings saved at
  once on dark toggle; `APP_VERSION` in pali_tts.py → installer names "Read Pāli Aloud v2.5.exe"
  / ".dmg" (CI reads it). Windows right-click on selected text: not possible system-wide
  (no Services equivalent) → not done; options: browser extension, Explorer menu for .txt files.
- Mobile (discussed 2026-11-03): old Kivy prototype in `android/`, iOS Shortcut in `ios/`.

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
  Ctrl+Cmd+O via `defaults write pbs NSServicesStatus` key
  `(null) - Read Pali Aloud - runWorkflowAsService` = `@^o`. Removes old ~/Library/Scripts/PaliTTS.
- `.github/workflows/build_macos.yml`: `uv` 0.12.21 installs python-build-standalone 3.13
  (Tk 9.0.4) for arm64 + x86_64; pip installs `requirements-macos.txt` wheels; slims; reports
  min macOS (arm64 11, Intel 10.15); tests Intel under Rosetta; builds `PaliTTS-macOS.dmg`;
  installs from a quarantined DMG; tests say/afconvert/join; screenshots + OCRs the window
  (light, dark-by-toggle, system dark, opened via `open`, via Services; prints window owner
  name = Dock name); uploads artifacts; Release on `v*` tag or published Release.
- DMG is unsigned: first open needs System Settings → Privacy & Security → Open Anyway.
- `assets/AppIcon.png` (1024, made from the owner's image, outline square only).

## Windows (v2.2, first version; owner tests on own Windows PC)
- `windows/read_pali_aloud.py` = entry of `ReadPaliAloud.exe` (PyInstaller one-folder, windowed):
  no args → window; `--input-file F`; `--hotkey` → `windows/hotkey.py`; `--selftest OUT` (CI).
- `hotkey.py`: ctypes `RegisterHotKey` Ctrl+Alt+P (mutex = single instance; message box if taken),
  waits for keys up, sends Ctrl+C, reads clipboard (replaces it), starts exe `--input-file`.
- Playback: `MciPlayer` (winmm MCI, pause/resume/length) in `pali_tts.py`; Mac `AfplayPlayer`.
  Translation/Both use Windows voices (see v2.3). Window icon from `AppIcon.ico`, DPI aware.
- `windows/PaliTTS.iss` (UTF-8 BOM): per-user install to %LOCALAPPDATA%\Programs\Read Pali Aloud,
  Start menu "Read Pāli Aloud", Startup shortcut `--hotkey`, kills running exe on (un)install.
- `.github/workflows/build_windows.yml`: Python 3.13, PyInstaller, selftest, Inno Setup,
  silent install, `.github/scripts/win_gui_test.ps1` (window text via env `PALI_TTS_DUMP`,
  Ctrl+Alt+P on a WinForms textbox, screenshots), uninstall; artifact `PaliTTS-Windows`.
- Unsigned exe: SmartScreen → "More info" → "Run anyway". English voice on Windows (SAPI) later.
- Icon: `tools/make_icon.py` made PNG/ICNS/ICO from the original (run only on the original).

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
1. ññ: teacher picked 4 (ನ್ನ್ಯ) → fixed in v2.2 (`NYA_SPOKEN`), test button removed.
6b. Ctrl+Alt+P on Windows: implemented in v2.2, needs testing on a real PC.
7b. English voice on Windows/Android: use each system's local voices when we get there.

## Bhikkhunī Pātimokkha side task
- `BiPv8.xlsx` (560 rows) made by `tools/update_bip.py` (AnkiConnect, or `--txt` exports).
  Excel columns: order, noID, Alt Pali, Alt English, Alt Audio, Pali, English, Audio ←
  export fields 11, 1, 4 (or 3 if empty), 19, 18, 3, 7, 10. New range notes keep source IDs
  (`BI VIN PAT SK 51-55`).
- Checked the "for Bhikkhunī" deck against SuttaCentral `pli-tv-bi-pm`: 13 Pāli differences
  (PK 2/3/5, SA 1/16/CONCL, NP 15, PC 36, ND 4, PJ 2/5/6, PC 20) + SA 7–9 English missing
  "immediate … sending away and". Owner said to park this for now.
