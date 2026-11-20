"""Postgres + pgvector storage. Vectors are full precision and exactly searched."""
from functools import lru_cache
from .config import get_settings


SCHEMA = """
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename TEXT NOT NULL,
    sha256 TEXT NOT NULL UNIQUE,
    page_count INTEGER NOT NULL,
    chunk_count INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS chunks (
    id BIGSERIAL PRIMARY KEY,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    page_number INTEGER NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(3072) NOT NULL,
    UNIQUE(document_id, page_number, chunk_index)
);
CREATE INDEX IF NOT EXISTS chunks_document_idx ON chunks(document_id);
"""


def as_vector(values: list[float]) -> str:
    if len(values) != 3072:
        raise ValueError("Embedding must contain 3072 floats")
    import math
    if any(not math.isfinite(value) for value in values):
        raise ValueError("Embedding contains non-finite values")
    return "[" + ",".join(str(float(value)) for value in values) + "]"


class Repository:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self._ready = False

    def _connect(self):
        import psycopg
        return psycopg.connect(self.database_url, connect_timeout=4)

    def ensure_schema(self):
        if self._ready:
            return
        with self._connect() as conn:
            conn.execute(SCHEMA)
        self._ready = True

    def ping(self) -> None:
        """Verify an actual connection, even if schema was created earlier."""
        self.ensure_schema()
        with self._connect() as conn:
            conn.execute("SELECT 1")

    def list_documents(self) -> list[dict]:
        from psycopg.rows import dict_row
        self.ensure_schema()
        with self._connect() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT * FROM documents ORDER BY created_at DESC, filename")
            return list(cur.fetchall())

    def document_by_hash(self, sha256: str) -> dict | None:
        from psycopg.rows import dict_row
        self.ensure_schema()
        with self._connect() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT * FROM documents WHERE sha256 = %s", (sha256,))
            return cur.fetchone()

    def document_by_id(self, document_id: str) -> dict | None:
        from psycopg.rows import dict_row
        self.ensure_schema()
        with self._connect() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT * FROM documents WHERE id = %s::uuid", (document_id,))
            return cur.fetchone()

    def save_document(self, filename: str, sha256: str, page_count: int, chunks, vectors: list[list[float]]) -> dict:
        from psycopg.rows import dict_row
        if len(chunks) != len(vectors):
            raise ValueError("Embedding count does not match chunk count")
        self.ensure_schema()
        with self._connect() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "INSERT INTO documents (filename, sha256, page_count, chunk_count) "
                "VALUES (%s, %s, %s, %s) ON CONFLICT (sha256) DO NOTHING RETURNING *",
                (filename, sha256, page_count, len(chunks)),
            )
            doc = cur.fetchone()
            if doc is None:
                cur.execute("SELECT * FROM documents WHERE sha256 = %s", (sha256,))
                return cur.fetchone()
            for chunk, vector in zip(chunks, vectors):
                cur.execute(
                    "INSERT INTO chunks (document_id, page_number, chunk_index, content, embedding) "
                    "VALUES (%s, %s, %s, %s, %s::vector)",
                    (doc["id"], chunk.page, chunk.index, chunk.content, as_vector(vector)),
                )
            return doc

    def search(self, vector: list[float], *, document_id: str | None = None, limit: int = 3) -> list[dict]:
        from psycopg.rows import dict_row
        self.ensure_schema()
        v = as_vector(vector)
        with self._connect() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT c.document_id, d.filename, c.page_number AS page, "
                "c.chunk_index, c.content, "
                "1 - (c.embedding <=> %s::vector) AS similarity "
                "FROM chunks c JOIN documents d ON c.document_id = d.id "
                "WHERE (%s::uuid IS NULL OR c.document_id = %s::uuid) "
                "ORDER BY c.embedding <=> %s::vector LIMIT %s",
                (v, document_id, document_id, v, limit),
            )
            return list(cur.fetchall())

    def delete_document(self, document_id: str) -> bool:
        self.ensure_schema()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM documents WHERE id = %s::uuid", (document_id,))
                return cur.rowcount > 0


@lru_cache

def get_repository() -> Repository:
    return Repository(get_settings().database_url)
