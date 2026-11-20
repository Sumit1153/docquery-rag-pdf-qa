"""Environment configuration. Never commit a real .env file."""
from dataclasses import dataclass
import os
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    database_url: str = "postgresql://docquery:docquery@localhost:5432/docquery"
    gemini_api_key: str = ""
    embedding_model: str = "gemini-embedding-001"
    generation_model: str = "gemini-2.5-flash"
    embedding_dimensions: int = 3072
    max_pdf_mb: int = 10
    max_pages: int = 30
    max_chunks: int = 150
    chunk_chars: int = 950
    overlap_sentences: int = 1


@lru_cache

def get_settings() -> Settings:
    return Settings(
        database_url=os.getenv("DATABASE_URL", Settings.database_url),
        gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip(),
        embedding_model=os.getenv("EMBEDDING_MODEL", Settings.embedding_model),
        generation_model=os.getenv("GENERATION_MODEL", Settings.generation_model),
    )
