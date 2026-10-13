import re
import os
import threading
import tempfile
import shutil
from datetime import datetime

from kivy.app import App
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.metrics import dp

IS_ANDROID = False
try:
    import android
    IS_ANDROID = True
except ImportError:
    pass

ENGLISH_MARKERS = {
    "the", "of", "is", "are", "was", "were", "and", "that", "this", "with",
    "he", "she", "it", "they", "his", "her", "their", "there", "when", "which",
    "have", "has", "had", "not", "but", "for", "from", "into", "will", "would",
    "should", "does", "do", "an", "in", "on", "at", "by", "as", "or", "if",
    "here", "how", "what", "who", "one", "all", "also", "then", "than",
}

SPEEDS = [
    ("Slow  0.75x",  -25),
    ("Normal  1x",     0),
    ("Fast  1.5x",    50),
    ("2x",           100),
]

ANDROID_RATES = {-25: 0.75, 0: 1.0, 50: 1.5, 100: 2.0}
EDGE_RATES    = {-25: "-25%", 0: "+0%", 50: "+50%", 100: "+100%"}


# ── Pali filtering (same as desktop) ─────────────────────────────────────────
def is_latin_char(ch):
    cp = ord(ch)
    return cp < 0x0250 or (0x1E00 <= cp <= 0x1EFF)

def is_non_latin_line(line):
    alpha = [ch for ch in line if ch.isalpha()]
    if not alpha:
        return False
    return sum(1 for ch in alpha if not is_latin_char(ch)) / len(alpha) > 0.3

def is_section_marker(line):
    return len(re.sub(r'[\s\d\.\(\)\[\]\-–—:;,\xa7ivxlcmIVXLCM]',
                      '', line.strip())) == 0

def is_english_line(line):
    words = re.findall(r"[a-zA-Z]+", line.lower())
    if not words:
        return False
    matches = sum(1 for w in words if w in ENGLISH_MARKERS)
    return matches >= 2 or (len(words) >= 3 and matches / len(words) > 0.3)

def filter_pali_lines(text):
    lines = text.splitlines()
    kept = [ln for ln in lines
            if ln.strip()
            and not is_section_marker(ln)
            and not is_english_line(ln)
            and not is_non_latin_line(ln)]
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


# ── Android TTS ───────────────────────────────────────────────────────────────
def _speak_android(tts, kannada, rate_percent):
    from jnius import autoclass
    TextToSpeech = autoclass("android.speech.tts.TextToSpeech")
    tts.setSpeechRate(ANDROID_RATES.get(rate_percent, 1.0))
    tts.speak(kannada, TextToSpeech.QUEUE_FLUSH, None, "pali_utt")


# ── Desktop fallback (edge-tts + afplay) for testing on Mac ──────────────────
def _speak_desktop(kannada, rate_percent, voice_gender):
    import asyncio
    import edge_tts
    import subprocess
    voice = "kn-IN-GaganNeural" if voice_gender == "male" else "kn-IN-SapnaNeural"
    rate  = EDGE_RATES.get(rate_percent, "+0%")
    async def gen():
        fd, path = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)
        await edge_tts.Communicate(kannada, voice, rate=rate).save(path)
        return path
    path = asyncio.run(gen())
    subprocess.run(["afplay", path])
    try:
        os.unlink(path)
    except Exception:
        pass


