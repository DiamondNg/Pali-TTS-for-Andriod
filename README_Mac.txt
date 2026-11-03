Read Pāli Aloud (Pali TTS) — macOS
==================================

REQUIREMENTS
  • macOS 11 or later on Apple Silicon (M1/M2/M3/M4...);
    macOS 10.15 (Catalina) or later on Intel Macs
  • Nothing else to install: Python and all libraries are inside the DMG
  • Internet connection for the Microsoft voice (Pali→Kannada script
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
     The installer creates the app "Read Pāli Aloud" in Applications
     (about 70–100 MB) — no internet needed to install.
  2. When finished it says "Done!" — close the Terminal window.
  3. If the shortcut or right-click menu item does not work at once,
     log out and back in (or restart).

HOW TO USE
  • Select text in any app (browser, PDF, Word...) and press
    Control-Command-O, or right-click → Services → "Read Pali Aloud".
    (Change the shortcut: System Settings → Keyboard → Keyboard
    Shortcuts → Services → Text.)
  • Or open "Read Pāli Aloud" from Launchpad / Applications and paste text.
  The window:
       - Pāli speed slider 0.33x – 1.67x (1x = the old 0.75x)
       - Translation speed: 0.75x – 3x (the Mac voice's own speed)
       - Read: Pāli / Translation / Both. Translation = every line that is
         not Pāli, in any language (English, Chinese, Malay...), read by
         one of the Mac's own voices (offline); choose it under
         "Translation voice" (all installed voices, by language; more in
         System Settings → Accessibility → Spoken Content → System voice
         → Manage Voices). Both reads Pāli and translation lines in order,
         e.g. a SuttaCentral page with Pāli and English selected.
         "Auto (by language)" (default) picks a voice for each line from
         its language (Chinese, Japanese, Thai, Malay, Spanish, French,
         Vietnamese, Russian...) if such a voice is installed; English and
         languages without a voice use the system voice.
       - Pāli voice: Male or Female (Microsoft, needs internet)
       - "Save audio to Downloads": always MP3; the speed is added
         to the file name
       - ▶ Play / ⏸ Pause / ▶ Resume, ⏹ Stop; Space bar = play / pause
         (press Esc first if you are typing in the text box)
       - Dark mode checkbox (top right); by default it follows the Mac
       - ññ (aññaṃ, paññā...) is read with the spelling the teacher chose
         in the v2.1 test (number 4).
       - Settings are remembered for next time.

UNINSTALL
  Run in Terminal:
    rm -rf ~/Library/Services/"Read Pali Aloud.workflow"
    rm -rf /Applications/"Read Pāli Aloud.app" ~/Applications/"Read Pāli Aloud.app"

TROUBLESHOOTING
  • "The app is damaged" — run the installer again.
  • "No Pali text detected" — the tool filters out non-Pāli lines and
    section numbers; make sure the selection contains Pali words.
  • "Transliteration failed" — the local converter failed and the
    online aksharamukha API was unreachable; re-run the installer.
  • "Audio generation failed" — check internet; Microsoft TTS
    (speech.platform.bing.com) must be reachable.
  • Service not in right-click menu — try System Settings →
    Privacy & Security → Automation, or log out and back in.
