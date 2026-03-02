"""
Meeting Notes Cleaner v2
Features: owner detection, action item tracker (SQLite), priority engine, benchmark
"""

import warnings
warnings.filterwarnings("ignore")

from flask import Flask, render_template_string, request, jsonify
import re
import sqlite3
import json
from datetime import datetime

app = Flask(__name__)
DB = "meetings.db"

# ── Database setup ────────────────────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS meetings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            created_at TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meeting_id INTEGER,
            text TEXT,
            priority TEXT,
            owner TEXT,
            status TEXT DEFAULT 'todo',
            FOREIGN KEY (meeting_id) REFERENCES meetings(id)
        )
    """)
    conn.commit()
    conn.close()

init_db()

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
    """Uppercase acronyms, title-case everything else."""
    words = name.split()
    result = []
    for w in words:
        result.append(w.upper() if w.lower() in ACRONYMS else w.capitalize())
    return " ".join(result)

def detect_owner(text):
    # Pattern 1: "Name - ..." or "Name: ..."
    m = re.match(r'^([A-Za-z][a-z]+(?:\s+[A-Za-z][a-z]+)?)\s*[-:]', text)
    if m:
        candidate = m.group(1).strip()
        if candidate.lower() not in {"the", "a", "an", "key", "main", "note", "update"}:
            return format_owner(candidate)

    # Pattern 2: "assigned to Name"
    m = re.search(r'assigned to ([A-Za-z][a-z]+)', text, re.IGNORECASE)
    if m:
        return format_owner(m.group(1))

    # Pattern 3: "Name will/to/should ..."
    m = re.search(r'\b([A-Z][a-z]{2,})\s+(will|to|should|must|needs to)', text)
    if m:
        candidate = m.group(1)
        if candidate.lower() not in TEAM_TOKENS:
            return format_owner(candidate)

    # Pattern 4: team tokens e.g. "dev team", "devops", "marketing"
    for token in ["dev team", "devops", "backend team", "frontend team", "qa team",
                  "marketing", "legal", "finance", "hr", "product team", "sales team",
                  "cto", "cfo", "ceo"]:
        if token in text.lower():
            return format_owner(token)

    return None

# ── Note cleaning ─────────────────────────────────────────────────────────────
def clean_item(text):
    text = re.sub(r'^[\-\*\•\d\.\)]+\s*', '', text).strip()
    text = re.sub(r'^([A-Za-z][a-z]*(?:\s+[a-z]+)?)\s*[-:]\s*',
                  lambda m: m.group(1).capitalize() + ': ', text)
    text = text[0].upper() + text[1:] if text else text
    if text and not text.endswith(('.', '!', '?')):
        text += '.'
    return text

def split_notes(raw_notes):
    lines = raw_notes.split('\n')
    items = []
    for line in lines:
        line = line.strip()
        if not line or len(line) < 5:
            continue
        for part in re.split(r';', line):
            part = part.strip()
            if len(part) > 5:
                items.append(part)
    return items

def process_notes(raw_notes):
    items = split_notes(raw_notes)
    results = []
    for item in items:
        priority = flag_priority(item)
        owner    = detect_owner(item)
        cleaned  = clean_item(item)
        results.append({
            "text":     cleaned,
            "priority": priority,
            "owner":    owner or "Unassigned",
            "status":   "todo"
        })
    order = {"high": 0, "medium": 1, "low": 2}
    results.sort(key=lambda x: order[x["priority"]])
    return results

# ── HTML ──────────────────────────────────────────────────────────────────────
HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Meeting Notes Cleaner</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Georgia', serif; background: #0f0f0f; color: #e8e8e8; min-height: 100vh; padding: 40px 20px; }
.container { max-width: 960px; margin: 0 auto; }
h1 { font-size: 2rem; font-weight: normal; letter-spacing: -0.5px; color: #fff; margin-bottom: 4px; }
.subtitle { color: #555; font-size: 0.82rem; font-family: monospace; margin-bottom: 32px; }
.tabs { display: flex; gap: 4px; margin-bottom: 20px; }
.tab { padding: 8px 20px; border-radius: 5px; font-family: monospace; font-size: 0.8rem;
       cursor: pointer; border: 1px solid #2a2a2a; background: #1a1a1a; color: #666;
       letter-spacing: 0.5px; transition: all 0.15s; }
.tab.active { background: #e8e8e8; color: #0f0f0f; border-color: #e8e8e8; }
.panel { background: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 8px; padding: 24px; margin-bottom: 20px; }
.page { display: none; } .page.active { display: block; }
label { display: block; font-size: 0.7rem; letter-spacing: 1.5px; text-transform: uppercase;
        color: #555; margin-bottom: 8px; font-family: monospace; }
input[type=text] { width: 100%; background: #111; border: 1px solid #2a2a2a; border-radius: 6px;
  color: #e8e8e8; font-family: monospace; font-size: 0.88rem; padding: 10px 14px;
  outline: none; margin-bottom: 14px; transition: border-color 0.2s; }
input[type=text]:focus { border-color: #444; }
textarea { width: 100%; height: 190px; background: #111; border: 1px solid #2a2a2a;
  border-radius: 6px; color: #e8e8e8; font-family: monospace; font-size: 0.88rem;
  line-height: 1.7; padding: 14px; resize: vertical; outline: none; transition: border-color 0.2s; }
textarea:focus { border-color: #444; }
.btn { background: #e8e8e8; color: #0f0f0f; border: none; padding: 11px 26px;
       border-radius: 6px; font-size: 0.82rem; font-weight: bold; cursor: pointer;
       transition: background 0.15s; margin-top: 14px; margin-right: 8px; }
.btn:hover { background: #fff; }
.btn:disabled { background: #2a2a2a; color: #555; cursor: not-allowed; }
.btn-sm { padding: 5px 12px; font-size: 0.72rem; margin: 0; border-radius: 4px; }
.btn-ghost { background: transparent; border: 1px solid #333; color: #888; }
.btn-ghost:hover { background: #222; color: #e8e8e8; }
.spinner { display: none; margin-top: 14px; font-family: monospace; font-size: 0.8rem; color: #555; }
.results-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.results-title { font-size: 0.7rem; letter-spacing: 1.5px; text-transform: uppercase; color: #555; font-family: monospace; }
.counts { font-family: monospace; font-size: 0.75rem; }
.counts span { margin-left: 10px; }
.item { display: flex; align-items: flex-start; gap: 10px; padding: 13px 15px;
        border-radius: 6px; margin-bottom: 8px; border-left: 3px solid transparent; }
.item.high   { background: #1f1410; border-left-color: #c0392b; }
.item.medium { background: #15180f; border-left-color: #8a9a2a; }
.item.low    { background: #111820; border-left-color: #2a6a8a; }
.item.done   { opacity: 0.4; }
.badge { font-size: 0.6rem; font-family: monospace; font-weight: bold; letter-spacing: 1px;
         padding: 3px 7px; border-radius: 3px; white-space: nowrap; margin-top: 3px; }
.high   .badge { background: #c0392b; color: #fff; }
.medium .badge { background: #6a7a1a; color: #fff; }
.low    .badge { background: #1a5a7a; color: #fff; }
.item-body { flex: 1; }
.item-text { font-size: 0.88rem; line-height: 1.5; color: #ddd; margin-bottom: 6px; }
.item-meta { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.owner-tag { font-size: 0.7rem; font-family: monospace; color: #888;
             background: #222; padding: 2px 8px; border-radius: 3px; }
.owner-tag.assigned { color: #aaa; background: #1e2a1e; }
.status-select { font-size: 0.7rem; font-family: monospace; background: #1a1a1a;
                 color: #888; border: 1px solid #333; border-radius: 3px;
                 padding: 2px 6px; cursor: pointer; outline: none; }
.item-actions { display: flex; gap: 6px; margin-top: 4px; }
.error { color: #c0392b; font-family: monospace; font-size: 0.82rem; margin-top: 12px; }
.meeting-card { padding: 14px 16px; border: 1px solid #2a2a2a; border-radius: 6px;
                margin-bottom: 10px; cursor: pointer; transition: border-color 0.15s; }
.meeting-card:hover { border-color: #444; }
.meeting-card-title { font-size: 0.9rem; color: #ddd; margin-bottom: 4px; }
.meeting-card-meta { font-size: 0.72rem; font-family: monospace; color: #555; }
.meeting-detail { display: none; }
.save-bar { display: flex; gap: 10px; align-items: center; margin-top: 14px; flex-wrap: wrap; }
.empty { color: #444; font-family: monospace; font-size: 0.85rem; padding: 20px 0; }
</style>
</head>
<body>
<div class="container">
  <h1>Meeting Notes Cleaner</h1>
  <p class="subtitle">owner detection &mdash; priority engine &mdash; action tracker &mdash; local sqlite</p>

  <div class="tabs">
    <div class="tab active" onclick="switchTab('clean')">Clean Notes</div>
    <div class="tab" onclick="switchTab('history')">History</div>
  </div>

  <!-- ── CLEAN NOTES PAGE ── -->
  <div class="page active" id="page-clean">
    <div class="panel">
      <label>Meeting Title</label>
      <input type="text" id="title" placeholder="e.g. Sprint Planning — March 2">
      <label>Raw Notes</label>
      <textarea id="notes" placeholder="One item per line:&#10;&#10;john - finished auth module, pushing to staging today&#10;priya - blocked on API spec, needs it asap or sprint is at risk&#10;deployment pipeline broke last night, critical blocker&#10;sara - design review thursday, needs product sign off"></textarea>
      <div class="save-bar">
        <button class="btn" id="btn" onclick="processNotes()">Clean Notes &rarr;</button>
        <button class="btn btn-ghost" id="save-btn" style="display:none" onclick="saveMeeting()">Save to History</button>
      </div>
      <div class="spinner" id="spinner">processing...</div>
      <div class="error" id="error"></div>
    </div>

    <div class="panel" id="results" style="display:none">
      <div class="results-header">
        <span class="results-title">Cleaned Output</span>
        <span class="counts" id="counts"></span>
      </div>
      <div id="output"></div>
    </div>
  </div>

  <!-- ── HISTORY PAGE ── -->
  <div class="page" id="page-history">
    <div class="panel">
      <div class="results-title" style="margin-bottom:16px">Saved Meetings</div>
      <div id="meetings-list"></div>
    </div>
    <div class="panel meeting-detail" id="meeting-detail">
      <div class="results-header">
        <span class="results-title" id="detail-title"></span>
        <span class="counts" id="detail-meta"></span>
      </div>
      <div id="detail-items"></div>
    </div>
  </div>
</div>

<script>
let currentPoints = [];
let currentMeetingId = null;

function switchTab(tab) {
  document.querySelectorAll('.tab').forEach((t,i) => t.classList.toggle('active', ['clean','history'][i] === tab));
  document.querySelectorAll('.page').forEach((p,i) => p.classList.toggle('active', ['clean','history'][i] === tab));
  if (tab === 'history') loadHistory();
}

function renderItems(points, container, meetingId) {
  container.innerHTML = points.map((p, i) => `
    <div class="item ${p.priority} ${p.status === 'done' ? 'done' : ''}" id="item-${meetingId}-${i}">
      <span class="badge">${p.priority.toUpperCase()}</span>
      <div class="item-body">
        <div class="item-text">${p.text}</div>
        <div class="item-meta">
          <span class="owner-tag ${p.owner !== 'Unassigned' ? 'assigned' : ''}">
            ${p.owner !== 'Unassigned' ? '👤 ' : ''}${p.owner}
          </span>
          <select class="status-select" onchange="updateStatus(${meetingId}, ${i}, this.value, '${p.priority}')">
            <option value="todo"        ${p.status==='todo'        ?'selected':''}>○ Todo</option>
            <option value="in-progress" ${p.status==='in-progress' ?'selected':''}>◑ In Progress</option>
            <option value="done"        ${p.status==='done'        ?'selected':''}>● Done</option>
          </select>
        </div>
      </div>
    </div>
  `).join('');
}

async function processNotes() {
  const notes = document.getElementById('notes').value.trim();
  if (!notes) return;
  const btn = document.getElementById('btn');
  const spinner = document.getElementById('spinner');
  const error = document.getElementById('error');

  btn.disabled = true;
  spinner.style.display = 'block';
  error.textContent = '';
  document.getElementById('results').style.display = 'none';
  document.getElementById('save-btn').style.display = 'none';

  try {
    const res = await fetch('/process', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({notes})
    });
    const data = await res.json();
    if (data.error) throw new Error(data.error);
    currentPoints = data.points;
    currentMeetingId = null;

    const high = data.points.filter(p=>p.priority==='high').length;
    const med  = data.points.filter(p=>p.priority==='medium').length;
    const low  = data.points.filter(p=>p.priority==='low').length;
    document.getElementById('counts').innerHTML =
      `<span style="color:#c0392b">${high} high</span>` +
      `<span style="color:#8a9a2a">${med} medium</span>` +
      `<span style="color:#2a6a8a">${low} low</span>`;

    renderItems(data.points, document.getElementById('output'), 'new');
    document.getElementById('results').style.display = 'block';
    document.getElementById('save-btn').style.display = 'inline-block';
  } catch(e) {
    error.textContent = 'Error: ' + e.message;
  } finally {
    btn.disabled = false;
    spinner.style.display = 'none';
  }
}

async function saveMeeting() {
  const title = document.getElementById('title').value.trim() || 'Untitled Meeting';
  const res = await fetch('/save', {
    method: 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify({title, points: currentPoints})
  });
  const data = await res.json();
  if (data.id) {
    currentMeetingId = data.id;
    document.getElementById('save-btn').textContent = '✓ Saved';
    document.getElementById('save-btn').disabled = true;
    // Re-render with real meeting id for status tracking
    renderItems(currentPoints, document.getElementById('output'), data.id);
  }
}

async function updateStatus(meetingId, itemIndex, status, priority) {
  if (!meetingId || meetingId === 'new') return;
  await fetch('/update_status', {
    method: 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify({meeting_id: meetingId, item_index: itemIndex, status})
  });
  const el = document.getElementById(`item-${meetingId}-${itemIndex}`);
  if (el) el.classList.toggle('done', status === 'done');
}

async function loadHistory() {
  const res = await fetch('/meetings');
  const data = await res.json();
  const list = document.getElementById('meetings-list');
  if (!data.meetings.length) {
    list.innerHTML = '<div class="empty">No saved meetings yet.</div>';
    return;
  }
  list.innerHTML = data.meetings.map(m => `
    <div class="meeting-card" onclick="loadMeeting(${m.id})">
      <div class="meeting-card-title">${m.title}</div>
      <div class="meeting-card-meta">${m.created_at} &mdash; ${m.item_count} items
        &nbsp;·&nbsp; <span style="color:#c0392b">${m.high_count} high</span>
      </div>
    </div>
  `).join('');
  document.getElementById('meeting-detail').style.display = 'none';
}

async function loadMeeting(id) {
  const res = await fetch(`/meeting/${id}`);
  const data = await res.json();
  document.getElementById('detail-title').textContent = data.title;
  document.getElementById('detail-meta').textContent = data.created_at;
  renderItems(data.items, document.getElementById('detail-items'), id);
  document.getElementById('meeting-detail').style.display = 'block';
}

document.getElementById('notes').addEventListener('keydown', e => {
  if (e.key === 'Enter' && e.ctrlKey) processNotes();
});
</script>
</body>
</html>
"""

