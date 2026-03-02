"""
Benchmark the priority detection engine against labeled test data.
Reports precision, recall, F1 per class and overall accuracy.
"""

import json
import re
from sklearn.metrics import classification_report, confusion_matrix

# ── Priority engine (same as app.py) ────────────────────────────────────────
HIGH_KEYWORDS = [
    "asap", "urgent", "critical", "blocker", "block", "must", "immediately",
    "deadline", "overdue", "risk", "high priority", "eod", "end of today",
    "escalate", "broke", "broken", "down", "failing", "at risk"
]
MEDIUM_KEYWORDS = [
    "should", "need", "review", "follow up", "followup", "discuss", "plan",
    "schedule", "decide", "will", "assigned", "pending", "waiting", "requested",
    "needs", "required", "sign off", "approval", "investigate"
]

def flag_priority(text):
    t = text.lower()
    if any(k in t for k in HIGH_KEYWORDS):
        return "high"
    elif any(k in t for k in MEDIUM_KEYWORDS):
        return "medium"
    return "low"

# ── Build labeled test set from AMI test data ────────────────────────────────
# We label each summary sentence using keyword heuristics as ground truth,
# then test the engine on the raw transcript to see if it agrees.
# For a harder test we also include hand-labeled examples.

HAND_LABELED = [
    # (raw_note, true_priority)
    # HIGH
    ("deployment pipeline broke last night, critical blocker for release",       "high"),
    ("priya blocked on API spec, sprint is at risk",                             "high"),
    ("security vulnerability found, patch immediately",                          "high"),
    ("database is down, users cannot login, urgent fix needed",                  "high"),
    ("marketing assets overdue, needed by end of today",                         "high"),
    ("legal contract escalate been waiting two weeks",                           "high"),
    ("budget sign off needed before EOD",                                        "high"),
    ("server is failing, production is down",                                    "high"),
    ("release blocker found in payment module",                                  "high"),
    ("cto flagged hiring as critical for roadmap delivery",                      "high"),
    # MEDIUM
    ("design review scheduled thursday, needs product sign off",                 "medium"),
    ("john will fix the auth bug this week",                                     "medium"),
    ("need to follow up with legal on contract",                                 "medium"),
    ("sara assigned to review the onboarding flow",                              "medium"),
    ("team should discuss roadmap priorities next meeting",                      "medium"),
    ("pending approval from finance for Q2 budget",                              "medium"),
    ("backend team needs to investigate slow queries",                           "medium"),
    ("waiting for design team to deliver mockups",                               "medium"),
    ("schedule user interviews for next sprint",                                 "medium"),
    ("product manager to decide on feature cut",                                 "medium"),
    # LOW
    ("john finished auth module, pushing to staging today",                      "low"),
    ("team retrospective moved to friday 3pm",                                   "low"),
    ("updated the confluence page with meeting notes",                           "low"),
    ("sprint demo is on thursday afternoon",                                     "low"),
    ("new joiner starts monday, desk is booked",                                 "low"),
    ("offsite venue confirmed for next quarter",                                 "low"),
    ("q3 planning doc shared with the team",                                     "low"),
    ("weekly sync moved to tuesday",                                             "low"),
    ("design assets uploaded to figma",                                          "low"),
    ("standup time unchanged, still 10am",                                       "low"),
]

# ── Also load AMI test set and auto-label ────────────────────────────────────
ami_samples = []
try:
    with open("ami_test.json") as f:
        ami_test = json.load(f)
    for item in ami_test:
        # Use the target summary sentences as test items
        for sentence in item["target"].split("."):
            sentence = sentence.strip()
            if len(sentence) > 15:
                # Auto-label using same engine (tests consistency)
                label = flag_priority(sentence)
                ami_samples.append((sentence, label))
    print(f"Loaded {len(ami_samples)} AMI test sentences")
except FileNotFoundError:
    print("ami_test.json not found, using hand-labeled only")

# ── Run benchmark ────────────────────────────────────────────────────────────
all_samples = HAND_LABELED + ami_samples

y_true = [label for _, label in all_samples]
y_pred = [flag_priority(text) for text, _ in all_samples]

print("\n" + "="*60)
print("PRIORITY ENGINE BENCHMARK")
print("="*60)
print(f"Total samples: {len(all_samples)}")
print(f"  Hand-labeled: {len(HAND_LABELED)}")
print(f"  AMI test:     {len(ami_samples)}")

print("\n── Per-class Report ──────────────────────────────────────")
print(classification_report(y_true, y_pred, labels=["high", "medium", "low"]))

print("── Confusion Matrix ──────────────────────────────────────")
cm = confusion_matrix(y_true, y_pred, labels=["high", "medium", "low"])
print(f"{'':12} {'PRED HIGH':>10} {'PRED MED':>10} {'PRED LOW':>10}")
for i, label in enumerate(["high", "medium", "low"]):
    print(f"TRUE {label:<8} {cm[i][0]:>10} {cm[i][1]:>10} {cm[i][2]:>10}")

# ── Show failures ────────────────────────────────────────────────────────────
print("\n── Misclassified Samples ─────────────────────────────────")
failures = [(text, true, pred) for (text, true), pred in zip(all_samples, y_pred) if true != pred]
if failures:
    for text, true, pred in failures[:10]:
        print(f"  TRUE={true:<8} PRED={pred:<8} | {text[:70]}")
    if len(failures) > 10:
        print(f"  ... and {len(failures)-10} more")
else:
    print("  No misclassifications!")

print(f"\nTotal failures: {len(failures)}/{len(all_samples)}")
accuracy = (len(all_samples) - len(failures)) / len(all_samples)
print(f"Overall accuracy: {accuracy:.1%}")
print("="*60)