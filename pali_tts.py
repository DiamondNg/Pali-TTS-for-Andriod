import sys
import os
import re
import subprocess
import tempfile
import shutil
import signal
import threading
import time
import json
import platform
from datetime import datetime
import tkinter as tk
from tkinter import ttk
import wave

try:  # HTTPS certificates for the bundled Python
    import certifi
    os.environ.setdefault("SSL_CERT_FILE", certifi.where())
except ImportError:
    pass

IS_MAC     = platform.system() == "Darwin"
IS_WINDOWS = platform.system() == "Windows"
CREATE_NO_WINDOW = 0x08000000

INPUT_FILE = None
for i, a in enumerate(sys.argv[1:], 1):
    if a == "--input-file" and i + 1 < len(sys.argv):
        INPUT_FILE = sys.argv[i + 1]

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
ENGLISH_WPM = 175  # macOS `say` words per minute at 1x (all languages)

# "en" = translation: any language that is not Pāli, read by the computer's own voice
MODES = [("Pāli", "pi"), ("Translation", "en"), ("Both", "both")]
SYSTEM_VOICE = "System default"
AUTO_VOICE = "Auto (by language)"  # a voice per line, chosen by its language

PLAY_TEXT   = "\u25B6  Play"
RESUME_TEXT = "\u25B6  Resume"
PAUSE_TEXT  = "\u23F8  Pause"

VOICES = [
    ("Male",   "kn-IN-GaganNeural"),
    ("Female", "kn-IN-SapnaNeural"),
]


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


# ── Translation voices: the computer's own, any language, offline ─────────────
# macOS sound-effect voices: not useful for reading suttas
NOVELTY_VOICES = {
    "Albert", "Bad News", "Bahh", "Bells", "Boing", "Bubbles", "Cellos",
    "Deranged", "Good News", "Hysterical", "Jester", "Organ", "Pipe Organ",
    "Superstar", "Trinoids", "Whisper", "Wobble", "Zarvox",
}

def system_voices():
    """[(label, voice_id)] of all installed voices, sorted by language."""
    try:
        voices = _mac_voices() if IS_MAC else _windows_voices() if IS_WINDOWS else []
    except Exception:
        voices = []
    return sorted(voices, key=lambda v: v[0].lower())

def _mac_voices():
    out = subprocess.run(["say", "-v", "?"], capture_output=True,
                         text=True, timeout=15).stdout
    voices, seen = [], set()
    for line in out.splitlines():
        m = re.match(r"^(.+?)\s+([a-z]{2,3}[_-][A-Za-z0-9]+)\s+#", line)
        if not m:
            continue
        name, lang = m.group(1).strip(), m.group(2).replace("_", "-")
        if name in seen or name in NOVELTY_VOICES:
            continue
        seen.add(name)
        voices.append(("%s · %s" % (lang, name), name))
    return voices

def say_to_file(text, out_path, wpm, voice):
    cmd = ["say", "-r", str(wpm), "-o", out_path]
    if voice:
        cmd += ["-v", voice]
    subprocess.run(cmd + ["-f", "-"], input=text, text=True, check=True,
                   capture_output=True, timeout=600)

# Windows: PowerShell 5.1 (part of Windows 10/11) reaches both kinds of voices:
# "OneCore" voices (Settings → Time & language → Speech, language packs) via
# WinRT, and classic SAPI voices (incl. third-party ones) via System.Speech.
WIN_SPEECH_PS = r"""
param([string]$Mode, [string]$JobFile, [string]$OutFile)
$ErrorActionPreference = 'Stop'
$utf8 = New-Object System.Text.UTF8Encoding $false
function Load-WinRT {
  Add-Type -AssemblyName System.Runtime.WindowsRuntime
  $null = [Windows.Media.SpeechSynthesis.SpeechSynthesizer, Windows.Media.SpeechSynthesis, ContentType = WindowsRuntime]
  $script:asTask = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and
    $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' } | Select-Object -First 1
}
function Await($op, [Type]$type) {
  $t = $script:asTask.MakeGenericMethod($type).Invoke($null, @($op)); $null = $t.Wait(-1); $t.Result
}
if ($Mode -eq 'list') {
  $list = @()
  try { Load-WinRT
    foreach ($v in [Windows.Media.SpeechSynthesis.SpeechSynthesizer]::AllVoices) {
      $list += @{ label = "$($v.Language) · $($v.DisplayName)"; id = "winrt:$($v.Id)" } }
  } catch { }
  try { Add-Type -AssemblyName System.Speech
    $s = New-Object System.Speech.Synthesis.SpeechSynthesizer
    foreach ($v in $s.GetInstalledVoices()) { if ($v.Enabled) { $i = $v.VoiceInfo
      $list += @{ label = "$($i.Culture.Name) · $($i.Name)"; id = "sapi:$($i.Name)" } } }
    $s.Dispose()
  } catch { }
  [IO.File]::WriteAllText($OutFile, (ConvertTo-Json @($list) -Compress), $utf8)
  exit 0
}
$job = [IO.File]::ReadAllText($JobFile, $utf8) | ConvertFrom-Json
$voice = [string]$job.voice; $mult = [double]$job.mult
function Speak-Sapi([string]$name) {
  Add-Type -AssemblyName System.Speech
  $s = New-Object System.Speech.Synthesis.SpeechSynthesizer
  if ($name) { $s.SelectVoice($name) }
  $s.Rate = [int][Math]::Max(-10, [Math]::Min(10, [Math]::Round(10 * [Math]::Log($mult) / [Math]::Log(3))))
  $fmt = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(24000,
    [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)
  foreach ($j in $job.jobs) { $s.SetOutputToWaveFile([string]$j.out, $fmt); $s.Speak([string]$j.text) }
  $s.SetOutputToNull(); $s.Dispose()
}
if ($voice.StartsWith('sapi:')) { Speak-Sapi $voice.Substring(5); exit 0 }
try { Load-WinRT
  $s = New-Object Windows.Media.SpeechSynthesis.SpeechSynthesizer
  if ($voice.StartsWith('winrt:')) {
    $v = [Windows.Media.SpeechSynthesis.SpeechSynthesizer]::AllVoices | Where-Object { $_.Id -eq $voice.Substring(6) } | Select-Object -First 1
    if ($v) { $s.Voice = $v } }
  try { $s.Options.SpeakingRate = [Math]::Max(0.5, $mult) } catch { }
} catch { Speak-Sapi ''; exit 0 }   # no WinRT voices: classic default voice
foreach ($j in $job.jobs) {
  $stream = Await ($s.SynthesizeTextToStreamAsync([string]$j.text)) ([Windows.Media.SpeechSynthesis.SpeechSynthesisStream])
  $in = [System.IO.WindowsRuntimeStreamExtensions]::AsStreamForRead($stream.GetInputStreamAt(0))
  $fs = [IO.File]::Create([string]$j.out); $in.CopyTo($fs); $fs.Close(); $in.Dispose(); $stream.Dispose()
}
"""

