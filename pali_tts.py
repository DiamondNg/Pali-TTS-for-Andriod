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

# (label, edge-tts rate, multiplier for the English voice)
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
ENGLISH_WPM = 175  # macOS `say` words per minute at 1x

MODES = [("Pāli", "pi"), ("English", "en"), ("Both", "both")]
SYSTEM_VOICE = "System default"

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

def split_segments(text):
    """[(lang, text)] in reading order; lang is "pi" or "en"."""
    segs = []
    for ln in text.splitlines():
        if not ln.strip() or is_section_marker(ln) or is_non_latin_line(ln):
            continue
        lang = "en" if is_english_line(ln) else "pi"
        if segs and segs[-1][0] == lang:
            segs[-1] = (lang, segs[-1][1] + " " + ln)
        else:
            segs.append((lang, ln))
    return [(lang, " ".join(t.split())) for lang, t in segs]

def clean_pali(text):
    # Quotes would make the voice pause (sarīran"ti): delete them, no space
    return re.sub(r"[\"'“”‘’]", "", text)

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


# ── English voice (macOS `say`, offline) ──────────────────────────────────────
# macOS sound-effect voices: not useful for reading suttas
NOVELTY_VOICES = {
    "Albert", "Bad News", "Bahh", "Bells", "Boing", "Bubbles", "Cellos",
    "Deranged", "Good News", "Hysterical", "Jester", "Organ", "Pipe Organ",
    "Superstar", "Trinoids", "Whisper", "Wobble", "Zarvox",
}

def english_voices():
    """Names of the installed English voices (macOS)."""
    if not IS_MAC:
        return []
    try:
        out = subprocess.run(["say", "-v", "?"], capture_output=True,
                             text=True, timeout=15).stdout
    except Exception:
        return []
    names = []
    for line in out.splitlines():
        m = re.match(r"^(.+?)\s+([a-z]{2,3})[_-]([A-Za-z0-9]+)\s+#", line)
        name = m.group(1).strip() if m else ""
        if m and m.group(2) == "en" and name not in names and name not in NOVELTY_VOICES:
            names.append(name)
    return names

def say_to_file(text, out_path, wpm, voice):
    cmd = ["say", "-r", str(wpm), "-o", out_path]
    if voice and voice != SYSTEM_VOICE:
        cmd += ["-v", voice]
    subprocess.run(cmd + ["-f", "-"], input=text, text=True, check=True,
                   capture_output=True, timeout=600)


# ── Joining segments (macOS: afconvert ships with the system) ─────────────────
SAMPLE_RATE = 24000  # = edge-tts output

def to_wav(src, dst):
    subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@%d" % SAMPLE_RATE,
                    "-c", "1", src, dst], check=True, capture_output=True, timeout=600)

def build_joined(parts, rate, voice, en_voice, wpm, status=lambda msg: None):
    """parts: [("kn", kannada_text) or ("en", english_text)] → (wav path, seconds).
    Kannada parts use Microsoft's voice, English parts the Mac's own voice."""
    work = tempfile.mkdtemp(prefix="palitts")
    try:
        jobs, files = [], []
        for i, (lang, text) in enumerate(parts):
            src = os.path.join(work, "%03d.%s" % (i, "mp3" if lang == "kn" else "aiff"))
            if lang == "kn":
                jobs.append((text, src))
            files.append((lang, text, src))
        if jobs:
            status("Generating Pāli audio...")
            generate_audio_many(jobs, rate, voice)
        status("Generating English audio...")
        wavs = []
        for lang, text, src in files:
            if lang == "en":
                say_to_file(text, src, wpm, en_voice)
            wav = src.rsplit(".", 1)[0] + ".wav"
            to_wav(src, wav)
            wavs.append(wav)
        tmp_fd, out = tempfile.mkstemp(suffix=".wav")
        os.close(tmp_fd)
        return out, join_wavs(wavs, out)
    finally:
        shutil.rmtree(work, ignore_errors=True)

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

# Colours for the non-macOS dark mode (macOS uses its own dark appearance)
DARK = {"bg": "#1e1e1e", "fg": "#e6e6e6", "field": "#2b2b2b", "accent": "#3a3a3a"}


