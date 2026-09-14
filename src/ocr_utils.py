"""
Shared OCR helpers for scanned (image-only) council PDFs.

Renders PDF pages with pypdfium2 (pure-Python, no Poppler needed) and runs
EasyOCR word/line detection, then reconstructs rough table rows by
clustering detected text boxes on their vertical center.
"""
from pathlib import Path

import numpy as np
import pypdfium2 as pdfium


def render_page(pdf_path: Path, page_index: int, scale: int = 3):
    pdf = pdfium.PdfDocument(str(pdf_path))
    try:
        page = pdf[page_index]
        bitmap = page.render(scale=scale)
        return np.array(bitmap.to_pil().convert("RGB"))
    finally:
        pdf.close()


def page_count(pdf_path: Path) -> int:
    pdf = pdfium.PdfDocument(str(pdf_path))
    try:
        return len(pdf)
    finally:
        pdf.close()


def ocr_page(reader, image_array):
    """Returns list of (x_center, y_center, text, confidence)."""
    results = reader.readtext(image_array, detail=1, paragraph=False)
    items = []
    for bbox, text, conf in results:
        xs = [pt[0] for pt in bbox]
        ys = [pt[1] for pt in bbox]
        items.append((sum(xs) / 4, sum(ys) / 4, text.strip(), conf))
    return items


def reconstruct_rows(items, y_tolerance: float = 14.0):
    """Cluster OCR word boxes into rows by y-center, then order each row left-to-right."""
    items = sorted(items, key=lambda t: t[1])
    rows = []
    current = []
    current_y = None
    for x, y, text, conf in items:
        if not text:
            continue
        if current_y is None or abs(y - current_y) <= y_tolerance:
            current.append((x, y, text, conf))
            current_y = y if current_y is None else (current_y * len(current) + y) / (len(current) + 1)
        else:
            rows.append(sorted(current, key=lambda t: t[0]))
            current = [(x, y, text, conf)]
            current_y = y
    if current:
        rows.append(sorted(current, key=lambda t: t[0]))
    return [
        {
            "row_text": " ".join(t[2] for t in row),
            "min_confidence": round(min(t[3] for t in row), 3),
            "words": row,
        }
        for row in rows
    ]


def ocr_document_rows(reader, pdf_path: Path, max_pages: int | None = None):
    """Yields (page_index, row_dict) for every reconstructed row in a scanned PDF."""
    n_pages = page_count(pdf_path)
    if max_pages:
        n_pages = min(n_pages, max_pages)
    for page_index in range(n_pages):
        img = render_page(pdf_path, page_index)
        items = ocr_page(reader, img)
        for row in reconstruct_rows(items):
            yield page_index, row
