# Meeting Notes Cleaner + MeetingMind

Two projects in one repo — a local AI meeting notes cleaner and a full multi-user SaaS application built on top of it.

---

## Project 1: Meeting Notes Cleaner (`app_v2.py`)

A local, no-API meeting notes cleaner that takes raw messy notes and returns clean prioritized action items with owner detection and team analytics.

### Demo

**Input:**
```
troy - blocked on API spec from backend, needs it asap or sprint is at risk
deployment pipeline broke last night, devops investigating, critical blocker
sara - design review scheduled thursday, needs sign off from product before then
john - finished auth module, pushing to staging today
```

**Output:**
```
HIGH  👤 Troy     Troy: blocked on API spec, needs it asap or sprint is at risk.
HIGH  👤 Devops   Deployment pipeline broke last night, critical blocker.
MED   👤 Sara     Sara: design review thursday, needs sign off from product.
LOW   👤 John     John: finished auth module, pushing to staging today.
```

### Features

| Feature | Description |
|---|---|
| Priority Engine | Flags HIGH / MEDIUM / LOW — 99.7% accuracy on 322 samples |
| Owner Detection | Extracts person/team from 4 patterns (name-, assigned to, Name will, team tokens) |
| Action Tracker | Mark items Todo / In Progress / Done, persisted in SQLite |
| Meeting History | Save and browse past meetings |
| Health Score | % of previous meeting items closed before next meeting |
| Meeting Debt | Flags owners with 3+ unresolved HIGH items across meetings |
| Workload View | Per-owner completion rate and overload detection |
| Audio Input | Record meeting → Whisper transcribes locally → notes auto-filled |
| REST API | FastAPI with auto-generated Swagger docs at /docs |
| Export | Download cleaned notes as PDF or Markdown |
| Docker | Runs in container with `docker compose up --build` |

### Benchmark Results

Tested priority engine against 322 labeled samples (30 hand-labeled + 292 AMI corpus).

| Class | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| High | 1.00 | 1.00 | 1.00 | 17 |
| Medium | 0.99 | 1.00 | 1.00 | 172 |
| Low | 1.00 | 0.99 | 1.00 | 133 |

**Overall accuracy: 99.7%** (321/322 correct)

### Model Evaluation — ROUGE Scores

| Metric | Score | Meaning |
|---|---|---|
| ROUGE-1 | 0.1761 | Word overlap |
| ROUGE-2 | 0.0510 | Bigram overlap |
| ROUGE-L | 0.1473 | Longest common subsequence |

Above random baseline (~0.10). Upgrading to flan-t5-base projected to reach ROUGE-1 ~0.25.

### Unit Tests

```bash
pytest tests/ -v
# 43 passed in 2.12s
```

### Quick Start

```bash
git clone https://github.com/vijay0320/meeting-notes-cleaner
cd meeting-notes-cleaner

python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Flask app
python app_v2.py
# Open http://localhost:8080

# FastAPI
uvicorn api:app --reload --port 8080
# Docs at http://localhost:8080/docs

# Docker
docker compose up --build
```

### Retrain Model (Optional)

Model weights not committed (293MB). Retrain in 3 steps:

```bash
# 1. Download AMI corpus annotations
curl -O https://groups.inf.ed.ac.uk/ami/AMICorpusAnnotations/ami_public_manual_1.6.2.zip
unzip ami_public_manual_1.6.2.zip -d ami_annotations

# 2. Generate training data
python augment_data_v2.py

# 3. Fine-tune flan-t5-small (~20 mins on M1 CPU)
python train_v2.py
```

### Version History (v1.0 → v12.0)

| Version | What was added |
|---|---|
| v1.0 | flan-t5-small fine-tuned + priority engine + Flask UI |
| v2.0 | Owner detection + action tracker + SQLite + benchmark 99.7% |
| v3.0 | Meeting health score + meeting debt tracker |
| v4.0 | Owner workload view |
| v5.0 | ROUGE evaluation (ROUGE-1: 0.176) |
| v6.0 | Docker containerization |
| v7.0 | Whisper audio input (local, no API) |
| v8.0 | pytest unit tests (43/43 passing) |
| v9.0 | FastAPI migration (auto docs, Pydantic, uvicorn) |
| v10.0 | Comprehensive README + CI/CD GitHub Actions |
| v11.0 | PDF and Markdown export |
| v12.0 | Project cleanup |

---

## Project 2: MeetingMind (`meetingmind/`)

A full multi-user SaaS application built on top of the meeting notes cleaner. Teams can collaborate — managers clean notes and assign tasks, members see their tasks and update progress in real time.

### Demo Flow

```
Manager registers → creates team (invite code generated)
Manager pastes messy notes → AI cleans → assigns tasks to members
Members register with invite code → see their assigned tasks
Members update status → manager sees live toast notification
Manager views team workload → clicks member card → sees their tasks
Email sent on task assigned, completion, and overdue alerts
```