# ── Routes ────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/process", methods=["POST"])
def process():
    try:
        data = request.get_json()
        notes = data.get("notes", "").strip()
        if not notes:
            return jsonify({"error": "No notes provided"})
        return jsonify({"points": process_notes(notes)})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/save", methods=["POST"])
def save():
    try:
        data = request.get_json()
        title  = data.get("title", "Untitled")
        points = data.get("points", [])
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("INSERT INTO meetings (title, created_at) VALUES (?, ?)",
                  (title, datetime.now().strftime("%Y-%m-%d %H:%M")))
        meeting_id = c.lastrowid
        for p in points:
            c.execute("INSERT INTO items (meeting_id, text, priority, owner, status) VALUES (?,?,?,?,?)",
                      (meeting_id, p["text"], p["priority"], p["owner"], p.get("status","todo")))
        conn.commit()
        conn.close()
        return jsonify({"id": meeting_id})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/update_status", methods=["POST"])
def update_status():
    try:
        data = request.get_json()
        meeting_id = data["meeting_id"]
        item_index = data["item_index"]
        status     = data["status"]
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT id FROM items WHERE meeting_id=? ORDER BY id", (meeting_id,))
        ids = [r[0] for r in c.fetchall()]
        if item_index < len(ids):
            c.execute("UPDATE items SET status=? WHERE id=?", (status, ids[item_index]))
        conn.commit()
        conn.close()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/meetings")
