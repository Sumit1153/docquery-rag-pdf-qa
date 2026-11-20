# Verification checklist

## Tested without cloud services

Run `python -m pytest -q`. Offline tests check PDF extraction, page numbers, sentence chunking and overlap, malformed PDFs, size/page caps, duplicate detection, fake Gemini retrieval, scoped search, API validation, and error handling.

## Live verification (requires your own API key and Docker)

1. `Copy-Item .env.example .env`; put a real `GEMINI_API_KEY` in `.env`.
2. `docker compose up --build` and open http://127.0.0.1:8000.
3. Check `/api/health` for `database: connected` and `gemini_configured: true`.
4. Upload `sample_data/team_handbook.pdf`.
5. Ask "How many days per week can employees work remotely?". Expect an answer mentioning **three days**, with **page 1** listed as a source.
6. Ask "When must travel reimbursements be submitted?". Expect **30 days**, with **page 2** as a source.
7. Ask an unrelated question. The application should decline if the excerpts do not support an answer, although LLM behavior may vary.
8. Refresh the page to verify persisted document list. Delete the document; ensure it disappears.
9. Inspect API docs at http://127.0.0.1:8000/docs.
10. Check the repository Actions tab for the offline test workflow after pushing.

**Evidence policy:** A passing offline test suite does not prove that Gemini calls or PostgreSQL work in your environment. Live steps above must be performed before claiming end-to-end cloud integration has been validated.
