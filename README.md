# Meeting Notes Cleaner

A local, no-API meeting notes cleaner built with fine-tuned FLAN-T5, Flask, FastAPI, and Whisper. Takes raw messy meeting notes and returns clean prioritized action items with owner detection and team analytics.

## Demo

**Input** — raw messy notes:
```
troy - blocked on API spec from backend, needs it asap or sprint is at risk
deployment pipeline broke last night, devops investigating, critical blocker
sara - design review scheduled thursday, needs sign off from product before then
john - finished auth module, pushing to staging today
```

**Output** — cleaned and prioritized:
```
HIGH  👤 Troy    Troy: blocked on API spec, needs it asap or sprint is at risk.
HIGH  👤 Devops   Deployment pipeline broke last night, critical blocker.
MED   👤 Sara     Sara: design review thursday, needs sign off from product.
LOW   👤 John     John: finished auth module, pushing to staging today.
```

---

## Features

| Feature | Description |
|---|---|
| Priority Engine | Flags items HIGH / MEDIUM / LOW — 99.7% accuracy on 322 samples |
| Owner Detection | Extracts person/team from 4 patterns (name-, assigned to, Name will, team tokens) |
| Action Tracker | Mark items Todo / In Progress / Done, persisted in SQLite |
| Meeting History | Save and browse past meetings |
| Health Score | % of previous meeting items closed before next meeting |
| Meeting Debt | Flags owners with 3+ unresolved HIGH items across meetings |
| Workload View | Per-owner completion rate and overload detection |
| Audio Input | Record meeting → Whisper transcribes locally → notes auto-filled |
| REST API | FastAPI with auto-generated Swagger docs at /docs |
| Docker | Runs in container with `docker compose up --build` |

---

## Benchmark Results

Tested priority engine against 322 labeled samples (30 hand-labeled + 292 AMI corpus).

| Class | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| High | 1.00 | 1.00 | 1.00 | 17 |
| Medium | 0.99 | 1.00 | 1.00 | 172 |
| Low | 1.00 | 0.99 | 1.00 | 133 |

**Overall accuracy: 99.7%** (321/322 correct)

```bash
python benchmark.py  # run it yourself
```

---

## Model Evaluation — ROUGE Scores

Evaluated on 15 AMI test meetings comparing model output against human summaries.

| Metric | Score | Meaning |
|---|---|---|
| ROUGE-1 | 0.1761 | Word overlap |
| ROUGE-2 | 0.0510 | Bigram overlap |
| ROUGE-L | 0.1473 | Longest common subsequence |

Above random baseline (~0.10). Upgrading to flan-t5-base projected to reach ROUGE-1 ~0.25.

```bash
python rouge_eval.py  # run it yourself
```

---

## Unit Tests

43 tests covering priority engine, owner detection and Flask API routes.

```bash
pytest tests/ -v
# 43 passed in 2.12s
```

| File | Tests | Coverage |
|---|---|---|
| tests/test_priority.py | 23 | flag_priority() — HIGH/MEDIUM/LOW cases |
| tests/test_owner.py | 11 | detect_owner() — 4 patterns + acronyms |
| tests/test_routes.py | 9 | Flask API — /process, sorting, validation |

---

## Quick Start

### Option 1 — Local Python

```bash
git clone https://github.com/vijay0320/meeting-notes-cleaner
cd meeting-notes-cleaner

# Python 3.11 required
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run Flask app
python app_v2.py
# Open http://localhost:8080

# OR run FastAPI
uvicorn api:app --reload --port 8080
# Docs at http://localhost:8080/docs
```

### Option 2 — Docker

```bash
docker compose up --build
# Open http://localhost:8080
```

---

## Retrain Model (Optional)

Model weights are not committed (293MB). Retrain in 3 steps:

```bash
# 1. Download AMI corpus annotations (22MB, free)
curl -O https://groups.inf.ed.ac.uk/ami/AMICorpusAnnotations/ami_public_manual_1.6.2.zip
unzip ami_public_manual_1.6.2.zip -d ami_annotations

# 2. Generate training data (AMI + 300 synthetic samples)
python augment_data_v2.py

# 3. Fine-tune flan-t5-small (~20 mins on M1 CPU)
python train_v2.py
# Saves to my_meeting_model_v2/
```

---

## API Reference

FastAPI with interactive docs at `http://localhost:8080/docs`

| Method | Route | Description |
|---|---|---|
| POST | /process | Clean and prioritize notes |
| POST | /save | Save meeting to database |
| POST | /update_status | Update item status |
| GET | /meetings | All meetings with health scores |
| GET | /meeting/{id} | Single meeting detail |
| GET | /debt | Meeting debt warnings |
| GET | /workload | Owner workload stats |
| POST | /transcribe | Transcribe audio with Whisper |

---

## Project Structure

```
meeting-notes-cleaner/
├── app_v2.py            # Flask app — full UI + all features
├── api.py               # FastAPI — REST API + Swagger docs
├── db.py                # SQLite queries — health score, debt, workload
├── train_v2.py          # Fine-tune flan-t5-small
├── augment_data_v2.py   # Generate synthetic training data
├── infer_v2.py          # Test model inference
├── benchmark.py         # Priority engine evaluation
├── rouge_eval.py        # ROUGE score evaluation
├── requirements.txt     # Python dependencies
├── Dockerfile           # Container definition
├── docker-compose.yml   # Run with docker compose up
├── .dockerignore        # Exclude unnecessary files
└── tests/
    ├── test_priority.py # 23 priority engine tests
    ├── test_owner.py    # 11 owner detection tests
    └── test_routes.py   # 9 Flask route tests
```

---

## Stack

| Layer | Tech |
|---|---|
| Model | google/flan-t5-small fine-tuned on AMI corpus |
| Audio | OpenAI Whisper base (local, no API) |
| Backend | Flask + FastAPI |
| Frontend | Vanilla HTML/CSS/JS |
| Database | SQLite |
| Training | PyTorch + HuggingFace Transformers |
| Testing | pytest + pytest-flask |
| Container | Docker + docker-compose |
| Data | AMI Meeting Corpus (CC BY 4.0) |

---

## Version History

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

---

## Model Training History

| Version | Train Loss | Val Loss | Data |
|---|---|---|---|
| v1 | 1.73 | 2.60 | AMI only, 113 samples |
| v2 | 0.76 | 1.13 | AMI + synthetic, 363 samples |