# ── KV Layout ─────────────────────────────────────────────────────────────────
KV = """
BoxLayout:
    orientation: 'vertical'
    padding: dp(20)
    spacing: dp(12)

    Label:
        text: 'Pali text  (paste or edit):'
        size_hint_y: None
        height: dp(30)
        halign: 'left'
        text_size: self.width, None
        color: 0.15, 0.15, 0.15, 1
        font_size: dp(15)

    TextInput:
        id: text_box
        size_hint_y: 0.38
        multiline: True
        font_size: dp(15)
        hint_text: 'Paste Pali text here...'

    Label:
        id: speed_label
        text: 'Speed:  Normal  1x'
        size_hint_y: None
        height: dp(32)
        bold: True
        halign: 'left'
        text_size: self.width, None
        color: 0.1, 0.1, 0.1, 1
        font_size: dp(15)

    Slider:
        id: speed_slider
        min: 0
        max: 3
        value: 1
        step: 1
        size_hint_y: None
        height: dp(48)
        on_value: app.on_speed_change(int(round(self.value)))

    GridLayout:
        cols: 4
        size_hint_y: None
        height: dp(22)
        Label:
            text: 'Slow'
            font_size: dp(12)
            color: 0.45, 0.45, 0.45, 1
        Label:
            text: 'Normal'
            font_size: dp(12)
            color: 0.45, 0.45, 0.45, 1
        Label:
            text: 'Fast'
            font_size: dp(12)
            color: 0.45, 0.45, 0.45, 1
        Label:
            text: '2x'
            font_size: dp(12)
            color: 0.45, 0.45, 0.45, 1

    BoxLayout:
        orientation: 'horizontal'
        size_hint_y: None
        height: dp(52)
        spacing: dp(10)

        Label:
            text: 'Voice:'
            size_hint_x: None
            width: dp(60)
            font_size: dp(15)
            halign: 'left'
            text_size: self.size

        ToggleButton:
            id: male_btn
            text: 'Male'
            group: 'voice'
            state: 'down'
            font_size: dp(15)
            on_press: app.on_voice_change('male')

        ToggleButton:
            id: female_btn
            text: 'Female'
            group: 'voice'
            font_size: dp(15)
            on_press: app.on_voice_change('female')

    BoxLayout:
        orientation: 'horizontal'
        size_hint_y: None
        height: dp(44)
        spacing: dp(10)

        CheckBox:
            id: save_cb
            size_hint_x: None
            width: dp(44)
            active: False

        Label:
            text: 'Save MP3 to Downloads'
            font_size: dp(15)
            halign: 'left'
            text_size: self.size

    BoxLayout:
        orientation: 'horizontal'
        size_hint_y: None
        height: dp(64)
        spacing: dp(12)

        Button:
            text: 'Close'
            font_size: dp(18)
            on_press: app.stop()

        Button:
            id: play_btn
            text: 'Play'
            font_size: dp(18)
            on_press: app.play()

    Label:
        id: status_label
        text: ''
        size_hint_y: None
        height: dp(32)
        halign: 'left'
        text_size: self.width, None
        color: 0.35, 0.35, 0.35, 1
        font_size: dp(13)
"""


