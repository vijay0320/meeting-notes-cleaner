# Meeting Notes Cleaner

A local, no-API meeting notes cleaner that takes raw messy notes and returns clean prioritized action items with owner detection and an action item tracker.

## Demo

**Input** — raw messy notes:
```
Troy - blocked on API spec from backend, needs it asap or sprint is at risk
deployment pipeline broke last night, devops investigating, critical blocker
sara - design review scheduled thursday, needs sign off from product before then
john - finished auth module, pushing to staging today
```

**Output** — cleaned and prioritized:
```
HIGH  👤 Troy       Troy: blocked on API spec, needs it asap or sprint is at risk.
HIGH  👤 Devops      Deployment pipeline broke last night, critical blocker.
MED   👤 Sara        Sara: design review thursday, needs sign off from product.
LOW   👤 John        John: finished auth module, pushing to staging today.
```

---

## Features

- **Priority Engine** — flags items as HIGH / MEDIUM / LOW based on urgency keywords
- **Owner Detection** — extracts person/team names from 4 patterns (name-, assigned to, Name will, team tokens)
- **Action Item Tracker** — mark items as Todo / In Progress / Done, persisted in SQLite
- **Meeting History** — save and browse past meetings
- **100% Local** — no API, no internet required at runtime

---

## Benchmark Results

Tested against 30 hand-labeled examples + 292 AMI corpus test sentences (322 total).

| Class  | Precision | Recall | F1   | Support |
|--------|-----------|--------|------|---------|
| High   | 1.00      | 1.00   | 1.00 | 17      |
| Medium | 0.99      | 1.00   | 1.00 | 172     |
| Low    | 1.00      | 0.99   | 1.00 | 133     |

**Overall accuracy: 99.7%** (321/322 correct)

**Confusion Matrix:**

|             | Pred HIGH | Pred MED | Pred LOW |
|-------------|-----------|----------|----------|
| True HIGH   | 17        | 0        | 0        |
| True MEDIUM | 0         | 172      | 0        |
| True LOW    | 0         | 1        | 132      |

Only misclassification: `"q3 planning doc shared with the team"` predicted MEDIUM (triggered by "team"), true label LOW.

Run benchmarks yourself:
```bash
python benchmark.py
```

---

## Model

Fine-tuned `google/flan-t5-small` on the [AMI Meeting Corpus](https://groups.inf.ed.ac.uk/ami/corpus/) + 300 synthetic meeting samples across 5 domains (engineering, product, marketing, finance, HR).

| Version | Train Loss | Val Loss | Notes               |
|---------|------------|----------|---------------------|
| v1      | 1.73       | 2.60     | AMI only, 113 samples |
| v2      | 0.76       | 1.13     | + synthetic data, 363 samples |

> Model weights are not committed to git (293MB). Retrain using instructions below.

---
## Model Evaluation — ROUGE Scores

Evaluated on 15 AMI test meetings comparing model output against human summaries.

| Metric  | Score  | Meaning                    |
|---------|--------|----------------------------|
| ROUGE-1 | 0.1761 | Word overlap               |
| ROUGE-2 | 0.0510 | Bigram overlap             |
| ROUGE-L | 0.1473 | Longest common subsequence |

**Above random baseline (~0.10) but below large models (BART ~0.45).**
Expected for flan-t5-small (80MB) trained on 142 meetings.
Upgrading to flan-t5-base projected to reach ROUGE-1 ~0.25.

## Setup

```bash
# Clone
git clone https://github.com/vijay0320/meeting-notes-cleaner.git
cd meeting-notes-cleaner

# Create virtual environment with Python 3.11
python3.11 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Run

```bash
python app_v2.py
# Open http://127.0.0.1:8080
```

---

## Retrain Model (Optional)

```bash
# 1. Download AMI annotations (22MB)
curl -O https://groups.inf.ed.ac.uk/ami/AMICorpusAnnotations/ami_public_manual_1.6.2.zip
unzip ami_public_manual_1.6.2.zip -d ami_annotations

# 2. Build dataset (AMI + synthetic data)
python augment_data_v2.py

# 3. Fine-tune flan-t5-small
python train_v2.py
# Saves to my_meeting_model_v2/

# 4. Test inference
python infer_v2.py
```

---

## Stack

| Layer     | Tech                                      |
|-----------|-------------------------------------------|
| Model     | google/flan-t5-small (fine-tuned on AMI)  |
| Backend   | Flask                                     |
| Frontend  | Vanilla HTML / CSS / JS                   |
| Database  | SQLite                                    |
| Training  | PyTorch + HuggingFace Transformers        |
| Data      | AMI Meeting Corpus (CC BY 4.0)            |

---

## Project Structure

```
meeting-notes-cleaner/
├── app_v2.py            # Flask app — priority engine, owner detection, tracker
├── train_v2.py          # Fine-tune flan-t5-small on AMI + synthetic data
├── augment_data_v2.py   # Generate synthetic training data (5 domains, 300 samples)
├── infer_v2.py          # Test model inference locally
├── benchmark.py         # Evaluate priority engine — precision/recall/F1
├── requirements.txt     # Python dependencies
└── README.md
```

---

## Git History

```
v1.0  baseline: flan-t5-small + priority engine + flask UI
      feature/owner-detection-tracker-benchmark
        └── owner detection (4 patterns)
        └── action item tracker (SQLite)
        └── meeting history
        └── benchmark 99.7% accuracy
```
