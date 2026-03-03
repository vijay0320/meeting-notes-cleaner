"""
meetingmind/main.py — FastAPI backend for MeetingMind
Multi-user, JWT auth, role-based access
Run: uvicorn meetingmind.main:app --reload --port 8090
Docs: http://localhost:8090/docs
"""
import os
import re
import string
import random
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from meetingmind.db import get_conn, init_db
from meetingmind.auth import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    decode_token, revoke_token, is_token_revoked,
    is_account_locked, record_failed_login, reset_failed_logins,
    cleanup_expired_tokens
)
from meetingmind.models import (
    RegisterRequest, LoginRequest, TokenResponse, RefreshRequest,
    UserResponse, ProcessNotesRequest, ItemAssignRequest,
    ItemResponse, MeetingResponse, UpdateStatusRequest, TeamMemberResponse
)

# ── App setup ─────────────────────────────────────────────────────────────────
app = FastAPI(
    title="MeetingMind API",
    description="Multi-user AI meeting intelligence with JWT auth",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8090", "http://127.0.0.1:8090"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (HTML pages)
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Initialize DB on startup
@app.on_event("startup")
def startup():
    init_db()
    print("MeetingMind started.")

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
    "not set up", "set up", "slow query", "affecting"
]
ACRONYMS = {"cto", "cfo", "ceo", "coo", "hr", "qa", "api", "ui", "ux"}

def flag_priority(text: str) -> str:
    t = text.lower()
    if any(k in t for k in HIGH_KEYWORDS): return "high"
    elif any(k in t for k in MEDIUM_KEYWORDS): return "medium"
    return "low"

def clean_item(text: str) -> str:
    text = re.sub(r'^[\-\*\•\d\.\)]+\s*', '', text).strip()
    text = re.sub(r'^([A-Za-z][a-z]*(?:\s+[a-z]+)?)\s*[-:]\s*',
                  lambda m: m.group(1).capitalize() + ': ', text)
    text = text[0].upper() + text[1:] if text else text
    if text and not text.endswith(('.', '!', '?')): text += '.'
    return text

def split_notes(raw: str) -> list:
    lines = re.split(r'\n|\r\n', raw)
    items = []
    for line in lines:
        line = line.strip()
        if not line or len(line) < 5: continue
        parts = re.split(r'(?<=[a-z])\.\s+|;', line)
        for part in parts:
            part = part.strip().rstrip('.')
            if len(part) > 5: items.append(part)
    return items

# ── Auth helpers ──────────────────────────────────────────────────────────────
security = HTTPBearer()

def generate_team_code(length=8) -> str:
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=length))

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")

    conn = get_conn()
    if is_token_revoked(payload["jti"], conn):
        conn.close()
        raise HTTPException(status_code=401, detail="Token has been revoked")

    user = conn.execute("SELECT * FROM users WHERE id = ?", (int(payload["sub"]),)).fetchone()
    conn.close()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return dict(user), payload

def require_manager(current=Depends(get_current_user)):
    user, payload = current
    if user["role"] != "manager":
        raise HTTPException(status_code=403, detail="Manager access required")
    return user, payload

# ── Pages ─────────────────────────────────────────────────────────────────────
@app.get("/", response_class=FileResponse, include_in_schema=False)
def landing():
    return FileResponse(os.path.join(static_dir, "landing.html"))

@app.get("/login", response_class=FileResponse, include_in_schema=False)
def login_page():
    return FileResponse(os.path.join(static_dir, "login.html"))

@app.get("/register", response_class=FileResponse, include_in_schema=False)
def register_page():
    return FileResponse(os.path.join(static_dir, "register.html"))

@app.get("/dashboard", response_class=FileResponse, include_in_schema=False)
def dashboard_page():
    return FileResponse(os.path.join(static_dir, "dashboard.html"))

@app.get("/tasks", response_class=FileResponse, include_in_schema=False)
def tasks_page():
    return FileResponse(os.path.join(static_dir, "tasks.html"))

# ── Auth routes ───────────────────────────────────────────────────────────────
@app.post("/auth/register", response_model=TokenResponse, tags=["Auth"])
def register(req: RegisterRequest):
    conn = get_conn()

    # Check email not taken
    existing = conn.execute("SELECT id FROM users WHERE email = ?", (req.email,)).fetchone()
    if existing:
        conn.close()
        raise HTTPException(status_code=400, detail="Email already registered")

    # Handle team
    team_id = None
    if req.team_code:
        team = conn.execute("SELECT id FROM teams WHERE code = ?", (req.team_code.upper(),)).fetchone()
        if not team:
            conn.close()
            raise HTTPException(status_code=400, detail="Invalid team code")
        team_id = team["id"]
    elif req.role == "manager":
        # Create new team for manager
        code = generate_team_code()
        while conn.execute("SELECT id FROM teams WHERE code = ?", (code,)).fetchone():
            code = generate_team_code()
        conn.execute("INSERT INTO teams (name, code) VALUES (?, ?)", (f"{req.name}'s Team", code))
        conn.commit()
        team_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    else:
        conn.close()
        raise HTTPException(status_code=400, detail="Members must provide a team code")

    # Create user
    password_hash = hash_password(req.password)
    conn.execute(
        "INSERT INTO users (name, email, password_hash, role, team_id) VALUES (?, ?, ?, ?, ?)",
        (req.name, req.email, password_hash, req.role, team_id)
    )
    conn.commit()
    user_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()

    access_token = create_access_token(user_id, req.role)
    refresh_token = create_refresh_token(user_id)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        role=req.role,
        name=req.name,
        user_id=user_id
    )

