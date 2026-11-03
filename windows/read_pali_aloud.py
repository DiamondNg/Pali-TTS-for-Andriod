"""Windows entry point of ReadPaliAloud.exe (built with PyInstaller).

  ReadPaliAloud.exe                      open the window
  ReadPaliAloud.exe --input-file F       open the window with the text in F
  ReadPaliAloud.exe --hotkey             background helper: Ctrl+Alt+P reads the selection
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
        lines.append("SELFTEST OK")
    except Exception:
        lines.append(traceback.format_exc())
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    args = sys.argv[1:]
    if "--hotkey" in args:
        import hotkey
        hotkey.main()
    elif "--selftest" in args:
        selftest(args[args.index("--selftest") + 1])
    else:
        import pali_tts
        pali_tts.main()


if __name__ == "__main__":
    main()