def _run_win_speech(*args, timeout=600):
    script = os.path.join(tempfile.gettempdir(), "palitts_speech_v1.ps1")
    with open(script, "w", encoding="utf-8-sig") as f:  # BOM: PowerShell 5.1 reads "·" right
        f.write(WIN_SPEECH_PS)
    r = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive",
                        "-ExecutionPolicy", "Bypass", "-File", script] + list(args),
                       capture_output=True, timeout=timeout, creationflags=CREATE_NO_WINDOW)
    if r.returncode:
        raise RuntimeError(r.stderr.decode("utf-8", "replace")[-2000:])

def _windows_voices():
    fd, out = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    try:
        _run_win_speech("list", "", out, timeout=60)
        with open(out, encoding="utf-8-sig") as f:
            data = json.load(f)
    finally:
        _unlink(out)
    if isinstance(data, dict):
        data = [data]
    return [(d["label"], d["id"]) for d in data if d.get("id")]

# Preferred region when a language has voices for several countries
PREFERRED_REGION = {"en": "en-US", "zh": "zh-CN", "pt": "pt-BR", "es": "es-ES",
                    "fr": "fr-FR", "de": "de-DE", "ar": "ar-SA", "ms": "ms-MY"}
SIMILAR_LANGUAGE = {"ms": ["id"], "id": ["ms"], "uk": ["ru"]}
ELOQUENCE_VOICES = {"Eddy", "Flo", "Grandma", "Grandpa", "Reed", "Rocko", "Sandy", "Shelley"}

def pick_voice(voices, lang):
    """Voice id for language code `lang` from [(label, id)] ("" = system default).
    English uses the system voice (on a Mac usually the best English voice)."""
    if lang == "en":
        return ""
    for code in [lang] + SIMILAR_LANGUAGE.get(lang, []):
        match = [(label, vid) for label, vid in voices
                 if label.lower().split("-")[0].split(" ")[0] == code]
        if match:
            pref = PREFERRED_REGION.get(code, "").lower()
            # Preferred country first; Apple's robotic "Eloquence" voices
            # (Eddy, Flo, Reed... named "Eddy (Chinese (China mainland))") last
            match.sort(key=lambda v: (bool(pref) and not v[0].lower().startswith(pref),
                                      "(" in v[1] or v[1] in ELOQUENCE_VOICES))
            return match[0][1]
    return ""

def speak_many(jobs, voice_id, mult, work):
    """jobs: [(text, path_without_extension)] → [audio file paths], spoken
    by the computer's own voice (voice_id None/"" = system default)."""
    if IS_MAC:
        paths = []
        for text, base in jobs:
            say_to_file(text, base + ".aiff", round(ENGLISH_WPM * mult), voice_id)
            paths.append(base + ".aiff")
        return paths
    if IS_WINDOWS:
        job = {"voice": voice_id or "", "mult": mult,
               "jobs": [{"text": t, "out": b + ".src.wav"} for t, b in jobs]}
        job_file = os.path.join(work, "job.json")
        with open(job_file, "w", encoding="utf-8") as f:
            json.dump(job, f)
        _run_win_speech("speak", job_file, "")
        return [b + ".src.wav" for _, b in jobs]
    raise RuntimeError("No system voice on this computer")


# ── Joining segments ──────────────────────────────────────────────────────────
SAMPLE_RATE = 24000  # = edge-tts output

