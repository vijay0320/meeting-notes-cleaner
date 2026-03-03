"""
api.py — FastAPI version of the Meeting Notes Cleaner backend
Run with: uvicorn api:app --reload --port 8080
Docs at:  http://localhost:8080/docs
"""

import warnings
warnings.filterwarnings("ignore")

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import sqlite3
import tempfile
import os
import re
from datetime import datetime
import whisper

from db import get_all_meetings, get_meeting_debt, get_owner_workload, compute_health_score

# ── App setup ─────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Meeting Notes Cleaner API",
    description="Local, no-API meeting notes cleaner with priority engine, owner detection and analytics.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB = "meetings.db"

# Load Whisper once at startup
print("Loading Whisper model...")
_whisper_model = whisper.load_model("base", device="cpu")
print("Whisper ready.")

# ── Pydantic models (request/response schemas) ────────────────────────────────
class ProcessRequest(BaseModel):
    notes: str

class ItemResponse(BaseModel):
    text: str
    priority: str
    owner: str
    status: str

class ProcessResponse(BaseModel):
    points: list[ItemResponse]

class SaveRequest(BaseModel):
    title: str
    points: list[ItemResponse]

class SaveResponse(BaseModel):
    id: int

class UpdateStatusRequest(BaseModel):
    meeting_id: int
    item_index: int
    status: str

# ── Priority engine ───────────────────────────────────────────────────────────
HIGH_KEYWORDS = [
    "asap", "urgent", "critical", "blocker", "block", "must", "immediately",
    "deadline", "overdue", "risk", "high priority", "eod", "end of today",
    "escalate", "broke", "broken", "down", "failing", "at risk",
    "expires", "not started", "renew", "must fix", "before release"
]
MEDIUM_KEYWORDS = [
    "should", "need", "review", "follow up", "followup", "discuss", "plan",
    "schedule", "decide", "will", "assigned", "pending", "waiting", "requested",
    "needs", "required", "sign off", "approval", "investigate",
    "not set up", "starts monday", "set up", "slow query", "affecting", "deck not"
]
ACRONYMS = {"cto", "cfo", "ceo", "coo", "hr", "qa", "api", "ui", "ux"}

def flag_priority(text):
    t = text.lower()
    if any(k in t for k in HIGH_KEYWORDS):
        return "high"
    elif any(k in t for k in MEDIUM_KEYWORDS):
        return "medium"
    return "low"

# ── Owner detection ───────────────────────────────────────────────────────────
TEAM_TOKENS = {"team", "lead", "manager", "director", "engineer", "designer",
               "devops", "dev", "qa", "cto", "ceo", "cfo", "hr", "legal",
               "marketing", "finance", "product", "backend", "frontend", "sales"}

def format_owner(name):
    words = name.split()
    return " ".join(w.upper() if w.lower() in ACRONYMS else w.capitalize() for w in words)

def detect_owner(text):
    m = re.match(r'^([A-Za-z][a-z]+(?:\s+[A-Za-z][a-z]+)?)\s*[-:]', text)
    if m:
        candidate = m.group(1).strip()
        if candidate.lower() not in {"the", "a", "an", "key", "main", "note", "update"}:
            return format_owner(candidate)
    m = re.search(r'assigned to ([A-Za-z][a-z]+)', text, re.IGNORECASE)
    if m:
        return format_owner(m.group(1))
    m = re.search(r'\b([A-Z][a-z]{2,})\s+(will|to|should|must|needs to)', text)
    if m:
        candidate = m.group(1)
        if candidate.lower() not in TEAM_TOKENS:
            return format_owner(candidate)
    for token in ["dev team", "devops", "backend team", "frontend team", "qa team",
                  "marketing", "legal", "finance", "hr", "product team", "product manager",
                  "sales team", "cto", "cfo", "ceo"]:
        if token in text.lower():
            return format_owner(token)
    return None

# ── Note processing ───────────────────────────────────────────────────────────
def clean_item(text):
    text = re.sub(r'^[\-\*\•\d\.\)]+\s*', '', text).strip()
    text = re.sub(r'^([A-Za-z][a-z]*(?:\s+[a-z]+)?)\s*[-:]\s*',
                  lambda m: m.group(1).capitalize() + ': ', text)
    text = text[0].upper() + text[1:] if text else text
    if text and not text.endswith(('.', '!', '?')):
        text += '.'
    return text

def split_notes(raw_notes):
    lines = re.split(r'\n|\r\n', raw_notes)
    items = []
    for line in lines:
        line = line.strip()
        if not line or len(line) < 5:
            continue
        parts = re.split(r'(?<=[a-z])\.\s+|;', line)
        for part in parts:
            part = part.strip().rstrip('.')
            if len(part) > 5:
                items.append(part)
    return items

