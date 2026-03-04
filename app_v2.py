"""
Meeting Notes Cleaner v2
Full pipeline: transcript extraction → messiness detection → ML cleaning → priority classification
Model: fine-tuned flan-t5-base (sunny0320/meeting-notes-cleaner-v3)
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

print("Loading flan-t5-base from HuggingFace...")
_device = torch.device("cpu")
_tokenizer = T5Tokenizer.from_pretrained("sunny0320/meeting-notes-cleaner-v3")
_model = T5ForConditionalGeneration.from_pretrained("sunny0320/meeting-notes-cleaner-v3").to(_device)
_model.eval()
print("flan-t5-base ready.")

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
    "expires", "not started", "renew", "must fix", "before release",
    "crashed", "crash", "outage", "emergency", "hotfix"
]
MEDIUM_KEYWORDS = [
    "should", "need", "review", "follow up", "followup", "discuss", "plan",
    "schedule", "decide", "will", "assigned", "pending", "waiting", "requested",
    "needs", "required", "sign off", "approval", "investigate", "prepare",
    "not set up", "starts monday", "set up", "slow query", "affecting",
    "optimize", "streamline", "simplify", "update", "adjust", "explore", "analysis", "run another", "also run"
]

LOW_SIGNALS = ["at some point", "eventually", "fun", "nice to have", "whenever", 
               "someday", "in the future", "low priority", "not urgent", "no rush"]

def flag_priority(text):
    t = text.lower()
    if any(k in t for k in LOW_SIGNALS): return "low"
    if any(k in t for k in HIGH_KEYWORDS): return "high"
    elif any(k in t for k in MEDIUM_KEYWORDS): return "medium"
    return "low"

ACRONYMS = {"cto", "cfo", "ceo", "coo", "hr", "qa", "api", "ui", "ux", "vp", "cro", "cmo"}
TEAM_TOKENS = {"team", "lead", "manager", "director", "engineer", "designer",
               "devops", "dev", "qa", "cto", "ceo", "cfo", "hr", "legal",
               "marketing", "finance", "product", "backend", "frontend", "sales"}

def format_owner(name):
    return " ".join(w.upper() if w.lower() in ACRONYMS else w.capitalize() for w in name.split())

def detect_owner(text, speaker=None):
    if speaker and speaker.lower() not in {"unknown", "unassigned"}:
        return format_owner(speaker)
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
                  "marketing", "legal", "finance", "hr", "product team",
                  "sales team", "cto", "cfo", "ceo"]:
        if token in text.lower(): return format_owner(token)
    return None

ACTION_VERBS = [
    "will", "need to", "needs to", "must", "should", "going to", "also",
    "plan to", "committed to", "agreed to", "prepare", "review",
    "investigate", "fix", "update", "send", "complete", "submit",
    "analyze", "present", "require", "estimate", "shift", "adjust",
    "optimize", "simplify", "streamline", "explore", "support", "add"
]
DEADLINE_WORDS = [
    "week", "weeks", "days", "month", "friday", "monday", "tuesday",
    "wednesday", "thursday", "before", "by", "deadline", "schedule",
    "timeline", "next meeting", "launch"
]
SPEAKER_PATTERN = re.compile(r'^([A-Z][a-z]+):\s*(.+)$')

def is_transcript(text):
    lines = text.strip().split('\n')
    speaker_lines = sum(1 for l in lines if SPEAKER_PATTERN.match(l.strip()))
    return speaker_lines >= 3

def has_action(text):
    text_lower = text.lower()
    has_verb = any(verb in text_lower for verb in ACTION_VERBS)
    has_deadline = any(d in text_lower for d in DEADLINE_WORDS)
    is_question = text.strip().endswith('?')
    is_short = len(text.split()) < 6
    # Exclude pure context/acknowledgement sentences
    exclude_starts = ["thanks", "thank you", "yes,", "no,", "okay", "great", "sounds good",
                      "that makes sense", "that's", "this is", "i see", "i agree", "i understand",
                      "based on", "from a customer", "right now average"]
    starts_with_exclude = any(text_lower.startswith(e) for e in exclude_starts)
    return (has_verb or has_deadline) and not is_question and not is_short and not starts_with_exclude

def normalize_pronouns(text, speaker):
    text = re.sub(r"\bI'll\b", f"{speaker} will", text)
    text = re.sub(r"\bI will\b", f"{speaker} will", text)
    text = re.sub(r"\bI can\b", f"{speaker} can", text)
    text = re.sub(r"\bI'd\b", f"{speaker} would", text)
    text = re.sub(r"\bWe'll\b", "the team will", text)
    text = re.sub(r"\bwe'll\b", "the team will", text)
    text = re.sub(r"\bwe will\b", "the team will", text)
    text = re.sub(r"\bwe need\b", "the team needs", text)
    text = re.sub(r"\bwe may\b", "the team may", text)
    text = re.sub(r"\bwe can\b", "the team can", text)
    return text

def extract_from_transcript(transcript):
    lines = transcript.strip().split('\n')
    action_items = []
    seen = set()
    for line in lines:
        line = line.strip()
        m = SPEAKER_PATTERN.match(line)
        if m:
            speaker = m.group(1)
            text = m.group(2).strip()
            if has_action(text):
                normalized = normalize_pronouns(text, speaker)
                key = normalized[:50].lower()
                if key not in seen:
                    seen.add(key)
                    action_items.append((speaker, normalized))
    return action_items

SHORTHAND = {
    'asap', 'eod', 'b4', 'tmrw', 'lst', 'nite', 'wk', 'pls', 'plz',
    'w/', 'w/o', 'dept', 'mgmt', 'ur', 'thru', 'pct',
    'brken', 'rdy', 'waitng', 'intgration', 'expirng'
}

def is_messy(text):
    words = text.lower().split()
    shorthand_count = sum(1 for w in words if w in SHORTHAND)
    has_number_typo = bool(re.search(r'\d[a-z]|[a-z]\d', text))
    return shorthand_count >= 2 or has_number_typo

def post_process(text):
    text = re.sub(r'\bhas crashes\b', 'has crashed', text)
    text = re.sub(r'\bbeen review\b', 'been reviewed', text)
    # Fix missing spaces before capitalized words
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
    # Fix "complete down" -> "completely down"
    text = re.sub(r'\bcomplete down\b', 'completely down', text)
    return text

def ml_clean(text):
    prompt = f"summarize meeting notes: {text}"
    inputs = _tokenizer(prompt, return_tensors="pt", max_length=128, truncation=True).to(_device)
    with torch.no_grad():
        outputs = _model.generate(
            **inputs,
            max_new_tokens=64,
            num_beams=4,
            no_repeat_ngram_size=3,
            early_stopping=True,
            repetition_penalty=1.5
        )
    cleaned = _tokenizer.decode(outputs[0], skip_special_tokens=True).strip()
    if not cleaned or len(cleaned) < 5:
        cleaned = text
    cleaned = post_process(cleaned)
    # Fix missing spaces between words merged by ML model
    cleaned = re.sub(r'([a-z])([A-Z][a-z])', r'\1 \2', cleaned)
    cleaned = cleaned[0].upper() + cleaned[1:] if cleaned else cleaned
    if cleaned and not cleaned.endswith(('.', '!', '?')):
        cleaned += '.'
    return cleaned

def smart_clean(text):
    if is_messy(text):
        return ml_clean(text)
    else:
        text = text.strip()
        if text and not text.endswith(('.', '!', '?')):
            text += '.'
        return text

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
    results = []
    if is_transcript(raw_notes):
        extracted = extract_from_transcript(raw_notes)
        for speaker, text in extracted:
            results.append({
                "text": smart_clean(text),
                "priority": flag_priority(text),
                "owner": detect_owner(text, speaker) or "Unassigned",
                "status": "todo"
            })
    else:
        items = split_notes(raw_notes)
        for item in items:
            results.append({
                "text": smart_clean(item),
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
