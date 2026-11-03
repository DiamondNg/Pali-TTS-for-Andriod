#!/bin/bash
# Automated test of the Android app on the emulator (CI). No sound can be checked:
# Microsoft's voices refuse GitHub's servers, so only the rest is tested.
set -uo pipefail
PKG=org.sasanarakkha.readpalialoud
APK=$(ls dist/*.apk | head -1)
mkdir -p shots
fail() { echo "FAIL: $*"; exit 1; }

adb install -r "$APK" || fail "install"
adb logcat -c

ui_dump() {  # visible texts of the screen → shots/$1.xml
  adb shell uiautomator dump /sdcard/ui.xml >/dev/null 2>&1
  adb pull /sdcard/ui.xml "shots/$1.xml" >/dev/null 2>&1
}

wait_log() {  # wait up to $2 s for $1 in the app's log
  for _ in $(seq 1 "$2"); do
    adb logcat -d -s PaliTTS:* | grep -q "$1" && return 0
    sleep 1
  done
  return 1
}

echo "== 1. Self-test: Python, Aksharamukha, language detection, phone voices, joining audio"
adb shell am start -n "$PKG/.MainActivity" --ez selftest true
wait_log "SELFTEST OK\|SELFTEST FAILED" 180
adb logcat -d -s PaliTTS:* python.stdout:* python.stderr:* AndroidRuntime:* | tee shots/selftest.log
grep -q "SELFTEST OK" shots/selftest.log || fail "selftest"
grep -q "ನಮೋ ತಸ್ಸ ಭಗವತೋ" shots/selftest.log || fail "Kannada transliteration"
grep -q '"nya": true' shots/selftest.log || fail "ññ spelling"
grep -q "SELFTEST piper" shots/selftest.log || fail "offline Piper voice"
grep -q '"en", "Homage to the Blessed One' shots/selftest.log || fail "translation line not detected"
sleep 2
adb exec-out screencap -p > shots/1_start.png
ui_dump 1_start
grep -q "Pāli speed:  1x" shots/1_start.xml || fail "speed label (Python speeds)"
echo "OK: main window"
sleep 3
adb shell dumpsys notification --noredact | grep -A3 "pkg=$PKG" | head -20 | tee shots/notification.txt
grep -q "pkg=$PKG" shots/notification.txt || fail "no player notification while playing"
adb shell dumpsys media_session | grep -A6 "ReadPaliAloud" | head -20
adb shell input keyevent KEYCODE_HOME
sleep 2
adb shell cmd statusbar expand-notifications
sleep 2
adb exec-out screencap -p > shots/1b_notification.png
adb shell cmd statusbar collapse
adb shell dumpsys activity services "$PKG" | grep -q "PlaybackService" || fail "player stopped when the app left the screen"
echo "OK: background player + notification"

echo "== 2. Text selected in another app → Read Pāli Aloud (PROCESS_TEXT)"
adb logcat -c
adb shell "am start -a android.intent.action.PROCESS_TEXT -t text/plain --es android.intent.extra.PROCESS_TEXT 'Evaṃ me sutaṃ — ekaṃ samayaṃ bhagavā.'"
sleep 15
adb exec-out screencap -p > shots/2_process_text.png
ui_dump 2_process_text
grep -q "Evaṃ me sutaṃ  ekaṃ samayaṃ bhagavā." shots/2_process_text.xml || \
  grep -q "Evaṃ me sutaṃ" shots/2_process_text.xml || fail "selected text not shown"
grep -o 'text="[^"]*"' shots/2_process_text.xml | head -40
adb logcat -d -s PaliTTS:* python.stderr:* | tail -30

echo "== 3. Share → Read Pāli Aloud (SEND), Both mode text"
adb shell "am start -a android.intent.action.SEND -t text/plain --es android.intent.extra.TEXT 'Namo tassa bhagavato.\nHomage to the Blessed One.'"
sleep 10
adb exec-out screencap -p > shots/3_share.png
ui_dump 3_share
grep -q "Namo tassa bhagavato" shots/3_share.xml || fail "shared text not shown"

echo "== 4. Dark mode"
adb shell cmd uimode night yes
sleep 4
adb exec-out screencap -p > shots/4_dark.png
adb shell cmd uimode night no

echo "== 5. Help"
adb shell am force-stop "$PKG"
adb shell am start -n "$PKG/.MainActivity"
sleep 6
adb logcat -d -s AndroidRuntime:E | grep -q "FATAL EXCEPTION" && fail "app crashed"
echo "ALL ANDROID TESTS PASSED"
