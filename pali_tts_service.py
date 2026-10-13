import sys
import os
import re
import asyncio
import subprocess
import urllib.request
import urllib.parse
import tempfile
import shlex
import shutil
from datetime import datetime

import edge_tts

SAVE_TO_DOWNLOADS = "--save" in sys.argv
VOICE = "kn-IN-SapnaNeural" if "--female" in sys.argv else "kn-IN-GaganNeural"

RATE = "+0%"
if "--slow" in sys.argv:
    RATE = "-25%"
elif "--fast" in sys.argv:
    RATE = "+50%"
elif "--very-fast" in sys.argv:
    RATE = "+100%"

# Common English words that identify a line as an English translation
ENGLISH_MARKERS = {
    "the", "of", "is", "are", "was", "were", "and", "that", "this", "with",
    "he", "she", "it", "they", "his", "her", "their", "there", "when", "which",
    "have", "has", "had", "not", "but", "for", "from", "into", "will", "would",
    "should", "does", "do", "an", "in", "on", "at", "by", "as", "or", "if",
    "here", "how", "what", "who", "one", "all", "also", "then", "than",
}


def notify(message):
    subprocess.run(
        ["osascript", "-e", "display notification \"" + message + "\" with title \"Pali TTS\""],
        capture_output=True,
    )


def to_kannada(text):
    # aksharamukha handles ṃ (dot-below, U+1E43) but not ṁ (dot-above, U+1E41)
    text = text.replace("ṁ", "ṃ").replace("Ṁ", "Ṃ")
    # POST instead of GET so large pages don't hit URL length limits
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
    # Replace Latin punctuation with Indic equivalents so TTS doesn't read them as words
    kannada = kannada.replace(".", "।")
    kannada = kannada.replace(";", "।")
    kannada = kannada.replace("!", "।")
    kannada = kannada.replace("?", "।")
    return kannada


def is_latin_char(ch):
    cp = ord(ch)
    # Latin Basic, Latin-1, Latin Extended A/B, and Latin Extended Additional (Pali diacritics)
    return cp < 0x0250 or (0x1E00 <= cp <= 0x1EFF)


def is_non_latin_line(line):
    """True if the line is mostly Indic/non-Latin script (Sinhala, Devanagari, etc.)."""
    alpha = [ch for ch in line if ch.isalpha()]
    if not alpha:
        return False
    non_latin = sum(1 for ch in alpha if not is_latin_char(ch))
    return non_latin / len(alpha) > 0.3


def is_section_marker(line):
    """True if the line is just a number, bullet, or section label (e.g. '5.', '(iv)', '§3')."""
    stripped = re.sub(r'[\s\d\.\(\)\[\]\-–—:;,§ivxlcmIVXLCM]', '', line.strip())
    return len(stripped) == 0


def is_english_line(line):
    """True if the line looks like English prose."""
    words = re.findall(r"[a-zA-Z]+", line.lower())
    if not words:
        return False
    matches = sum(1 for w in words if w in ENGLISH_MARKERS)
    return matches >= 2 or (len(words) >= 3 and matches / len(words) > 0.3)


def filter_pali_lines(text):
    """Drop English and non-Latin-script lines; keep Roman Pali."""
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


def main():
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

    play_cmd = "afplay " + shlex.quote(tmp_path) + " && rm " + shlex.quote(tmp_path)

    if SAVE_TO_DOWNLOADS:
        words = text.split()[:4]
        base = "_".join(words)
        base = re.sub(r'[/:\\*?"<>|,;.\(\)]', "", base).strip("_") or "pali_audio"
        downloads_dir = os.path.expanduser("~/Downloads")
        mp3_name = base + ".mp3"
        mp3_path = os.path.join(downloads_dir, mp3_name)
        if os.path.exists(mp3_path):
            mp3_name = base + "_" + datetime.now().strftime("%H%M%S") + ".mp3"
            mp3_path = os.path.join(downloads_dir, mp3_name)
        shutil.copy(tmp_path, mp3_path)
        subprocess.Popen(["bash", "-c", play_cmd])
        notify("Playing - Saved to Downloads: " + mp3_name)
    else:
        subprocess.Popen(["bash", "-c", play_cmd])
        notify("Playing Pali audio")


if __name__ == "__main__":
    main()