def meetings():
    try:
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("""
            SELECT m.id, m.title, m.created_at,
                   COUNT(i.id) as item_count,
                   SUM(CASE WHEN i.priority='high' THEN 1 ELSE 0 END) as high_count
            FROM meetings m
            LEFT JOIN items i ON i.meeting_id = m.id
            GROUP BY m.id ORDER BY m.id DESC
        """)
        rows = c.fetchall()
        conn.close()
        return jsonify({"meetings": [
            {"id": r[0], "title": r[1], "created_at": r[2],
             "item_count": r[3], "high_count": r[4] or 0}
            for r in rows
        ]})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/meeting/<int:meeting_id>")
def meeting(meeting_id):
    try:
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT title, created_at FROM meetings WHERE id=?", (meeting_id,))
        m = c.fetchone()
        c.execute("SELECT text, priority, owner, status FROM items WHERE meeting_id=? ORDER BY id",
                  (meeting_id,))
        items = [{"text": r[0], "priority": r[1], "owner": r[2], "status": r[3]}
                 for r in c.fetchall()]
        conn.close()
        return jsonify({"title": m[0], "created_at": m[1], "items": items})
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == "__main__":
    print("Starting at http://127.0.0.1:8080")
    app.run(debug=False, port=8080, host='127.0.0.1')