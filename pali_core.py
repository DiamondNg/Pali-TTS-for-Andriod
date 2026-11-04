# Read Pāli Aloud: the text part shared by every platform (Mac, Windows, Android):
# speeds, Pāli/translation detection, Pāli → Kannada script, Microsoft's voices.
# Android builds only when this file (not pali_tts.py, the desktop app) changes.
# Copyright (C) 2026 Āyasmā Paññādhammika
#
# This program is free software: you can redistribute it and/or modify it under the
# terms of the GNU Affero General Public License as published by the Free Software Foundation,
# either version 3 of the License, or (at your option) any later version.
# It is distributed WITHOUT ANY WARRANTY; see the file LICENSE for details.
import os
import re

try:  # HTTPS certificates for the bundled Python
    import certifi
    os.environ.setdefault("SSL_CERT_FILE", certifi.where())
except ImportError:
    pass


ENGLISH_MARKERS = {
    "the", "of", "is", "are", "was", "were", "and", "that", "this", "with",
    "he", "she", "it", "they", "his", "her", "their", "there", "when", "which",
    "have", "has", "had", "not", "but", "for", "from", "into", "will", "would",
    "should", "does", "do", "an", "in", "on", "at", "by", "as", "or", "if",
    "here", "how", "what", "who", "one", "all", "also", "then", "than",
    "i", "you", "we", "my", "to", "be", "thus", "said", "heard", "been",
    "these", "those", "them", "him", "its", "our", "your", "may", "can",
    "must", "such", "because", "about",
}
# IAST Pāli never uses these letters; English often does
NON_PALI_LETTERS = re.compile(r"[fqwxz]")
PALI_DIACRITICS = re.compile(r"[āīūṃṁṅñṭḍṇḷĀĪŪṂṀṄÑṬḌṆḶ]")

# (label, edge-tts rate, multiplier; the multiplier is no longer used)
# The teacher's old 0.75x is the new 1x; every old step was scaled by 4/3
# (old 1x -> 1.33x, old 1.25x -> 1.67x); old 1.5x and 1.75x were dropped.
SPEEDS = [
    ("0.33x", "-75%", 1 / 3),
    ("0.67x", "-50%", 2 / 3),
    ("1x",    "-25%", 1.0),
    ("1.33x", "+0%",  4 / 3),
    ("1.67x", "+25%", 5 / 3),
]
DEFAULT_SPEED = 2  # 1x
# Speed of the computer's own voice for translations (separate from the Pāli speed).
# 3x is the top: Windows' classic SAPI voices cannot go faster.
TRANSLATION_SPEEDS = [0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0]

def speed_label(mult):
    return "%gx" % mult


# ── Pali filtering ────────────────────────────────────────────────────────────
def is_latin_char(ch):
    cp = ord(ch)
    return cp < 0x0250 or (0x1E00 <= cp <= 0x1EFF)

def is_non_latin_line(line):
    alpha = [ch for ch in line if ch.isalpha()]
    if not alpha:
        return False
    return sum(1 for ch in alpha if not is_latin_char(ch)) / len(alpha) > 0.3

def is_section_marker(line):
    return len(re.sub(r'[\s\d\.\(\)\[\]\-–—:;,\xa7ivxlcmIVXLCM]', '', line.strip())) == 0

def is_english_line(line):
    words = re.findall(r"[a-zA-Z]+", line.lower())
    if not words:
        return False
    matches = sum(1 for w in words if w in ENGLISH_MARKERS or NON_PALI_LETTERS.search(w))
    if PALI_DIACRITICS.search(line) and matches < 2:
        return False
    return matches >= 2 or (len(words) >= 3 and matches / len(words) > 0.3)

# Every letter of romanised (IAST) Pāli; a word with any other letter is not Pāli
PALI_WORD = re.compile(r"[aāiīuūeokgṅcjñṭḍṇtdnpbmyrlvshḷṃṁ]+")
# Pāli words end in a vowel or ṃ; most Malay, Spanish, English... lines have
# words ending in other consonants ("dengar", "ocasión", "heard")
CLOSED_WORD = re.compile(r".*[^aāiīuūeoṃṁ]$")
# Pāli quotation ending "…"ti / "…"nti (iti), and doubled aspirates (bhikkhu, gacchati)
QUOTE_TI = re.compile(r"[\"'”’]n?ti\b")
PALI_CLUSTER = re.compile(r"kkh|ggh|cch|jjh|tth|ddh|pph|bbh")

