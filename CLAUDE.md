# Project memory for Claude

Pāli text-to-speech: Pāli (IAST) is converted to Kannada script with Aksharamukha and spoken by
Microsoft's Kannada neural voices via `edge-tts` (kn-IN-GaganNeural / kn-IN-SapnaNeural).
Owner is new to GitHub: give very step-by-step instructions, use the GitHub website (no terminal),
keep answers short, direct, with a confidence score; brainstorm before big changes.
Owner's rule: whenever starting a new chat would save tokens, say so, and update this file first
(so the new chat can continue from it).

## Status (2026-11-04)
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
- v2.5 also (same branch/PR #7): Windows = ONE background process `windows/tray.py` (`--tray`;
  `--hotkey` alias; no args/`--input-file` → hands text to the running copy via WM_COPYDATA to
  hidden window class `PaliTTS.TrayWindow`, mutex `Local\PaliTTS.ReadPaliAloud.Tray`). Threads:
  Tk main (`pali_tts.run_with_tray`, queue `pump`; Close = withdraw, tray Exit = quit), Win32
  (Shell_NotifyIcon menu Settings/Pause Floating Popup/Help/Exit, RegisterHotKey Ctrl+Shift+Y,
  WH_MOUSE_LL drag/double-click → check; re-hooked every 5 min; Esc = temporary hotkey while
  popup shown, no keyboard hook), worker (UIA via comtypes in `windows/uia.py`: focused element
  / element at cursor, walk parents for TextPattern.GetSelection; hotkey falls back to Ctrl+C).
  Popup `PaliTTS.Popup` WS_EX_NOACTIVATE, click → open window + autoplay. Settings `popup`,
  `tray_hint` (balloon once); startup = HKCU Run value "Read Pali Aloud" (installer [Registry],
  checkbox). Help button/window on both OSes: `help_text()` (Mac: Services, no tray),
  `AUTO_LANGUAGES`. `prepare_text` NFC + CR→LF. CI `win_gui_test.ps1` tests all of it.
- v2.6 on branch `claude/admiring-faraday-g9lutn` (no PR yet): Windows window reopened from the
  tray at minimum size (never-shown window reports winfo 1x1) → `show()` uses `_remembered_size()`
  (settings `size`); CI test 6 in `win_gui_test.ps1`. README.md rewritten to current status.
  Offline Kannada voice test kit `tools/offline_voices/` (Mac, owner evaluates): setup script
  (curl | bash) → ~/PaliTTS-voice-test (uv 0.12.21, Python 3.12, piper-tts, espeakng-loader,
  model kn_IN-syspin_male-medium from HF micahchoo/piper-kn), `run.sh` for an Automator Quick
  Action; compares Mac Soumya (kn_IN), Piper, eSpeak NG kn (ctypes; works on Linux). HF and
  aksharamukha are blocked from the sandbox: Piper part untested. Windows: no known Kannada voice.
