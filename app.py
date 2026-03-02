import warnings
warnings.filterwarnings("ignore")

from flask import Flask, render_template_string, request, jsonify
import re

app = Flask(__name__)

HIGH_KEYWORDS = ["asap", "urgent", "critical", "blocker", "block", "must", "immediately",
                 "deadline", "overdue", "risk", "high priority", "eod", "end of today",
                 "escalate", "broke", "broken", "down", "failing", "at risk"]
MEDIUM_KEYWORDS = ["should", "need", "review", "follow up", "followup", "discuss", "plan",
                   "schedule", "decide", "will", "assigned", "pending", "waiting", "requested",
                   "needs", "required", "sign off", "approval", "investigate"]

def flag_priority(text):
    t = text.lower()
    if any(k in t for k in HIGH_KEYWORDS):
        return "high"
    elif any(k in t for k in MEDIUM_KEYWORDS):
        return "medium"
    return "low"

def clean_item(text):
    """Clean up a single note item into a readable sentence."""
    # Remove leading dashes, bullets, numbers
    text = re.sub(r'^[\-\*\•\d\.\)]+\s*', '', text).strip()
    # Normalize name - action pattern "john - did X" → "John: did X"
    text = re.sub(r'^([A-Za-z]+)\s*[-:]\s*', lambda m: m.group(1).capitalize() + ': ', text)
    # Capitalize first letter
    text = text[0].upper() + text[1:] if text else text
    # Ensure ends with period
    if text and not text.endswith(('.', '!', '?')):
        text += '.'
    return text

def split_notes(raw_notes):
    """Split raw notes into individual items."""
    # Split on newlines first
    lines = raw_notes.split('\n')
    items = []
    for line in lines:
        line = line.strip()
        if not line or len(line) < 5:
            continue
        # Split long lines on semicolons
        parts = re.split(r';', line)
        for part in parts:
            part = part.strip()
            if len(part) > 5:
                items.append(part)
    return items

