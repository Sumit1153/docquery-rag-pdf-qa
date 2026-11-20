import pytest
from app.pdf_processing import PDFError, chunk_page, extract_pdf, normalize_text, sentences


def test_normalize_whitespace():
    assert normalize_text("  Hello \n world \t again ") == "Hello world again"


def test_extract_two_page_pdf(sample_pdf):
    pages, chunks = extract_pdf(sample_pdf)
    assert pages == 2
    assert [c.page for c in chunks] == [1, 2]
    assert "three days per week" in chunks[0].content
    assert "30 days" in chunks[1].content


def test_page_reference_starts_one(sample_pdf):
    _, chunks = extract_pdf(sample_pdf)
    assert chunks[0].page == 1


def test_reject_garbage():
    with pytest.raises(PDFError, match="valid PDF"):
        extract_pdf(b"definitely not a PDF")


def test_reject_truncated_pdf():
    with pytest.raises(PDFError, match="could not be read"):
        extract_pdf(b"%PDF-not-real")


def test_reject_too_many_pages(sample_pdf):
    with pytest.raises(PDFError, match="limit is 1"):
        extract_pdf(sample_pdf, max_pages=1)


def test_reject_too_many_chunks(sample_pdf):
    with pytest.raises(PDFError, match="too much text"):
        extract_pdf(sample_pdf, max_chunks=1)


def test_large_sentences_are_split():
    parts = sentences("A" * 1100, 300)
    assert len(parts) == 4
    assert all(len(p) <= 300 for p in parts)


def test_sentence_aware_chunks():
    chunks = chunk_page("Alpha sentence. Beta sentence. Gamma sentence.", page=3, max_chars=80)
    assert len(chunks) == 1
    assert chunks[0].page == 3


def test_chunk_overlaps_sentences():
    text = "First sentence is here with extra words. Second sentence has a story. Third sentence is here with extra words. Fourth sentence ends."
    result = chunk_page(text, page=7, max_chars=80, overlap_sentences=1)
    assert len(result) >= 2
    assert "Second sentence has a story." in result[0].content
    assert "Second sentence has a story." in result[1].content
    assert [c.index for c in result] == list(range(len(result)))


def test_no_cross_page_chunks(sample_pdf):
    _, chunks = extract_pdf(sample_pdf, chunk_chars=100)
    assert all(c.page in (1, 2) for c in chunks)
    assert all("Travel reimbursement" not in c.content for c in chunks if c.page == 1)


def test_empty_page_no_chunk():
    assert chunk_page("\n  ", page=5) == []


def test_invalid_max_chars():
    with pytest.raises(ValueError):
        chunk_page("hello", page=1, max_chars=20)
