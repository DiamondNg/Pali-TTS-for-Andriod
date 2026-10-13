import os
import sys

# Critical: Must be set BEFORE importing torch to prevent the aten::_fft_r2c MPS crash
os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"

from aksharamukha import transliterate
import numpy as np
import soundfile as sf
import torch
from transformers import AutoModel

# 1. Device Selection
# Uses Apple Silicon GPU acceleration with CPU fallback for unsupported FFT kernels
device = "mps" if torch.backends.mps.is_available() else "cpu"
print(f"Executing on hardware device: {device}")

# 2. Voice Selection
print("\n--- Pāḷi Text-to-Speech (IndicF5) ---")
voice_choice = (
    input("Select Voice -> (F)emale [PaliF.wav] or (M)ale [PaliM.wav] (default: F): ")
    .strip()
    .lower()
)

if voice_choice.startswith("m"):
    ref_audio = "PaliM.wav"
    output_filename = "generated_pali_male.wav"
    speaker = "Male"
else:
    ref_audio = "PaliF.wav"
    output_filename = "generated_pali_female.wav"
    speaker = "Female"

if not os.path.exists(ref_audio):
    print(
        f"\nError: '{ref_audio}' was not found in the current working directory."
    )
    print("Ensure the file exists and is located in the same folder as this script.")
    sys.exit(1)

# 3. Multiline Input Capture
# Standard input() breaks on line returns. This loop captures multi-line pasted text.
print(
    f"\nSelected Voice: {speaker} ({ref_audio})"
)
print("Paste your Pāḷi text below. When finished, press Enter twice:")

lines = []
while True:
    try:
        line = input()
        if not line.strip():
            if lines:
                break
            continue
        lines.append(line.strip())
    except EOFError:
        break

target_pali_roman = " ".join(lines).strip()

# Strip curly quotation marks that can corrupt tokenization
target_pali_roman = (
    target_pali_roman.replace("“", "")
    .replace("”", "")
    .replace('"', "")
    .replace("'", "")
)

if not target_pali_roman:
    print("Error: No text was provided.")
    sys.exit(1)

# 4. Reference Transcript & Transliteration
# Must match the spoken content of PaliF.wav and PaliM.wav exactly
ref_pali_roman = "Kathañca, bhikkhave, bhikkhu kāye kāyānupassī viharati?"

print("\n[1/3] Transliterating Roman Pāḷi to Kannada script...")
ref_kannada = transliterate.process(
    "IASTPali", "Kannada", ref_pali_roman, nativize=True
)
target_kannada = transliterate.process(
    "IASTPali", "Kannada", target_pali_roman, nativize=True
)

# 5. Load Model
print(f"[2/3] Loading IndicF5 model to {device}...")
try:
    model = AutoModel.from_pretrained("ai4bharat/IndicF5", trust_remote_code=True)
    model = model.to(device)
except Exception as e:
    print(f"Error loading model to {device}: {e}")
    print("Attempting fallback to CPU...")
    device = "cpu"
    model = AutoModel.from_pretrained("ai4bharat/IndicF5", trust_remote_code=True)
    model = model.to("cpu")

# 6. Synthesize Speech
print(f"[3/3] Synthesizing audio via {speaker} voice...")
audio = model(
    target_kannada,
    ref_audio_path=ref_audio,
    ref_text=ref_kannada,
)

# 7. Format Conversion & Audio Export
if audio.dtype == np.int16:
    audio = audio.astype(np.float32) / 32768.0

sf.write(output_filename, audio, samplerate=24000)
print(f"\nGeneration complete. Audio saved to: {output_filename}\n")