"""Try OFFLINE Kannada voices on Pāli text (test tool, not part of the app).

Usage:  python kannada_voice_test.py "Evaṃ me sutaṃ ..."      (or text on stdin)

Pāli (IAST) → Kannada script (same rules as the app: quotes removed, ṁ → ṃ,
ññ → ನ್ನ್ಯ; local aksharamukha, online service as fallback), then the text is
spoken by each available offline voice, one after another:
  1. Mac voice "Soumya" (Kannada, built into macOS; add it in System Settings)
  2. Piper "kn_IN-syspin_male-medium" (neural, micahchoo/piper-kn on Hugging Face)
  3. eSpeak NG "kn" (rule-based, very small, robotic)
Each result is saved in ~/Downloads/Kannada voice test/ so they can be compared.
Set ONLY=piper (or mac / espeak) to hear just one voice.
"""
import ctypes
import os
import re
import shutil
import subprocess
import sys
import time
import wave

try:  # the Python from uv has no CA certificates of its own (HTTPS fallback)
    import certifi
    os.environ.setdefault("SSL_CERT_FILE", certifi.where())
except ImportError:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = os.path.join(HERE, "piper", "kn_IN-syspin_male-medium.onnx")
OUT_DIR = os.path.expanduser("~/Downloads/Kannada voice test")
NYA_AKSHARAMUKHA, NYA_SPOKEN = "ಞ್ಞ", "ನ್ನ್ಯ"


def notify(msg):
    if sys.platform == "darwin":
        subprocess.run(["osascript", "-e", 'display notification "%s" with title '
                        '"Kannada voice test"' % msg.replace('"', "'")], capture_output=True)
    print(msg, flush=True)


# ── Pāli → Kannada (as pali_tts.to_kannada) ─────────────────────────────────
def to_kannada(text):
    text = re.sub(r"[\"'“”‘’]", "", text).replace("ṁ", "ṃ").replace("Ṁ", "Ṃ")
    text = re.sub(r"[–—-]", " ", text)
    try:
        import ast
        if not hasattr(ast, "Str"):
            ast.Str = str
        from aksharamukha import transliterate
        kn = transliterate.process("IASTPali", "Kannada", text, nativize=True)
    except Exception:
        import urllib.parse
        import urllib.request
        data = urllib.parse.urlencode({"source": "IASTPali", "target": "Kannada",
                                       "nativize": "true", "text": text}).encode()
        with urllib.request.urlopen("https://aksharamukha-plugin.appspot.com/api/public",
                                    data, timeout=30) as r:
            kn = r.read().decode("utf-8")
    for ch in ".;!?":
        kn = kn.replace(ch, "।")
    return kn.replace(NYA_AKSHARAMUKHA, NYA_SPOKEN)


# ── Voices ─────────────────────────────────────────────────────────────────
def mac_voice():
    """Name of an installed Kannada Mac voice (Soumya), or None."""
    if sys.platform != "darwin":
        return None
    out = subprocess.run(["say", "-v", "?"], capture_output=True, text=True).stdout
    for line in out.splitlines():
        m = re.match(r"(.+?)\s+(kn[_-]IN)\b", line)
        if m:
            return m.group(1).strip()
    return None


def speak_mac(kn, path):
    voice = mac_voice()
    if not voice:
        raise RuntimeError("no Kannada Mac voice: System Settings → Accessibility → Spoken "
                           "Content → System voice → Manage Voices → Kannada → Soumya")
    subprocess.run(["say", "-v", voice, "-o", path, kn], check=True)
    return "Mac " + voice


def speak_piper(kn, path):
    if not os.path.exists(MODEL):
        raise RuntimeError("Piper model missing (run the setup again)")
    from piper import PiperVoice
    voice = PiperVoice.load(MODEL)
    with wave.open(path, "wb") as f:
        voice.synthesize_wav(kn, f)
    return "Piper kn_IN syspin male"


def speak_espeak(kn, path):
    import espeakng_loader
    lib = ctypes.cdll.LoadLibrary(espeakng_loader.get_library_path())
    data = espeakng_loader.get_data_path()
    chunks = []
    CB = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.POINTER(ctypes.c_short), ctypes.c_int,
                          ctypes.c_void_p)

    def on_audio(wav, n, events):
        if n > 0:
            chunks.append(ctypes.string_at(wav, n * 2))
        return 0
    cb = CB(on_audio)
    lib.espeak_Initialize.restype = ctypes.c_int
    lib.espeak_ng_InitializePath(data.encode())  # the espeak-ng-data folder itself
    rate = lib.espeak_Initialize(2, 0, data.encode(), 0)  # AUDIO_OUTPUT_SYNCHRONOUS
    if rate <= 0:
        raise RuntimeError("eSpeak NG did not start")
    lib.espeak_SetSynthCallback(cb)
    if lib.espeak_SetVoiceByName(b"kn") != 0:
        raise RuntimeError("eSpeak NG has no Kannada voice")
    b = kn.encode("utf-8") + b"\0"
    lib.espeak_Synth(b, len(b), 0, 1, 0, 1, None, None)  # POS_CHARACTER, espeakCHARS_UTF8
    lib.espeak_Synchronize()
    with wave.open(path, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(rate)
        f.writeframes(b"".join(chunks))
    return "eSpeak NG kn"


ENGINES = [("mac", speak_mac, ".aiff"), ("piper", speak_piper, ".wav"),
           ("espeak", speak_espeak, ".wav")]


def play(path):
    if sys.platform == "darwin":
        subprocess.run(["afplay", path])
    elif shutil.which("aplay"):
        subprocess.run(["aplay", "-q", path])


def main():
    text = " ".join(sys.argv[1:]).strip() or sys.stdin.read().strip()
    if not text:
        notify("No text: select some Pāli first.")
        return 1
    kn = to_kannada(text)
    os.makedirs(OUT_DIR, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    with open(os.path.join(OUT_DIR, stamp + "_text.txt"), "w", encoding="utf-8") as f:
        f.write(text + "\n\n" + kn + "\n")
    only = os.environ.get("ONLY", "").lower()
    for n, (key, fn, ext) in enumerate(ENGINES, 1):
        if only and key != only:
            continue
        path = os.path.join(OUT_DIR, "%s_%d_%s%s" % (stamp, n, key, ext))
        try:
            name = fn(kn, path)
        except Exception as e:
            notify("%d. %s: skipped (%s)" % (n, key, e))
            continue
        notify("%d. %s" % (n, name))
        play(path)
        time.sleep(0.7)
    return 0


if __name__ == "__main__":
    sys.exit(main())
