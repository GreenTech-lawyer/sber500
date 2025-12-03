import io
import os

from PIL import Image
import pytesseract
from pdf2image import convert_from_bytes
from PyPDF2 import PdfReader


pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

IMG_OCR_LANG = os.getenv("IMG_OCR_LANG", 'rus')

def ocr_from_image_bytes(img_bytes: bytes) -> str:
    """Запускает OCR на байты изображения и возвращает распознанный тест"""
    img = Image.open(io.BytesIO(img_bytes)).convert('RGB')
    return pytesseract.image_to_string(img)


def ocr_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """Извлекает текст напрямую из PDF"""
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        full = []
        for p in reader.pages:
            try:
                txt = p.extract_text()
            except Exception:
                txt = None
            if txt:
                full.append(txt)
        if ''.join(full).strip():
            return '\n'.join(full)
    except Exception:
        pass


    pages = convert_from_bytes(pdf_bytes, dpi=200)
    texts = []
    for page in pages:
        texts.append(pytesseract.image_to_string(page, lang=IMG_OCR_LANG))
    return '\n'.join(texts)
