"""
Meeting Notes Cleaner v2
Features: flan-t5-small ML cleaning, owner detection, action item tracker (SQLite), priority engine, meeting health score
"""

import warnings
warnings.filterwarnings("ignore")

from flask import Flask, request, jsonify, send_from_directory
import re
import sqlite3
from datetime import datetime
from db import get_all_meetings, get_meeting_debt
import whisper
import tempfile
import os
import torch
from transformers import T5ForConditionalGeneration, T5Tokenizer

print("Loading Whisper model...")
_whisper_model = whisper.load_model("base", device="cpu")
print("Whisper ready.")

print("Loading flan-t5 model from HuggingFace...")
_device = torch.device("cpu")
_tokenizer = T5Tokenizer.from_pretrained("sunny0320/meeting-notes-cleaner-v2")
_model = T5ForConditionalGeneration.from_pretrained("sunny0320/meeting-notes-cleaner-v2").to(_device)
_model.eval()
print("flan-t5 ready.")

app = Flask(__name__, static_folder="static")
DB = "meetings.db"

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS meetings (
        id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, created_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY AUTOINCREMENT, meeting_id INTEGER,
        text TEXT, priority TEXT, owner TEXT, status TEXT DEFAULT 'todo',
        FOREIGN KEY (meeting_id) REFERENCES meetings(id))""")
    conn.commit()
    conn.close()

init_db()

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
    if any(k in t for k in HIGH_KEYWORDS): return "high"
    elif any(k in t for k in MEDIUM_KEYWORDS): return "medium"
    return "low"

TEAM_TOKENS = {"team", "lead", "manager", "director", "engineer", "designer",
               "devops", "dev", "qa", "cto", "ceo", "cfo", "hr", "legal",
               "marketing", "finance", "product", "backend", "frontend", "sales"}

def format_owner(name):
    return " ".join(w.upper() if w.lower() in ACRONYMS else w.capitalize() for w in name.split())

def detect_owner(text):
    m = re.match(r'^([A-Za-z][a-z]+(?:\s+[A-Za-z][a-z]+)?)\s*[-:]', text)
    if m:
        candidate = m.group(1).strip()
        if candidate.lower() not in {"the", "a", "an", "key", "main", "note", "update"}:
            return format_owner(candidate)
    m = re.search(r'assigned to ([A-Za-z][a-z]+)', text, re.IGNORECASE)
    if m: return format_owner(m.group(1))
    m = re.search(r'\b([A-Z][a-z]{2,})\s+(will|to|should|must|needs to)', text)
    if m:
        candidate = m.group(1)
        if candidate.lower() not in TEAM_TOKENS: return format_owner(candidate)
    for token in ["dev team", "devops", "backend team", "frontend team", "qa team",
                  "marketing", "legal", "finance", "hr", "product team", "product manager",
                  "sales team", "cto", "cfo", "ceo"]:
        if token in text.lower(): return format_owner(token)
    return None

def ml_clean(text):
    """Use flan-t5 to clean and rewrite a raw meeting note."""
    prompt = f"Rewrite as a professional action item, fix typos, remove filler words: {text}"
    inputs = _tokenizer(prompt, return_tensors="pt", max_length=128, truncation=True).to(_device)
    with torch.no_grad():
        outputs = _model.generate(**inputs, max_new_tokens=64)
    cleaned = _tokenizer.decode(outputs[0], skip_special_tokens=True).strip()
    # Fallback to basic clean if model returns empty or too short
    if not cleaned or len(cleaned) < 5:
        cleaned = text
    cleaned = cleaned[0].upper() + cleaned[1:] if cleaned else cleaned
    if cleaned and not cleaned.endswith(('.', '!', '?')):
        cleaned += '.'
    return cleaned

def split_notes(raw_notes):
    lines = re.split(r'\n|\r\n', raw_notes)
    items = []
    for line in lines:
        line = line.strip()
        if not line or len(line) < 5: continue
        parts = re.split(r'(?<=[a-z])\.\s+|;', line)
        for part in parts:
            part = part.strip().rstrip('.')
            if len(part) > 5: items.append(part)
    return items

def process_notes(raw_notes):
    items = split_notes(raw_notes)
    results = []
    for item in items:
        results.append({
            "text": ml_clean(item),
            "priority": flag_priority(item),
            "owner": detect_owner(item) or "Unassigned",
            "status": "todo"
        })
    order = {"high": 0, "medium": 1, "low": 2}
    results.sort(key=lambda x: order[x["priority"]])
    return results

@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/process", methods=["POST"])
def process():
    try:
        data = request.get_json()
        notes = data.get("notes", "").strip()
        if not notes: return jsonify({"error": "No notes provided"})
        return jsonify({"points": process_notes(notes)})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/save", methods=["POST"])
def save():
    try:
        data = request.get_json()
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("INSERT INTO meetings (title, created_at) VALUES (?, ?)",
                  (data.get("title", "Untitled"), datetime.now().strftime("%Y-%m-%d %H:%M")))
        meeting_id = c.lastrowid
        for p in data.get("points", []):
            c.execute("INSERT INTO items (meeting_id, text, priority, owner, status) VALUES (?,?,?,?,?)",
                      (meeting_id, p["text"], p["priority"], p["owner"], p.get("status", "todo")))
        conn.commit()
        conn.close()
        return jsonify({"id": meeting_id})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/update_status", methods=["POST"])
def update_status():
    try:
        data = request.get_json()
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT id FROM items WHERE meeting_id=? ORDER BY id", (data["meeting_id"],))
        ids = [r[0] for r in c.fetchall()]
        if data["item_index"] < len(ids):
            c.execute("UPDATE items SET status=? WHERE id=?", (data["status"], ids[data["item_index"]]))
        conn.commit()
        conn.close()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/meetings")
def meetings():
    try: return jsonify({"meetings": get_all_meetings()})
    except Exception as e: return jsonify({"error": str(e)})

@app.route("/meeting/<int:meeting_id>")
def meeting(meeting_id):
    try:
        from db import compute_health_score
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT title, created_at FROM meetings WHERE id=?", (meeting_id,))
        m = c.fetchone()
        c.execute("SELECT text, priority, owner, status FROM items WHERE meeting_id=? ORDER BY id", (meeting_id,))
        items = [{"text": r[0], "priority": r[1], "owner": r[2], "status": r[3]} for r in c.fetchall()]
        conn.close()
        return jsonify({"title": m[0], "created_at": m[1], "items": items, "health": compute_health_score(meeting_id)})
    except Exception as e: return jsonify({"error": str(e)})

@app.route("/workload")
def workload():
    try:
        from db import get_owner_workload
        return jsonify({"workload": get_owner_workload()})
    except Exception as e: return jsonify({"error": str(e)})

@app.route("/debt")
def debt():
    try: return jsonify({"debt": get_meeting_debt()})
    except Exception as e: return jsonify({"error": str(e)})

@app.route("/transcribe", methods=["POST"])
def transcribe():
    try:
        audio_file = request.files.get("audio")
        if not audio_file: return jsonify({"error": "No audio file received"})
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
            audio_file.save(tmp.name)
            tmp_path = tmp.name
        result = _whisper_model.transcribe(tmp_path)
        os.unlink(tmp_path)
        raw = result["text"].strip()
        sentences = [s.strip() for s in raw.split('.') if len(s.strip()) > 5]
        return jsonify({"text": "\n".join(sentences)})
    except Exception as e: return jsonify({"error": str(e)})

if __name__ == "__main__":
    print("Starting at http://localhost:8080")
    app.run(debug=False, port=8080, host='0.0.0.0')
