"""PDF extraction and simple sentence-aware chunks, preserving page metadata."""
from dataclasses import dataclass
from io import BytesIO
import re
from pypdf import PdfReader


class PDFError(ValueError):
    pass


@dataclass(frozen=True)
class Chunk:
    page: int
    index: int
    content: str


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def sentences(text: str, max_chars: int) -> list[str]:
    """Split on sentence endings; split very long sentences on word boundaries."""
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'“])", normalize_text(text))
    output = []
    for part in parts:
        if not part:
            continue
        if len(part) <= max_chars:
            output.append(part)
            continue
        words = part.split()
        buf = ""
        for word in words:
            if len(word) > max_chars:
                if buf:
                    output.append(buf)
                    buf = ""
                output.extend(word[i : i + max_chars] for i in range(0, len(word), max_chars))
            elif not buf:
                buf = word
            elif len(buf) + 1 + len(word) <= max_chars:
                buf += " " + word
            else:
                output.append(buf)
                buf = word
        if buf:
            output.append(buf)
    return output


def chunk_page(text: str, page: int, max_chars: int = 950, overlap_sentences: int = 1) -> list[Chunk]:
    if max_chars < 80:
        raise ValueError("max_chars must be >= 80")
    units = sentences(text, max_chars)
    if not units:
        return []
    result: list[Chunk] = []
    start = 0
    while start < len(units):
        end = start
        size = 0
        while end < len(units):
            addition = len(units[end]) + (1 if end > start else 0)
            if end > start and size + addition > max_chars:
                break
            size += addition
            end += 1
        content = " ".join(units[start:end])
        result.append(Chunk(page=page, index=len(result), content=content))
        if end == len(units):
            break
        start = max(start + 1, end - min(overlap_sentences, end - start - 1))
    return result


def extract_pdf(data: bytes, *, max_pages: int = 30, chunk_chars: int = 950,
                overlap_sentences: int = 1, max_chunks: int = 150) -> tuple[int, list[Chunk]]:
    if not data.startswith(b"%PDF-"):
        raise PDFError("Only valid PDF files are accepted.")
    try:
        reader = PdfReader(BytesIO(data), strict=False)
        if reader.is_encrypted:
            raise PDFError("Password-protected PDFs are not supported.")
        page_count = len(reader.pages)
        if page_count == 0:
            raise PDFError("This PDF has no pages.")
        if page_count > max_pages:
            raise PDFError(f"This PDF has {page_count} pages; limit is {max_pages} pages.")
        chunks: list[Chunk] = []
        for page_num, page in enumerate(reader.pages, start=1):
            raw = page.extract_text() or ""
            chunks.extend(chunk_page(raw, page_num, max_chars=chunk_chars,
                                     overlap_sentences=overlap_sentences))
            if len(chunks) > max_chunks:
                raise PDFError(f"This document has too much text; limit is {max_chunks} chunks.")
    except PDFError:
        raise
    except Exception as exc:
        raise PDFError("The PDF could not be read. Try another text-based PDF.") from exc
    if not chunks:
        raise PDFError("No selectable text was found. Scanned PDFs need OCR, which this version does not include.")
    return page_count, chunks
