Pali TTS — iOS Shortcut (iPad)
==============================

Select Pali text anywhere -> tap Share -> Read Pali Aloud -> audio plays.

BEFORE YOU START
  1. Make sure your iPad is on iOS 15 or later
  2. Install a Kannada voice:
       Settings -> Accessibility -> Spoken Content -> Voices
       -> tap "Add Voice" -> scroll to Kannada -> download Meera or Rishi
  3. You need internet when using the shortcut

════════════════════════════════════════════════════════════════
CREATE THE SHORTCUT
════════════════════════════════════════════════════════════════

Open the Shortcuts app. Tap the blue + button (top right).

── Step 1: Name it ──────────────────────────────────────────────

At the very top where it says "New Shortcut", tap it and type:
  Read Pali Aloud
Tap Done on the keyboard.

── Step 2: Configure what it receives ───────────────────────────

Tap the settings icon at the top right (looks like a slider/toggle icon).

You will see a screen with "Details" options.
  • Tap "Add to Share Sheet" to turn it ON (green)
  • Under "Receive", tap "Nothing" and change it to select:
      ✓ Text
      ✓ Rich Text
    (tick both, then tap Done)
  • Tap Done to go back to the shortcut editor.

── Step 3: Add the first action (POST to aksharamukha) ──────────

At the bottom of the screen, tap the search bar that says
"Search for apps and actions".

Type: URL
Tap "Get Contents of URL" from the list.

A blue block appears in the shortcut. Now set it up:

  a) Tap the "URL" field inside the block and type (or paste):
       https://aksharamukha-plugin.appspot.com/api/public

  b) Tap "Show More" (or the expand arrow) on the same block.

  c) Tap "Method" and change it from GET to POST.

  d) Tap "Request Body" and choose "Form".

  e) You will see an "Add new field" button. Tap it 4 times
     to add 4 fields. Fill them in like this:

     Field 1:  Key: source    Value: IASTPali
     Field 2:  Key: target    Value: Kannada
     Field 3:  Key: nativize  Value: true
     Field 4:  Key: text      Value: [see below]

     For Field 4 value: don't type anything.
     Instead tap the Value box, then tap the orange/blue
     "Shortcut Input" pill that appears above the keyboard.
     This inserts the selected text automatically.

── Step 4: Add the second action (Speak) ────────────────────────

Tap the search bar again at the bottom.
Type: Speak
Tap "Speak Text" from the list.

A new block appears. Set it up:

  a) The text field in the block should already say
     "Contents of URL" — if not, tap it and select
     "Contents of URL" from the suggestions.

  b) Tap "Show More" on the Speak Text block:
       Language: tap it -> search for Kannada -> select "Kannada (India)"
       Rate: 0.45
       Pitch: 1.0
       Wait Until Finished: turn ON

── Step 5: Save ─────────────────────────────────────────────────

Tap Done (top right). The shortcut is saved.

════════════════════════════════════════════════════════════════
HOW TO USE IT
════════════════════════════════════════════════════════════════

  1. In any app — PDF reader, Safari, Books, Word — press and
     hold on Pali text until the selection handles appear.
     Drag to select the text you want.

  2. Tap the Share icon (box with arrow pointing up), OR
     tap "Share" in the popup menu above the selected text.

  3. In the Share Sheet that slides up, look for
     "Read Pali Aloud". You may need to scroll right
     along the top row of icons.

  4. Tap it — audio starts playing in a few seconds.

FIRST TIME ONLY: iOS may ask "Allow Read Pali Aloud to access
your network?" — tap Allow.

To change speed: open Shortcuts app, tap the shortcut,
tap the Speak Text block, change Rate:
  0.3 = slow  |  0.45 = normal  |  0.6 = fast

════════════════════════════════════════════════════════════════
IF YOU CAN'T FIND IT IN THE SHARE SHEET
════════════════════════════════════════════════════════════════

  1. Open Shortcuts app
  2. Long-press "Read Pali Aloud" -> Details
  3. Make sure "Add to Share Sheet" is ON
  4. Try sharing again — it should now appear

════════════════════════════════════════════════════════════════
TROUBLESHOOTING
════════════════════════════════════════════════════════════════

  No sound / wrong language:
    Check the Kannada voice is downloaded:
    Settings -> Accessibility -> Spoken Content -> Voices -> Kannada

  "The operation couldn't be completed" or blank result:
    The aksharamukha API may be temporarily down. Try again shortly.

  Shortcut runs but nothing happens:
    Make sure "Wait Until Finished" is ON in the Speak Text block.