def process_notes(raw_notes):
    items = split_notes(raw_notes)
    results = []
    for item in items:
        priority = flag_priority(item)
        owner = detect_owner(item)
        cleaned = clean_item(item)
        results.append(ItemResponse(
            text=cleaned,
            priority=priority,
            owner=owner or "Unassigned",
            status="todo"
        ))
    order = {"high": 0, "medium": 1, "low": 2}
    results.sort(key=lambda x: order[x.priority])
    return results

# ── Database helpers ──────────────────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS meetings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT, created_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        meeting_id INTEGER, text TEXT, priority TEXT,
        owner TEXT, status TEXT DEFAULT 'todo',
        FOREIGN KEY (meeting_id) REFERENCES meetings(id))""")
    conn.commit()
    conn.close()

init_db()

# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse, tags=["UI"])
def index():
    with open("app_v2.py") as f:
        content = f.read()
    # Extract HTML from Flask app and serve it
    return "<h2>Use <a href='/docs'>/docs</a> for the API or run app_v2.py for the full UI.</h2>"

@app.post("/process", response_model=ProcessResponse, tags=["Notes"])
def process(req: ProcessRequest):
    """
    Clean and prioritize raw meeting notes.
    Returns items sorted by priority (high → medium → low).
    """
    if not req.notes.strip():
        raise HTTPException(status_code=400, detail="Notes cannot be empty")
    return ProcessResponse(points=process_notes(req.notes))

@app.post("/save", response_model=SaveResponse, tags=["Meetings"])
def save(req: SaveRequest):
    """Save a meeting and its action items to the database."""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("INSERT INTO meetings (title, created_at) VALUES (?, ?)",
              (req.title, datetime.now().strftime("%Y-%m-%d %H:%M")))
    meeting_id = c.lastrowid
    for p in req.points:
        c.execute("INSERT INTO items (meeting_id, text, priority, owner, status) VALUES (?,?,?,?,?)",
                  (meeting_id, p.text, p.priority, p.owner, p.status))
    conn.commit()
    conn.close()
    return SaveResponse(id=meeting_id)

@app.post("/update_status", tags=["Meetings"])
def update_status(req: UpdateStatusRequest):
    """Update the status of a specific action item."""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT id FROM items WHERE meeting_id=? ORDER BY id", (req.meeting_id,))
    ids = [r[0] for r in c.fetchall()]
    if req.item_index < len(ids):
        c.execute("UPDATE items SET status=? WHERE id=?", (req.status, ids[req.item_index]))
    conn.commit()
    conn.close()
    return {"ok": True}

@app.get("/meetings", tags=["Meetings"])
def meetings():
    """Get all saved meetings with health scores."""
    return {"meetings": get_all_meetings()}

@app.get("/meeting/{meeting_id}", tags=["Meetings"])
def meeting(meeting_id: int):
    """Get a specific meeting with its items and health score."""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT title, created_at FROM meetings WHERE id=?", (meeting_id,))
    m = c.fetchone()
    if not m:
        raise HTTPException(status_code=404, detail="Meeting not found")
    c.execute("SELECT text, priority, owner, status FROM items WHERE meeting_id=? ORDER BY id",
              (meeting_id,))
    items = [{"text": r[0], "priority": r[1], "owner": r[2], "status": r[3]}
             for r in c.fetchall()]
    conn.close()
    return {"title": m[0], "created_at": m[1], "items": items,
            "health": compute_health_score(meeting_id)}

@app.get("/debt", tags=["Analytics"])
def debt():
    """Get owners with 3+ unresolved HIGH items across meetings."""
    return {"debt": get_meeting_debt()}

@app.get("/workload", tags=["Analytics"])
def workload():
    """Get per-owner workload stats across all meetings."""
    return {"workload": get_owner_workload()}

@app.post("/transcribe", tags=["Audio"])
async def transcribe(audio: UploadFile = File(...)):
    """
    Transcribe audio using Whisper (runs locally, no API).
    Send audio as multipart/form-data with key 'audio'.
    Returns transcribed text split into one item per sentence.
    """
    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
        content = await audio.read()
        tmp.write(content)
        tmp_path = tmp.name
    result = _whisper_model.transcribe(tmp_path)
    os.unlink(tmp_path)
    raw = result["text"].strip()
    sentences = [s.strip() for s in raw.split('.') if len(s.strip()) > 5]
    return {"text": "\n".join(sentences)}

if __name__ == "__main__":
    import uvicorn
    print("Starting FastAPI at http://localhost:8080")
    print("API docs at  http://localhost:8080/docs")
    uvicorn.run("api:app", host="0.0.0.0", port=8080, reload=True)