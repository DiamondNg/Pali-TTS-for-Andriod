import os

from huggingface_hub import login
from transformers import AutoModel

# 1. Authenticate — set your token first:  export HF_TOKEN=hf_xxx
login(token=os.environ["HF_TOKEN"])

# 2. Load model
repo_id = "ai4bharat/IndicF5"
print("Downloading and loading model...")
model = AutoModel.from_pretrained(repo_id, trust_remote_code=True)
print("IndicF5 loaded successfully!")