class PaliTTSWindow:
    def __init__(self, root, initial_text=""):
        self.root = root
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
        self.en_voices = english_voices()
        en_voice = settings.get("en_voice")
        if en_voice not in self.en_voices:
            en_voice = SYSTEM_VOICE

        root.title("Read Pāli Aloud")
        root.resizable(False, False)
        root.configure(padx=20, pady=15)
        root.protocol("WM_DELETE_WINDOW", self._close)

        # ── Text area + dark mode toggle ─────────────────────────────────────
        top = ttk.Frame(root)
        top.pack(fill="x")
        ttk.Label(top, text="Text  (paste or edit):").pack(side="left")
        self.dark_var = tk.BooleanVar(value=self._initial_dark())
        ttk.Checkbutton(top, text="Dark mode", variable=self.dark_var,
                        command=self._on_dark_toggle).pack(side="right")
        txt_frame = tk.Frame(root)
        txt_frame.pack(fill="x", pady=(4, 14))
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
        self.speed_label = ttk.Label(root, text="", font=("", 11, "bold"))
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
        ttk.Label(en_frame, text="English voice:").pack(side="left", padx=(0, 10))
        self.en_voice_var = tk.StringVar(value=en_voice)
        self.en_combo = ttk.Combobox(en_frame, textvariable=self.en_voice_var,
                                     values=[SYSTEM_VOICE] + self.en_voices,
                                     state="readonly", width=22)
        self.en_combo.pack(side="left")

        # ── Save checkbox ─────────────────────────────────────────────────────
        self.save_var = tk.BooleanVar(value=bool(settings.get("save", False)))
        ttk.Checkbutton(root, text="Save audio to Downloads",
                        variable=self.save_var).pack(anchor="w", pady=(10, 0))
        self.save_note = ttk.Label(root, text="", foreground=MUTED, font=("", 9))
        self.save_note.pack(anchor="w")

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
        ttk.Label(root, text="Tip: Space bar = play / pause (Esc leaves the text box)",
                  foreground=MUTED, font=("", 8)).pack(anchor="w", pady=(4, 0))

        self._on_mode()
        if "dark" in settings:
            self._apply_theme()

        # ── Keyboard ──────────────────────────────────────────────────────────
        root.bind("<space>", self._on_space)
        self.text_box.bind("<Escape>", lambda e: root.focus_set())

        # ── Position near cursor ──────────────────────────────────────────────
        root.update_idletasks()
        w = root.winfo_reqwidth()
        h = root.winfo_reqheight()
        cx = root.winfo_pointerx()
        cy = root.winfo_pointery()
        # Keep the whole window on screen (below the macOS menu bar)
        x = max(0, min(cx - w // 2, root.winfo_screenwidth() - w))
        y = max(30, min(cy - h // 2, root.winfo_screenheight() - h - 40))
        root.geometry("+%d+%d" % (x, y))
        root.lift()
        root.attributes("-topmost", True)
        root.after(200, lambda: root.attributes("-topmost", False))
        root.focus_force()
        if initial_text:
            root.focus_set()  # so Space plays straight away
        else:
            self.text_box.focus_set()

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
        self.speed_label.config(text="Speed:  " + SPEEDS[idx][0])

    def _on_mode(self):
        mode = self.mode_var.get()
        self.en_combo.config(state="disabled" if mode == "pi" else "readonly")
        self.save_note.config(text="Saved as MP3 at the chosen speed and voice." if mode == "pi"
                              else "Saved as M4A (Apple audio) at the chosen speed and voices.")

    def _current_key(self):
        """Settings key (mode, segments, speed, voice, English voice), or None."""
        text_content = self.text_box.get("1.0", "end-1c").strip()
        if not text_content:
            self.status_var.set("Please paste some text first.")
            return None
        mode = self.mode_var.get()
        if mode == "pi":
            text = " ".join(filter_pali_lines(text_content).split())
            segs = (("pi", text),) if text else ()
        else:
            if not IS_MAC:
                self.status_var.set("The English voice works on Mac only for now.")
                return None
            segs = tuple(split_segments(text_content))
            if mode == "en":
                segs = tuple(sg for sg in segs if sg[0] == "en")
        if not segs:
            self.status_var.set("No English text detected." if mode == "en"
                                else "No Pāli text detected.")
            return None
        en_voice = self.en_voice_var.get() if mode != "pi" else None
        return (mode, segs, self._speed_index(), self.voice_var.get(), en_voice)

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
        mode, segs, speed, voice, en_voice = key
        _, rate, mult = SPEEDS[speed]
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

        # English / Both: make each part, convert to WAV, join into one file
        try:
            self._set_status("Transliterating...")
            parts = [("kn", to_kannada(text)) if lang == "pi" else ("en", text)
                     for lang, text in segs]
            out, secs = build_joined(parts, rate, voice, en_voice,
                                     round(ENGLISH_WPM * mult), self._set_status)
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
        base += "_" + SPEEDS[speed][0]
        if mode == "pi":
            ext = ".mp3"
        else:
            ext = ".m4a"
            base += "_" + ("english" if mode == "en" else "pali_english")
        dl = os.path.join(os.path.expanduser("~"), "Downloads")
        name = base + ext
        path = os.path.join(dl, name)
        if os.path.exists(path):
            name = base + "_" + datetime.now().strftime("%H%M%S") + ext
            path = os.path.join(dl, name)
        try:
            if ext == ".mp3":
                shutil.copy(self.audio_path, path)
            else:
                subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", self.audio_path, path],
                               check=True, capture_output=True, timeout=600)
        except (OSError, subprocess.SubprocessError):
            return "Could not save audio to Downloads."
        self.saved_key = key
        return "Saved: " + name

    def _close(self):
        data = {
            "rate": SPEEDS[self._speed_index()][1],
            "voice": self.voice_var.get(),
            "save": bool(self.save_var.get()),
            "mode": self.mode_var.get(),
            "en_voice": self.en_voice_var.get(),
        }
        if "dark" in self.settings:
            data["dark"] = self.settings["dark"]
        save_settings(data)
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


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    raw = ""
    if INPUT_FILE:
        try:
            with open(INPUT_FILE, "r", encoding="utf-8") as f:
                raw = f.read().strip()
            os.unlink(INPUT_FILE)
        except Exception:
            raw = ""
    elif sys.stdin is not None and not sys.stdin.isatty():
        # Selected text from the Services menu; empty when opened as an app
        try:
            raw = sys.stdin.read().strip()
        except (OSError, ValueError):
            raw = ""

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

    show_gui(initial_text=raw)


if __name__ == "__main__":
    main()
