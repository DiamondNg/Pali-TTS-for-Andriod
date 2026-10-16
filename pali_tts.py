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

IS_MAC     = platform.system() == "Darwin"
IS_WINDOWS = platform.system() == "Windows"
CREATE_NO_WINDOW = 0x08000000

INPUT_FILE = None
for i, a in enumerate(sys.argv[1:], 1):
    if a == "--input-file" and i < len(sys.argv):
        INPUT_FILE = sys.argv[i + 1]

ENGLISH_MARKERS = {
    "the", "of", "is", "are", "was", "were", "and", "that", "this", "with",
    "he", "she", "it", "they", "his", "her", "their", "there", "when", "which",
    "have", "has", "had", "not", "but", "for", "from", "into", "will", "would",
    "should", "does", "do", "an", "in", "on", "at", "by", "as", "or", "if",
    "here", "how", "what", "who", "one", "all", "also", "then", "than",
}

SPEEDS = [
    ("0.25x", "-75%"),
    ("0.5x",  "-50%"),
    ("0.75x", "-25%"),
    ("1x",    "+0%"),
    ("1.25x", "+25%"),
    ("1.5x",  "+50%"),
    ("1.75x", "+75%"),
]
DEFAULT_SPEED = 3  # 1x

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


# ── Aksharamukha API ──────────────────────────────────────────────────────────
def to_kannada(text):
    # aksharamukha handles ṃ (dot-below) but not ṁ (dot-above)
    text = text.replace("ṁ", "ṃ").replace("Ṁ", "Ṃ")
    try:
        kannada = _to_kannada_local(text)
    except Exception:
        kannada = _to_kannada_online(text)
    for ch in [".", ";", "!", "?"]:
        kannada = kannada.replace(ch, "।")
    return kannada

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