def line_language(line):
    """"pi" (Pāli), "en" (translation: any other language), or None (too short to tell).

    Other scripts (Chinese, Thai, ...) and English count as translation. Latin text
    is Pāli when its words use only Pāli letters and (nearly) all end in a vowel
    or ṃ — this also catches Pāli typed without diacritics ("Namo tassa bhagavato")."""
    if is_non_latin_line(line):
        return "en"
    words = re.findall(r"[^\W\d_]+", line.lower())
    if not words:
        return None
    if is_english_line(line):
        return "en"
    n = len(words)
    foreign = sum(1 for w in words if not PALI_WORD.fullmatch(w))
    closed = sum(1 for w in words if CLOSED_WORD.match(w))
    if foreign / n >= 0.3 or closed / n > 0.2:
        return "en"
    if PALI_DIACRITICS.search(line) or n >= 3:
        return "pi"
    # Short line without diacritics ("bhikkhavo"ti.): Pāli if it has a clear sign
    # of Pāli and no common word of another language (2-letter ones like na/te are Pāli too); otherwise too short to tell
    if not any(w in ENGLISH_MARKERS or (len(w) > 2 and any(w in m for m in LATIN_MARKERS.values()))
               for w in words) and (QUOTE_TI.search(line.lower()) or PALI_CLUSTER.search(line.lower())):
        return "pi"
    return None

# Which language a translation line is in, for the "Auto" voice
SCRIPTS = [  # (first, last code point, language)
    (0x3040, 0x30FF, "ja"),  # Hiragana/Katakana (checked before Han)
    (0xAC00, 0xD7AF, "ko"), (0x1100, 0x11FF, "ko"),
    (0x4E00, 0x9FFF, "zh"), (0x3400, 0x4DBF, "zh"),
    (0x0E00, 0x0E7F, "th"), (0x0E80, 0x0EFF, "lo"), (0x1780, 0x17FF, "km"),
    (0x1000, 0x109F, "my"), (0x0D80, 0x0DFF, "si"), (0x0900, 0x097F, "hi"),
    (0x0980, 0x09FF, "bn"), (0x0B80, 0x0BFF, "ta"), (0x0C00, 0x0C7F, "te"),
    (0x0C80, 0x0CFF, "kn"), (0x0D00, 0x0D7F, "ml"), (0x0A80, 0x0AFF, "gu"),
    (0x0A00, 0x0A7F, "pa"), (0x0600, 0x06FF, "ar"), (0x0590, 0x05FF, "he"),
    (0x0370, 0x03FF, "el"), (0x0400, 0x04FF, "ru"), (0x10A0, 0x10FF, "ka"),
]
LATIN_MARKERS = {  # common short words of languages written in Latin letters
    "ms": "yang dan ini itu dengan untuk tidak ada saya dia mereka akan dari kepada pada "
          "oleh telah sudah atau juga kami kita adalah apa bagaimana",
    "es": "el la los las que y de del en un una por con para es no se lo su al como más",
    "fr": "le la les des est et que une un dans pour pas qui sur au du ce il elle je",
    "de": "der die das und ist nicht ich ein eine zu mit von den dem sich auch es",
    "it": "il che di è non una per con del della sono gli le lo un si come",
    "pt": "o que não uma os as com para do da em um é se ao dos das mas",
    "nl": "de het een en van is dat niet ik zijn met voor op te",
    "tl": "ang ng mga sa na at ay si ni ito",
}
LATIN_MARKERS = {k: set(v.split()) for k, v in LATIN_MARKERS.items()}
VIETNAMESE = re.compile(r"[ăâđêôơưĂÂĐÊÔƠƯẠ-ỹ]")

def guess_language(line):
    """Language code ("en", "zh", "ms", ...) of a non-Pāli line."""
    counts = {}
    for ch in line:
        cp = ord(ch)
        for lo, hi, code in SCRIPTS:
            if lo <= cp <= hi:
                counts[code] = counts.get(code, 0) + 1
                break
    if counts:
        if "ja" in counts:
            return "ja"  # Japanese mixes kana with Chinese characters
        if "ru" in counts and re.search(r"[іїєґІЇЄҐ]", line):
            return "uk"
        return max(counts, key=counts.get)
    if VIETNAMESE.search(line):
        return "vi"
    words = re.findall(r"[^\W\d_]+", line.lower())
    best, score = "en", sum(1 for w in words if w in ENGLISH_MARKERS)
    for code, markers in LATIN_MARKERS.items():
        n = sum(1 for w in words if w in markers)
        if n > score:
            best, score = code, n
    return best

