Read Pāli Aloud — iOS Shortcut (iPhone and iPad)
================================================

Select Pāli text anywhere -> Share -> Read Pali Aloud -> it is spoken.

What it does: sends the Pāli to the Aksharamukha website, which writes it
in Kannada letters, then an Apple Kannada voice reads those letters.
It does the same clean-up as the desktop app: removes quotes, fixes ṁ and
ññ, and turns . ; ! ? into pauses.

Limits (compared with the desktop/Android app):
  • Select ONLY Pāli. English lines would be turned into Kannada letters
    too and sound like nonsense.
  • Needs internet (for the Aksharamukha website).
  • Uses Apple's Kannada voice (not the Microsoft voice: Shortcuts can't
    reach it).

════════════════════════════════════════════════════════════════
PART 1 — CHECK THE KANNADA VOICE  (most common cause of garbled sound)
════════════════════════════════════════════════════════════════

If no Kannada voice is installed, iOS reads the Kannada letters with
another voice. That sounds garbled or silent.

  1. Settings -> Accessibility -> Spoken Content -> Voices
  2. Look for "Kannada". Tap it and download a voice (tap the cloud
     icon). Wait until the download finishes.
  3. If there is no "Kannada" in the list, your iOS version has no
     Kannada voice. Then this shortcut cannot work properly —
     tell Claude which iOS version you have.

════════════════════════════════════════════════════════════════
PART 2 — FIND WHERE IT GOES WRONG  (2 minutes, do this once)
════════════════════════════════════════════════════════════════

  1. Open your existing shortcut in the Shortcuts app.
  2. Below "Get Contents of URL" add the action "Quick Look"
     (search: Quick Look).
  3. Run the shortcut on the test word:  aññaṃ dhammaṃ
  4. Look at what Quick Look shows:
       • Kannada letters (like ಅನ್ನ್ಯಂ ಧಮ್ಮಂ or ಅಞ್ಞಂ ಧಮ್ಮಂ)
           -> the text is fine; the VOICE is the problem -> Part 1,
              and in Part 3 step 9 choose the Kannada voice by name.
       • English words, an error message, or web page code (< >)
           -> the website failed -> check internet, try again later.
       • Latin letters with odd marks or boxes
           -> the input is the problem -> Part 3 step 3.
  5. Delete the Quick Look action afterwards (long-press it -> Delete).

════════════════════════════════════════════════════════════════
PART 3 — BUILD THE IMPROVED SHORTCUT
════════════════════════════════════════════════════════════════

Tip: to copy the special text below (Kannada letters, regex), open this
page on the iPhone/iPad, press and hold on it, Copy, then paste.

Open Shortcuts -> tap + (top right). Name it:  Read Pali Aloud

── Step 1: Receive text from the Share menu ─────────────────────

  Tap the (i) / settings button -> turn ON "Show in Share Sheet".
  At the top of the shortcut a block appears: "Receive ... from".
    • Tap the input types -> keep only Text (and Rich Text).
    • "If there's no input" -> choose "Get Clipboard".
      (So you can also Copy text and run the shortcut from its icon.)

── Step 2: Remove quotes ────────────────────────────────────────

  Add action "Replace Text".
    Find:           ["'“”‘’]
    Replace with:   (leave EMPTY)
    Input:          Shortcut Input
    Show More -> Regular Expression: ON
  (Quotes make the voice pause in the middle of "sarīran’ti".)

── Step 3: Fix ṁ and dashes ─────────────────────────────────────

  Add "Replace Text":   Find  ṁ   Replace with  ṃ
                        (Regular Expression OFF, Case Sensitive ON)
  Add "Replace Text":   Find  Ṁ   Replace with  Ṃ
  Add "Replace Text":   Find  [—–]   Replace with  (one space)
                        Regular Expression ON

  Each new Replace Text must use the result of the one before
  ("Updated Text") — Shortcuts normally links it by itself.

  ONLY if Part 2 showed odd marks/boxes (letters stored as "a + mark"),
  add one more Replace Text per letter, Regular Expression ON:
      Find  a\x{0304}   Replace with  ā
      Find  i\x{0304}   Replace with  ī
      Find  u\x{0304}   Replace with  ū
      Find  m\x{0323}   Replace with  ṃ
      Find  n\x{0307}   Replace with  ṅ
      Find  n\x{0303}   Replace with  ñ
      Find  t\x{0323}   Replace with  ṭ
      Find  d\x{0323}   Replace with  ḍ
      Find  n\x{0323}   Replace with  ṇ
      Find  l\x{0323}   Replace with  ḷ

── Step 4: Convert to Kannada letters ───────────────────────────

  Add action "Get Contents of URL".
    URL:  https://aksharamukha-plugin.appspot.com/api/public
    Show More:
      Method:        POST
      Request Body:  Form
      Add 4 fields (Text type):
        source    IASTPali
        target    Kannada
        nativize  true
        text      -> tap the value, choose the magic variable
                     "Updated Text" (result of the LAST Replace Text,
                     NOT "Shortcut Input")

  ⚠ If "text" still uses "Shortcut Input", steps 2–3 are skipped.

── Step 5: Fix ññ ───────────────────────────────────────────────

  The Kannada voice says ಞ್ಞ like "bb" (aññaṃ -> "abbaṃ").
  The teacher chose the spelling ನ್ನ್ಯ instead.

  Add "Replace Text":
    Find:          ಞ್ಞ
    Replace with:  ನ್ನ್ಯ
    Input:         Contents of URL
    Regular Expression OFF

── Step 6: Full stops become pauses ─────────────────────────────

  Add "Replace Text":
    Find:          [.;!?]
    Replace with:  ।
    Regular Expression ON

── Step 7: Speak ────────────────────────────────────────────────

  Add action "Speak Text". Text = "Updated Text" (from step 6).
  Show More:
    Wait Until Finished:  ON
    Language:  Kannada (India)
    Voice:     choose the Kannada voice by name (not "Default")
    Rate:      start at the middle; slower = more to the left
    Pitch:     middle

  Tap Done. The shortcut is saved.

════════════════════════════════════════════════════════════════
HOW TO USE IT
════════════════════════════════════════════════════════════════

  1. In any app (Safari, Books, PDF reader…) press and hold on the
     Pāli text and drag the handles to select it.
  2. Tap "Share" in the menu above the selection
     (or the Share icon: a box with an arrow).
  3. Tap "Read Pali Aloud" (scroll the list if needed;
     "Edit Actions" lets you put it at the top).
  4. First time: allow the shortcut to use the internet / send text
     to aksharamukha-plugin.appspot.com -> "Always Allow".

  Some apps (Books, some PDF readers) share a file instead of text.
  Then: select -> Copy -> run the shortcut from the Shortcuts app or
  from its Home Screen icon (it reads the clipboard).

════════════════════════════════════════════════════════════════
TROUBLESHOOTING
════════════════════════════════════════════════════════════════

  Garbled / foreign-sounding voice:
    Part 1 (Kannada voice), then step 7 (choose the voice by name).
    Also check you selected only Pāli, no English.

  "The operation couldn't be completed" or blank:
    The Aksharamukha website may be down, or no internet. Try later.

  Still says "abbaṃ" for aññaṃ:
    Step 5 must come AFTER "Get Contents of URL", and its Find text
    must be the Kannada ಞ್ಞ copied from this page.

  Not in the Share menu:
    Shortcuts -> long-press Read Pali Aloud -> Details ->
    "Show in Share Sheet" ON.
