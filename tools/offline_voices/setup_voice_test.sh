#!/bin/bash
# Sets up the OFFLINE Kannada voice test on a Mac (test only, not the app).
# Everything goes into ~/PaliTTS-voice-test (delete that folder to remove it all).
# Run in Terminal:
#   curl -fsSL https://raw.githubusercontent.com/DiamondNg/Pali-TTS-for-Andriod/claude/admiring-faraday-g9lutn/tools/offline_voices/setup_voice_test.sh | bash
set -euo pipefail
BRANCH="${BRANCH:-claude/admiring-faraday-g9lutn}"
RAW="https://raw.githubusercontent.com/DiamondNg/Pali-TTS-for-Andriod/$BRANCH/tools/offline_voices"
DIR="$HOME/PaliTTS-voice-test"
UV_VERSION=0.12.21
HF="https://huggingface.co/micahchoo/piper-kn"
MODEL=kn_IN-syspin_male-medium.onnx
mkdir -p "$DIR/piper" "$DIR/bin"
export UV_PYTHON_INSTALL_DIR="$DIR/python" UV_CACHE_DIR="$DIR/cache"

echo "1/4  Tool for a private Python (uv $UV_VERSION)..."
case "$(uname -m)" in arm64) ARCH=aarch64 ;; *) ARCH=x86_64 ;; esac
if [ ! -x "$DIR/bin/uv" ]; then
  curl -fsSL "https://github.com/astral-sh/uv/releases/download/$UV_VERSION/uv-$ARCH-apple-darwin.tar.gz" \
    | tar -xzf - -C "$DIR/bin" --strip-components 1
fi

echo "2/4  Python + Piper + eSpeak NG (about 150 MB)..."
[ -x "$DIR/venv/bin/python" ] || "$DIR/bin/uv" venv -q --python 3.12 "$DIR/venv"
"$DIR/bin/uv" pip install -q --python "$DIR/venv/bin/python" piper-tts espeakng-loader certifi

echo "3/4  Piper Kannada voice from Hugging Face (about 60 MB)..."
# Find the model's folder in the repository (in case it is not at the top)
PATH_IN_REPO=$(curl -fsSL "https://huggingface.co/api/models/micahchoo/piper-kn" \
  | grep -o "\"rfilename\":\"[^\"]*$MODEL\"" | head -1 | sed 's/.*:"//; s/"$//') || true
PATH_IN_REPO="${PATH_IN_REPO:-$MODEL}"
for f in "$PATH_IN_REPO" "$PATH_IN_REPO.json"; do
  [ -s "$DIR/piper/$(basename "$f")" ] || curl -fL --progress-bar -o "$DIR/piper/$(basename "$f")" "$HF/resolve/main/$f"
done

echo "4/4  Test script..."
curl -fsSL -o "$DIR/kannada_voice_test.py" "$RAW/kannada_voice_test.py"
cat > "$DIR/run.sh" <<'RUN'
#!/bin/bash
exec "$HOME/PaliTTS-voice-test/venv/bin/python" "$HOME/PaliTTS-voice-test/kannada_voice_test.py" "$@"
RUN
chmod +x "$DIR/run.sh"

echo
if say -v '?' | grep 'kn_IN' >/dev/null; then
  echo "Mac Kannada voice: installed."
else
  echo "Mac Kannada voice (Soumya) is NOT installed. To add it: System Settings → Accessibility"
  echo "→ Spoken Content → System voice → Manage Voices… → Kannada → Soumya (download)."
fi
echo "Done. Now a short test (each voice says the same words):"
"$DIR/run.sh" "Evaṃ me sutaṃ. Ekaṃ samayaṃ bhagavā sāvatthiyaṃ viharati."
