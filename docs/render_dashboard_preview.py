"""Generate an illustrated interface preview with stubbed API data (not a live Gemini run)."""
from pathlib import Path
import json
import re
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
html = (ROOT / "static" / "index.html").read_text()
html = re.sub(r'<link rel="stylesheet"[^>]+>', '', html)
html = re.sub(r'<script src="/static/app.js" defer></script>', '', html)
css = (ROOT / "static" / "styles.css").read_text()
css = css.split("\n", 1)[1]  # Skip Google Fonts import for offline preview
script = (ROOT / "static" / "app.js").read_text()
ID = "00000000-0000-0000-0000-000000000001"
health = {"status": "ok", "database": "connected", "gemini_configured": True}
docs = [{"id": ID, "filename": "team_handbook.pdf", "page_count": 2, "chunk_count": 2, "created_at": "2026-11-21T00:00:00Z"}]
answer = {
    "answer": "Employees may work remotely three days per week. They are expected onsite for the remaining two days [1].",
    "sources": [{"ref": 1, "filename": "team_handbook.pdf", "page": 1, "similarity": 0.86,
                 "snippet": "Remote work policy: Employees may work remotely three days per week. On the remaining two days, employees work onsite with their team.", "document_id": ID}],
    "retrieval_count": 1, "latency_ms": 480,
}

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path="/usr/bin/chromium", headless=True, args=["--no-sandbox"])
    page = browser.new_page(viewport={"width": 1512, "height": 1050}, device_scale_factor=1)
    page.goto("about:blank")
    page.set_content(html)
    page.add_style_tag(content=css)
    page.evaluate("""(responses) => { window.fetch = async (url) => new Response(JSON.stringify(
        String(url).includes('/health') ? responses.health :
        String(url).includes('/ask') ? responses.answer : responses.docs
    ), {status:200,headers:{'Content-Type':'application/json'}}); }""", {"health": health, "docs": docs, "answer": answer})
    page.add_script_tag(content=script)
    page.locator("#question").fill("How many days per week can employees work remotely?")
    page.locator("#ask-button").click()
    page.locator(".source").first.wait_for(timeout=8000)
    page.screenshot(path=str(ROOT / "docs" / "dashboard.png"), full_page=True)
    browser.close()
    print("Saved preview to", ROOT / "docs" / "dashboard.png")
