import os
import re
from pathlib import Path

import scipy
import torch
from transformers import AutoModelForPreTraining, AutoTokenizer
from transformers.models.vits.modeling_vits import VitsModel

transformer_model = "mrrtmob/khmer-tts"
hf_token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_API_KEY")

PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = PROJECT_ROOT / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
_SAFE_FILENAME = re.compile(r"[^A-Za-z0-9._-]+")

model = None
tokenizer = None
_load_error = None


def _load_model():
    global model, tokenizer, _load_error

    if model is not None and tokenizer is not None:
        return model, tokenizer

    if _load_error:
        raise _load_error

    try:
        model = VitsModel.from_pretrained("Kimang18/mms-tts-khm-finetuned")
        tokenizer = AutoTokenizer.from_pretrained("Kimang18/mms-tts-khm-finetuned")
    except Exception as exc:
        _load_error = exc
        raise

    return model, tokenizer


def generate_audio(text, file_name):
    model, tokenizer = _load_model()
    base_name = os.path.splitext(os.path.basename(file_name or "output"))[0].strip()
    if not base_name:
        base_name = "output"
    safe_name = _SAFE_FILENAME.sub("_", base_name)
    audio_path = OUTPUT_DIR / f"{safe_name}.wav"

    inputs = tokenizer(text, return_tensors="pt")
    with torch.no_grad():
        output = model(**inputs).waveform
        scipy.io.wavfile.write(
            audio_path,
            rate=model.config.sampling_rate,
            data=output[0].cpu().numpy(),
        )

    return f"/outputs/{audio_path.name}"