def split_segments(text):
    """[(lang, text)] in reading order; lang is "pi" (Pāli) or the language code
    of a translation line ("en", "zh", "ms", ...)."""
    segs, pending = [], []
    for ln in text.splitlines():
        if not ln.strip() or is_section_marker(ln):
            continue
        lang = line_language(ln)
        if lang is None:  # short line: goes with its neighbours
            if not segs:
                pending.append(ln)
                continue
            lang = segs[-1][0]
        elif lang == "en":
            lang = guess_language(ln)
        if pending:
            ln = " ".join(pending + [ln])
            pending = []
        if segs and segs[-1][0] == lang:
            segs[-1] = (lang, segs[-1][1] + " " + ln)
        else:
            segs.append((lang, ln))
    if pending:
        segs.append(("pi", " ".join(pending)))
    return [(lang, " ".join(t.split())) for lang, t in segs]

def clean_pali(text):
    # Quotes would make the voice pause (sarīran"ti): delete them, no space
    return re.sub(r"[\"'“”‘’]", "", text)

def filter_pali_lines(text):
    kept = [t for lang, t in split_segments(text) if lang == "pi"]
    # Nothing looks like Pāli (e.g. typed without diacritics): read it all
    return " ".join(kept) if kept else " ".join(ln for ln in text.splitlines() if ln.strip())

# ── Aksharamukha API ──────────────────────────────────────────────────────────
# ññ: Aksharamukha writes ಞ್ಞ, which the Kannada voice says like "bb" (aññaṃ →
# "abbaṃ"). The teacher compared 6 spellings (v2.1 "ññ test") and chose ನ್ನ್ಯ.
NYA_AKSHARAMUKHA = "ಞ್ಞ"
NYA_SPOKEN = "ನ್ನ್ಯ"

def to_kannada(text):
    # aksharamukha handles ṃ (dot-below) but not ṁ (dot-above)
    text = clean_pali(text).replace("ṁ", "ṃ").replace("Ṁ", "Ṃ")
    try:
        kannada = _to_kannada_local(text)
    except Exception:
        kannada = _to_kannada_online(text)
    for ch in [".", ";", "!", "?"]:
        kannada = kannada.replace(ch, "।")
    return kannada.replace(NYA_AKSHARAMUKHA, NYA_SPOKEN)

def _to_kannada_local(text):
    # Offline, via the aksharamukha package (installed by the installer).
    # aksharamukha 2.3 does an unused `from ast import Str`, which
    # Python 3.14 removed; provide a stand-in so the import succeeds.
    import ast
    if not hasattr(ast, "Str"):
        ast.Str = str
    from aksharamukha import transliterate
    return transliterate.process("IASTPali", "Kannada", text, nativize=True)

def _to_kannada_online(text):
    import urllib.request
    import urllib.parse
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
        return resp.read().decode("utf-8")


# ── Edge TTS ──────────────────────────────────────────────────────────────────
async def _generate(kannada_text, output_path, rate, voice):
    import edge_tts
    communicate = edge_tts.Communicate(kannada_text, voice, rate=rate)
    await communicate.save(output_path)

def generate_audio(kannada_text, output_path, rate, voice):
    import asyncio
    asyncio.run(_generate(kannada_text, output_path, rate, voice))

def generate_audio_many(jobs, rate, voice):
    """jobs: [(kannada_text, output_path)], generated concurrently."""
    import asyncio

    async def run():
        await asyncio.gather(*[_generate(t, p, rate, voice) for t, p in jobs])
    asyncio.run(run())


# ── Offline voices ───────────────────────────────────────────────────────────
def rate_factor(rate):
    """edge-tts rate ("-25%") → speed factor (0.75) for the offline voices, so that
    every voice is equally fast at the same slider step."""
    return 1 + int(rate.rstrip("%")) / 100


# ── Text received from another program ────────────────────────────────────────
def prepare_text(raw):
    """Text as received from another program, ready for the text box."""
    import unicodedata
    raw = unicodedata.normalize("NFC", raw)  # ā as one letter, not a + ̄
    raw = raw.replace("\r\n", "\n").replace("\r", "\n").strip()
    # Dashes become pauses; quotes are removed later from the Pāli only
    for ch in ["—", "–"]:
        raw = raw.replace(ch, " ")
    dump = os.environ.get("PALI_TTS_DUMP")  # automated tests: record the text received
    if dump:
        try:
            with open(dump, "w", encoding="utf-8") as f:
                f.write(raw)
        except OSError:
            pass
    return raw
