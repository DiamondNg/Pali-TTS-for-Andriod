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
  1. Double-click "Read Pāli Aloud v2.5.exe" (the installer).
     The installer is not signed, so Windows may show
     "Windows protected your PC": click "More info" → "Run anyway".
  2. Click through the installer (no administrator password needed;
     it installs for your Windows user only).

HOW TO USE
  (All of this is also in the app: click "Help" at the top of the window.)
  • Select text in any program (browser, PDF, Word...) and press
    Ctrl + Shift + Y. The window opens with the selected text.
  • Or select text with the mouse: a small blue "▶ Read Pāli" button
    appears next to the mouse. Click it and the text is read aloud.
    Esc or a click elsewhere hides the button. Turn it off with the
    checkbox in the window, or tray icon → "Pause Floating Popup".
  • The text is read straight from the program (Windows UI Automation),
    not copied: the clipboard stays as it is, so clipboard tools such as
    GoldenDict are not set off. Programs that don't share their text this
    way (some PDF readers): no button; Ctrl + Shift + Y then copies the
    selection (this replaces the clipboard).
    Windows has no right-click menu for selected text in all programs.
  • Tray icon (bottom right; maybe under the ^ arrow): click = open the
    window; right-click = Settings, Pause Floating Popup, Help, Exit.
  • Close only hides the window; the app stays in the tray so the
    shortcut and button keep working. Quit completely: tray icon → Exit.
  • "Run on Windows startup" (checkbox in the window): starts it in the
    tray when you sign in (on by default; reinstalling turns it on again).
  • Or open "Read Pāli Aloud" from the Start menu and paste text.
  The window:
       - Pāli speed slider 0.33x – 1.67x
       - Translation speed slider 0.75x – 3x (the Windows voice's own speed)
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
       - The window can be made bigger (the text box grows with it).
       - Settings, window size and dark mode are remembered for next time.

UNINSTALL
  Settings → Apps → Installed apps → "Read Pāli Aloud" → Uninstall.

TROUBLESHOOTING
  • Ctrl + Shift + Y or the button do nothing: is the tray icon there?
    If not, open Read Pāli Aloud from the Start menu. If another program
    already uses Ctrl + Shift + Y, the window says so.
  • "Audio generation failed" — check internet; Microsoft TTS
    (speech.platform.bing.com) must be reachable.
