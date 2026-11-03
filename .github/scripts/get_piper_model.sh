#!/bin/bash
# Downloads the offline Kannada Piper voice (Hugging Face micahchoo/piper-kn) into ./voices
# (the app looks for voices/kn_IN-syspin_male-medium.onnx + .onnx.json next to pali_tts.py).
set -euo pipefail
MODEL=kn_IN-syspin_male-medium.onnx
HF=https://huggingface.co/micahchoo/piper-kn
mkdir -p voices
# The model's path in the repository (in case it is in a folder)
P=$(curl -fsSL --retry 3 "https://huggingface.co/api/models/micahchoo/piper-kn" \
    | grep -o "\"rfilename\":\"[^\"]*$MODEL\"" | head -1 | sed 's/.*:"//; s/"$//') || true
P="${P:-$MODEL}"
echo "model path in repository: $P"
for f in "$P" "$P.json"; do
  curl -fsSL --retry 3 -o "voices/$(basename "$f")" "$HF/resolve/main/$f"
done
ls -l voices
# Record exactly which file was bundled
(command -v sha256sum >/dev/null && sha256sum voices/*) || shasum -a 256 voices/*
