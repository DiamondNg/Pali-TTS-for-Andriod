# Project memory for Claude

Pāli text-to-speech: Pāli (IAST) is converted to Kannada script with Aksharamukha and spoken by
Microsoft's Kannada neural voices via `edge-tts` (kn-IN-GaganNeural / kn-IN-SapnaNeural).
Owner is new to GitHub: give very step-by-step instructions, use the GitHub website (no terminal),
keep answers short, direct, with a confidence score; brainstorm before big changes.

## Status (2026-11-02)
- PR #1 and #2 merged. macOS is the focus; Windows installer is still broken (copies a missing
  `pali_tts.py` from `windows/`, calls `pyinstaller` directly). Android/iOS untouched.
- Teacher confirmed the Mac DMG installs and works.

## macOS architecture
- `pali_tts.py`: Tkinter window (text box, 7-step speed slider 0.25x–1.75x mapped to edge-tts
  rates -75%..+75%, Male/Female voice, Save MP3 to Downloads, ▶ Play/⏸ Pause/▶ Resume via
  SIGSTOP/SIGCONT on `afplay`, ⏹ Stop, Space = play/pause, elapsed/total time via `afinfo`,
  settings in `~/Library/Application Support/PaliTTS/settings.json`, window kept on screen).
  Transliteration: local `aksharamukha` (with `ast.Str` shim for Python 3.14), online API fallback.
- `Install Pali TTS.command` (only installer; `install_pali_service.sh` just calls it): copies the
  bundled Python for the Mac's chip (`hw.optional.arm64`) to `~/Library/Scripts/PaliTTS/runtime`
  (or `/Library/...` for all users), clears quarantine, writes `run.sh`, creates the Automator
  Service `~/Library/Services/Read Pali Aloud.workflow`, runs `pbs -update`.
- `.github/workflows/build_macos.yml`: `uv` 0.12.21 installs python-build-standalone 3.13
  (Tk 9.0.4) for arm64 + x86_64; pip installs `requirements-macos.txt` wheels into each
  (macosx_11_0_arm64 / macosx_10_13_x86_64); slims; reports min macOS (arm64 11, Intel 10.15);
  tests Intel under Rosetta; builds `PaliTTS-macOS.dmg` (~134 MB, runtimes in hidden `.runtime/`);
  installs from a quarantined DMG; screenshots + OCRs the real window
  (`.github/scripts/gui_check.py`, prints a base64 thumbnail into the log); uploads artifacts;
  publishes a Release on `v*` tag or when a Release is published on the website.
- DMG is unsigned: first open needs System Settings → Privacy & Security → Open Anyway.

## Environment gotchas (cloud sessions)
- Microsoft TTS (speech.platform.bing.com) is unreachable from the sandbox and returns 403 to
  GitHub runners: audio can't be tested automatically; ask the owner to test on a Mac.
- raw.githubusercontent.com works (SuttaCentral data: `suttacentral/bilara-data`, branch
  `published`); suttacentral.net API and Actions artifact downloads are blocked → read CI logs.
- Filenames of the deck exports use decomposed Unicode (ī = i + U+0304): use globs.

## Open feedback from the teacher (not yet implemented, discussed 2026-11-02)
1. `aññaṁ` sounds like "abbaṁ": Aksharamukha gives ಅಞ್ಞಂ (ಞ್ಞ); the Kannada voice mispronounces ಞ್ಞ.
   Needs an audio A/B test of substitutes on a real Mac.
2. `sarīran"ti` pauses before ti: curly quotes are replaced by spaces in `main()` and straight `"`
   passes through. Fix: delete quotes without a space (`sarīranti` → ಸರೀರಂತಿ).
3. Speeds: old 0.75x becomes the new 1x; drop old 1.5x/1.75x.
4. Window title "Read Pāli Aloud".
5. Real app in Applications/Launchpad; Dock shows "python3.13" → needs a proper .app bundle with
   its own icon/name.
6. Shortcut Ctrl+Cmd+P (Mac Service, via `pbs` NSServicesStatus) and Ctrl+Alt+P on Windows.
7. Idea: English TTS too (Pāli only / English only / both) for SuttaCentral pages; English voice
   from the computer's installed voices.

## Bhikkhunī Pātimokkha side task
- `BiPv8.xlsx` (560 rows) made by `tools/update_bip.py` (AnkiConnect, or `--txt` exports).
  Excel columns: order, noID, Alt Pali, Alt English, Alt Audio, Pali, English, Audio ←
  export fields 11, 1, 4 (or 3 if empty), 19, 18, 3, 7, 10. New range notes keep source IDs
  (`BI VIN PAT SK 51-55`).
- Checked the "for Bhikkhunī" deck against SuttaCentral `pli-tv-bi-pm`: 13 Pāli differences
  (PK 2/3/5, SA 1/16/CONCL, NP 15, PC 36, ND 4, PJ 2/5/6, PC 20) + SA 7–9 English missing
  "immediate … sending away and". Owner said to park this for now.