def process_notes(raw_notes):
    items = split_notes(raw_notes)
    results = []
    for item in items:
        priority = flag_priority(item)
        cleaned = clean_item(item)
        results.append({"text": cleaned, "priority": priority})
    # Sort high → medium → low
    order = {"high": 0, "medium": 1, "low": 2}
    results.sort(key=lambda x: order[x["priority"]])
    return results

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
  .container { max-width: 860px; margin: 0 auto; }
  h1 { font-size: 2rem; font-weight: normal; letter-spacing: -0.5px; margin-bottom: 6px; color: #fff; }
  .subtitle { color: #555; font-size: 0.85rem; margin-bottom: 36px; font-family: monospace; }
  .panel { background: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 8px; padding: 24px; margin-bottom: 20px; }
  label { display: block; font-size: 0.72rem; letter-spacing: 1.5px; text-transform: uppercase; color: #555; margin-bottom: 10px; font-family: monospace; }
  textarea { width: 100%; height: 200px; background: #111; border: 1px solid #2a2a2a; border-radius: 6px; color: #e8e8e8; font-family: monospace; font-size: 0.88rem; line-height: 1.7; padding: 14px; resize: vertical; outline: none; transition: border-color 0.2s; }
  textarea:focus { border-color: #444; }
  button { margin-top: 14px; background: #e8e8e8; color: #0f0f0f; border: none; padding: 12px 28px; border-radius: 6px; font-size: 0.85rem; font-weight: bold; cursor: pointer; transition: background 0.15s; }
  button:hover { background: #fff; }
  button:disabled { background: #2a2a2a; color: #555; cursor: not-allowed; }
  .spinner { display: none; margin-top: 14px; font-family: monospace; font-size: 0.8rem; color: #555; }
  .results { display: none; }
  .results-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
  .results-title { font-size: 0.72rem; letter-spacing: 1.5px; text-transform: uppercase; color: #555; font-family: monospace; }
  .counts { font-family: monospace; font-size: 0.75rem; }
  .counts span { margin-left: 12px; }
  .point { display: flex; align-items: flex-start; gap: 12px; padding: 13px 16px; border-radius: 6px; margin-bottom: 8px; border-left: 3px solid transparent; }
  .point.high  { background: #1f1410; border-left-color: #c0392b; }
  .point.medium{ background: #15180f; border-left-color: #8a9a2a; }
  .point.low   { background: #111820; border-left-color: #2a6a8a; }
  .badge { font-size: 0.62rem; font-family: monospace; font-weight: bold; letter-spacing: 1px; padding: 3px 8px; border-radius: 3px; white-space: nowrap; margin-top: 3px; }
  .high   .badge { background: #c0392b; color: #fff; }
  .medium .badge { background: #6a7a1a; color: #fff; }
  .low    .badge { background: #1a5a7a; color: #fff; }
  .point-text { font-size: 0.9rem; line-height: 1.5; color: #ddd; }
  .error { color: #c0392b; font-family: monospace; font-size: 0.82rem; margin-top: 12px; }
</style>
</head>
<body>
<div class="container">
  <h1>Meeting Notes Cleaner</h1>
  <p class="subtitle">paste raw notes &mdash; one item per line &mdash; get clean prioritized output</p>

  <div class="panel">
    <label>Raw Meeting Notes</label>
    <textarea id="notes" placeholder="One item per line, e.g.:&#10;&#10;john - finished auth module, pushing to staging today&#10;priya - blocked on API spec, needs it asap or sprint is at risk&#10;deployment pipeline broke last night, critical blocker&#10;design review thursday, needs product sign off&#10;marketing assets overdue, end of today deadline"></textarea>
    <button id="btn" onclick="processNotes()">Clean Notes &rarr;</button>
    <div class="spinner" id="spinner">processing...</div>
    <div class="error" id="error"></div>
  </div>

  <div class="panel results" id="results">
    <div class="results-header">
      <span class="results-title">Cleaned Output</span>
      <span class="counts" id="counts"></span>
    </div>
    <div id="output"></div>
  </div>
</div>

<script>
async function processNotes() {
  const notes = document.getElementById('notes').value.trim();
  if (!notes) return;
  const btn = document.getElementById('btn');
  const spinner = document.getElementById('spinner');
  const error = document.getElementById('error');
  const results = document.getElementById('results');

  btn.disabled = true;
  spinner.style.display = 'block';
  error.textContent = '';
  results.style.display = 'none';

  try {
    const res = await fetch('/process', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({notes})
    });
    const data = await res.json();
    if (data.error) throw new Error(data.error);

    const high = data.points.filter(p => p.priority === 'high').length;
    const med  = data.points.filter(p => p.priority === 'medium').length;
    const low  = data.points.filter(p => p.priority === 'low').length;
    document.getElementById('counts').innerHTML =
      `<span style="color:#c0392b">${high} high</span>` +
      `<span style="color:#8a9a2a">${med} medium</span>` +
      `<span style="color:#2a6a8a">${low} low</span>`;

    document.getElementById('output').innerHTML = data.points.map(p => `
      <div class="point ${p.priority}">
        <span class="badge">${p.priority.toUpperCase()}</span>
        <span class="point-text">${p.text}</span>
      </div>
    `).join('');

    results.style.display = 'block';
  } catch(e) {
    error.textContent = 'Error: ' + e.message;
  } finally {
    btn.disabled = false;
    spinner.style.display = 'none';
  }
}
document.getElementById('notes').addEventListener('keydown', e => {
  if (e.key === 'Enter' && e.ctrlKey) processNotes();
});
</script>
</body>
</html>
"""

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
        points = process_notes(notes)
        return jsonify({"points": points})
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == "__main__":
    print("Starting at http://127.0.0.1:8080")
    app.run(debug=False, port=8080, host='127.0.0.1')