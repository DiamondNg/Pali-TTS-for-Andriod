# Pāḷi TTS

Text-to-speech for Pāḷi text, using an **edge-tts Kannada voice** (the Kannada script/phonetics approximate Pāḷi pronunciation well). The input text is filtered to strip English, other Indic scripts, and numbers before being sent to TTS.

This repo holds **four platform variants** of the same idea, all driven by Python (except iOS, which is a Shortcuts recipe).

## Platforms

| Platform | Stack | Entry point | How it's used |
|----------|-------|-------------|---------------|
| **macOS** | Python + Tkinter, right-click Service | `pali_tts.py`, `pali_tts_service.py` | Select text → right-click → Services |
| **Windows** | Python + Tkinter + AutoHotkey v1 | `windows/pali_tts_windows.py`, `windows/pali_tts.ahk` | Select text → press `Win+P` |
| **Android** | Kivy + Buildozer (APK) | `android/main.py`, `android/buildozer.spec` | Share Sheet or paste into app |
| **iOS** | Shortcuts app (no native code) | `ios/README_iOS_Shortcut.txt` | Share Sheet action |

## Repository layout

```
.
├── pali_tts.py                 # macOS/Windows Tkinter GUI (shared core)
├── pali_tts_service.py         # macOS Service runner
├── install_pali_service.sh     # macOS installer
├── README_Mac.txt              # macOS setup & usage
├── android/
│   ├── main.py                 # Kivy app
│   ├── buildozer.spec          # Android build config (API 33, NDK 25b, Python 3.11, Kivy 2.3.0)
│   ├── README_Android.txt
│   └── README_GitHub_Build.txt
├── windows/
│   ├── pali_tts_windows.py     # Windows variant
│   ├── pali_tts.ahk            # Win+P hotkey binding
│   ├── install_pali_windows.bat
│   └── README_Windows.txt
├── ios/
│   └── README_iOS_Shortcut.txt # Shortcuts recipe (aksharamukha API + native Kannada TTS)
└── .github/workflows/
    └── build_android.yml       # CI: builds the Android APK
```

## Building

- **Android:** push to GitHub and let `.github/workflows/build_android.yml` build the APK, or build locally with Buildozer (Linux/WSL2) — see `android/README_Android.txt`.
- **macOS:** run `install_pali_service.sh` — see `README_Mac.txt`.
- **Windows:** run `windows/install_pali_windows.bat` — see `windows/README_Windows.txt`.
- **iOS:** follow `ios/README_iOS_Shortcut.txt`.

## Dependencies

- Python 3.11
- `edge-tts` (TTS engine)
- Kivy 2.3.0 (Android only)
- AutoHotkey v1 (Windows only)