@app.post("/auth/login", response_model=TokenResponse, tags=["Auth"])
def login(req: LoginRequest):
    conn = get_conn()
    user = conn.execute("SELECT * FROM users WHERE email = ?", (req.email,)).fetchone()

    if not user:
        conn.close()
        raise HTTPException(status_code=401, detail="Invalid email or password")

    user = dict(user)

    # Check lockout
    if is_account_locked(user):
        conn.close()
        raise HTTPException(status_code=429, detail="Account locked. Try again in 15 minutes.")

    # Verify password
    if not verify_password(req.password, user["password_hash"]):
        record_failed_login(user["id"], conn)
        conn.close()
        remaining = 5 - (user["failed_logins"] + 1)
        raise HTTPException(
            status_code=401,
            detail=f"Invalid email or password. {max(0,remaining)} attempts remaining."
        )

    reset_failed_logins(user["id"], conn)
    cleanup_expired_tokens(conn)
    conn.close()

    access_token = create_access_token(user["id"], user["role"])
    refresh_token = create_refresh_token(user["id"])
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        role=user["role"],
        name=user["name"],
        user_id=user["id"]
    )

@app.post("/auth/logout", tags=["Auth"])
def logout(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    payload = decode_token(token)
    if payload:
        conn = get_conn()
        from datetime import datetime
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        revoke_token(payload["jti"], exp, conn)
        conn.close()
    return {"message": "Logged out successfully"}

@app.post("/auth/refresh", response_model=TokenResponse, tags=["Auth"])
def refresh(req: RefreshRequest):
    payload = decode_token(req.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    conn = get_conn()
    if is_token_revoked(payload["jti"], conn):
        conn.close()
        raise HTTPException(status_code=401, detail="Refresh token revoked")

    user = conn.execute("SELECT * FROM users WHERE id = ?", (int(payload["sub"]),)).fetchone()
    conn.close()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    user = dict(user)
    access_token = create_access_token(user["id"], user["role"])
    new_refresh = create_refresh_token(user["id"])
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh,
        role=user["role"],
        name=user["name"],
        user_id=user["id"]
    )

@app.get("/auth/me", response_model=UserResponse, tags=["Auth"])
def me(current=Depends(get_current_user)):
    user, _ = current
    conn = get_conn()
    team = conn.execute("SELECT name FROM teams WHERE id = ?", (user["team_id"],)).fetchone()
    conn.close()
    return UserResponse(
        id=user["id"], name=user["name"], email=user["email"],
        role=user["role"], team_id=user["team_id"],
        team_name=team["name"] if team else None
    )

# ── Meeting routes ────────────────────────────────────────────────────────────
@app.post("/meetings/process", tags=["Meetings"])
def process_notes(req: ProcessNotesRequest, current=Depends(require_manager)):
    user, _ = current
    items_raw = split_notes(req.notes)
    items = []
    for raw in items_raw:
        items.append({
            "text": clean_item(raw),
            "priority": flag_priority(raw),
            "owner_id": None,
            "owner_name": None,
            "status": "todo"
        })
    order = {"high": 0, "medium": 1, "low": 2}
    items.sort(key=lambda x: order[x["priority"]])
    return {"title": req.title, "points": items}

@app.post("/meetings/save", tags=["Meetings"])
def save_meeting(req: ProcessNotesRequest, current=Depends(require_manager)):
    user, _ = current
    conn = get_conn()
    conn.execute(
        "INSERT INTO meetings (title, manager_id, team_id) VALUES (?, ?, ?)",
        (req.title, user["id"], user["team_id"])
    )
    conn.commit()
    meeting_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    items = split_notes(req.notes)
    for raw in items:
        conn.execute(
            "INSERT INTO items (meeting_id, text, priority) VALUES (?, ?, ?)",
            (meeting_id, clean_item(raw), flag_priority(raw))
        )
    conn.commit()
    conn.close()
    return {"id": meeting_id}

@app.get("/meetings", tags=["Meetings"])
def get_meetings(current=Depends(get_current_user)):
    user, _ = current
    conn = get_conn()
    rows = conn.execute("""
        SELECT m.id, m.title, m.created_at,
               COUNT(i.id) as item_count,
               SUM(CASE WHEN i.priority='high' THEN 1 ELSE 0 END) as high_count,
               SUM(CASE WHEN i.status='done' THEN 1 ELSE 0 END) as done_count
        FROM meetings m
        LEFT JOIN items i ON i.meeting_id = m.id
        WHERE m.team_id = ?
        GROUP BY m.id ORDER BY m.id DESC
    """, (user["team_id"],)).fetchall()
    conn.close()
    return {"meetings": [dict(r) for r in rows]}

@app.get("/meetings/{meeting_id}/items", tags=["Meetings"])
def get_items(meeting_id: int, current=Depends(get_current_user)):
    user, _ = current
    conn = get_conn()
    items = conn.execute(
        "SELECT * FROM items WHERE meeting_id = ? ORDER BY id",
        (meeting_id,)
    ).fetchall()
    conn.close()
    return {"items": [dict(i) for i in items]}

@app.put("/meetings/{meeting_id}/items/{item_id}/assign", tags=["Meetings"])
def assign_item(meeting_id: int, item_id: int, req: ItemAssignRequest, current=Depends(require_manager)):
    conn = get_conn()
    owner_name = req.owner_name
    if req.owner_id:
        user = conn.execute("SELECT name FROM users WHERE id = ?", (req.owner_id,)).fetchone()
        if user: owner_name = user["name"]
    conn.execute(
        "UPDATE items SET owner_id = ?, owner_name = ? WHERE id = ? AND meeting_id = ?",
        (req.owner_id, owner_name, item_id, meeting_id)
    )
    conn.commit()
    conn.close()
    return {"ok": True}

@app.put("/items/{item_id}/status", tags=["Items"])
def update_status(item_id: int, req: UpdateStatusRequest, current=Depends(get_current_user)):
    user, _ = current
    conn = get_conn()
    item = conn.execute("SELECT owner_id FROM items WHERE id = ?", (item_id,)).fetchone()
    if not item:
        conn.close()
        raise HTTPException(status_code=404, detail="Item not found")
    # Members can only update their own items, managers can update any
    if user["role"] == "member" and item["owner_id"] != user["id"]:
        conn.close()
        raise HTTPException(status_code=403, detail="You can only update your own items")
    conn.execute("UPDATE items SET status = ? WHERE id = ?", (req.status, item_id))
    conn.commit()
    conn.close()
    return {"ok": True}

# ── My tasks (member view) ────────────────────────────────────────────────────
@app.get("/tasks", tags=["Tasks"])
def my_tasks(current=Depends(get_current_user)):
    user, _ = current
    conn = get_conn()
    items = conn.execute("""
        SELECT i.*, m.title as meeting_title
        FROM items i
        JOIN meetings m ON m.id = i.meeting_id
        WHERE i.owner_id = ?
        ORDER BY
            CASE i.priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END,
            CASE i.status WHEN 'todo' THEN 0 WHEN 'in-progress' THEN 1 ELSE 2 END
    """, (user["id"],)).fetchall()
    conn.close()
    return {"tasks": [dict(i) for i in items]}

# ── Team analytics (manager only) ────────────────────────────────────────────
@app.get("/team/members", tags=["Team"])
def team_members(current=Depends(require_manager)):
    user, _ = current
    conn = get_conn()
    members = conn.execute("""
        SELECT u.id, u.name, u.email, u.role,
               COUNT(i.id) as total_items,
               SUM(CASE WHEN i.status != 'done' THEN 1 ELSE 0 END) as open_items,
               SUM(CASE WHEN i.status = 'done' THEN 1 ELSE 0 END) as done_items,
               SUM(CASE WHEN i.priority='high' AND i.status!='done' THEN 1 ELSE 0 END) as open_high
        FROM users u
        LEFT JOIN items i ON i.owner_id = u.id
        WHERE u.team_id = ?
        GROUP BY u.id
        ORDER BY open_high DESC, open_items DESC
    """, (user["team_id"],)).fetchall()
    conn.close()
    result = []
    for m in members:
        m = dict(m)
        total = m["total_items"] or 0
        done = m["done_items"] or 0
        m["completion_rate"] = round((done/total)*100) if total > 0 else 0
        m["overloaded"] = m["open_high"] >= 3 and m["role"] != "manager"
        result.append(m)
    return {"members": result}

@app.get("/team/code", tags=["Team"])
def team_code(current=Depends(require_manager)):
    user, _ = current
    conn = get_conn()
    team = conn.execute("SELECT code, name FROM teams WHERE id = ?", (user["team_id"],)).fetchone()
    conn.close()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return {"code": team["code"], "name": team["name"]}

if __name__ == "__main__":
    import uvicorn
    print("Starting MeetingMind at http://localhost:8090")
    print("API docs at   http://localhost:8090/docs")
    uvicorn.run("meetingmind.main:app", host="0.0.0.0", port=8090, reload=True)
