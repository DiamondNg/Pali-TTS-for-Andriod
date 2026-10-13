Pali TTS — macOS
================

REQUIREMENTS
  • macOS 10.15 or later
  • Python 3 (https://www.python.org  or  brew install python)
  • Internet connection (used for transliteration + TTS)

NETWORK DOMAINS TO WHITELIST (if on a filtered network)
  • aksharamukha-plugin.appspot.com  (HTTPS port 443)
  • speech.platform.bing.com         (WSS  port 443)

INSTALLATION
  1. Double-click "Install Pali TTS.command"
     A Terminal window opens and runs the installer automatically.
  2. When finished it says "Done!" — close the Terminal window.
  3. If the right-click menu item does not appear immediately,
     log out and back in (or restart).

HOW TO USE
  1. Select any Pali text in any application (browser, PDF, Word, etc.)
  2. Right-click → Services → "Read Pali Aloud"
  3. A small window appears:
       - Drag the slider to choose speed (Slow / Normal / Fast / 2×)
       - Tick "Save MP3 to Downloads" if you want a file
       - Click ▶ Play  (or Cancel to abort)
  4. A notification confirms playback or the saved filename.

UNINSTALL
  Run in Terminal:
    rm -rf ~/Library/Services/"Read Pali Aloud.workflow"
    rm -rf ~/Library/Scripts/PaliTTS

TROUBLESHOOTING
  • "No Pali text detected" — the tool filters out English and
    section numbers; make sure the selection contains Pali words.
  • "Transliteration failed" — check internet; the aksharamukha
    API must be reachable.
  • "Audio generation failed" — check internet; Microsoft TTS
    (speech.platform.bing.com) must be reachable.
  • Service not in right-click menu — try System Settings →
    Privacy & Security → Automation, or log out and back in.
