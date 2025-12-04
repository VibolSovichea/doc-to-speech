import os
import sys
import tempfile

import requests

from services.extractor.extractor import extract_text_ocr
from utils.gemini_client import text_cleanup


def download_file(url: str) -> str:
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Failed to download file from {url}")
    temp_dir = tempfile.gettempdir()
    file_name = url.split("/")[-1]
    file_path = os.path.join(temp_dir, file_name)

    with open(file_path, "wb") as f:
        f.write(response.content)

    return file_path


def process_file(file: str):
    if not os.path.exists(file):
        raise FileNotFoundError(f"File not found: {file}")

    text = extract_text_ocr(file)
    if not text:
        raise ValueError("No text extracted from the file")
        return
    cleanup = text_cleanup(text)

    # print("Extracted text:", text)
    return cleanup
