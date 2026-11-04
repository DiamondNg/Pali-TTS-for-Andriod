# Read Pāli Aloud for Android: the Python side, called from Kotlin (Chaquopy).
# All text handling comes from pali_core.py (shared with the desktop app), so every platform
# detects languages and transliterates exactly the same way.
# Copyright (C) 2026 Āyasmā Paññādhammika — AGPL-3.0-or-later (see LICENSE).
import json
import re
import sys
import types
import unicodedata


def _stub_aksharamukha_dependencies():
    """aksharamukha imports packages it needs only for other scripts (Hebrew, Japanese,
    files...). They are not installed on Android; these stand-ins let the import work.
    Checked on 362 lines of the Pātimokkha: output identical to the full install."""
    def module(name, **attrs):
        if name not in sys.modules:
            m = types.ModuleType(name)
            m.__dict__.update(attrs)
            sys.modules[name] = m

    sys.modules.setdefault("regex", re)             # gimeltra: Semitic scripts only
    module("yaml", safe_load=lambda stream: {})     # only a "hacked font" warning
    module("requests")                              # only an online Malayalam option
    module("langcodes")                             # only language-name lookups
    module("fontTools", unicodedata=unicodedata)    # gimeltra only
    sys.modules.setdefault("fontTools.unicodedata", unicodedata)


_stub_aksharamukha_dependencies()
import pali_core as core  # noqa: E402  (after the stand-ins)


def speeds():
    """Pāli speed labels ("0.33x" ...) and the default index, as JSON."""
    return json.dumps({"labels": [s[0] for s in core.SPEEDS], "default": core.DEFAULT_SPEED,
                       "translation": core.TRANSLATION_SPEEDS})


def prepare_text(raw):
    return core.prepare_text(raw)


def segments(text, mode):
    """[[lang, text], ...] to read, as JSON. lang "pi" = Pāli, otherwise the language
    code of a translation line. Same rules as the desktop app."""
    text = text.strip()
    if mode == "pi":
        pali = " ".join(core.filter_pali_lines(text).split())
        segs = [["pi", pali]] if pali else []
    else:
        segs = [list(s) for s in core.split_segments(text)]
        if mode == "en":
            segs = [s for s in segs if s[0] != "pi"]
    return json.dumps(segs, ensure_ascii=False)


def kannada(text):
    """Pāli (IAST) → Kannada script, spelled for the Kannada voice."""
    return core.to_kannada(text)


def microsoft(jobs_json, speed_index, voice):
    """Microsoft's online Kannada voice. jobs: [[kannada_text, mp3_path], ...],
    made at the same time."""
    jobs = [tuple(j) for j in json.loads(jobs_json)]
    rate = core.SPEEDS[int(speed_index)][1]
    core.generate_audio_many(jobs, rate, voice)


def rate_factor(speed_index):
    """Speed factor of a Pāli speed step for the offline (Android) voice, as on desktop."""
    return core.rate_factor(core.SPEEDS[int(speed_index)][1])


def save_name(mode, first_text, speed_index, translation_speed):
    """File name (without extension) for saved audio, as on the desktop."""
    words = first_text.split()[:4]
    base = re.sub(r'[/:\\*?"<>|,;.\(\)\'“”‘’]', "", "_".join(words)).strip("_") or "pali_audio"
    pali = core.SPEEDS[int(speed_index)][0]
    en = core.speed_label(float(translation_speed))
    if mode == "pi":
        return base + "_" + pali
    if mode == "en":
        return base + "_translation_" + en
    return base + "_pali_%s_translation_%s" % (pali, en)


def selftest():
    """Used by the automated build test (no audio: Microsoft blocks build servers)."""
    sample = ("Namo tassa bhagavato arahato sammāsambuddhassa.\n"
              "Homage to the Blessed One, the Worthy One, the Perfectly Enlightened One.\n"
              "Aññaṃ pucchāmi.")
    segs = json.loads(segments(sample, "both"))
    kn = kannada(segs[0][1])
    return json.dumps({"segments": segs, "kannada": kn,
                       "nya": core.NYA_SPOKEN in kannada("aññaṃ")}, ensure_ascii=False)
