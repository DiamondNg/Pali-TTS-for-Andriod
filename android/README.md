# Read Pāli Aloud for Android

Same features as the desktop app, on Android 7 or newer.

## Install (testing version)
1. On the GitHub website: **Actions** → **Build Android app** → the newest green run →
   **Artifacts** → **PaliTTS-Android** (download, unzip).
2. Copy `Read Pali Aloud v….apk` to the phone (or download it on the phone) and tap it.
3. Android asks to allow installing from this source (Chrome / Files): allow it.

## Use
- Open the app, paste text, tap **Play**.
- Or, in any app: select text → in the small menu (tap ⋮ if needed) → **Read Pāli Aloud**.
- Or: **Share** → **Read Pāli Aloud**.

## How it is built
Kotlin user interface; the text handling is the desktop's `pali_tts.py`, run by
[Chaquopy](https://chaquo.com/chaquopy/) (Python inside Android). GitHub Actions builds
the APK and tests it on an Android emulator (`.github/workflows/build_android.yml`).
