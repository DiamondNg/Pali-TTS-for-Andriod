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
WHY THE OLD SHORTCUT SOUNDED GARBLED  (two real causes, both fixed below)
════════════════════════════════════════════════════════════════

The old shortcut (tested 2026-11-05 on the Mac with "shortcuts run") had
TWO faults:

  1. In "Get Contents of URL" the field "source" was set to "Pāḷi".
     "Pāḷi" is NOT a code the Aksharamukha website understands, so the
     website gave the text BACK UNCHANGED (still in Latin letters). The
     Kannada voice then tried to read Latin letters -> garbled nonsense.
     The source MUST be exactly:  IASTPali   (see Step 4).

  2. There was NO clean-up at all: no quote removal, no ññ fix, and — most
     important — no fix for letters stored as "letter + separate mark".
     Text copied from Books, Safari, many PDFs and websites stores ñ as
     "n" + a separate tilde mark. Aksharamukha mis-reads only that one
     letter (ñ), and ñ/ññ is in a huge share of Pāli words (paññā,
     suññatā, aññā, ñāṇa, saññā…). So most sentences came out wrong.
     Step 3 fixes this.

Good news from the test: the Aksharamukha WEBSITE gives EXACTLY the same
Kannada as the desktop app (pali_core.to_kannada) once "source" is
IASTPali — so the website itself is fine. Only ñ written as "n + mark"
needs fixing before sending; every other Pāli letter is read correctly
whether or not it is stored with a separate mark.

If you already have a shortcut, the FASTEST fix is PART 4 (two edits).
To build a clean one from scratch, use PART 3.

════════════════════════════════════════════════════════════════
PART 1 — CHECK THE KANNADA VOICE  (do this first, on each device)
════════════════════════════════════════════════════════════════

If no Kannada voice is installed, iOS reads the Kannada letters with
another voice. That sounds garbled or silent.

  1. Settings -> Accessibility -> Spoken Content -> Voices
  2. Look for "Kannada". Tap it and download a voice (tap the cloud
     icon). Wait until the download finishes. The voice is usually
     shown as "Soumya".
  3. If there is no "Kannada" in the list, your iOS version has no
     Kannada voice. Then this shortcut cannot work properly —
     tell Claude which iOS version you have.

