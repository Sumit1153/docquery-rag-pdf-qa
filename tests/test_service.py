from copy import deepcopy
import pytest
from app.service import DocQuery, clean_filename


def test_clean_windows_path():
    assert clean_filename(r"C:\Users\sumit\paper.PDF") == "paper.PDF"


def test_clean_posix_path():
    assert clean_filename("/tmp/myfile.pdf") == "myfile.pdf"


def test_reject_non_pdf_filename():
    with pytest.raises(ValueError, match=".pdf"):
        clean_filename("model.py")


def test_ingestion_and_duplicate(sample_pdf, fake_repo, fake_gemini, settings):
    service = DocQuery(settings, fake_repo, fake_gemini)
    first = service.ingest("handbook.pdf", sample_pdf)
    second = service.ingest("handbook.pdf", sample_pdf)
    assert first["id"] == second["id"]
    assert len(fake_repo.docs) == 1
    assert fake_gemini.calls == [("RETRIEVAL_DOCUMENT", first["chunk_count"])]


def test_correct_page_numbers_stored(sample_pdf, fake_repo, fake_gemini, settings):
    doc = DocQuery(settings, fake_repo, fake_gemini).ingest("team.pdf", sample_pdf)
    assert {c.page for c in fake_repo.chunks[str(doc["id"])]} == {1, 2}


def test_reject_size_before_embedding(fake_repo, fake_gemini, settings):
    with pytest.raises(ValueError, match="10 MB"):
        DocQuery(settings, fake_repo, fake_gemini).ingest("big.pdf", b"x" * (10 * 1024 * 1024 + 1))
    assert fake_gemini.calls == []


def test_ask_top_three(sample_pdf, fake_repo, fake_gemini, settings):
    service = DocQuery(settings, fake_repo, fake_gemini)
    doc = service.ingest("book.pdf", sample_pdf)
    result = service.ask("What about remote work?", str(doc["id"]))
    assert result["sources"][0]["page"] == 1
    assert result["sources"][0]["ref"] == 1
    assert result["retrieval_count"] == 2
    assert fake_repo.last_search == (str(doc["id"]), 3, 3072)
    assert fake_gemini.calls[-1] == ("RETRIEVAL_QUERY", 1)


def test_ask_requires_docs(fake_repo, fake_gemini, settings):
    with pytest.raises(LookupError, match="Upload a PDF"):
        DocQuery(settings, fake_repo, fake_gemini).ask("What is the answer?")


def test_ask_missing_document(fake_repo, fake_gemini, settings):
    with pytest.raises(LookupError, match="does not exist"):
        DocQuery(settings, fake_repo, fake_gemini).ask("Question", "00000000-0000-0000-0000-000000000001")


def test_delete_document(sample_pdf, fake_repo, fake_gemini, settings):
    doc = DocQuery(settings, fake_repo, fake_gemini).ingest("team.pdf", sample_pdf)
    assert fake_repo.delete_document(str(doc["id"]))
    assert fake_repo.list_documents() == []


def test_no_search_hits_is_safe(sample_pdf, fake_repo, fake_gemini, settings, monkeypatch):
    service = DocQuery(settings, fake_repo, fake_gemini)
    service.ingest("team.pdf", sample_pdf)
    monkeypatch.setattr(fake_repo, "search", lambda *args, **kwargs: [])
    result = service.ask("What about the moon?")
    assert result["sources"] == []
    assert "could not find" in result["answer"]