# ── App ───────────────────────────────────────────────────────────────────────
class PaliTTSApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._speed_idx  = 1    # Normal
        self._voice      = "male"
        self._tts        = None
        self._tts_ready  = False
        self._tts_listener = None

    def build(self):
        return Builder.load_string(KV)

    def on_start(self):
        if IS_ANDROID:
            self._init_android_tts()
            text = self._get_share_text()
            if text:
                self.root.ids.text_box.text = text

    # ── Android TTS init ──────────────────────────────────────────────────────
    def _init_android_tts(self):
        try:
            from jnius import autoclass, PythonJavaClass, java_method
            from android import mActivity

            TextToSpeech = autoclass("android.speech.tts.TextToSpeech")
            Locale        = autoclass("java.util.Locale")
            app           = self

            class TTSInitListener(PythonJavaClass):
                __javainterfaces__ = [
                    "android/speech/tts/TextToSpeech$OnInitListener"
                ]
                __javacontext__ = "app"

                @java_method("(I)V")
                def onInit(self_j, status):
                    if status == 0:  # SUCCESS
                        locale = Locale("kn", "IN")
                        app._tts.setLanguage(locale)
                        app._tts_ready = True

            self._tts_listener = TTSInitListener()
            self._tts = TextToSpeech(mActivity, self._tts_listener)
        except Exception as e:
            self._set_status("TTS init failed: " + str(e))

    # ── Share intent ──────────────────────────────────────────────────────────
    def _get_share_text(self):
        try:
            from android import mActivity
            from jnius import autoclass
            Intent = autoclass("android.content.Intent")
            intent = mActivity.getIntent()
            if intent.getAction() == Intent.ACTION_SEND:
                text = intent.getStringExtra(Intent.EXTRA_TEXT)
                if text:
                    return text.strip()
        except Exception:
            pass
        return ""

    # ── UI callbacks ──────────────────────────────────────────────────────────
    def on_speed_change(self, idx):
        idx = max(0, min(3, idx))
        self._speed_idx = idx
        self.root.ids.speed_label.text = "Speed:  " + SPEEDS[idx][0]

    def on_voice_change(self, gender):
        self._voice = gender

    def _set_status(self, msg):
        def _apply(dt):
            try:
                self.root.ids.status_label.text = msg
            except Exception:
                pass
        Clock.schedule_once(_apply, 0)

    def _set_play_enabled(self, enabled):
        def _apply(dt):
            try:
                self.root.ids.play_btn.disabled = not enabled
            except Exception:
                pass
        Clock.schedule_once(_apply, 0)

    # ── Play ──────────────────────────────────────────────────────────────────
    def play(self):
        text_content = self.root.ids.text_box.text.strip()
        if not text_content:
            self.root.ids.status_label.text = "Please paste some Pali text first."
            return

        text = filter_pali_lines(text_content)
        text = " ".join(text.split())
        if not text:
            self.root.ids.status_label.text = "No Pali text detected."
            return

        self.root.ids.play_btn.disabled = True
        self.root.ids.status_label.text = "Connecting..."

        rate_percent = SPEEDS[self._speed_idx][1]
        save         = self.root.ids.save_cb.active

        t = threading.Thread(
            target=self._run_pipeline,
            args=(text, rate_percent, self._voice, save),
        )
        t.daemon = False
        t.start()

    def _run_pipeline(self, text, rate_percent, voice_gender, save):
        # 1. Transliterate
        try:
            self._set_status("Transliterating...")
            kannada = to_kannada(text)
        except Exception:
            self._set_status("Transliteration failed — check internet.")
            self._set_play_enabled(True)
            return

        # 2. Save MP3 (only available on desktop via edge-tts)
        if save and not IS_ANDROID:
            try:
                self._set_status("Generating audio...")
                import asyncio, edge_tts
                voice = ("kn-IN-GaganNeural" if voice_gender == "male"
                         else "kn-IN-SapnaNeural")
                rate  = EDGE_RATES.get(rate_percent, "+0%")
                async def gen():
                    fd, path = tempfile.mkstemp(suffix=".mp3")
                    os.close(fd)
                    await edge_tts.Communicate(kannada, voice, rate=rate).save(path)
                    return path
                src_path = asyncio.run(gen())
                words = text.split()[:4]
                base  = "_".join(words)
                base  = re.sub(r'[/:\\*?"<>|,;.\(\)]', "", base).strip("_") or "pali_audio"
                dl    = os.path.join(os.path.expanduser("~"), "Downloads")
                name  = base + ".mp3"
                dest  = os.path.join(dl, name)
                if os.path.exists(dest):
                    name = base + "_" + datetime.now().strftime("%H%M%S") + ".mp3"
                    dest = os.path.join(dl, name)
                shutil.copy(src_path, dest)
                os.unlink(src_path)
                self._set_status("Saved: " + name)
                self._set_play_enabled(True)
                return
            except Exception as e:
                self._set_status("Save failed: " + str(e))
                self._set_play_enabled(True)
                return

        # 3. Speak
        self._set_status("Playing...")
        try:
            if IS_ANDROID:
                if self._tts_ready:
                    Clock.schedule_once(
                        lambda dt: _speak_android(self._tts, kannada, rate_percent), 0
                    )
                    self._set_status("Done.")
                else:
                    self._set_status("TTS not ready yet — try again in a moment.")
            else:
                _speak_desktop(kannada, rate_percent, voice_gender)
                self._set_status("Done.")
        except Exception as e:
            self._set_status("Playback failed: " + str(e))

        self._set_play_enabled(True)


if __name__ == "__main__":
    PaliTTSApp().run()
