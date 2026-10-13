import os
import sys

from aksharamukha import transliterate
import numpy as np
import soundfile as sf
import torch
from transformers import AutoModel

# 1. Device Selection (Must be CPU on macOS due to MPS ComplexFloat limitations)
device = "cpu"
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
    print(f"\nError: '{ref_audio}' was not found in the current directory.")
    sys.exit(1)

# 3. Multiline Input Capture
print(f"\nSelected Voice: {speaker} ({ref_audio})")
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

# Sanitize quotation marks and dashes
for char in ['“', '”', '"', "'", "—", "–"]:
    target_pali_roman = target_pali_roman.replace(char, " ")

if not target_pali_roman.strip():
    print("Error: No text provided.")
    sys.exit(1)

# 4. Transliteration
# Must match the spoken content of PaliF.wav and PaliM.wav exactly
ref_pali_roman = "Kathañca, bhikkhave, bhikkhu kāye kāyānupassī viharati?"

print("\n[1/3] Transliterating Roman Pāḷi to Kannada script...")
ref_kannada = transliterate.process(
    "IASTPali", "Kannada", ref_pali_roman, nativize=True
)
target_kannada = transliterate.process(
    "IASTPali", "Kannada", target_pali_roman, nativize=True
)

# 5. Load Model to CPU
print(f"[2/3] Loading IndicF5 model to {device}...")
model = AutoModel.from_pretrained("ai4bharat/IndicF5", trust_remote_code=True)
model = model.to(device)

# 6. Audio Generation
print(f"[3/3] Synthesizing audio via {speaker} voice (CPU inference)...")
audio = model(
    target_kannada,
    ref_audio_path=ref_audio,
    ref_text=ref_kannada,
)

# 7. Export Audio
if audio.dtype == np.int16:
    audio = audio.astype(np.float32) / 32768.0

sf.write(output_filename, audio, samplerate=24000)
print(f"\nDone. Audio exported to: {output_filename}\n")