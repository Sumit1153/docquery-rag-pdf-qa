from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from app.config import get_settings
from app.main import app, get_gemini
from app.repository import get_repository
from app.service import DocQuery


@pytest.fixture
def client(fake_repo, fake_gemini, settings, monkeypatch):
    app.dependency_overrides[get_repository] = lambda: fake_repo
    app.dependency_overrides[get_settings] = lambda: settings
    monkeypatch.setattr("app.main.get_gemini", lambda: fake_gemini)
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_home_served(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "DocQuery" in r.text


def test_health(client):
    r = client.get("/api/health").json()
    assert r == {"status": "ok", "database": "connected", "gemini_configured": True}


def test_start_empty(client):
    assert client.get("/api/documents").json() == []


def test_upload_valid_pdf(client, sample_pdf):
    r = client.post("/api/documents", files={"file": ("handbook.pdf", sample_pdf, "application/pdf")})
    assert r.status_code == 201
    data = r.json()
    assert data["page_count"] == 2
    assert data["chunk_count"] >= 2
    assert len(client.get("/api/documents").json()) == 1


def test_upload_corrupt_pdf(client):
    r = client.post("/api/documents", files={"file": ("bad.pdf", b"not pdf", "application/pdf")})
    assert r.status_code == 422


def test_upload_bad_extension(client, sample_pdf):
    r = client.post("/api/documents", files={"file": ("a.exe", sample_pdf, "application/pdf")})
    assert r.status_code == 422


def test_upload_exceeds_size(client):
    r = client.post("/api/documents", files={"file": ("big.pdf", b"x" * (10 * 1024 * 1024 + 1), "application/pdf")})
    assert r.status_code == 413


def test_api_question(client, sample_pdf):
    doc = client.post("/api/documents", files={"file": ("handbook.pdf", sample_pdf, "application/pdf")}).json()
    r = client.post("/api/ask", json={"question": "How often can employees work remotely?", "document_id": doc["id"]})
    assert r.status_code == 200
    answer = r.json()
    assert answer["sources"][0]["page"] == 1
    assert answer["retrieval_count"] >= 1


def test_api_rejects_short_question(client):
    r = client.post("/api/ask", json={"question": "?"})
    assert r.status_code == 422


def test_api_rejects_invalid_document_id(client):
    r = client.post("/api/ask", json={"question": "What is this?", "document_id": "abc"})
    assert r.status_code == 422


def test_delete_document_endpoint(client, sample_pdf):
    doc = client.post("/api/documents", files={"file": ("handbook.pdf", sample_pdf, "application/pdf")}).json()
    assert client.delete(f"/api/documents/{doc['id']}").status_code == 200
    assert client.delete(f"/api/documents/{doc['id']}").status_code == 404


def test_missing_document_endpoint(client):
    assert client.delete(f"/api/documents/{uuid4()}").status_code == 404
