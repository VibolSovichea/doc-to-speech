# doc-to-speech

Document-to-speech pipeline that turns PDFs or images into polished Khmer audio.
The system extracts text via OCR, cleans it with Gemini, and generates spoken
output using either the legacy Hugging Face model or Google’s Gemini TTS.

---

## Architecture Overview

- **FastAPI backend (`src/app.py`)** – Receives uploads, orchestrates document
  extraction, text cleanup, and audio synthesis, then exposes results via REST
  and a lightweight UI.
- **Document extraction service (`src/services/extractor`)** – Handles PDFs via
  PyMuPDF when possible and falls back to OCR (Tesseract + OpenCV preprocessing)
  for scans and images.
- **Gemini helper (`src/utils/gemini_client.py`)** – Wraps the Gemini text model
  for cleanup prompts.
- **Text-to-speech services (`src/services/tts`)** – Contains the original
  Hugging Face based generator (`tts.py`) and the new Gemini streaming TTS
  implementation (`gen_tts.py`).
- **Frontend (`src/templates`, `src/static`)** – Minimal HTML/CSS/JS client that
  uploads files, shows cleaned text, and streams the generated audio.

All intermediate and final assets are written into `/data` (uploads) and
`/outputs` (audio) at the project root.

---

## Data Flow

1. **Upload** – `/process` accepts a PDF or image, saving it under `./data`.
2. **Extraction** – `extract_text_ocr` (or `extract_text_native`) reads text.
   Preprocessing resizes, denoises, and thresholds content before handing it to
   Tesseract with Khmer (`khm`) and English language packs.
3. **Cleanup** – `utils.gemini_client.text_cleanup` asks Gemini
   (`gemini-2.5-flash`) to normalize whitespace and fix OCR artefacts while
   preserving meaning.
4. **Synthesis** – `generate_audio_from_text` streams audio chunks from the
   Gemini TTS model (`gemini-2.5-flash-preview-tts`) and writes them to
   `/outputs/<base>.wav`. The FastAPI response returns both the cleaned text and
   the first audio file path.
5. **Frontend delivery** – The browser fetches `/static/main.js`, which renders
   the cleaned text, character counts, embeds the audio player, and exposes a
   download link (cache-busted per request).

---

## Key Components

### FastAPI application (`src/app.py`)

- Mounts static assets (`/static`) and generated audio (`/outputs`).
- `POST /process`:
  - Writes incoming file to disk.
  - Calls `process_file` (extraction + cleanup).
  - Calls `generate_audio_from_text`, passing the original file name as a hint so
    outputs are named consistently.
  - Returns `{status, response, audio}` where `audio` is the relative `/outputs`
    URL of the synthesized speech.

### Document processing (`src/utils/document_process.py`)

- `download_file` helper allows processing remote files (not wired into the API
  yet).
- `process_file` validates existence, extracts text, ensures something meaningful
  was found, and delegates to Gemini for cleanup.

### Extraction service (`src/services/extractor/extractor.py`)

- `extract_text_native` uses PyMuPDF for digital PDFs.
- `extract_text_ocr` handles scanned PDFs and raster images:
  - Converts each page to 300 DPI images.
  - Applies grayscale conversion, scaling, Gaussian blur, and Otsu thresholding
    before OCR.
  - Uses custom Tesseract config (`-l khm+eng --oem 3 --psm 6`).
- `extract_text` chooses between native and OCR paths and enforces a minimum
  text length so empty documents are caught early.

### Gemini helpers (`src/utils/gemini_client.py`)

- Loads environment variables (via `python-dotenv`) and instantiates a Gemini
  client once.
- `ask_gemini` is a general prompt wrapper; `text_cleanup` is the specific
  prompt used in the pipeline.

### Text-to-speech services (`src/services/tts`)

- `tts.py` – Existing Hugging Face model (`limphanith/tts-khmer`) that writes a
  `.wav` file via `scipy.io.wavfile`. Still available if you need to switch back.
- `gen_tts.py` – Gemini streaming TTS integration:
  - Lazily instantiates `genai.Client` with `GEMINI_API_KEY`.
  - Streams audio parts, examines MIME types, and converts raw PCM chunks into
    WAV containers when required.
  - Returns a list of `/outputs/...` paths; FastAPI currently uses the first
    entry.

### Frontend (`src/templates/index.html`, `src/static`)

- Responsive HTML/CSS shell with an upload form, cleaned text display, and audio
  playback section.
- `main.js` wires up the `/process` call, handles optimistic UI state, formats
  character counts, and updates the audio source/download link with cache
  busting to avoid stale files.

---

## Repository Layout

```
src/
  app.py                 # FastAPI entrypoint
  services/
    extractor/
      extractor.py       # PDF/image preprocessing and OCR
    tts/
      tts.py             # Legacy Hugging Face TTS
      gen_tts.py         # Gemini-based TTS (current default)
  utils/
    document_process.py  # File orchestration and cleanup
    gemini_client.py     # Gemini text helper
  static/                # CSS/JS served to the web client
  templates/             # Jinja2 HTML templates
outputs/                 # Generated audio files (served statically)
data/                    # Uploaded documents (created at runtime)
requirements.txt         # Python dependencies
setup.sh                 # Convenience setup script
```

---

## Configuration & Environment

| Variable             | Description                                                       |
|----------------------|-------------------------------------------------------------------|
| `GEMINI_API_KEY`     | Required for both text cleanup and Gemini TTS.                    |
| `GEMINI_TTS_MODEL`   | Optional override (default `gemini-2.5-flash-preview-tts`).       |
| `GEMINI_TTS_VOICE`   | Optional voice name override (default `Zephyr`).                  |
| `HF_TOKEN`/`HUGGINGFACE_API_KEY` | Required only if you switch back to the HF TTS path. |

Additional system dependencies:

- **Tesseract OCR** with Khmer language pack (`khm`).
- **Poppler** utilities for `pdf2image`.

`setup.sh` creates a virtual environment and installs Python dependencies, but
you must install Tesseract/Poppler separately (see the commented Homebrew lines
for macOS hints).

---

## Running Locally

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

export GEMINI_API_KEY=...
uvicorn src.app:app --reload
```

Navigate to `http://localhost:8000/app` for the UI, or `POST /process` with a
multipart form containing a `file` field to interact programmatically.

---

## API Reference

- `GET /` – Health message.
- `GET /app` – HTML UI.
- `POST /process` – Multipart upload endpoint.
  - Request: `file` (PDF/image).
  - Response: `{"status": "success", "response": "<cleaned text>", "audio": "/outputs/<file>.wav" }`
    or an error payload with HTTP 500.

All generated audio is served statically under `/outputs`, so the returned path
is immediately playable/downloadable by the browser.

---

## Extending the Project

- Swap TTS providers by switching imports in `src/app.py` (legacy module remains
  available).
- Add more preprocessing heuristics in `extractor.py` for different document
  types.
- Extend the frontend with progress polling, history, or authentication.
- Consider persisting metadata (text, audio path) to a database if you need
  retrieval later.

This document should give you enough context to navigate, modify, and deploy the
doc-to-speech pipeline end-to-end.
