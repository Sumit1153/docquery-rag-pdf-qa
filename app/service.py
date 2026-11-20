"""Orchestration of ingestion and retrieval. Dependencies can be faked in tests."""
from hashlib import sha256
from pathlib import PurePosixPath
from time import perf_counter
from .config import Settings
from .pdf_processing import extract_pdf


def clean_filename(filename: str) -> str:
    filename = filename.replace("\\", "/").split("/")[-1]
    filename = "".join(c for c in filename if c.isprintable()).strip()[:180]
    if not filename or PurePosixPath(filename).suffix.lower() != ".pdf":
        raise ValueError("Filename must end with .pdf")
    return filename


class DocQuery:
    def __init__(self, settings: Settings, repository, gemini):
        self.settings = settings
        self.repository = repository
        self.gemini = gemini

    def ingest(self, filename: str, data: bytes) -> dict:
        filename = clean_filename(filename)
        if len(data) > self.settings.max_pdf_mb * 1024 * 1024:
            raise ValueError(f"PDF must be at most {self.settings.max_pdf_mb} MB.")
        digest = sha256(data).hexdigest()
        previous = self.repository.document_by_hash(digest)
        if previous:
            return previous
        page_count, chunks = extract_pdf(
            data, max_pages=self.settings.max_pages,
            chunk_chars=self.settings.chunk_chars,
            overlap_sentences=self.settings.overlap_sentences,
            max_chunks=self.settings.max_chunks,
        )
        vectors = self.gemini.embed([chunk.content for chunk in chunks], task_type="RETRIEVAL_DOCUMENT")
        return self.repository.save_document(filename, digest, page_count, chunks, vectors)

    def ask(self, question: str, document_id: str | None = None) -> dict:
        start = perf_counter()
        if document_id and self.repository.document_by_id(document_id) is None:
            raise LookupError("Selected document does not exist.")
        if not self.repository.list_documents():
            raise LookupError("Upload a PDF before asking questions.")
        vector = self.gemini.embed([question], task_type="RETRIEVAL_QUERY")[0]
        matches = self.repository.search(vector, document_id=document_id, limit=3)
        if not matches:
            return {"answer": "I could not find that information in the uploaded documents.",
                    "sources": [], "retrieval_count": 0, "latency_ms": int((perf_counter() - start) * 1000)}
        answer = self.gemini.answer(question, matches)
        sources = [
            {"ref": i, "filename": hit["filename"], "page": hit["page"],
             "similarity": max(-1, min(1, float(hit["similarity"]))),
             "snippet": hit["content"][:460], "document_id": hit["document_id"]}
            for i, hit in enumerate(matches, start=1)
        ]
        return {"answer": answer, "sources": sources, "retrieval_count": len(matches),
                "latency_ms": int((perf_counter() - start) * 1000)}
