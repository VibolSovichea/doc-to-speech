import os
from typing import cast

import cv2
import fitz
import numpy as np
import pytesseract
from pdf2image import convert_from_path
from PIL import Image


def preprocess(img):
    img = cv2.cvtColor(np.array(img), cv2.COLOR_BGR2GRAY)
    img = cv2.resize(img, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)
    img = cv2.GaussianBlur(img, (3, 3), 0)
    _, img = cv2.threshold(img, 0, 255, cv2.THRESH_OTSU)
    return img


def extract_text_native(pdf_path: str) -> str:
    text = ""
    try:
        with fitz.open(pdf_path) as doc:
            for page in doc:
                text += cast(str, page.get_text())
    except Exception as e:
        print(f"Error reading pdf: {e}")
    return text.strip()


def extract_text_ocr(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    text = ""

    try:
        if ext == ".pdf":
            images = convert_from_path(path, dpi=300)
            for img in images:
                processed = preprocess(img)
                text += pytesseract.image_to_string(processed, lang="khm") + "\n"

        elif ext in [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"]:
            img = Image.open(path)
            processed = preprocess(img)
            text = pytesseract.image_to_string(processed, lang="khm")

        else:
            raise ValueError(f"Unsupported file type: {ext}")

    except Exception as e:
        print(f"Error occurred while extracting text: {e}")

    return text.strip()


def extract_text(pdf_path: str) -> str:
    text = extract_text_native(pdf_path)
    if not text or len(text.strip()) < 100:
        text = extract_text_ocr(pdf_path)

    if not text:
        raise ValueError("Faild to extract text from pdf")

    return text
