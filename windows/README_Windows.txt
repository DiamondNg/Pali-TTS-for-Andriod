Pali TTS — Windows
==================

REQUIREMENTS
  • Windows 10 or later
  • Python 3  (https://www.python.org — check "Add Python to PATH")
  • AutoHotkey v1  (https://www.autohotkey.com)
  • Internet connection (used for transliteration + TTS)

NETWORK DOMAINS TO WHITELIST (if on a filtered network)
  • aksharamukha-plugin.appspot.com  (HTTPS port 443)
  • speech.platform.bing.com         (WSS  port 443)

INSTALLATION
  1. Install Python 3 and AutoHotkey v1 if not already installed.
  2. Double-click "install_pali_windows.bat"
     It installs packages, builds the exe, and adds the hotkey to startup.
  3. When finished it says "Installation complete!" — close the window.

HOW TO USE
  1. Select any Pali text in any application (browser, PDF, Word, etc.)
  2. Press  Win + P
  3. A small window appears:
       - Drag the slider to choose speed (Slow / Normal / Fast / 2×)
       - Tick "Save MP3 to Downloads" if you want a file
       - Click ▶ Play  (or Cancel to abort)
  4. A notification confirms playback or the saved filename.

  You can also right-click the tray icon (bottom-right corner) and
  choose "Read Pali Aloud".

UNINSTALL
  1. Right-click tray icon → Exit
  2. Delete  %LOCALAPPDATA%\PaliTTS\
  3. Delete  %APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\pali_tts.ahk
  4. Delete the desktop shortcut "Pali TTS"

TROUBLESHOOTING
  • "No Pali text detected" — the tool filters out English and
    section numbers; make sure the selection contains Pali words.
  • "Transliteration failed" — check internet; the aksharamukha
    API must be reachable.
  • "Audio generation failed" — check internet; Microsoft TTS
    (speech.platform.bing.com) must be reachable.
  • Hotkey not working — check the tray icon is visible; if not,
    double-click  %LOCALAPPDATA%\PaliTTS\pali_tts.ahk  to start it.
  • PyInstaller build fails — ensure Python is in PATH and
    re-run the installer as Administrator.
