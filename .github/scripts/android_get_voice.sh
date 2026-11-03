#!/bin/bash
# Offline Piper Kannada voice for the Android app (run from the repository root, before Gradle):
#  - android/app/libs/sherpa-onnx.aar: the engine (sherpa-onnx 1.13.8 = the last version with
#    eSpeak NG, which Piper voices need; 2.x dropped it)
#  - android/app/src/main/assets/piper/: the voice converted for sherpa-onnx (model.onnx with
#    metadata, tokens.txt) + eSpeak NG data (only the Kannada dictionary)
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

A=android/app/src/main/assets/piper
rm -rf "$A" && mkdir -p "$A"
cp "$W/$MODEL.onnx" "$A/model.onnx"
cp "$W/tokens.txt" "$A/tokens.txt"
# eSpeak NG data as packaged by sherpa-onnx with its Piper voices; keep only Kannada's dictionary
curl -fsSL --retry 3 -o "$W/amy.tar.bz2" \
  "https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-piper-en_US-amy-low.tar.bz2"
tar xjf "$W/amy.tar.bz2" -C "$W" --wildcards '*/espeak-ng-data/*'
cp -r "$W"/vits-piper-en_US-amy-low/espeak-ng-data "$A/"
find "$A/espeak-ng-data" -maxdepth 1 -name '*_dict' ! -name 'kn_dict' -delete
ls -l "$A" && du -sh "$A" "$A/espeak-ng-data" && head -5 "$A/tokens.txt"
python3 -c "import onnx; m = onnx.load('$A/model.onnx'); print({p.key: p.value for p in m.metadata_props})"
rm -rf "$W"
