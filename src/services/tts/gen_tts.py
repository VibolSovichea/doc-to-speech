import mimetypes
import os
import re
import struct
from pathlib import Path
from typing import Dict, List, Optional

from google import genai
from google.genai import types

PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = PROJECT_ROOT / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
_SAFE_FILENAME = re.compile(r"[^A-Za-z0-9._-]+")

_CLIENT: Optional[genai.Client] = None

DEFAULT_MODEL = os.getenv("GEMINI_TTS_MODEL", "gemini-2.5-flash-preview-tts")
DEFAULT_VOICE = os.getenv("GEMINI_TTS_VOICE", "Zephyr")


def _get_client() -> genai.Client:
    global _CLIENT
    if _CLIENT:
        return _CLIENT

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is required to call Gemini TTS.")

    _CLIENT = genai.Client(api_key=api_key)
    return _CLIENT


def _safe_base_name(name_hint: Optional[str], fallback: str = "gemini-output") -> str:
    if name_hint:
        base_name = os.path.splitext(os.path.basename(name_hint))[0]
    else:
        base_name = fallback

    base_name = base_name.strip() or fallback
    return _SAFE_FILENAME.sub("_", base_name)


def _build_output_path(base_name: str, index: int, extension: str) -> Path:
    suffix = f"-{index}" if index else ""
    return OUTPUT_DIR / f"{base_name}{suffix}{extension}"


def _extract_inline_audio(chunk: types.GenerateContentResponse) -> Optional[types.Part]:
    if (
        not chunk.candidates
        or not chunk.candidates[0].content
        or not chunk.candidates[0].content.parts
    ):
        return None

    part = chunk.candidates[0].content.parts[0]
    if getattr(part, "inline_data", None) and part.inline_data.data:
        return part
    return None


def generate_audio_from_text(
    text: str,
    *,
    name_hint: Optional[str] = None,
    model: Optional[str] = None,
    voice_name: Optional[str] = None,
) -> List[str]:
    """Generate audio files from text using Gemini TTS streaming API."""
    cleaned_text = (text or "").strip()
    if not cleaned_text:
        raise ValueError("Text input is required to synthesize speech.")

    client = _get_client()
    base_name = _safe_base_name(name_hint, fallback="gemini-output")

    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=cleaned_text)],
        )
    ]

    voice_config = types.VoiceConfig(
        prebuilt_voice_config=types.PrebuiltVoiceConfig(
            voice_name=voice_name or DEFAULT_VOICE
        )
    )

    config = types.GenerateContentConfig(
        temperature=1,
        response_modalities=["audio"],
        speech_config=types.SpeechConfig(voice_config=voice_config),
    )

    saved_files: List[str] = []
    index = 0

    for chunk in client.models.generate_content_stream(
        model=model or DEFAULT_MODEL,
        contents=contents,
        config=config,
    ):
        part = _extract_inline_audio(chunk)
        if not part:
            continue

        inline_data = part.inline_data
        data_buffer = inline_data.data
        extension = mimetypes.guess_extension(inline_data.mime_type)

        if extension is None:
            extension = ".wav"
            data_buffer = convert_to_wav(inline_data.data, inline_data.mime_type)

        output_path = _build_output_path(base_name, index, extension)
        output_path.write_bytes(data_buffer)
        saved_files.append(f"/outputs/{output_path.name}")
        index += 1

    if not saved_files:
        raise RuntimeError("Gemini TTS stream completed without audio data.")

    return saved_files


def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    """Wrap raw audio into a WAV container."""
    parameters = parse_audio_mime_type(mime_type)
    bits_per_sample = parameters["bits_per_sample"] or 16
    sample_rate = parameters["rate"] or 24000
    num_channels = 1
    data_size = len(audio_data)
    bytes_per_sample = bits_per_sample // 8
    block_align = num_channels * bytes_per_sample
    byte_rate = sample_rate * block_align
    chunk_size = 36 + data_size

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        chunk_size,
        b"WAVE",
        b"fmt ",
        16,
        1,
        num_channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b"data",
        data_size,
    )
    return header + audio_data


def parse_audio_mime_type(mime_type: str) -> Dict[str, Optional[int]]:
    """Extract rate and bit depth from a MIME type string, if present."""
    bits_per_sample: Optional[int] = None
    rate: Optional[int] = None

    parts = [param.strip() for param in mime_type.split(";") if param.strip()]
    for param in parts:
        lower = param.lower()
        if lower.startswith("rate="):
            try:
                rate = int(param.split("=", 1)[1])
            except (ValueError, IndexError):
                rate = None
        elif "audio/l" in lower:
            try:
                bits_part = param.split("l", 1)[1]
                bits_per_sample = int(bits_part)
            except (ValueError, IndexError):
                bits_per_sample = None

    return {"bits_per_sample": bits_per_sample, "rate": rate}


__all__ = [
    "generate_audio_from_text",
    "convert_to_wav",
    "parse_audio_mime_type",
]
