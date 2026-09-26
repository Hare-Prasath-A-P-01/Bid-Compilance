"""
Extracts raw text from uploaded bid documents.

- PDFs: text layer via pdfplumber, falls back to OCR per-page image if the
  PDF has no extractable text (i.e. it's a scanned copy).
- Images (jpg/png/etc): OCR via pytesseract.
- Plain text files: read directly.

Tesseract is an external binary. If it isn't installed on the host, OCR
gracefully degrades to an empty string rather than crashing the request.
"""
import os

import pdfplumber
from PIL import Image

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:  # pragma: no cover
    TESSERACT_AVAILABLE = False


def _ocr_image(path: str) -> str:
    if not TESSERACT_AVAILABLE:
        return ""
    try:
        return pytesseract.image_to_string(Image.open(path))
    except Exception:
        return ""


def _extract_pdf(path: str) -> tuple[str, str]:
    text_chunks = []
    used_ocr = False
    try:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                if page_text.strip():
                    text_chunks.append(page_text)
                elif TESSERACT_AVAILABLE:
                    # scanned page with no text layer -> OCR the rendered image
                    try:
                        img = page.to_image(resolution=200).original
                        text_chunks.append(pytesseract.image_to_string(img))
                        used_ocr = True
                    except Exception:
                        pass
    except Exception:
        return "", "pdf_error"
    return "\n".join(text_chunks), "pdf_ocr" if used_ocr else "pdf_text"


def _quality_score(text: str) -> float:
    if not text or not text.strip():
        return 0.0
    compact = text.strip()
    readable = sum(1 for char in compact if char.isalnum() or char.isspace())
    length_score = min(len(compact) / 500, 1.0)
    character_score = readable / len(compact)
    return round((length_score * 0.4) + (character_score * 0.6), 2)


def extract_document(path: str) -> tuple[str, str, float]:
    """Extract text plus the method and a conservative readability score."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        text, method = _extract_pdf(path)
    elif ext in (".png", ".jpg", ".jpeg", ".tiff", ".bmp"):
        method = "ocr" if TESSERACT_AVAILABLE else "ocr_unavailable"
        text = _ocr_image(path)
    elif ext in (".txt", ".md"):
        method = "plain_text"
        try:
            with open(path, "r", errors="ignore") as f:
                text = f.read()
        except Exception:
            text = ""
    else:
        method = "unsupported"
        text = ""
    return text, method, _quality_score(text)


def extract_text(path: str) -> str:
    return extract_document(path)[0]