def fmt_time(seconds):
    seconds = int(seconds)
    return "%d:%02d" % (seconds // 60, seconds % 60)


# ── GUI ───────────────────────────────────────────────────────────────────────
class PaliTTSWindow:
    def __init__(self, root, initial_text=""):
        self.root = root

        self.proc = None          # running afplay process (macOS)
        self.paused = False
        self.busy = False         # transliterating / generating audio
        self.audio_path = None    # last generated audio, reused when settings match
        self.audio_key = None     # (text, rate, voice) of audio_path
        self.play_key = None      # (text, rate, voice) of what is playing/paused
        self.saved_key = None     # (text, rate, voice) last saved to Downloads
        self.audio_secs = None    # length of audio_path in seconds
        self.elapsed = 0.0        # seconds played before the current run
        self.started = None       # time.monotonic() when playback (re)started
        self.poll_id = None       # pending root.after() for _poll

        settings = load_settings()
        speed = settings.get("speed", DEFAULT_SPEED)
        if not isinstance(speed, int) or not 0 <= speed < len(SPEEDS):
            speed = DEFAULT_SPEED
        voice = settings.get("voice")
        if voice not in [v for _, v in VOICES]:
            voice = VOICES[0][1]

        root.title("Pali TTS")
        root.resizable(False, False)
        root.configure(padx=20, pady=15)
        root.protocol("WM_DELETE_WINDOW", self._close)

        # ── Text area ─────────────────────────────────────────────────────────
        ttk.Label(root, text="Pali text  (paste or edit):").pack(anchor="w")
        txt_frame = tk.Frame(root)
        txt_frame.pack(fill="x", pady=(4, 14))
        self.text_box = tk.Text(txt_frame, height=6, width=38, wrap="word",
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
        for label, _ in SPEEDS:
            tk.Label(tick_frame, text=label, fg="#666",
                     font=("", 8)).pack(side="left", expand=True)
        self._on_drag(None)

        # ── Voice ─────────────────────────────────────────────────────────────
        voice_frame = ttk.Frame(root)
        voice_frame.pack(anchor="w", pady=(12, 0))
        ttk.Label(voice_frame, text="Voice:").pack(side="left", padx=(0, 10))
        self.voice_var = tk.StringVar(value=voice)
        for label, voice_id in VOICES:
            ttk.Radiobutton(voice_frame, text=label, variable=self.voice_var,
                            value=voice_id).pack(side="left", padx=(0, 12))

        # ── Save checkbox ─────────────────────────────────────────────────────
        self.save_var = tk.BooleanVar(value=bool(settings.get("save", False)))
        ttk.Checkbutton(root, text="Save MP3 to Downloads",
                        variable=self.save_var).pack(anchor="w", pady=(10, 0))
        ttk.Label(root, text="The MP3 is saved at the speed and voice chosen above.",
                  foreground="#666", font=("", 9)).pack(anchor="w")

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
                  foreground="#555", font=("", 9)).pack(side="left")
        self.time_var = tk.StringVar(value="")
        ttk.Label(status_frame, textvariable=self.time_var,
                  foreground="#555", font=("", 9)).pack(side="right")
        ttk.Label(root, text="Tip: Space bar = play / pause (Esc leaves the text box)",
                  foreground="#888", font=("", 8)).pack(anchor="w", pady=(4, 0))

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

    # ── Settings ──────────────────────────────────────────────────────────────
    def _speed_index(self):
        return max(0, min(len(SPEEDS) - 1, round(self.slider_var.get())))

    def _on_drag(self, _value):
        idx = self._speed_index()
        self.slider_var.set(idx)
        self.speed_label.config(text="Speed:  " + SPEEDS[idx][0])

    def _current_key(self):
        """(text, rate, voice) for the current settings, or None if no Pali text."""
        text_content = self.text_box.get("1.0", "end-1c").strip()
        if not text_content:
            self.status_var.set("Please paste some Pali text first.")
            return None
        text = " ".join(filter_pali_lines(text_content).split())
        if not text:
            self.status_var.set("No Pali text detected.")
            return None
        return (text, SPEEDS[self._speed_index()][1], self.voice_var.get())

    # ── Play / Pause / Stop ───────────────────────────────────────────────────
    def _on_space(self, event):
        # Let Space type in the text box and activate focused buttons as usual
        if event.widget is self.text_box or isinstance(
                event.widget, (ttk.Button, ttk.Checkbutton, ttk.Radiobutton)):
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
        return self.proc is not None and self.proc.poll() is None

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
        text, rate, voice = key
        try:
            self._set_status("Transliterating...")
            kannada = to_kannada(text)
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
        if IS_MAC:
            self.proc = subprocess.Popen(["afplay", self.audio_path])
            self.elapsed, self.started = 0.0, time.monotonic()
            self._show_time()
            self.play_btn.config(text=PAUSE_TEXT)
            self.stop_btn.config(state="normal")
            self._poll(self.proc)
        elif IS_WINDOWS:
            # playsound cannot pause; block the button until playback ends
            self.play_btn.config(state="disabled")
            path = self.audio_path

            def run():
                from playsound import playsound
                playsound(path)
                self._after(self._finished_windows)
            threading.Thread(target=run, daemon=True).start()

    def _finished_windows(self):
        self.play_btn.config(state="normal")
        self.status_var.set("Done.")

    def _poll(self, proc):
        if proc is not self.proc:
            return  # stopped or replaced
        if proc.poll() is None:
            if not self.paused:
                self._show_time()
            self.poll_id = self.root.after(200, self._poll, proc)
            return
        self.started = None
        if self.audio_secs:
            self.elapsed = self.audio_secs
        self._show_time()
        self.proc = None
        self.paused = False
        self.play_btn.config(text=PLAY_TEXT)
        self.stop_btn.config(state="disabled")
        if self.status_var.get() == "Playing...":
            self.status_var.set("Done.")

    def _pause(self):
        os.kill(self.proc.pid, signal.SIGSTOP)
        self.elapsed, self.started = self._played_secs(), None
        self.paused = True
        self.play_btn.config(text=RESUME_TEXT)
        self.status_var.set("Paused.")

    def _resume(self):
        self._save_if_requested(self.play_key)
        os.kill(self.proc.pid, signal.SIGCONT)
        self.started = time.monotonic()
        self.paused = False
        self.play_btn.config(text=PAUSE_TEXT)
        self.status_var.set("Playing...")

    def _stop(self):
        proc, self.proc = self.proc, None
        if proc is not None and proc.poll() is None:
            proc.kill()  # SIGKILL also ends a paused (SIGSTOPped) process
            proc.wait()
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
        words = key[0].split()[:4]
        base = "_".join(words)
        base = re.sub(r'[/:\\*?"<>|,;.\(\)]', "", base).strip("_") or "pali_audio"
        base += "_" + dict((r, l) for l, r in SPEEDS)[key[1]]
        dl = os.path.join(os.path.expanduser("~"), "Downloads")
        mp3_name = base + ".mp3"
        mp3_path = os.path.join(dl, mp3_name)
        if os.path.exists(mp3_path):
            mp3_name = base + "_" + datetime.now().strftime("%H%M%S") + ".mp3"
            mp3_path = os.path.join(dl, mp3_name)
        try:
            shutil.copy(self.audio_path, mp3_path)
        except OSError:
            return "Could not save MP3 to Downloads."
        self.saved_key = key
        return "Saved: " + mp3_name

    def _close(self):
        save_settings({
            "speed": self._speed_index(),
            "voice": self.voice_var.get(),
            "save": bool(self.save_var.get()),
        })
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


def show_gui(initial_text=""):
    root = tk.Tk()
    PaliTTSWindow(root, initial_text)
    root.mainloop()


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    if INPUT_FILE:
        try:
            with open(INPUT_FILE, "r", encoding="utf-8") as f:
                raw = f.read().strip()
            os.unlink(INPUT_FILE)
        except Exception:
            raw = ""
    else:
        raw = sys.stdin.read().strip()

    for ch in ["“", "”", "‘", "’", "—", "–"]:
        raw = raw.replace(ch, " ")

    show_gui(initial_text=raw)


if __name__ == "__main__":
    main()
