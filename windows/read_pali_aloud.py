"""Windows entry point of ReadPaliAloud.exe (built with PyInstaller).

  ReadPaliAloud.exe                      open the window (and run in the tray)
  ReadPaliAloud.exe --input-file F       open the window with the text in F
  ReadPaliAloud.exe --tray               run in the tray only (Windows startup);
                                         --hotkey (v2.2–v2.4) does the same
  If it is already running, the running copy shows its window instead.
  ReadPaliAloud.exe --selftest OUT       write a check of the bundled parts to OUT (CI)
"""
import sys


def selftest(out_path):
    import traceback
    lines = []
    try:
        import pali_tts
        lines.append("kannada: " + pali_tts.to_kannada("Evaṃ me sutaṃ. aññaṃ paññā"))
        import edge_tts, certifi, tkinter  # noqa: F401
        lines.append("edge_tts %s, certifi %s" % (edge_tts.__version__, certifi.where()))
        r = tkinter.Tk()
        lines.append("Tk %s" % r.call("info", "patchlevel"))
        r.destroy()
        voices = pali_tts.system_voices()
        lines.append("%d voices: %s" % (len(voices), "; ".join(l for l, _ in voices)))
        lines.append("segments: %r" % pali_tts.split_segments(
            "Evaṃ me sutaṃ.\nThus have I heard.\n如是我闻。\nDemikianlah yang saya dengar."))
        # Translation voices → WAV → join (offline; Microsoft's Pāli voice can't be reached in CI)
        import tempfile, os
        work = tempfile.mkdtemp()
        sapi = [v for _, v in voices if v.startswith("sapi:")][:1]
        for vid, speed in [("", 0.75), ("", 3.0)] + [(v, 3.0) for v in sapi]:
            src = pali_tts.speak_many([("Thus have I heard.", os.path.join(work, "a"))],
                                      vid, speed, work)[0]
            pali_tts.to_wav(src, os.path.join(work, "a.wav"))
            secs = pali_tts.join_wavs([os.path.join(work, "a.wav")] * 2,
                                      os.path.join(work, "j.wav"))
            lines.append("voice %r at %gx: joined %.2f s" % (vid or "default", speed, secs))
        pali_tts.wav_to_mp3(os.path.join(work, "j.wav"), os.path.join(work, "j.mp3"))
        lines.append("mp3: %d bytes" % os.path.getsize(os.path.join(work, "j.mp3")))
        pali_tts.to_wav(os.path.join(work, "j.mp3"), os.path.join(work, "back.wav"))
        # Offline Pāli voice (Piper), alone and in Both mode
        lines.append("piper model: %s" % pali_tts.piper_model_path())
        kn = pali_tts.to_kannada("Evaṃ me sutaṃ. Ekaṃ samayaṃ bhagavā sāvatthiyaṃ viharati.")
        for rate in ["-25%", "-75%"]:
            out, secs = pali_tts.build_joined([("kn", kn)], rate, "piper", None, 1.0)
            lines.append("piper %s: %.2f s" % (rate, secs))
            assert secs > 1.5, "Piper audio too short"
        out, secs = pali_tts.build_joined([("kn", kn), ("en", "Thus have I heard.")],
                                          "-25%", "piper", lambda lang: "", 1.0)
        lines.append("both with piper: %.2f s" % secs)
        lines.append("auto voices: %r" % {lang: pali_tts.pick_voice(voices, lang)
                                          for lang in ["en", "zh", "ja", "ms", "es"]})
        import tray, uia  # noqa: F401  (UI Automation wrappers must be bundled)
        uia._client()
        lines.append("UI Automation: %s" % uia.UIA.__name__)
        lines.append("help: %d characters" % len(pali_tts.help_text(tray=True)))
        lines.append("SELFTEST OK")
    except Exception:
        lines.append(traceback.format_exc())
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    args = sys.argv[1:]
    if "--selftest" in args:
        selftest(args[args.index("--selftest") + 1])
        return
    import tray
    if "--tray" in args or "--hotkey" in args:
        tray.main(show=False)
    else:
        import pali_tts
        tray.main(show=True, text=pali_tts.read_input())


if __name__ == "__main__":
    main()