def to_wav(src, dst):
    """Any audio file → mono 16-bit WAV at SAMPLE_RATE."""
    if IS_MAC:  # afconvert ships with macOS
        subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@%d" % SAMPLE_RATE,
                        "-c", "1", src, dst], check=True, capture_output=True, timeout=600)
        return
    import miniaudio  # Windows: bundled decoder (MP3/WAV) + resampler
    snd = miniaudio.decode_file(src, output_format=miniaudio.SampleFormat.SIGNED16,
                                nchannels=1, sample_rate=SAMPLE_RATE)
    with wave.open(dst, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(snd.samples.tobytes())

def build_joined(parts, rate, voice, voice_for, mult, status=lambda msg: None):
    """parts: [("kn", kannada_text) or (language code, translation_text)] → (wav, seconds).
    Kannada parts use Microsoft's voice; translation parts the computer's own voice
    voice_for(language code) (a voice id, "" = system default)."""
    work = tempfile.mkdtemp(prefix="palitts")
    try:
        bases = [os.path.join(work, "%03d" % i) for i in range(len(parts))]
        srcs = [None] * len(parts)
        kn = [(i, t) for i, (lang, t) in enumerate(parts) if lang == "kn"]
        other = [(i, t) for i, (lang, t) in enumerate(parts) if lang != "kn"]
        if kn:
            status("Generating Pāli audio...")
            for i, _ in kn:
                srcs[i] = bases[i] + ".mp3"
            generate_audio_many([(t, srcs[i]) for i, t in kn], rate, voice)
        if other:
            status("Generating translation audio...")
            groups = {}  # one call per voice (Windows: one PowerShell per voice)
            for i, t in other:
                groups.setdefault(voice_for(parts[i][0]), []).append((i, t))
            for vid, items in groups.items():
                paths = speak_many([(t, bases[i]) for i, t in items], vid, mult, work)
                for (i, _), path in zip(items, paths):
                    srcs[i] = path
        wavs = []
        for src, base in zip(srcs, bases):
            to_wav(src, base + ".wav")
            wavs.append(base + ".wav")
        tmp_fd, out = tempfile.mkstemp(suffix=".wav")
        os.close(tmp_fd)
        return out, join_wavs(wavs, out)
    finally:
        shutil.rmtree(work, ignore_errors=True)

def wav_to_mp3(src, dst, kbps=64):
    """Mono 16-bit WAV → MP3 with the bundled LAME encoder (lameenc)."""
    import lameenc
    with wave.open(src, "rb") as w:
        enc = lameenc.Encoder()
        enc.set_bit_rate(kbps)
        enc.set_in_sample_rate(w.getframerate())
        enc.set_channels(w.getnchannels())
        enc.set_quality(2)
        with open(dst, "wb") as out:
            while True:
                frames = w.readframes(SAMPLE_RATE * 10)
                if not frames:
                    break
                out.write(enc.encode(frames))
            out.write(enc.flush())

def join_wavs(parts, dst, gap=0.4):
    """Concatenate mono 16-bit WAVs with a short silence between them."""
    silence = b"\0\0" * int(SAMPLE_RATE * gap)
    with wave.open(dst, "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(SAMPLE_RATE)
        for i, part in enumerate(parts):
            if i:
                out.writeframes(silence)
            with wave.open(part, "rb") as w:
                out.writeframes(w.readframes(w.getnframes()))
        return out.getnframes() / SAMPLE_RATE


# ── Settings (remembered between uses) ────────────────────────────────────────
def _settings_path():
    if IS_WINDOWS:
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    else:
        base = os.path.join(os.path.expanduser("~"), "Library", "Application Support")
    return os.path.join(base, "PaliTTS", "settings.json")

def load_settings():
    try:
        with open(_settings_path(), encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}

def save_settings(data):
    path = _settings_path()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except OSError:
        pass


# ── Audio helpers ─────────────────────────────────────────────────────────────
def audio_duration(path):
    """Length of the audio file in seconds, or None if unknown."""
    if not IS_MAC:
        return None
    try:
        out = subprocess.run(["afinfo", path], capture_output=True,
                             text=True, timeout=10).stdout
        m = re.search(r"estimated duration:\s*([\d.]+)", out)
        return float(m.group(1)) if m else None
    except Exception:
        return None

class AfplayPlayer:
    """macOS: `afplay` process; pause/resume with SIGSTOP/SIGCONT."""
    def __init__(self, path):
        self.proc = subprocess.Popen(["afplay", path])

    def done(self):
        return self.proc.poll() is not None

    def pause(self):
        os.kill(self.proc.pid, signal.SIGSTOP)

    def resume(self):
        os.kill(self.proc.pid, signal.SIGCONT)

    def stop(self):
        if self.proc.poll() is None:
            self.proc.kill()  # SIGKILL also ends a paused (SIGSTOPped) process
            self.proc.wait()


class MciPlayer:
    """Windows: Media Control Interface (winmm), built into every Windows.
    Use from the Tk main thread only."""
    count = 0

    def __init__(self, path):
        import ctypes
        self._send = ctypes.windll.winmm.mciSendStringW
        self._buf = ctypes.create_unicode_buffer(256)
        MciPlayer.count += 1
        self.alias = "pali%d" % MciPlayer.count
        kind = "waveaudio" if path.lower().endswith(".wav") else "mpegvideo"
        self._mci('open "%s" type %s alias %s' % (path, kind, self.alias), check=True)
        self._mci("set %s time format milliseconds" % self.alias)
        try:
            self._mci("play %s" % self.alias, check=True)
        except OSError:
            self._mci("close %s" % self.alias)
            raise

    def _mci(self, cmd, check=False):
        err = self._send(cmd, self._buf, 255, None)
        if err and check:
            raise OSError("MCI error %d: %s" % (err, cmd))
        return "" if err else self._buf.value

    def length(self):
        try:
            return int(self._mci("status %s length" % self.alias)) / 1000.0
        except ValueError:
            return None

    def done(self):
        return self._mci("status %s mode" % self.alias) not in ("playing", "paused", "seeking")

    def pause(self):
        self._mci("pause %s" % self.alias)

    def resume(self):
        self._mci("resume %s" % self.alias)

    def stop(self):
        self._mci("stop %s" % self.alias)
        self._mci("close %s" % self.alias)


def fmt_time(seconds):
    seconds = int(seconds)
    return "%d:%02d" % (seconds // 60, seconds % 60)


# ── GUI ───────────────────────────────────────────────────────────────────────
MUTED = "#808080"  # secondary text: readable on light and dark backgrounds
APP_VERSION = "2.6"
# Shortcut that opens the window with the selected text (set by the installers)
SHORTCUT = "Cmd+Shift+Y" if IS_MAC else "Ctrl+Shift+Y"

# Colours for the non-macOS dark mode (macOS uses its own dark appearance)
DARK = {"bg": "#1e1e1e", "fg": "#e6e6e6", "field": "#2b2b2b", "accent": "#3a3a3a"}


class PaliTTSWindow:
    def __init__(self, root, initial_text="", tray=None):
        self.root = root
        self.tray = tray          # Windows: tray.Background; closing only hides the window
        self.help_win = None
        self.aqua = root.tk.call("tk", "windowingsystem") == "aqua"

        self.player = None        # AfplayPlayer (macOS) / MciPlayer (Windows)
        self.paused = False
        self.busy = False         # transliterating / generating audio
        self.audio_path = None    # last generated audio, reused when settings match
        self.audio_key = None     # settings key of audio_path
        self.play_key = None      # key of what is playing/paused
        self.saved_key = None     # key last saved to Downloads
        self.audio_secs = None    # length of audio_path in seconds
        self.elapsed = 0.0        # seconds played before the current run
        self.started = None       # time.monotonic() when playback (re)started
        self.poll_id = None       # pending root.after() for _poll
        self.tk_widgets = []      # classic Tk widgets, recoloured for dark mode

        self.settings = settings = load_settings()
        rates = [r for _, r, _ in SPEEDS]
        speed = rates.index(settings["rate"]) if settings.get("rate") in rates else DEFAULT_SPEED
        voice = settings.get("voice")
        if voice not in [v for _, v in VOICES]:
            voice = VOICES[0][1]
        mode = settings.get("mode")
        if mode not in [m for _, m in MODES]:
            mode = "pi"
        # Translation voice: label shown → voice id. The full list loads in the
        # background (Windows needs a second); until then the saved one is offered.
        self.voice_ids = {AUTO_VOICE: "auto", SYSTEM_VOICE: ""}
        self.voices = []          # [(label, id)] of the installed voices
        en_id = settings.get("en_voice")
        en_label = settings.get("en_voice_label") or en_id  # v2.1 saved only a Mac name
        if not (isinstance(en_id, str) and isinstance(en_label, str)) or \
                en_id in ("auto", SYSTEM_VOICE) or "en_voice" not in settings:
            en_label = AUTO_VOICE
        elif not en_id:
            en_label = SYSTEM_VOICE
        else:
            self.voice_ids[en_label] = en_id

        root.title("Read Pāli Aloud")
        root.resizable(True, True)  # minimum size = the packed size, set below
        root.configure(padx=20, pady=15)
        root.protocol("WM_DELETE_WINDOW", self._close)

        # ── Text area + dark mode toggle ─────────────────────────────────────
        top = ttk.Frame(root)
        top.pack(fill="x")
        ttk.Label(top, text="Text  (paste or edit):").pack(side="left")
        self.dark_var = tk.BooleanVar(value=self._initial_dark())
        ttk.Checkbutton(top, text="Dark mode", variable=self.dark_var,
                        command=self._on_dark_toggle).pack(side="right")
        ttk.Button(top, text="Help", width=6,
                   command=self.show_help).pack(side="right", padx=(0, 12))
        txt_frame = tk.Frame(root)
        txt_frame.pack(fill="both", expand=True, pady=(4, 14))  # takes the extra space
        self.tk_widgets.append(txt_frame)
        self.text_box = tk.Text(txt_frame, height=6, width=40, wrap="word",
                                font=("", 10))
        scroll = ttk.Scrollbar(txt_frame, command=self.text_box.yview)
        self.text_box.configure(yscrollcommand=scroll.set)
        self.text_box.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        if initial_text:
            self.text_box.insert("1.0", initial_text)

        # ── Speed ─────────────────────────────────────────────────────────────
        self.speed_label = ttk.Label(root, text="", font=("", 11, "bold"))  # Pāli speed
        self.speed_label.pack(anchor="w")
        self.slider_var = tk.DoubleVar(value=speed)
        slider = ttk.Scale(root, from_=0, to=len(SPEEDS) - 1,
                           orient="horizontal", variable=self.slider_var,
                           command=self._on_drag, length=300)
        slider.pack(fill="x", pady=(4, 0))
        tick_frame = tk.Frame(root)
        tick_frame.pack(fill="x")
        self.tk_widgets.append(tick_frame)
        for label, _, _ in SPEEDS:
            lbl = tk.Label(tick_frame, text=label, fg=MUTED, font=("", 8))
            lbl.pack(side="left", expand=True)
            self.tk_widgets.append(lbl)
        self._on_drag(None)

        # ── What to read ──────────────────────────────────────────────────────
        mode_frame = ttk.Frame(root)
        mode_frame.pack(anchor="w", pady=(12, 0))
        ttk.Label(mode_frame, text="Read:").pack(side="left", padx=(0, 10))
        self.mode_var = tk.StringVar(value=mode)
        for label, value in MODES:
            ttk.Radiobutton(mode_frame, text=label, variable=self.mode_var, value=value,
                            command=self._on_mode).pack(side="left", padx=(0, 12))

        # ── Voices ────────────────────────────────────────────────────────────
        voice_frame = ttk.Frame(root)
        voice_frame.pack(anchor="w", pady=(8, 0))
        ttk.Label(voice_frame, text="Pāli voice:").pack(side="left", padx=(0, 10))
        self.voice_var = tk.StringVar(value=voice)
        for label, voice_id in VOICES:
            ttk.Radiobutton(voice_frame, text=label, variable=self.voice_var,
                            value=voice_id).pack(side="left", padx=(0, 12))
        en_frame = ttk.Frame(root)
        en_frame.pack(anchor="w", pady=(8, 0))
        ttk.Label(en_frame, text="Translation voice:").pack(side="left", padx=(0, 10))
        self.en_voice_var = tk.StringVar(value=en_label)
        self.en_combo = ttk.Combobox(en_frame, textvariable=self.en_voice_var,
                                     values=list(self.voice_ids), height=20,
                                     state="readonly", width=30)
        self.en_combo.pack(side="left")
        # Translation speed: its own slider (the Pāli slider above is unchanged)
        en_speed = settings.get("en_speed")
        if en_speed not in TRANSLATION_SPEEDS:
            en_speed = 1.0
        self.en_speed_label = ttk.Label(root, text="", font=("", 11, "bold"))
        self.en_speed_label.pack(anchor="w", pady=(10, 0))
        self.en_slider_var = tk.DoubleVar(value=TRANSLATION_SPEEDS.index(en_speed))
        self.en_slider = ttk.Scale(root, from_=0, to=len(TRANSLATION_SPEEDS) - 1,
                                   orient="horizontal", variable=self.en_slider_var,
                                   command=self._on_en_drag, length=300)
        self.en_slider.pack(fill="x", pady=(4, 0))
        tick_frame = tk.Frame(root)
        tick_frame.pack(fill="x")
        self.tk_widgets.append(tick_frame)
        for m in TRANSLATION_SPEEDS:
            lbl = tk.Label(tick_frame, text=speed_label(m), fg=MUTED, font=("", 8))
            lbl.pack(side="left", expand=True)
            self.tk_widgets.append(lbl)
        self._on_en_drag(None)
        threading.Thread(target=self._load_voices, daemon=True).start()

        # ── Save checkbox ─────────────────────────────────────────────────────
        self.save_var = tk.BooleanVar(value=bool(settings.get("save", False)))
        ttk.Checkbutton(root, text="Save audio to Downloads",
                        variable=self.save_var).pack(anchor="w", pady=(10, 0))
        self.save_note = ttk.Label(root, text="", foreground=MUTED, font=("", 9))
        self.save_note.pack(anchor="w")
        if tray is not None:  # Windows background options
            self.popup_var = tk.BooleanVar(value=bool(settings.get("popup", True)))
            ttk.Checkbutton(root, text="Show a \u25B6 Read Pāli button when I select text",
                            variable=self.popup_var,
                            command=self._on_popup_toggle).pack(anchor="w", pady=(4, 0))
            self.startup_var = tk.BooleanVar(value=tray.startup_enabled())
            ttk.Checkbutton(root, text="Run on Windows startup", variable=self.startup_var,
                            command=self._on_startup_toggle).pack(anchor="w", pady=(4, 0))

        # ── Buttons ───────────────────────────────────────────────────────────
        btn_frame = ttk.Frame(root)
        btn_frame.pack(fill="x", pady=(14, 0))
        ttk.Button(btn_frame, text="Close",
                   command=self._close).pack(side="left", expand=True, padx=(0, 6))
        self.stop_btn = ttk.Button(btn_frame, text="⏹  Stop",
                                   command=self._stop, state="disabled")
        self.stop_btn.pack(side="left", expand=True, padx=6)
        self.play_btn = ttk.Button(btn_frame, text=PLAY_TEXT, command=self._toggle)
        self.play_btn.pack(side="right", expand=True, padx=(6, 0))

        # ── Status + progress ─────────────────────────────────────────────────
        status_frame = ttk.Frame(root)
        status_frame.pack(fill="x", pady=(8, 0))
        self.status_var = tk.StringVar(value="")
        ttk.Label(status_frame, textvariable=self.status_var,
                  foreground=MUTED, font=("", 9)).pack(side="left")
        self.time_var = tk.StringVar(value="")
        ttk.Label(status_frame, textvariable=self.time_var,
                  foreground=MUTED, font=("", 9)).pack(side="right")
        ttk.Label(root, text="Tip: select text in any app and press " + SHORTCUT +
                  " to open it here", foreground=MUTED, font=("", 8)).pack(anchor="w", pady=(4, 0))
        ttk.Label(root, text="Tip: Space bar = play / pause (Esc leaves the text box) · "
                  "more under Help", foreground=MUTED, font=("", 8)).pack(anchor="w")

        self._on_mode()
        if "dark" in settings:
            self._apply_theme()

        # ── Keyboard ──────────────────────────────────────────────────────────
        root.bind("<space>", self._on_space)
        self.text_box.bind("<Escape>", lambda e: root.focus_set())

        # ── Size (remembered; never smaller than the original) + position ───
        root.update_idletasks()
        self.min_size = (root.winfo_reqwidth(), root.winfo_reqheight())
        root.minsize(*self.min_size)
        self._place(*self._remembered_size())
        if tray is None:
            self._present(bool(initial_text))

    def _remembered_size(self):
        """The saved window size, never smaller than the packed size or bigger than the screen."""
        root = self.root
        min_w, min_h = self.min_size
        size = self.settings.get("size")
        try:
            w, h = max(min_w, int(size[0])), max(min_h, int(size[1]))
        except (TypeError, ValueError, IndexError):
            w, h = min_w, min_h
        return min(w, root.winfo_screenwidth()), min(h, root.winfo_screenheight() - 70)

    def _place(self, w, h):
        """Size w×h, centred on the mouse pointer, whole window on screen."""
        root = self.root
        cx = root.winfo_pointerx()
        cy = root.winfo_pointery()
        # Keep the whole window on screen (below the macOS menu bar)
        x = max(0, min(cx - w // 2, root.winfo_screenwidth() - w))
        y = max(30, min(cy - h // 2, root.winfo_screenheight() - h - 40))
        root.geometry("%dx%d+%d+%d" % (w, h, x, y))

    def _present(self, has_text):
        root = self.root
        root.deiconify()
        root.lift()
        root.attributes("-topmost", True)
        root.after(200, lambda: root.attributes("-topmost", False))
        root.focus_force()
        if has_text:
            root.focus_set()  # so Space plays straight away
        else:
            self.text_box.focus_set()

    # ── Shown again from the tray / shortcut / floating button (Windows) ─────
    def show(self, text=None, autoplay=False):
        """Bring the window up; text (if given) replaces the text box's text."""
        hidden = self.root.state() == "withdrawn"
        if text is not None:
            text = prepare_text(text)
            if text:
                self._stop()
                self.text_box.delete("1.0", "end")
                self.text_box.insert("1.0", text)
            elif hidden:
                self.status_var.set("No selected text found: paste the text here.")
        if hidden:  # appear where the mouse is, at the remembered size
            # (not winfo_width/height: a window that was never shown reports 1x1,
            # which minsize turned into the smallest size)
            self._place(*self._remembered_size())
        self._present(bool(text))
        if autoplay and text and not self.busy:
            self._start()

    def _on_popup_toggle(self):
        self.settings["popup"] = bool(self.popup_var.get())
        self.tray.set_popup_enabled(self.settings["popup"])
        self._save_settings()

    def set_popup(self, enabled):  # from the tray menu
        self.popup_var.set(bool(enabled))
        self.settings["popup"] = bool(enabled)
        self._save_settings()

    def _on_startup_toggle(self):
        if not self.tray.set_startup(bool(self.startup_var.get())):
            self.startup_var.set(self.tray.startup_enabled())
            self.status_var.set("Could not change the Windows startup setting.")

    # ── Help ──────────────────────────────────────────────────────────────────
    def show_help(self):
        if self.help_win is not None and self.help_win.winfo_exists():
            self.help_win.deiconify()
            self.help_win.lift()
            self.help_win.focus_force()
            return
        win = self.help_win = tk.Toplevel(self.root)
        win.title("Read Pāli Aloud – Help")
        win.geometry("560x520")
        win.minsize(360, 260)
        frame = tk.Frame(win)
        frame.pack(fill="both", expand=True)
        box = tk.Text(frame, wrap="word", font=("", 10), padx=12, pady=10,
                      relief="flat", borderwidth=0)
        scroll = ttk.Scrollbar(frame, command=box.yview)
        box.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        box.pack(side="left", fill="both", expand=True)
        box.tag_configure("h", font=("", 11, "bold"), spacing1=8, spacing3=2)
        for line in help_text(tray=self.tray is not None).splitlines():
            if line.startswith("# "):
                box.insert("end", line[2:] + "\n", "h")
            else:
                box.insert("end", line + "\n")
        box.configure(state="disabled")
        ttk.Button(win, text="Close", command=win.destroy).pack(pady=8)
        win.bind("<Escape>", lambda e: win.destroy())
        if bool(self.dark_var.get()):
            if self.aqua:
                try:
                    win.tk.call("::tk::unsupported::MacWindowStyle", "appearance",
                                win, "darkaqua")
                except tk.TclError:
                    pass
            else:
                win.configure(bg=DARK["bg"])
                frame.configure(bg=DARK["bg"])
                box.configure(bg=DARK["field"], fg=DARK["fg"])
        win.lift()
        win.focus_force()

    # ── Dark mode ─────────────────────────────────────────────────────────────
    def _initial_dark(self):
        if "dark" in self.settings:
            return bool(self.settings["dark"])
        if self.aqua:  # follow the Mac's appearance until the user chooses
            try:
                return bool(int(self.root.tk.call(
                    "::tk::unsupported::MacWindowStyle", "isdark", self.root)))
            except (tk.TclError, ValueError):
                return False
        return False

    def _on_dark_toggle(self):
        self.settings["dark"] = bool(self.dark_var.get())
        self._apply_theme()
        self._save_settings()  # at once, in case the window is not closed normally

    def _apply_theme(self):
        dark = bool(self.dark_var.get())
        if self.aqua:
            # Native macOS dark/light appearance for this window
            try:
                self.root.tk.call("::tk::unsupported::MacWindowStyle", "appearance",
                                  self.root, "darkaqua" if dark else "aqua")
            except tk.TclError:
                pass
            return
        style = ttk.Style(self.root)
        if not hasattr(self, "_light_theme"):
            self._light_theme = style.theme_use()
            self._light_bg = self.root.cget("bg")
            self._light_text = (self.text_box.cget("bg"), self.text_box.cget("fg"))
        if dark:
            style.theme_use("clam")
            bg, fg, field, accent = DARK["bg"], DARK["fg"], DARK["field"], DARK["accent"]
            style.configure(".", background=bg, foreground=fg, fieldbackground=field)
            style.configure("TButton", background=accent)
            style.configure("TScrollbar", troughcolor=bg, background=accent)
            style.configure("Horizontal.TScale", troughcolor=field, background=accent)
            style.map("TButton", background=[("active", "#4a4a4a")])
            style.map("TCombobox", fieldbackground=[("readonly", field)],
                      foreground=[("readonly", fg)])
            style.map("TCheckbutton", background=[("active", bg)])
            style.map("TRadiobutton", background=[("active", bg)])
            self.root.configure(bg=bg)
            self.text_box.configure(bg=field, fg=fg, insertbackground=fg)
            for wdg in self.tk_widgets:
                wdg.configure(bg=bg)
        else:
            style.theme_use(self._light_theme)
            self.root.configure(bg=self._light_bg)
            self.text_box.configure(bg=self._light_text[0], fg=self._light_text[1],
                                    insertbackground=self._light_text[1])
            for wdg in self.tk_widgets:
                wdg.configure(bg=self._light_bg)

    # ── Settings ──────────────────────────────────────────────────────────────
    def _speed_index(self):
        return max(0, min(len(SPEEDS) - 1, round(self.slider_var.get())))

    def _on_drag(self, _value):
        idx = self._speed_index()
        self.slider_var.set(idx)
        self.speed_label.config(text="Pāli speed:  " + SPEEDS[idx][0])

    def _load_voices(self):
        voices = system_voices()
        self._after(self._voices_loaded, voices)

    def _voices_loaded(self, voices):
        self.voices = voices
        ids = {AUTO_VOICE: "auto", SYSTEM_VOICE: ""}
        ids.update(voices)
        current = self.en_voice_var.get()
        if current not in ids:
            # Saved voice was renamed or removed: keep it if its id still exists
            saved_id = self.voice_ids.get(current)
            match = [label for label, vid in voices if vid == saved_id]
            self.en_voice_var.set(match[0] if match else SYSTEM_VOICE)
        self.voice_ids = ids
        self.en_combo.config(values=list(ids))

    def _on_mode(self):
        mode = self.mode_var.get()
        self.en_combo.config(state="disabled" if mode == "pi" else "readonly")
        self.en_slider.state(["disabled"] if mode == "pi" else ["!disabled"])
        self.save_note.config(text="Saved as MP3 at the chosen speed and voice%s."
                              % ("" if mode == "pi" else "s"))

    def _en_speed(self):
        idx = max(0, min(len(TRANSLATION_SPEEDS) - 1, round(self.en_slider_var.get())))
        return TRANSLATION_SPEEDS[idx]

    def _on_en_drag(self, _value):
        speed = self._en_speed()
        self.en_slider_var.set(TRANSLATION_SPEEDS.index(speed))
        self.en_speed_label.config(text="Translation speed:  " + speed_label(speed))

    def _current_key(self):
        """Settings key (mode, segments, Pāli speed index, Pāli voice, translation voice id,
        translation speed), or None."""
        text_content = self.text_box.get("1.0", "end-1c").strip()
        if not text_content:
            self.status_var.set("Please paste some text first.")
            return None
        mode = self.mode_var.get()
        if mode == "pi":
            text = " ".join(filter_pali_lines(text_content).split())
            segs = (("pi", text),) if text else ()
        else:
            if not (IS_MAC or IS_WINDOWS):
                self.status_var.set("Translation voices work on Mac and Windows only.")
                return None
            segs = tuple(split_segments(text_content))
            if mode == "en":
                segs = tuple(sg for sg in segs if sg[0] != "pi")
        if not segs:
            self.status_var.set("No translation (non-Pāli) text detected." if mode == "en"
                                else "No Pāli text detected.")
            return None
        en_voice = self.voice_ids.get(self.en_voice_var.get(), "") if mode != "pi" else None
        en_speed = self._en_speed() if mode != "pi" else None
        return (mode, segs, self._speed_index(), self.voice_var.get(), en_voice, en_speed)

    # ── Play / Pause / Stop ───────────────────────────────────────────────────
    def _on_space(self, event):
        # Let Space type in the text box and activate focused buttons as usual
        if event.widget is self.text_box or isinstance(
                event.widget, (ttk.Button, ttk.Checkbutton, ttk.Radiobutton, ttk.Combobox)):
            return None
        self._toggle()
        return "break"

    def _played_secs(self):
        if self.started is None:
            return self.elapsed
        return self.elapsed + time.monotonic() - self.started

    def _show_time(self):
        played = self._played_secs()
        if self.audio_secs:
            self.time_var.set(fmt_time(min(played, self.audio_secs)) + " / " +
                              fmt_time(self.audio_secs))
        else:
            self.time_var.set(fmt_time(played))

    def _is_playing(self):
        return self.player is not None and not self.player.done()

    def _toggle(self):
        if self.busy:
            return
        if self._is_playing():
            if not self.paused:
                self._pause()
                return
            # Paused: resume, unless text/speed/voice changed meanwhile
            if self._current_key() == self.play_key:
                self._resume()
                return
            self._stop()
        self._start()

    def _start(self):
        key = self._current_key()
        if key is None:
            return
        if key == self.audio_key and self.audio_path and os.path.exists(self.audio_path):
            self._begin_playback(key)
            return
        self.busy = True
        self.time_var.set("")
        self.play_btn.config(state="disabled")
        self.status_var.set("Connecting...")
        threading.Thread(target=self._generate, args=(key,), daemon=True).start()

    def _generate(self, key):
        mode, segs, speed, voice, en_voice, en_speed = key
        _, rate, _ = SPEEDS[speed]
        if mode == "pi":  # one MP3 straight from Microsoft
            try:
                self._set_status("Transliterating...")
                kannada = to_kannada(segs[0][1])
            except Exception:
                self._after(self._generation_failed, "Transliteration failed — check internet.")
                return
            tmp_fd, tmp_path = tempfile.mkstemp(suffix=".mp3")
            os.close(tmp_fd)
            try:
                self._set_status("Generating audio...")
                generate_audio(kannada, tmp_path, rate, voice)
            except Exception:
                _unlink(tmp_path)
                self._after(self._generation_failed, "Audio generation failed — check internet.")
                return
            self._after(self._generated, key, tmp_path, audio_duration(tmp_path))
            return

        # Translation / Both: make each part, convert to WAV, join into one file
        try:
            self._set_status("Transliterating...")
            parts = [("kn", to_kannada(text)) if lang == "pi" else (lang, text)
                     for lang, text in segs]
            voices = self.voices
            voice_for = (lambda lang: pick_voice(voices, lang)) if en_voice == "auto" \
                else (lambda lang: en_voice)
            out, secs = build_joined(parts, rate, voice, voice_for, en_speed, self._set_status)
        except Exception:
            self._after(self._generation_failed, "Audio generation failed — check internet.")
            return
        self._after(self._generated, key, out, secs)

    def _generation_failed(self, msg):
        self.busy = False
        self.status_var.set(msg)
        self.play_btn.config(state="normal")

    def _generated(self, key, path, secs):
        self.busy = False
        self.audio_secs = secs
        self.play_btn.config(state="normal")
        if self.audio_path and self.audio_path != path:
            _unlink(self.audio_path)
        self.audio_path, self.audio_key = path, key
        self._begin_playback(key)

    def _begin_playback(self, key):
        saved_msg = self._save_if_requested(key)
        self.play_key = key
        self.paused = False
        self.status_var.set(saved_msg or "Playing...")
        try:
            if IS_MAC:
                self.player = AfplayPlayer(self.audio_path)
            elif IS_WINDOWS:
                self.player = MciPlayer(self.audio_path)
                if not self.audio_secs:
                    self.audio_secs = self.player.length()
            else:
                self.status_var.set("Playback works on Mac and Windows only.")
                return
        except OSError:
            self.player = None
            self.status_var.set("Could not play the audio.")
            return
        self.elapsed, self.started = 0.0, time.monotonic()
        self._show_time()
        self.play_btn.config(text=PAUSE_TEXT)
        self.stop_btn.config(state="normal")
        self._poll(self.player)

    def _poll(self, player):
        if player is not self.player:
            return  # stopped or replaced
        if not player.done():
            if not self.paused:
                self._show_time()
            self.poll_id = self.root.after(200, self._poll, player)
            return
        player.stop()
        self.started = None
        if self.audio_secs:
            self.elapsed = self.audio_secs
        self._show_time()
        self.player = None
        self.paused = False
        self.play_btn.config(text=PLAY_TEXT)
        self.stop_btn.config(state="disabled")
        if self.status_var.get() == "Playing...":
            self.status_var.set("Done.")

    def _pause(self):
        self.player.pause()
        self.elapsed, self.started = self._played_secs(), None
        self.paused = True
        self.play_btn.config(text=RESUME_TEXT)
        self.status_var.set("Paused.")

    def _resume(self):
        self._save_if_requested(self.play_key)
        self.player.resume()
        self.started = time.monotonic()
        self.paused = False
        self.play_btn.config(text=PAUSE_TEXT)
        self.status_var.set("Playing...")

    def _stop(self):
        player, self.player = self.player, None
        if player is not None:
            player.stop()
        self.started = None
        self.time_var.set("")
        self.paused = False
        self.play_btn.config(text=PLAY_TEXT)
        self.stop_btn.config(state="disabled")
        if not self.busy:
            self.status_var.set("Stopped.")

    def _save_if_requested(self, key):
        if not self.save_var.get() or key == self.saved_key:
            return None
        mode, segs, speed = key[0], key[1], key[2]
        words = segs[0][1].split()[:4]
        base = "_".join(words)
        base = re.sub(r'[/:\\*?"<>|,;.\(\)\'“”‘’]', "", base).strip("_") or "pali_audio"
        en_speed = speed_label(key[5]) if mode != "pi" else ""
        if mode == "pi":
            base += "_" + SPEEDS[speed][0]
        elif mode == "en":
            base += "_translation_" + en_speed
        else:
            base += "_pali_%s_translation_%s" % (SPEEDS[speed][0], en_speed)
        ext = ".mp3"
        dl = os.path.join(os.path.expanduser("~"), "Downloads")
        name = base + ext
        path = os.path.join(dl, name)
        if os.path.exists(path):
            name = base + "_" + datetime.now().strftime("%H%M%S") + ext
            path = os.path.join(dl, name)
        try:
            if mode == "pi":  # already MP3 from Microsoft
                shutil.copy(self.audio_path, path)
            else:
                wav_to_mp3(self.audio_path, path)
        except Exception:  # disk full, no permission, encoder missing...
            return "Could not save audio to Downloads."
        self.saved_key = key
        return "Saved: " + name

    def _save_settings(self):
        data = {
            "rate": SPEEDS[self._speed_index()][1],
            "en_speed": self._en_speed(),
            "voice": self.voice_var.get(),
            "save": bool(self.save_var.get()),
            "mode": self.mode_var.get(),
            "en_voice": self.voice_ids.get(self.en_voice_var.get(), ""),
            "en_voice_label": self.en_voice_var.get(),
        }
        if "dark" in self.settings:
            data["dark"] = self.settings["dark"]
        try:
            if self.root.state() == "normal":  # not maximised/minimised
                data["size"] = [self.root.winfo_width(), self.root.winfo_height()]
            elif "size" in self.settings:
                data["size"] = self.settings["size"]
        except tk.TclError:
            pass
        self.settings.update(data)
        save_settings(self.settings)

    def _close(self):
        if self.tray is not None:  # Windows: hide in the tray, keep running
            self._save_settings()
            self._stop()
            self.root.withdraw()
            if self.help_win is not None and self.help_win.winfo_exists():
                self.help_win.destroy()
            if not self.settings.get("tray_hint"):
                self.settings["tray_hint"] = True
                self._save_settings()
                self.tray.balloon("Read Pāli Aloud is still running",
                                  "It is in the tray (bottom right). Right-click its icon "
                                  "and choose Exit to close it completely.")
            return
        self.quit()

    def quit(self):
        self._save_settings()
        self._stop()
        if self.poll_id is not None:
            self.root.after_cancel(self.poll_id)
        if self.audio_path:
            _unlink(self.audio_path)
        self.root.destroy()

    # ── Thread helpers ────────────────────────────────────────────────────────
    def _after(self, fn, *args):
        try:
            self.root.after(0, fn, *args)
        except (tk.TclError, RuntimeError):
            pass  # window already closed

    def _set_status(self, msg):
        self._after(self.status_var.set, msg)


def _unlink(path):
    try:
        os.unlink(path)
    except OSError:
        pass


def _windows_setup(root):
    """Sharp text on high-DPI screens, own taskbar button, app icon."""
    import ctypes
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("PaliTTS.ReadPaliAloud")
    except Exception:
        pass
    here = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False)
                                           else __file__))
    for ico in (os.path.join(here, "AppIcon.ico"),
                os.path.join(here, "assets", "AppIcon.ico"),
                os.path.join(getattr(sys, "_MEIPASS", here), "AppIcon.ico")):
        if os.path.exists(ico):
            try:
                root.iconbitmap(default=ico)
            except tk.TclError:
                pass
            break


def show_gui(initial_text=""):
    if IS_WINDOWS:
        try:  # before Tk starts, so Windows does not blur the window
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
    root = tk.Tk()
    if IS_WINDOWS:
        _windows_setup(root)
    PaliTTSWindow(root, initial_text)
    root.mainloop()


def run_with_tray(background_class, show=False, text=""):
    """Windows: one process in the background (tray icon, Ctrl+Shift+Y, floating
    button); the window is hidden instead of closed. Exit from the tray menu."""
    import queue
    root = tk.Tk()
    root.withdraw()
    _windows_setup(root)
    commands = queue.Queue()
    settings = load_settings()
    bg = background_class(commands, popup_enabled=bool(settings.get("popup", True)))
    bg.start()
    window = PaliTTSWindow(root, "", tray=bg)
    if not bg.hotkey_ok:
        window.status_var.set("Ctrl+Shift+Y is used by another program: shortcut is off.")

    def pump():
        try:
            while True:
                cmd = commands.get_nowait()
                if cmd[0] == "open":
                    window.show(cmd[1], autoplay=cmd[2])
                elif cmd[0] == "show":
                    window.show()
                elif cmd[0] == "help":
                    window.show_help()
                elif cmd[0] == "popup":
                    window.set_popup(cmd[1])
                elif cmd[0] == "exit":
                    window.quit()
                    return
        except queue.Empty:
            pass
        except Exception:
            pass
        root.after(100, pump)

    root.after(100, pump)
    if show:
        root.after(150, lambda: window.show(text or None))
    root.mainloop()
    bg.stop()
    time.sleep(0.3)  # let the tray icon go


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


def read_input():
    """Text given on start: --input-file, or the Mac Services menu (stdin)."""
    raw = ""
    if INPUT_FILE:
        try:
            with open(INPUT_FILE, "r", encoding="utf-8") as f:
                raw = f.read()
            os.unlink(INPUT_FILE)
        except Exception:
            raw = ""
    elif sys.stdin is not None and not sys.stdin.isatty():
        # Selected text from the Services menu; empty when opened as an app
        try:
            raw = sys.stdin.read()
        except (OSError, ValueError):
            raw = ""
    return raw


# Languages "Auto (by language)" recognises (needs a voice of that language installed)
AUTO_LANGUAGES = (
    "By their script: Chinese, Japanese, Korean, Thai, Lao, Khmer, Burmese, Sinhala, "
    "Hindi (all Devanagari text), Bengali, Tamil, Telugu, Kannada, Malayalam, Gujarati, "
    "Punjabi, Arabic, Hebrew, Greek, Russian (all Cyrillic text), Ukrainian, Georgian.\n"
    "By common words, in Latin letters: English, Malay (uses an Indonesian voice if there "
    "is no Malay one), Spanish, French, German, Italian, Portuguese, Dutch, Tagalog; "
    "Vietnamese by its letters.\n"
    "Anything else, and very short lines, is read as English with the system voice.")


def help_text(tray=False):
    """Help window text; lines starting with "# " are headings."""
    if IS_MAC:
        open_it = (
            "# Open it with selected text\n"
            "• Select text in any app (browser, PDF, Word...) and press Cmd+Shift+Y.\n"
            "• Or right-click the selection → Services → Read Pali Aloud. This works in "
            "every Mac app.\n"
            "• Or open Read Pāli Aloud from Launchpad / Applications and paste text.\n"
            "• Change the shortcut: System Settings → Keyboard → Keyboard Shortcuts → "
            "Services → Text → Read Pali Aloud.\n"
            "• If the shortcut or menu item does not work at first: log out and in again.")
        quit_it = (
            "# Closing\n"
            "• Close (or the red button) closes the app. Nothing keeps running "
            "in the background: the shortcut and the Services menu start it again.")
        voices = ("System Settings → Accessibility → Spoken Content → System voice → "
                  "Manage Voices")
    else:
        open_it = (
            "# Open it with selected text\n"
            "• Select text in any program and press Ctrl+Shift+Y. The window opens with "
            "that text.\n"
            "• Or select text with the mouse: a small blue \u25B6 Read Pāli button appears "
            "next to the mouse. Click it to read the text aloud at once.\n"
            "   – Press Esc, or click anywhere else, to hide the button.\n"
            "   – Turn the button off: untick \"Show a \u25B6 Read Pāli button when I select "
            "text\" in this window, or right-click the tray icon → Pause Floating Popup.\n"
            "• The text is read straight from the program (Windows UI Automation), without "
            "copying: the clipboard is not changed, so clipboard tools such as GoldenDict "
            "are not set off. Works in Edge, Chrome, Word, Notepad and most programs.\n"
            "• A few programs (some PDF readers, for example) do not share their text this "
            "way: there the button does not appear, and Ctrl+Shift+Y copies the selection "
            "instead (this does replace the clipboard).\n"
            "• Windows has no right-click menu item for selected text in all programs; use "
            "Ctrl+Shift+Y or the button.\n"
            "• Or open Read Pāli Aloud from the Start menu and paste text.\n"
            "\n"
            "# Tray icon (bottom right of the taskbar)\n"
            "• Read Pāli Aloud keeps running in the tray, so the shortcut and the button "
            "always work. If you don't see the icon, click the ^ arrow next to the clock.\n"
            "• Click the icon: open this window.\n"
            "• Right-click the icon: Settings (this window), Pause Floating Popup (tick = "
            "the button is off), Help, Exit.\n"
            "\n"
            "# Closing and exiting\n"
            "• Close (or the window's ×) only hides the window; the app stays in the tray.\n"
            "• To quit completely: right-click the tray icon → Exit. Ctrl+Shift+Y and the "
            "button then stop working until you open Read Pāli Aloud again.\n"
            "• \"Run on Windows startup\" (in this window) starts it in the tray when you "
            "sign in to Windows.")
        quit_it = ""
        voices = "Settings → Time & language → Speech → Add voices"
    parts = [open_it,
             "# Play, pause and stop\n"
             "• \u25B6 Play reads the text; it becomes \u23F8 Pause, then \u25B6 Resume.\n"
             "• \u23F9 Stop stops; the next Play starts from the beginning.\n"
             "• Space bar = play / pause. When you are typing in the text box, press Esc "
             "first (Esc leaves the text box), then Space.\n"
             "• The time shows how far it has read and how long the audio is.",
             "# Settings in the window\n"
             "• Pāli speed: 0.33x to 1.67x. Translation speed: 0.75x to 3x.\n"
             "• Read: Pāli only, Translation only (every line that is not Pāli), or Both "
             "in order.\n"
             "• Pāli voice: Male or Female (Microsoft's Kannada voices; needs internet).\n"
             "• Translation voice: one of this computer's own voices (no internet "
             "needed). More voices: " + voices + ".\n"
             "• Save audio to Downloads: saves an MP3; the speed is in the file name.\n"
             "• Dark mode: top right.\n"
             "• The window can be made bigger; the text box grows with it.\n"
             "• All settings, the window size and dark mode are remembered.",
             "# Auto (by language) translation voice\n"
             "Picks a voice for each translation line from its language, if a voice of "
             "that language is installed.\n" + AUTO_LANGUAGES,
             "# Good to know\n"
             "• Lines are sorted into Pāli and translation one by one. Pāli without "
             "diacritics is recognised too; very short lines in other languages that end "
             "in vowels may be taken for Pāli.\n"
             "• Quotation marks are left out of the Pāli; dashes become short pauses.\n"
             "• The Pāli voice needs speech.platform.bing.com (internet)."]
    if quit_it:
        parts.append(quit_it)
    return "\n\n".join(parts) + "\n\nRead Pāli Aloud " + APP_VERSION


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    show_gui(initial_text=prepare_text(read_input()))


if __name__ == "__main__":
    main()