### Features

| Feature | Description |
|---|---|
| Auth | JWT tokens, bcrypt hashing, brute force protection, token blacklist |
| Roles | Manager (full access) + Member (own tasks only) |
| Team codes | Auto-generated invite code, members join with code |
| Clean Notes | AI-powered note cleaning with assignment dropdowns |
| Real-time | SSE broadcast — manager sees status changes instantly |
| Workload view | Clickable member cards with task detail panel |
| Email | Gmail SMTP — task assigned, all done, overdue HIGH items |
| Landing page | Animated marketing page with AnimeJS |

### Quick Start

```bash
# 1. Install dependencies
pip install fastapi uvicorn "python-jose[cryptography]" "passlib[bcrypt]" \
    python-dotenv "pydantic[email]" aiosmtplib bcrypt

# 2. Generate secret key
python -c "import secrets; print(secrets.token_hex(32))"

# 3. Create meetingmind/.env
SECRET_KEY=your_generated_key
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
GMAIL_USER=your@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
APP_URL=http://localhost:8091

# 4. Run
uvicorn meetingmind.main:app --port 8091 --host 127.0.0.1

# Open http://localhost:8091
# API docs at http://localhost:8091/docs
```

### API Routes

| Method | Route | Access | Description |
|---|---|---|---|
| POST | /auth/register | Public | Register with role + team code |
| POST | /auth/login | Public | Returns JWT tokens |
| POST | /auth/logout | Auth | Revokes token |
| GET | /auth/me | Auth | Current user info |
| POST | /meetings/process | Manager | Clean and prioritize notes |
| POST | /meetings/save | Manager | Save meeting + email assigned members |
| GET | /meetings | Auth | All team meetings |
| PUT | /items/{id}/status | Auth | Update item status |
| GET | /api/tasks | Auth | Member's assigned tasks |
| GET | /team/members | Manager | Team workload stats |
| GET | /team/members/{id}/items | Manager | Member's task detail |
| GET | /team/code | Manager | Team invite code |
| GET | /events | Auth | SSE real-time stream |
| POST | /admin/check-overdue | Manager | Trigger overdue email check |

### Security

- 256-bit secret key from .env (never committed)
- Access tokens expire in 30 minutes
- Refresh tokens expire in 7 days
- Token blacklist in SQLite (revoked on logout)
- bcrypt password hashing (cost factor 12)
- 5 failed login attempts → 15 minute lockout
- Role-based access control on every route
- Members can only update their own items

### Version History (v13.0 → v18.0)

| Version | What was added |
|---|---|
| v13.0 | Landing page + login + register UI with AnimeJS |
| v14.0 | JWT auth + manager dashboard + member tasks view |
| v15.0 | Full task assignment flow |
| v16.0 | Real-time updates via SSE + toast notifications |
| v17.0 | Manager workload view + member task detail panel |
| v18.0 | Email notifications (assigned, complete, overdue) |

---

## Stack

| Layer | Tech |
|---|---|
| AI Model | google/flan-t5-small fine-tuned on AMI corpus |
| Audio | OpenAI Whisper base (local, no API) |
| Backend | Flask + FastAPI |
| Frontend | Vanilla HTML/CSS/JS + AnimeJS |
| Database | SQLite |
| Auth | JWT (python-jose) + bcrypt |
| Email | Gmail SMTP (aiosmtplib) |
| Real-time | Server-Sent Events (SSE) |
| Training | PyTorch + HuggingFace Transformers |
| Testing | pytest + pytest-flask (43/43) |
| Container | Docker + docker-compose |
| CI/CD | GitHub Actions (auto-run pytest on PR) |
| Data | AMI Meeting Corpus (CC BY 4.0) |

---

## Project Structure

```
meeting-notes-cleaner/
├── app_v2.py               # Flask app — single user
├── api.py                  # FastAPI version
├── db.py                   # SQLite queries
├── train_v2.py             # Fine-tune flan-t5-small
├── augment_data_v2.py      # Synthetic data generation
├── benchmark.py            # Priority engine benchmark
├── rouge_eval.py           # ROUGE evaluation
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── static/index.html       # Single-user UI
├── tests/                  # 43 unit tests
├── .github/workflows/      # CI/CD
└── meetingmind/            # Multi-user SaaS
    ├── main.py             # FastAPI backend
    ├── auth.py             # JWT + bcrypt
    ├── db.py               # Schema + queries
    ├── models.py           # Pydantic models
    ├── email.py            # Email notifications
    ├── .env                # Secrets (gitignored)
    └── static/
        ├── landing.html
        ├── login.html
        ├── register.html
        ├── dashboard.html
        └── tasks.html
```