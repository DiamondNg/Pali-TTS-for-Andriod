Pali TTS — macOS
================

REQUIREMENTS
  • macOS 10.15 or later
  • Python 3.8+ with Tkinter. Easiest: the installer from
    https://www.python.org/downloads/macos/
    (Homebrew Python also works, but needs:  brew install python-tk)
  • Internet connection (for the Microsoft voice; Pali→Kannada script
    conversion runs on the Mac, with the online service as a fallback)

NETWORK DOMAINS TO WHITELIST (if on a filtered network)
  • aksharamukha-plugin.appspot.com  (HTTPS port 443, fallback only)
  • speech.platform.bing.com         (WSS  port 443)

INSTALLATION
  1. Open PaliTTS-macOS.dmg, then double-click "Install Pali TTS.command"
     A Terminal window opens and runs the installer automatically.
     If macOS says it "cannot verify" the file (it is not Apple-signed):
     click Done, then System Settings → Privacy & Security → scroll down
     → "Open Anyway" for "Install Pali TTS.command".
     The installer creates its own Python environment in
     ~/Library/Scripts/PaliTTS/venv (no system-wide pip install).
  2. When finished it says "Done!" — close the Terminal window.
  3. If the right-click menu item does not appear immediately,
     log out and back in (or restart).

HOW TO USE
  1. Select any Pali text in any application (browser, PDF, Word, etc.)
  2. Right-click → Services → "Read Pali Aloud"
  3. A small window appears:
       - Drag the slider to choose speed (0.25x to 1.75x)
       - Choose Male or Female voice
       - Tick "Save MP3 to Downloads" to keep a file; it is saved at
         the chosen speed (the speed is added to the file name)
       - Click ▶ Play. While playing the button becomes ⏸ Pause;
         click it to pause, and ▶ Resume to continue from that point.
         ⏹ Stop ends playback. If you change the text, speed or voice
         while paused, Resume starts again with the new settings.
       - Space bar = play / pause (press Esc first if you are typing
         in the text box). Elapsed / total time shows bottom-right.
       - Closing the window stops playback. Speed, voice and the
         save option are remembered for next time.

UNINSTALL
  Run in Terminal:
    rm -rf ~/Library/Services/"Read Pali Aloud.workflow"
    rm -rf ~/Library/Scripts/PaliTTS

TROUBLESHOOTING
  • "Python environment is broken" — Python was upgraded/removed;
    run the installer again.
  • "No Pali text detected" — the tool filters out English and
    section numbers; make sure the selection contains Pali words.
  • "Transliteration failed" — the local converter failed and the
    online aksharamukha API was unreachable; re-run the installer.
  • "Audio generation failed" — check internet; Microsoft TTS
    (speech.platform.bing.com) must be reachable.
  • Service not in right-click menu — try System Settings →
    Privacy & Security → Automation, or log out and back in.
