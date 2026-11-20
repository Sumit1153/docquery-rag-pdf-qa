"""FastAPI application for PDF Q&A; local MVP (no authentication)."""
from functools import lru_cache
from pathlib import Path
from uuid import UUID
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from .config import get_settings, Settings
from .gemini_client import GeminiError, GeminiService
from .pdf_processing import PDFError
from .repository import Repository, get_repository
from .schemas import AskRequest, AskResponse, DocumentOut, HealthOut
from .service import DocQuery

ROOT = Path(__file__).resolve().parent.parent
app = FastAPI(title="DocQuery — RAG PDF Q&A", version="1.0.0", description="Upload PDFs and ask cited questions using Gemini and PostgreSQL/pgvector.")
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


@lru_cache

def get_gemini() -> GeminiService:
    return GeminiService(get_settings())


def get_service(repo: Repository = Depends(get_repository), settings: Settings = Depends(get_settings)) -> DocQuery:
    return DocQuery(settings, repo, get_gemini())


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(ROOT / "static" / "index.html")


@app.get("/api/health", response_model=HealthOut)
def health(repo: Repository = Depends(get_repository), settings: Settings = Depends(get_settings)):
    try:
        repo.ping()
        database = "connected"
    except Exception:
        database = "unavailable"
    return {"status": "ok" if database == "connected" and settings.gemini_api_key else "setup_required",
            "database": database, "gemini_configured": bool(settings.gemini_api_key)}


@app.get("/api/documents", response_model=list[DocumentOut])
def documents(repo: Repository = Depends(get_repository)):
    try:
        return repo.list_documents()
    except Exception as exc:
        raise HTTPException(503, "Database unavailable. Start PostgreSQL using Docker Compose.") from exc


@app.post("/api/documents", response_model=DocumentOut, status_code=201)
async def upload_document(file: UploadFile = File(...), repo: Repository = Depends(get_repository),
                          settings: Settings = Depends(get_settings)):
    data = await file.read(settings.max_pdf_mb * 1024 * 1024 + 1)
    await file.close()
    if len(data) > settings.max_pdf_mb * 1024 * 1024:
        raise HTTPException(413, f"PDF must be at most {settings.max_pdf_mb} MB.")
    try:
        service = DocQuery(settings, repo, get_gemini())
        return service.ingest(file.filename or "", data)
    except (ValueError, PDFError) as exc:
        raise HTTPException(422, str(exc)) from exc
    except GeminiError as exc:
        raise HTTPException(502, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(503, "Upload failed. Check database availability and server logs.") from exc


@app.delete("/api/documents/{document_id}")
def delete_document(document_id: UUID, repo: Repository = Depends(get_repository)):
    try:
        if not repo.delete_document(str(document_id)):
            raise HTTPException(404, "Document not found")
        return {"deleted": str(document_id)}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(503, "Database unavailable.") from exc


@app.post("/api/ask", response_model=AskResponse)
def ask(body: AskRequest, repo: Repository = Depends(get_repository), settings: Settings = Depends(get_settings)):
    try:
        return DocQuery(settings, repo, get_gemini()).ask(body.question, str(body.document_id) if body.document_id else None)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except GeminiError as exc:
        raise HTTPException(502, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(503, "Question failed. Check database availability and server logs.") from exc
