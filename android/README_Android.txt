Pali TTS — Android (Kivy)
=========================

HOW IT WORKS
  Same pipeline as Mac/Windows:
    selected text -> aksharamukha API (Pali -> Kannada script)
                  -> Android's built-in TTS speaks the Kannada

  Voice: uses Android's on-device Kannada TTS (usually Google TTS).
  Quality is good on modern Android with Google TTS installed.

  Note: Save MP3 is not available in the Android version.

REQUIREMENTS TO BUILD
  • A Linux machine (or Docker / WSL2 on Mac/Windows)
    Buildozer does not build Android APKs on macOS natively.
  • Python 3.11
  • Java JDK 17 (OpenJDK)
  • Git

════════════════════════════════════════════════════════════════
BUILD INSTRUCTIONS (Linux / WSL2)
════════════════════════════════════════════════════════════════

── 1. Install dependencies ──────────────────────────────────────

  sudo apt update
  sudo apt install -y python3 python3-pip git zip unzip openjdk-17-jdk \
      autoconf libtool pkg-config zlib1g-dev libncurses5-dev \
      libncursesw5-dev libtinfo5 cmake libffi-dev libssl-dev

── 2. Install Buildozer ─────────────────────────────────────────

  pip3 install --user buildozer cython

── 3. Copy files into a build folder ────────────────────────────

  mkdir ~/palitts_build
  cp main.py ~/palitts_build/
  cp buildozer.spec ~/palitts_build/
  cd ~/palitts_build

── 4. Build the APK ─────────────────────────────────────────────

  buildozer android debug

  First build takes 20-40 minutes (downloads Android SDK/NDK).
  Subsequent builds are much faster.

  The APK will be at:
    bin/palitts-1.0-arm64-v8a_armeabi-v7a-debug.apk

── 5. Install on your Android device ────────────────────────────

  Option A — USB cable:
    Enable USB Debugging on the phone:
      Settings -> About phone -> tap "Build number" 7 times
      Settings -> Developer options -> USB Debugging ON
    Then:
      buildozer android deploy run
    (installs and launches the app automatically)

  Option B — copy the APK:
    Transfer the APK file to your phone, tap it to install.
    You may need to allow "Install from unknown sources" in Settings.

════════════════════════════════════════════════════════════════
BUILD ON MAC USING DOCKER (alternative)
════════════════════════════════════════════════════════════════

  Install Docker Desktop, then:

  docker run --rm -v "$(pwd)":/home/user/hostcwd \
      kivy/buildozer \
      android debug

  This runs Buildozer inside a Linux container on your Mac.

════════════════════════════════════════════════════════════════
USING THE APP
════════════════════════════════════════════════════════════════

  Option A — Share Sheet:
    In any app (PDF reader, browser, etc.) select Pali text
    -> tap Share -> "Pali TTS"
    The text arrives pre-filled; press Play.

  Option B — Open directly:
    Tap the Pali TTS icon on your home screen.
    Paste text into the box, press Play.

  Requirements:
    • Internet connection (aksharamukha API)
    • Google TTS installed with Kannada voice:
        Settings -> General management -> Language -> Text-to-speech
        -> Preferred engine: Google -> Language: Kannada

════════════════════════════════════════════════════════════════
TROUBLESHOOTING
════════════════════════════════════════════════════════════════

  "Transliteration failed":
    Check internet connection. aksharamukha-plugin.appspot.com
    must be reachable.

  No audio / silence:
    Go to Android Settings -> Text-to-speech and make sure
    Kannada is available. Download the Kannada voice pack if needed.

  "TTS not ready yet":
    The TTS engine takes a second to initialise on first launch.
    Wait a moment and press Play again.

  Build errors:
    Make sure Java JDK 17 is installed (not 11 or 21).
    Run: java -version  (should show 17.x)
