import sys
import os
import re
import subprocess
import tempfile
import shutil
import threading
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
    ("Slow  0.75x",  "-25%"),
    ("Normal  1x",   "+0%"),
    ("Fast  1.5x",   "+50%"),
    ("2x",           "+100%"),
]

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
    import urllib.request
    import urllib.parse
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
    for ch in [".", ";", "!", "?"]:
        kannada = kannada.replace(ch, "।")
    return kannada


# ── Edge TTS ──────────────────────────────────────────────────────────────────
async def _generate(kannada_text, output_path, rate, voice):
    import edge_tts
    communicate = edge_tts.Communicate(kannada_text, voice, rate=rate)
    await communicate.save(output_path)

def generate_audio(kannada_text, output_path, rate, voice):
    import asyncio
    asyncio.run(_generate(kannada_text, output_path, rate, voice))


# ── Audio playback ────────────────────────────────────────────────────────────
def play_and_cleanup(path):
    if IS_MAC:
        subprocess.run(["afplay", path])
    elif IS_WINDOWS:
        from playsound import playsound
        playsound(path)
    try:
        os.unlink(path)
    except Exception:
        pass


# ── GUI ───────────────────────────────────────────────────────────────────────
class PaliTTSWindow:
    def __init__(self, root, initial_text=""):
        self.root = root

        root.title("Pali TTS")
        root.resizable(False, False)
        root.configure(padx=20, pady=15)

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
        self.speed_label = ttk.Label(root, text="Speed:  Normal  1x",
                                     font=("", 11, "bold"))
        self.speed_label.pack(anchor="w")
        self.slider_var = tk.DoubleVar(value=1.0)
        slider = ttk.Scale(root, from_=0, to=3, orient="horizontal",
                           variable=self.slider_var, command=self._on_drag,
                           length=280)
        slider.pack(fill="x", pady=(4, 0))
        tick_frame = tk.Frame(root)
        tick_frame.pack(fill="x")
        for label, _ in SPEEDS:
            tk.Label(tick_frame, text=label.split()[0], fg="#666",
                     font=("", 8)).pack(side="left", expand=True)

        # ── Voice ─────────────────────────────────────────────────────────────
        voice_frame = ttk.Frame(root)
        voice_frame.pack(anchor="w", pady=(12, 0))
        ttk.Label(voice_frame, text="Voice:").pack(side="left", padx=(0, 10))
        self.voice_var = tk.StringVar(value="kn-IN-GaganNeural")
        for label, voice_id in VOICES:
            ttk.Radiobutton(voice_frame, text=label, variable=self.voice_var,
                            value=voice_id).pack(side="left", padx=(0, 12))

        # ── Save checkbox ─────────────────────────────────────────────────────
        self.save_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(root, text="Save MP3 to Downloads",
                        variable=self.save_var).pack(anchor="w", pady=(10, 0))

        # ── Buttons ───────────────────────────────────────────────────────────
        btn_frame = ttk.Frame(root)
        btn_frame.pack(fill="x", pady=(14, 0))
        ttk.Button(btn_frame, text="Close",
                   command=root.destroy).pack(side="left", expand=True, padx=(0, 6))
        self.play_btn = ttk.Button(btn_frame, text="Play", command=self._play)
        self.play_btn.pack(side="right", expand=True, padx=(6, 0))

        # ── Status label ──────────────────────────────────────────────────────
        self.status_var = tk.StringVar(value="")
        ttk.Label(root, textvariable=self.status_var,
                  foreground="#555", font=("", 9)).pack(anchor="w", pady=(8, 0))

        # ── Position near cursor ──────────────────────────────────────────────
        root.update_idletasks()
        w = root.winfo_reqwidth()
        h = root.winfo_reqheight()
        cx = root.winfo_pointerx()
        cy = root.winfo_pointery()
        root.geometry("+%d+%d" % (cx - w // 2, cy - h // 2))
        root.lift()
        root.attributes("-topmost", True)
        root.after(200, lambda: root.attributes("-topmost", False))
        root.focus_force()
        self.text_box.focus_set()

    def _on_drag(self, _value):
        idx = max(0, min(3, round(self.slider_var.get())))
        self.slider_var.set(idx)
        label, _ = SPEEDS[idx]
        self.speed_label.config(text="Speed:  " + label)

    def _set_status(self, msg):
        try:
            self.root.after(0, lambda: self.status_var.set(msg))
        except tk.TclError:
            pass

    def _set_play_enabled(self, enabled):
        try:
            state = "normal" if enabled else "disabled"
            self.root.after(0, lambda: self.play_btn.config(state=state))
        except tk.TclError:
            pass

    def _play(self):
        text_content = self.text_box.get("1.0", "end-1c").strip()
        if not text_content:
            self.status_var.set("Please paste some Pali text first.")
            return

        text = filter_pali_lines(text_content)
        text = " ".join(text.split())
        if not text:
            self.status_var.set("No Pali text detected.")
            return

        idx = max(0, min(3, round(self.slider_var.get())))
        _, rate = SPEEDS[idx]
        voice = self.voice_var.get()
        save  = self.save_var.get()

        self.play_btn.config(state="disabled")
        self.status_var.set("Connecting...")

        t = threading.Thread(target=self._run_pipeline,
                             args=(text, rate, voice, save))
        t.daemon = False  # keep process alive until audio finishes
        t.start()

    def _run_pipeline(self, text, rate, voice, save):
        try:
            self._set_status("Transliterating...")
            kannada = to_kannada(text)
        except Exception:
            self._set_status("Transliteration failed — check internet.")
            self._set_play_enabled(True)
            return

        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".mp3")
        os.close(tmp_fd)

        try:
            self._set_status("Generating audio...")
            generate_audio(kannada, tmp_path, rate, voice)
        except Exception:
            self._set_status("Audio generation failed — check internet.")
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
            self._set_play_enabled(True)
            return

        if save:
            words = text.split()[:4]
            base = "_".join(words)
            base = re.sub(r'[/:\\*?"<>|,;.\(\)]', "", base).strip("_") or "pali_audio"
            dl = os.path.join(os.path.expanduser("~"), "Downloads")
            mp3_name = base + ".mp3"
            mp3_path = os.path.join(dl, mp3_name)
            if os.path.exists(mp3_path):
                mp3_name = base + "_" + datetime.now().strftime("%H%M%S") + ".mp3"
                mp3_path = os.path.join(dl, mp3_name)
            shutil.copy(tmp_path, mp3_path)
            self._set_status("Saved: " + mp3_name)
        else:
            self._set_status("Playing...")

        play_and_cleanup(tmp_path)

        if not save:
            self._set_status("Done.")
        self._set_play_enabled(True)


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
