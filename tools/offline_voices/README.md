# Offline Kannada voices: test kit (Mac)

Lets you hear Pāḷi read by **offline** Kannada voices before we put one in the app. Nothing is
installed in the system: everything goes into the folder `~/PaliTTS-voice-test` (delete it to
remove all). Pāḷi → Kannada script uses the online Aksharamukha service, like the first version.

Voices compared (one after another, same text):

1. **Mac "Soumya"** — Kannada voice built into macOS (free download in System Settings).
2. **Piper `kn_IN-syspin_male-medium`** — neural, male, from
   [micahchoo/piper-kn](https://huggingface.co/micahchoo/piper-kn) (about 60 MB).
3. **eSpeak NG `kn`** — rule-based, very small, robotic.

Each result is also saved in `Downloads/Kannada voice test/` (with the Kannada text).

## 1. Set up (once, about 5 minutes)

1. Open **Terminal** (Cmd‑Space, type `Terminal`, Enter).
2. Paste this line and press Enter:

   ```bash
   curl -fsSL https://raw.githubusercontent.com/DiamondNg/Pali-TTS-for-Andriod/claude/admiring-faraday-g9lutn/tools/offline_voices/setup_voice_test.sh | bash
   ```
3. Wait for "Done". It then reads "Evaṃ me sutaṃ…" with each voice.
4. If it says Soumya is not installed: System Settings → Accessibility → Spoken Content →
   System voice → **Manage Voices…** → Kannada → tick **Soumya**. (Your system voice does not
   have to change.)

## 2. Quick Action in Automator (right-click on selected text)

1. Open **Automator** (Cmd‑Space, `Automator`) → **New Document** → **Quick Action** → Choose.
2. At the top: *Workflow receives current* **text** in **any application**.
3. In the search box on the left type `shell`; drag **Run Shell Script** to the right.
4. Shell: `/bin/bash`; *Pass input*: **as arguments**. Replace the text in the box with:

   ```bash
   ~/PaliTTS-voice-test/run.sh "$@"
   ```
5. File → Save → name it `Try Kannada Voices`.
6. Use it: select Pāḷi text anywhere → right‑click → **Services** (or Quick Actions) →
   **Try Kannada Voices**. Notifications show which voice is speaking.
   (Optional shortcut: System Settings → Keyboard → Keyboard Shortcuts → Services → Text.)

To hear only one voice, use `ONLY=piper ~/PaliTTS-voice-test/run.sh "$@"` in step 4
(`mac`, `piper` or `espeak`).

## Notes

- Windows: as far as we know Windows has **no** built-in Kannada voice (Settings → Time &
  language → Speech lists none). If you find one, it will already appear in the app's
  "Translation voice" list.
- Piper and eSpeak NG also run on Windows and Android, so if Piper sounds good it can work
  everywhere; the Mac voice works only on Mac/iPhone.
