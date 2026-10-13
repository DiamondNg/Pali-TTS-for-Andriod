import os
import sys
import numpy as np
import soundfile as sf
import torch
from transformers import AutoModel
from aksharamukha import transliterate

os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"

# 1. Hardware target
device = "mps" if torch.backends.mps.is_available() else "cpu"

# 2. Interactive Prompts
print("\n--- Pāḷi Text-to-Speech ---")
voice_choice = input("Select Voice - (M)ale or (F)emale? [Default: F]: ").strip().lower()
target_pali_roman = input("\nEnter the Pāḷi text to synthesize:\n> ").strip()

if not target_pali_roman:
    print("Error: Target text cannot be empty.")
    sys.exit(1)

# 3. Assign files based on user selection
if voice_choice.startswith('m'):
    ref_audio = "PaliM.wav"
    output_filename = "generated_male.wav"
else:
    ref_audio = "PaliF.wav"
    output_filename = "generated_female.wav"

if not os.path.exists(ref_audio):
    print(f"Error: {ref_audio} not found in the current directory.")
    sys.exit(1)

# 4. Transliteration
# This MUST match the exact text spoken in the reference clips.
ref_pali_roman = "Kathañca, bhikkhave, bhikkhu kāye kāyānupassī viharati?"

print("\nTransliterating Pāḷi Roman to Kannada script...")
ref_kannada = transliterate.process("IASTPali", "Kannada", ref_pali_roman, nativize=True)
target_kannada = transliterate.process("IASTPali", "Kannada", target_pali_roman, nativize=True)

# 5. Model Loading
print(f"Loading IndicF5 model to {device}...")
model = AutoModel.from_pretrained("ai4bharat/IndicF5", trust_remote_code=True)
model = model.to(device)

# 6. Audio Synthesis
print(f"Synthesizing using {ref_audio}...")
audio = model(
    target_kannada,
    ref_audio_path=ref_audio,
    ref_text=ref_kannada,
)

# 7. Audio Export
if audio.dtype == np.int16:
    audio = audio.astype(np.float32) / 32768.0

sf.write(output_filename, audio, samplerate=24000)
print(f"\nDone. Audio saved as {output_filename}")