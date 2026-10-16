"""CI helper: capture the Pali TTS window, OCR it, print a thumbnail.

Usage: gui_check.py NAME   (run while pali_tts.py is showing its window)
Prints the recognised text, and a base64 JPEG thumbnail between markers.
"""
import base64
import io
import subprocess
import sys

import Quartz
import Vision
from Foundation import NSURL
from PIL import Image

name = sys.argv[1]
pids = {int(p) for p in subprocess.run(["pgrep", "-f", "pali_tts.py"], capture_output=True,
                                       text=True).stdout.split()}
wins = Quartz.CGWindowListCopyWindowInfo(Quartz.kCGWindowListOptionOnScreenOnly, Quartz.kCGNullWindowID)
ours = [w for w in wins if w.get("kCGWindowOwnerPID") in pids and w.get("kCGWindowLayer") == 0]
print(f"[{name}] pids={sorted(pids)} windows={[(w['kCGWindowNumber'], dict(w['kCGWindowBounds'])) for w in ours]}")
if not ours:
    print(f"[{name}] NO WINDOW")
    sys.exit(0)
wid = ours[0]["kCGWindowNumber"]
path = f"shots/{name}-window.png"
subprocess.run(["screencapture", "-x", "-o", f"-l{wid}", path], check=True)

req = Vision.VNRecognizeTextRequest.alloc().init()
handler = Vision.VNImageRequestHandler.alloc().initWithURL_options_(NSURL.fileURLWithPath_(path), None)
handler.performRequests_error_([req], None)
text = [o.topCandidates_(1)[0].string() for o in (req.results() or [])]
print(f"[{name}] OCR ({len(text)} lines): {text}")

im = Image.open(path).convert("RGB")
im.thumbnail((480, 640))
buf = io.BytesIO()
im.save(buf, "JPEG", quality=70)
print(f"[{name}] THUMB-BEGIN")
print(base64.b64encode(buf.getvalue()).decode())
print(f"[{name}] THUMB-END")
