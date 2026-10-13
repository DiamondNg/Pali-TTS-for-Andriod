import sys
import os
import re
import asyncio
import subprocess
import urllib.request
import urllib.parse
import tempfile
import shutil
import threading
from datetime import datetime

import edge_tts
from playsound import playsound

# ── Parse arguments ───────────────────────────────────────────────────────────
args = sys.argv[1:]
SAVE_TO_DOWNLOADS = "--save" in args
VOICE = "kn-IN-SapnaNeural" if "--female" in args else "kn-IN-GaganNeural"

RATE = "+0%"
if "--slow" in args:
    RATE = "-25%"
elif "--fast" in args:
    RATE = "+50%"
elif "--very-fast" in args:
    RATE = "+100%"

INPUT_FILE = None
for i, a in enumerate(args):
    if a == "--input-file" and i + 1 < len(args):
        INPUT_FILE = args[i + 1]

CREATE_NO_WINDOW = 0x08000000

# ── Common English markers for translation-line detection ────────────────────
ENGLISH_MARKERS = {
    "the", "of", "is", "are", "was", "were", "and", "that", "this", "with",
    "he", "she", "it", "they", "his", "her", "their", "there", "when", "which",
    "have", "has", "had", "not", "but", "for", "from", "into", "will", "would",
    "should", "does", "do", "an", "in", "on", "at", "by", "as", "or", "if",
    "here", "how", "what", "who", "one", "all", "also", "then", "than",
}


def notify(message):
    ps = (
        "[System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms') | Out-Null; "
        "$n = New-Object System.Windows.Forms.NotifyIcon; "
        "$n.Icon = [System.Drawing.SystemIcons]::Information; "
        "$n.Visible = $true; "
        "$n.ShowBalloonTip(3000, 'Pali TTS', '" + message.replace("'", "") + "', 1); "
        "Start-Sleep 4; $n.Dispose()"
    )
    subprocess.Popen(
        ["powershell", "-WindowStyle", "Hidden", "-Command", ps],
        creationflags=CREATE_NO_WINDOW,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def to_kannada(text):
    text = text.replace("ṁ", "ṃ").replace("Ṁ", "Ṃ")
    data = urllib.parse.urlencode({
        "source": "IASTPali",
        "target": "Kannada",
        "nativize": "true",
        "text": text,
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://aksharamukha-plugin.appspot.com/api/public",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        kannada = resp.read().decode("utf-8")
    kannada = kannada.replace(".", "।")
    kannada = kannada.replace(";", "।")
    kannada = kannada.replace("!", "।")
    kannada = kannada.replace("?", "।")
    return kannada


def is_latin_char(ch):
    cp = ord(ch)
    return cp < 0x0250 or (0x1E00 <= cp <= 0x1EFF)


def is_non_latin_line(line):
    alpha = [ch for ch in line if ch.isalpha()]
    if not alpha:
        return False
    non_latin = sum(1 for ch in alpha if not is_latin_char(ch))
    return non_latin / len(alpha) > 0.3


def is_section_marker(line):
    stripped = re.sub(r'[\s\d\.\(\)\[\]\-–—:;,§ivxlcmIVXLCM]', '', line.strip())
    return len(stripped) == 0


def is_english_line(line):
    words = re.findall(r"[a-zA-Z]+", line.lower())
    if not words:
        return False
    matches = sum(1 for w in words if w in ENGLISH_MARKERS)
    return matches >= 2 or (len(words) >= 3 and matches / len(words) > 0.3)


def filter_pali_lines(text):
    lines = text.splitlines()
    kept = [
        ln for ln in lines
        if ln.strip()
        and not is_section_marker(ln)
        and not is_english_line(ln)
        and not is_non_latin_line(ln)
    ]
    return " ".join(kept) if kept else " ".join(ln for ln in lines if ln.strip())


async def generate_audio(kannada_text, output_path):
    communicate = edge_tts.Communicate(kannada_text, VOICE, rate=RATE)
    await communicate.save(output_path)


def play_and_cleanup(path):
    try:
        playsound(path)
    except Exception:
        pass
    finally:
        try:
            os.unlink(path)
        except Exception:
            pass


def main():
    # Read input from file (written by AutoHotkey) or stdin
    if INPUT_FILE:
        try:
            with open(INPUT_FILE, "r", encoding="utf-8") as f:
                raw = f.read().strip()
            os.unlink(INPUT_FILE)
        except Exception as e:
            notify("Could not read input file: " + str(e))
            sys.exit(1)
    else:
        raw = sys.stdin.read().strip()

    if not raw:
        notify("No text received.")
        sys.exit(1)

    for ch in ["“", "”", "‘", "’", "—", "–"]:
        raw = raw.replace(ch, " ")

    text = filter_pali_lines(raw)
    text = " ".join(text.split())

    if not text:
        notify("No Pali text detected in selection.")
        sys.exit(1)

    try:
        kannada = to_kannada(text)
    except Exception as e:
        notify("Transliteration failed (check internet): " + str(e))
        sys.exit(1)

    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".mp3")
    os.close(tmp_fd)

    try:
        asyncio.run(generate_audio(kannada, tmp_path))
    except Exception as e:
        notify("Audio generation failed (check internet): " + str(e))
        os.unlink(tmp_path)
        sys.exit(1)

    if SAVE_TO_DOWNLOADS:
        words = text.split()[:4]
        base = "_".join(words)
        base = re.sub(r'[/:\\*?"<>|,;.\(\)]', "", base).strip("_") or "pali_audio"
        downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        mp3_name = base + ".mp3"
        mp3_path = os.path.join(downloads_dir, mp3_name)
        if os.path.exists(mp3_path):
            mp3_name = base + "_" + datetime.now().strftime("%H%M%S") + ".mp3"
            mp3_path = os.path.join(downloads_dir, mp3_name)
        shutil.copy(tmp_path, mp3_path)
        notify("Playing - Saved to Downloads: " + mp3_name)
    else:
        notify("Playing Pali audio")

    # Non-daemon thread keeps process alive until audio finishes
    thread = threading.Thread(target=play_and_cleanup, args=(tmp_path,))
    thread.start()
    thread.join()


if __name__ == "__main__":
    main()