- v2.6 also (same branch, PR): Pāli voice = Combobox `VOICES` (Microsoft M/F online, "piper"
  offline, Mac "soumya" = kn_IN `say` voice); `pali_audio()`, `piper_to_wav()` (length_scale /
  `rate_factor`), `VoiceError` messages. Model downloaded by CI (`.github/scripts/get_piper_model.sh`
  → `voices/`, gitignored; GitHub web upload limit 25 MB, model ~60 MB) and bundled (Mac
  Resources/voices, Win _internal/voices). Mac: onnxruntime 1.23.2 --no-deps, macOS 13+ for Piper;
  `slim_piper.py` drops other eSpeak dicts/Hebrew/Arabic models. Help window: markup (#, •, –, **).
  Licences: app AGPL-3.0-or-later (owner chose, = Aksharamukha) (owner: Āyasmā Paññādhammika, wants free distribution; told
  GPL allows selling); Piper voice CC BY 4.0 (credited in Help/README), piper-tts + eSpeak GPL-3,
  Aksharamukha AGPL-3, edge-tts/lameenc LGPL-3.
- v2.7 on branch `claude/busy-bell-5kx2wl`: save folder choosable ("Save audio to: <folder>" +
  "Change folder…" → `filedialog.askdirectory`), setting `save_dir` (default `default_save_dir()` =
  ~/Downloads); missing folder → error message, no silent fallback. Untested locally (no Tk).
- v2.8 on branch `claude/brave-cray-21enqi` (PR #11, open, description updated for 145k list; brave-sagan Android merged in, 2026-11-04):
  `pali_core.py` = text part shared with Android (markers, SPEEDS, detection, to_kannada,
  edge-tts, rate_factor, prepare_text); `pali_tts.py` does `from pali_core import *`;
  Android CI path filter = `pali_core.py` only (desktop-only changes don't rebuild Android);
  APP_VERSION stays in pali_tts.py (2.8). Detection: short line w/o diacritics is Pāli if
  `QUOTE_TI` (”ti/’nti) or `PALI_CLUSTER` (kkh, cch, tth, ddh…) and no English/≥3-letter
  Latin marker ("“bhikkhavo”ti." after "“Mendicants!”" was read in English). Owner asked
  about a Pāli word list: lookup is fast (set), cost is size; maybe later (SuttaCentral freq list).
  Mac: one copy (Unix socket instance.sock in settings dir; 2nd start hands text, exits; CI
  test "single"); autoplay when started with text (Services/shortcut) and on hand-off.
  Windows: Ctrl+Shift+Y and WM_COPYDATA text now autoplay. Android: always saves MP3 via
  LAME 3.100 (NDK, `android/app/src/main/cpp`, source fetched by
  `.github/scripts/android_get_lame.sh`, sha256 pinned; not compiled locally: sandbox blocked).
- v2.8 also (owner's spec, 2026-11-04): word-list detection. `pali_words.py` (2.2 MB, made by
  `tools/build_pali_words.py BILARA_DIR`, sparse clone of bilara-data `published`): WORDS = ALL
  145k Pāli forms (3+ letters) of Sutta+Vinaya (owner: 30k→50k→all; coverage 30k 88.2% / 50k
  92.9% / all 100% of 3+ letter occurrences; unseen AN10 text 88.8/91.8/94.3%), load ≈360 ms
  desktop (lazy, first detection), NOT_PLAIN
  (folded forms that are English words), ENGLISH (top 3000 Sujato/Brahmali words never Pāli).
  `line_language`: >10% of words end in a consonant other than ṃ/m → en (owner's rule, m added
  by owner; `QUOTE_N`: n before a quote = ṃ, "dhamman’ti", else 1.7% of Pāli misread); then each
  word votes Pāli (list / folded list / Pāli-only letter, not ñ alone = Spanish) or foreign
  (markers, ENGLISH, f/q/w/x/z, closed ending); words in both lists or `PALI_SHORT` vote nothing;
  more votes wins; tie with foreign → en; no votes → quote-ti/cluster → pi, 3+ words → pi, else
  None. No "any diacritic → Pāli" (names in English). Owner: don't worry about Malay (Pāli loans;
  "Saya suka kopi", "Ya, Bhante." → pi accepted). Held-out AN10 (3000 lines each): 0% wrong on
  Pāli with/without diacritics, English 0.03% (a bare "Sāriputta" line).
  `PALI_TITLE` (…sutta/vagga/vatthu/kathā… endings) votes Pāli: one-word headings were most
  "unknown" lines. `line_languages()` + `line_period()`: unknown (short) line takes the language
  one period back; period 1 (plain text), 2 (pi/translation alternating), 3 (pi/en/zh), 4; needs
  4+ known pairs, ≥90% agreement. AN10 interleaved test: alternating wrong 0.81%→0.02%
  (diacritics), 2.13%→0.02% (plain); pi/en/zh same gain; paragraph blocks 0.03% (unchanged);
  Pāli only 0%. Help (desktop help_text + Android HELP) lists these steps.
- iOS (2026-11-04): owner chose option B (no native app: $99/yr, App Store vs AGPL/GPL). `ios/README_iOS_Shortcut.txt`
  rewritten: Kannada voice check, Quick Look diagnosis, Replace Text steps = desktop clean-up
  (quotes, ṁ, dashes, optional NFD fixes, ಞ್ಞ→ನ್ನ್ಯ, [.;!?]→।), Speak Text voice by name. Untested
  (owner reported garbled voice with the old recipe; cause not yet known).
- Mobile (2026-11-03): owner chose Android focus; advice given: Android first, iOS later
  (Apple $99/yr + Mac needed; Python core can be reused on iOS via Python 3.13 iOS support).
- Android v1 on branch `claude/brave-sagan-mijd62` (no PR yet): Kivy prototype deleted;
  `android/` = Gradle project (AGP 8.7.3, Kotlin 2.0.21, Chaquopy 16.1.0, Python 3.11 (3.12+ lacks armeabi-v7a), minSdk 24,
  targetSdk 35, id `io.github.diamondng.readpalialoud` (owner: no sasanarakkha in the ID; Mac bundle id unchanged)). Kotlin UI (`MainActivity.kt`,
  `PhoneVoices.kt` = Android TextToSpeech, `AudioTools.kt` = MediaCodec decode/join/AAC M4A)
  + `app/src/main/python/bridge.py` importing the shared `pali_tts.py` (copied at build;
  tkinter import now optional). Pip `--no-deps` from `app/requirements.txt` (all pure Python);
  aksharamukha deps regex/yaml/requests/langcodes/fontTools stubbed in bridge.py (verified
  identical output, 362 lines). Pāli voices: Microsoft M/F (online), phone Kannada (offline,
  `android-kn`). Translation: Auto (by language) / phone default / any phone voice.
  PROCESS_TEXT (select text → menu) + SEND (Share) → autoplay. Save: CreateDocument; MP3 if
  Microsoft Pāli only, else M4A. Signing: committed `app/testing.keystore` (pw readpali) unless
  secrets ANDROID_KEYSTORE_BASE64/_PASSWORD, ANDROID_KEY_ALIAS/_PASSWORD. CI
  `build_android.yml` builds APK "Read Pali Aloud v<ver>.apk", emulator test
  `.github/scripts/android_test.sh`. Android SDK/Maven blocked in sandbox: compile only in CI.
  Owner answers (2026-11-03): public users, Android first; APK on GitHub Releases for now;
  private key later (explained); background player YES → `Playback.kt` (app-wide MediaPlayer,
  focus/noisy) + `PlaybackService.kt` (mediaPlayback foreground service, MediaSessionCompat,
  MediaStyle notification); Python/voices/worker live in `Session` (window rebuild crashed
  before). Piper YES → `PiperVoice.kt` with sherpa-onnx **1.13.8** AAR (2.x dropped eSpeak NG),
  fetched + model converted by `.github/scripts/android_get_voice.sh` (sherpa's
  add_meta_data.py + iso639-lang; espeak-ng-data from sherpa's amy package, only kn_dict).
  APK with the model inside was 205 MB → owner chose option C: voice NOT in the APK; zip
  `piper-kn-<hash>.zip` uploaded by CI to pre-release "android-voice" (never replaced),
  `assets/piper_download.json` (url/name/size) → app downloads on first choice (dialog,
  progress), unpacks to filesDir/piper, ⋮ "Remove Piper voice". Native libs compressed
  (`useLegacyPackaging`). Google Kannada voice: own TTS instance on engine
  com.google.android.tts + "Offline Kannada voice…" dialog (install intents) + Help. Autoplay
  on shared text: yes. Private signing key made 2026-11-03 (PKCS12, alias readpalialoud, 4096-bit, SHA-256 1B:A1:26:95:…:7D:78), given to owner as files; owner added the 4 GitHub secrets; CI log confirms PRIVATE key + fingerprint.
  CI GREEN 2026-11-03 run 41686297490 (all 5 emulator tests; Microsoft voice even worked from the
  emulator: 4 s played). APK 66 MB (artifact PaliTTS-Android). Next: owner tests on a phone, then PR + v2.x Release.

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