Note: the Kannada voice has a DIFFERENT internal name on each device
(on this Mac its id is "...enhanced.kn-IN.Alpana" but it is shown as
"Soumya"). So if you copy a shortcut from one device to another, open
Step 7 again on the new device and pick its Kannada voice — a voice
chosen on the iPad may not exist on the Mac, and the reverse.

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
              and in Part 3 step 7 choose the Kannada voice by name.
       • The SAME Latin letters you typed (aññaṃ dhammaṃ), unchanged
           -> "source" is wrong. It must be IASTPali -> Part 4 / Step 4.
              (This was the old shortcut's main fault.)
       • English words, an error message, or web page code (< >)
           -> the website failed -> check internet, try again later.
       • Kannada letters but with a stray "n" before each ñ-word
           -> the ñ "n + mark" problem -> Step 3.
  5. Delete the Quick Look action afterwards (long-press it -> Delete).

════════════════════════════════════════════════════════════════
PART 3 — BUILD THE SHORTCUT FROM SCRATCH
════════════════════════════════════════════════════════════════

Tip: to copy the special text below (Kannada letters, the ñ with a tilde,
regex), open this page on the iPhone/iPad, press and hold on it, Copy,
then paste.

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

── Step 3: Fix ñ, ṁ and dashes ──────────────────────────────────

  These three "Replace Text" actions are REQUIRED (not optional). Each
  one must use the result of the one before it ("Updated Text") —
  Shortcuts normally links it by itself; check the Input says
  "Updated Text", not "Shortcut Input".

  3a. Fix ñ stored as "n + mark"  (the big one)
      Add "Replace Text", Regular Expression ON:
        Find:          n\x{0303}
        Replace with:  ñ      (copy this ñ from this page)
      Add "Replace Text", Regular Expression ON:
        Find:          N\x{0303}
        Replace with:  Ñ
      (\x{0303} is the separate tilde mark. This is the one letter
       Aksharamukha gets wrong when it is stored that way. All other
       Pāli letters are fine, so they need no such fix.)

  3b. Fix ṁ (dot ABOVE) -> ṃ (dot BELOW), both ways it can be stored
      Add "Replace Text", Regular Expression ON:
        Find:          ṁ|m\x{0307}
        Replace with:  ṃ      (copy this ṃ — dot BELOW — from this page)
      Add "Replace Text", Regular Expression ON:
        Find:          Ṁ|M\x{0307}
        Replace with:  Ṃ
      (Aksharamukha does not read ṁ with the dot above; the desktop app
       changes it to ṃ too.)

  3c. Dashes -> a space
      Add "Replace Text", Regular Expression ON:
        Find:          [—–]
        Replace with:  (one space)

── Step 4: Convert to Kannada letters ───────────────────────────

  Add action "Get Contents of URL".
    URL:  https://aksharamukha-plugin.appspot.com/api/public
    Show More:
      Method:        POST
      Request Body:  Form
      Add 4 fields (Text type):
        source    IASTPali      ⚠ EXACTLY this. NOT "Pāḷi", NOT "Pali".
        target    Kannada
        nativize  true
        text      -> tap the value, choose the magic variable
                     "Updated Text" (result of the LAST Replace Text in
                     Step 3, NOT "Shortcut Input")

  ⚠ Two things break this step silently:
     • "source" anything other than IASTPali -> the website returns your
       Latin text unchanged and the voice garbles it.
     • "text" still set to "Shortcut Input" -> Steps 2–3 are skipped.

── Step 5: Fix ññ and the final nasal (niggahita ṃ) ─────────────

  These two "Replace Text" actions run on the KANNADA (the result of
  "Get Contents of URL"). Regular Expression OFF for both. The first one's
  Input is "Contents of URL"; the second one's Input is "Updated Text".

  5a. ññ
      The Kannada voice says ಞ್ಞ like "bb" (aññaṃ -> "abbaṃ").
      The teacher chose the spelling ನ್ನ್ಯ instead.
        Find:          ಞ್ಞ
        Replace with:  ನ್ನ್ಯ

  5b. niggahita ṃ  ->  "ng"   (Apple-voice workaround, iOS only)
      Aksharamukha writes niggahita as the anusvara ಂ. Microsoft's
      Kannada voice (desktop/Android) reads ಂ correctly, but Apple's
      Kannada voice (Soumya) says a word-final ಂ like "ma" (evaṃ ->
      "evama"). The owner chose the Sri-Lankan-chanting "ng" sound,
      which is the Kannada ಙ್ (velar nasal + halant):
        Find:          ಂ
        Replace with:  ಙ್
      Then, in case any ṁ with the dot ABOVE slipped through Step 3b:
        Find:          ṁ
        Replace with:  ಙ್
      (Do NOT do 5b on the desktop app — only the Apple Kannada voice
       needs it. The Microsoft voice should keep ಂ.)

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
    Voice:     choose the Kannada voice by name (it is usually shown as
               "Soumya"). "Default" also works IF a Kannada voice is
               installed and is your default — but picking by name is
               safer. Do this again on each device (see Part 1 note).
    Rate:      start at the middle; slower = more to the left
    Pitch:     middle

  Tap Done. The shortcut is saved.

════════════════════════════════════════════════════════════════
PART 4 — FASTEST FIX FOR AN EXISTING (GARBLED) SHORTCUT
════════════════════════════════════════════════════════════════

If you already made a shortcut that only has "Get Contents of URL" and
"Speak Text" (and sounds garbled), you do not have to rebuild it:

  1. Open it in Shortcuts. Tap "Get Contents of URL" -> Show More.
  2. In the form find the field "source". Change its value from "Pāḷi"
     (or whatever is there) to exactly:  IASTPali
     -> This alone makes clear Kannada speech for most text.
  3. For perfect reading of ñ-words and quotes, add the Step 2, Step 3,
     Step 5 and Step 6 "Replace Text" actions above, in that order
     (Step 2/3 BEFORE "Get Contents of URL"; Step 5/6 AFTER it), and make
     sure "Get Contents of URL" -> field "text" uses "Updated Text".
  4. Open "Speak Text" and pick the Kannada voice by name (Part 1 note).

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

  Garbled / foreign-sounding voice, OR it reads your Latin letters:
    Almost always "source" is not IASTPali -> Part 4 step 2. Then check
    Part 1 (Kannada voice) and step 7 (choose the voice by name).
    Also check you selected only Pāli, no English.

  Most words fine but ñ-words wrong (a stray "n" sound):
    Step 3a is missing or its Input is "Shortcut Input" instead of
    "Updated Text".

  "The operation couldn't be completed" or blank:
    The Aksharamukha website may be down, or no internet. Try later.

  Still says "abbaṃ" for aññaṃ:
    Step 5a must come AFTER "Get Contents of URL", and its Find text
    must be the Kannada ಞ್ಞ copied from this page.

  A word ends in "...ma" (evaṃ sounds like "evama"):
    The final nasal (anusvara ಂ) is being read as "ma" by Apple's
    Kannada voice. Add Step 5b (ಂ -> ಙ್, the "ng" sound).

  The popup / Quick Look shows gibberish like "à²ªà²žà³à²žà²¾":
    That is the correct Kannada (ಪಞ್ಞಾ) shown with the wrong text
    encoding — a known iOS quirk when the reply is typed text/html.
    It does NOT affect the voice. Remove the "Show Result" action (you
    don't need the popup) and judge by what you HEAR. Running the reply
    through the Step 5 "Replace Text" actions also turns it into plain
    text, which clears the gibberish downstream.

  Not in the Mac right-click (Services) menu:
    Shortcut Details -> "Use as Quick Action" + "Services Menu" ON, and
    "Receive Text input". Then LOG OUT and back in (the Services menu is
    cached per login). Delete any duplicate copies of the shortcut.

  Not in the Share menu (iPhone/iPad):
    Shortcuts -> long-press Read Pali Aloud -> Details ->
    "Show in Share Sheet" ON.
