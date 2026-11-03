#!/bin/bash
# Offline Piper Kannada voice for the Android app (run from the repository root, before Gradle):
#  - android/app/libs/sherpa-onnx.aar: the engine (sherpa-onnx 1.13.8 = the last version with
#    eSpeak NG, which Piper voices need; 2.x dropped it)
#  - dist-voice/piper-kn-<hash>.zip: the voice converted for sherpa-onnx (model.onnx with
#    metadata, tokens.txt) + eSpeak NG data (only the Kannada dictionary). Not in the APK:
#    the app downloads it from the GitHub Release "android-voice" when someone chooses Piper.
#  - android/app/src/main/assets/piper_download.json: where the app finds that zip
set -euo pipefail
SHERPA=1.13.8
MODEL=kn_IN-syspin_male-medium
bash .github/scripts/get_piper_model.sh          # → voices/$MODEL.onnx(.json)

mkdir -p android/app/libs
curl -fsSL --retry 3 -o android/app/libs/sherpa-onnx.aar \
  "https://github.com/k2-fsa/sherpa-onnx/releases/download/v$SHERPA/sherpa-onnx-$SHERPA.aar"

W=$(mktemp -d)
cp "voices/$MODEL.onnx" "voices/$MODEL.onnx.json" "$W/"
# sherpa-onnx's own converter (same release): writes tokens.txt, adds metadata to the model
curl -fsSL --retry 3 -o "$W/add_meta_data.py" \
  "https://raw.githubusercontent.com/k2-fsa/sherpa-onnx/v$SHERPA/scripts/piper/add_meta_data.py"
python3 -m pip install --quiet onnx iso639-lang
(cd "$W" && python3 add_meta_data.py --lang kn_IN --name syspin_male --kind medium)

A="$W/piper"
rm -rf "$A" && mkdir -p "$A"
cp "$W/$MODEL.onnx" "$A/model.onnx"
# sherpa-onnx 1.13.8 reads one letter per token (as Piper itself phonemizes: letter by letter);
# this model's table also lists some two-letter entries ("aɪ"), which would stop the engine.
python3 - "$W/tokens.txt" "$A/tokens.txt" "voices/$MODEL.onnx.json" <<'PY'
import json, sys
src, dst, cfg = sys.argv[1:]
c = json.load(open(cfg, encoding="utf-8"))
print("phoneme_type:", c.get("phoneme_type"), "espeak:", c.get("espeak"))
kept, dropped = [], []
for line in open(src, encoding="utf-8").read().split("\n"):
    if not line:
        continue
    tok, _, idx = line.rpartition(" ")
    (kept if len(tok) == 1 else dropped).append(line)
open(dst, "w", encoding="utf-8").write("\n".join(kept) + "\n")
print("tokens kept:", len(kept), "dropped (more than one letter):", dropped)
PY
# eSpeak NG data as packaged by sherpa-onnx with its Piper voices; keep only Kannada's dictionary
curl -fsSL --retry 3 -o "$W/amy.tar.bz2" \
  "https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-piper-en_US-amy-low.tar.bz2"
tar xjf "$W/amy.tar.bz2" -C "$W" --wildcards '*/espeak-ng-data/*'
cp -r "$W"/vits-piper-en_US-amy-low/espeak-ng-data "$A/"
find "$A/espeak-ng-data" -maxdepth 1 -name '*_dict' ! -name 'kn_dict' -delete
ls -l "$A" && du -sh "$A" "$A/espeak-ng-data" && head -5 "$A/tokens.txt"
python3 -c "import onnx; m = onnx.load('$A/model.onnx'); print({p.key: p.value for p in m.metadata_props})"
# Name by content: a voice already on the Release is never replaced, so older apps keep working
H=$(cat "$A/model.onnx" "$A/tokens.txt" | sha256sum | cut -c1-12)
NAME="piper-kn-$H.zip"
mkdir -p dist-voice
rm -f dist-voice/*.zip
(cd "$A" && find . -exec touch -d '2026-01-01 00:00:00' {} + && zip -qrX "$OLDPWD/dist-voice/$NAME" .)
SIZE=$(stat -c %s "dist-voice/$NAME")
mkdir -p android/app/src/main/assets
REPO="${GITHUB_REPOSITORY:-DiamondNg/Pali-TTS-for-Andriod}"
cat > android/app/src/main/assets/piper_download.json <<JSON
{"url": "https://github.com/$REPO/releases/download/android-voice/$NAME", "name": "$NAME", "size": $SIZE}
JSON
cat android/app/src/main/assets/piper_download.json
ls -l dist-voice
rm -rf "$W"
