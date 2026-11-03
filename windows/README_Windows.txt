Read Pāli Aloud (Pali TTS) — Windows
====================================

REQUIREMENTS
  • Windows 10 or 11, 64-bit
  • Nothing else to install: Python and all libraries are inside the installer
  • Internet connection for the Microsoft voice

NETWORK DOMAINS TO WHITELIST (if on a filtered network)
  • aksharamukha-plugin.appspot.com  (HTTPS port 443, fallback only)
  • speech.platform.bing.com         (WSS  port 443)

INSTALLATION
  1. Double-click PaliTTS-Setup.exe.
     The installer is not signed, so Windows may show
     "Windows protected your PC": click "More info" → "Run anyway".
  2. Click through the installer (no administrator password needed;
     it installs for your Windows user only).

HOW TO USE
  • Select text in any program (browser, PDF, Word...) and press
    Ctrl + Alt + P. The window opens with the selected text.
    (The shortcut copies the selection, so it replaces the clipboard.)
  • Or open "Read Pāli Aloud" from the Start menu and paste text.
  The window:
       - Pāli speed slider 0.33x – 1.67x
       - Translation speed: 0.75x – 3x (the Windows voice's own speed)
       - Pāli voice: Male or Female (Microsoft, needs internet)
       - "Save audio to Downloads": always MP3; the speed is added
         to the file name
       - ▶ Play / ⏸ Pause / ▶ Resume, ⏹ Stop; Space bar = play / pause
         (press Esc first if you are typing in the text box)
       - Dark mode checkbox (top right)
       - Read: Pāli / Translation / Both. Translation = every line that is
         not Pāli, in any language, read by one of Windows' own voices
         (offline); choose it under "Translation voice" (all installed
         voices, by language). More voices: Settings → Time & language →
         Speech → Add voices. Both reads Pāli and translation in order.
         "Auto (by language)" (default) picks a voice for each line from
         its language (Chinese, Japanese, Thai, Malay, Spanish, French,
         Vietnamese, Russian...) if such a voice is installed; English and
         languages without a voice use the system voice.
       - Settings are remembered for next time.

UNINSTALL
  Settings → Apps → Installed apps → "Read Pāli Aloud" → Uninstall.

TROUBLESHOOTING
  • Ctrl + Alt + P does nothing: sign out and in again (the small
    shortcut helper starts at login). If another program already uses
    Ctrl + Alt + P, a message says so at login.
  • "Audio generation failed" — check internet; Microsoft TTS
    (speech.platform.bing.com) must be reachable.
