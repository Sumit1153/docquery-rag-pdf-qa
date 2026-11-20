from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import pytest
from app.config import Settings

ROOT = Path(__file__).resolve().parents[1]


class FakeGemini:
    def __init__(self):
        self.calls = []

    def embed(self, texts, *, task_type):
        self.calls.append((task_type, len(texts)))
        return [[0.01] * 3072 for _ in texts]

    def answer(self, question, matches):
        return f"According to the PDF: {matches[0]['content'][:80]} [1]"


class FakeRepository:
    def __init__(self):
        self.docs = {}
        self.chunks = {}
        self.schema_calls = 0
        self.last_search = None

    def ensure_schema(self):
        self.schema_calls += 1

    def ping(self):
        self.ensure_schema()

    def list_documents(self):
        return list(self.docs.values())

    def document_by_hash(self, digest):
        return next((d for d in self.docs.values() if d["sha256"] == digest), None)

    def document_by_id(self, document_id):
        return self.docs.get(str(document_id))

    def save_document(self, filename, sha256, page_count, chunks, vectors):
        uid = uuid4()
        data = dict(id=uid, filename=filename, sha256=sha256, page_count=page_count,
                    chunk_count=len(chunks), created_at=datetime.now(timezone.utc))
        self.docs[str(uid)] = data
        self.chunks[str(uid)] = chunks
        return data

    def search(self, vector, *, document_id=None, limit=3):
        self.last_search = (document_id, limit, len(vector))
        hits = []
        for ident, chunks in self.chunks.items():
            if document_id and ident != document_id:
                continue
            for chunk in chunks:
                hits.append(dict(filename=self.docs[ident]["filename"], document_id=self.docs[ident]["id"],
                                 page=chunk.page, content=chunk.content, similarity=0.84,
                                 chunk_index=chunk.index))
        return hits[:limit]

    def delete_document(self, document_id):
        if str(document_id) not in self.docs:
            return False
        self.docs.pop(str(document_id))
        self.chunks.pop(str(document_id), None)
        return True


@pytest.fixture
def sample_pdf():
    return (ROOT / "sample_data" / "team_handbook.pdf").read_bytes()


@pytest.fixture
def fake_repo():
    return FakeRepository()


@pytest.fixture
def fake_gemini():
    return FakeGemini()


@pytest.fixture
def settings():
    return Settings(gemini_api_key="dummy-unit-test-key")
