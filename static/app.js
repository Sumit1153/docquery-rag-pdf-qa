"use strict";
const $ = id => document.getElementById(id);
const state = { documents: [] };

async function request(path, options = {}) {
  let response;
  try { response = await fetch(path, options); }
  catch { throw new Error("Could not reach DocQuery. Is the FastAPI server running?"); }
  let body = {};
  try { body = await response.json(); } catch { /* server/network failure */ }
  if (!response.ok) {
    const detail = body.detail;
    throw new Error(typeof detail === "string" ? detail : `Request failed (${response.status})`);
  }
  return body;
}

function showStatus(message, error = false) {
  const el = $("upload-status");
  el.textContent = message;
  el.classList.toggle("error", error);
}

function showResult(title, message, error = false) {
  const root = $("result");
  root.replaceChildren();
  root.className = error ? "result error" : "result";
  const heading = document.createElement("h3");
  heading.textContent = title;
  const body = document.createElement("div");
  body.className = "answer-body";
  body.textContent = message;
  root.append(heading, body);
  return root;
}

async function refreshHealth() {
  try {
    const health = await request("/api/health");
    const online = health.database === "connected" && health.gemini_configured;
    $("status-icon").classList.toggle("online", online);
    $("status-title").textContent = online ? "System ready" : "Setup required";
    $("status-subtitle").textContent = !health.gemini_configured ? "Add GEMINI_API_KEY in .env" :
      health.database !== "connected" ? "Start PostgreSQL database" : "Gemini + database connected";
  } catch {
    $("status-title").textContent = "Server unavailable";
    $("status-subtitle").textContent = "Restart the API server";
  }
}

function renderDocuments() {
  $("document-count").textContent = state.documents.length;
  const list = $("document-list");
  const select = $("document-select");
  const selected = select.value;
  list.replaceChildren();
  select.replaceChildren(new Option("All uploaded documents", ""));
  if (!state.documents.length) {
    const p = document.createElement("p");
    p.className = "sidebar-empty";
    p.textContent = "Uploaded files will appear here.";
    list.append(p);
  }
  for (const doc of state.documents) {
    select.append(new Option(`${doc.filename} (${doc.page_count} pages)`, doc.id));
    const row = document.createElement("div"); row.className = "doc-row";
    const icon = document.createElement("span"); icon.className = "doc-glyph"; icon.textContent = "▤";
    const content = document.createElement("div"); content.className = "doc-content";
    const name = document.createElement("span"); name.className = "doc-name"; name.title = doc.filename; name.textContent = doc.filename;
    const meta = document.createElement("span"); meta.className = "doc-meta"; meta.textContent = `${doc.page_count} pages · ${doc.chunk_count} chunks`;
    const del = document.createElement("button"); del.className = "doc-delete"; del.title = "Delete document"; del.textContent = "×";
    del.addEventListener("click", async () => {
      if (!confirm(`Delete ${doc.filename} and its saved chunks?`)) return;
      try { await request(`/api/documents/${doc.id}`, { method: "DELETE" }); await refreshDocuments(); }
      catch (error) { showResult("Delete failed", error.message, true); }
    });
    content.append(name, meta); row.append(icon, content, del); list.append(row);
  }
  if (state.documents.some(d => d.id === selected)) select.value = selected;
}

async function refreshDocuments() {
  try { state.documents = await request("/api/documents"); renderDocuments(); }
  catch (error) { showStatus(error.message, true); }
}

async function upload(file) {
  if (!file) return;
  if (!file.name.toLowerCase().endsWith(".pdf")) return showStatus("Choose a .pdf file.", true);
  if (file.size > 10 * 1024 * 1024) return showStatus("PDF must be 10 MB or smaller.", true);
  showStatus("Extracting, embedding & saving... This can take time.");
  const form = new FormData(); form.append("file", file);
  try {
    const doc = await request("/api/documents", { method: "POST", body: form });
    showStatus(`Added ${doc.filename} · ${doc.chunk_count} chunks`);
    await refreshDocuments();
    $("document-select").value = doc.id;
  } catch (error) { showStatus(error.message, true); }
  finally { $("file-input").value = ""; }
}

async function ask() {
  const question = $("question").value.trim();
  if (question.length < 3) return showResult("Please enter a question", "Your question must contain at least 3 characters.", true);
  const button = $("ask-button"); button.disabled = true; button.firstChild.textContent = "Searching... ";
  try {
    const result = await request("/api/ask", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, document_id: $("document-select").value || null }) });
    const root = showResult("Answer from your documents", result.answer);
    const meta = document.createElement("p"); meta.className = "meta";
    meta.textContent = `${result.retrieval_count} matching passage(s) · ${result.latency_ms} ms`;
    root.append(meta);
    if (result.sources.length) {
      const grid = document.createElement("div"); grid.className = "source-grid";
      for (const src of result.sources) {
        const card = document.createElement("div"); card.className = "source";
        const name = document.createElement("strong"); name.textContent = `[${src.ref}] ${src.filename} · page ${src.page}`;
        const snippet = document.createElement("p"); snippet.textContent = src.snippet;
        const score = document.createElement("small"); score.textContent = `Cosine similarity ${src.similarity.toFixed(3)}`;
        card.append(name, snippet, score); grid.append(card);
      }
      root.append(grid);
    }
    root.scrollIntoView({ behavior: "smooth", block: "nearest" });
  } catch (error) { showResult("Could not answer", error.message, true); }
  finally { button.disabled = false; button.firstChild.textContent = "Ask DocQuery "; }
}

$("browse").addEventListener("click", () => $("file-input").click());
$("file-input").addEventListener("change", event => upload(event.target.files[0]));
$("refresh-docs").addEventListener("click", refreshDocuments);
$("ask-button").addEventListener("click", ask);
$("question").addEventListener("keydown", event => { if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) ask(); });
for (const suggestion of document.querySelectorAll(".suggestion")) {
  suggestion.addEventListener("click", () => { $("question").value = suggestion.textContent; $("question").focus(); });
}
const dropzone = $("dropzone");
dropzone.addEventListener("dragover", event => { event.preventDefault(); dropzone.classList.add("dragover"); });
dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));
dropzone.addEventListener("drop", event => { event.preventDefault(); dropzone.classList.remove("dragover"); upload(event.dataTransfer.files[0]); });
refreshHealth(); refreshDocuments();
