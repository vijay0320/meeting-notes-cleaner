import torch
from transformers import T5ForConditionalGeneration, T5Tokenizer
import warnings
warnings.filterwarnings("ignore")

device = torch.device("cpu")
tokenizer = T5Tokenizer.from_pretrained("my_meeting_model_v2")
model = T5ForConditionalGeneration.from_pretrained("my_meeting_model_v2").to(device)
model.eval()

HIGH_KEYWORDS = ["asap", "urgent", "critical", "blocker", "must", "immediately", "deadline", "overdue", "risk", "high priority"]
MEDIUM_KEYWORDS = ["should", "need to", "review", "follow up", "discuss", "plan", "schedule", "decide", "will", "assigned"]

def flag_priority(text):
    text_lower = text.lower()
    if any(k in text_lower for k in HIGH_KEYWORDS):
        return "[HIGH]  "
    elif any(k in text_lower for k in MEDIUM_KEYWORDS):
        return "[MED]   "
    return "[LOW]   "

def clean_and_flag(title, raw_notes):
    input_text = f"summarize meeting notes: {raw_notes}"
    inputs = tokenizer(input_text, return_tensors="pt", max_length=256, truncation=True)
    outputs = model.generate(
        **inputs,
        max_length=200,        # increased from 150
        min_length=40,         # force longer output
        num_beams=4,
        length_penalty=2.0,    # push longer summaries
        early_stopping=True,
        no_repeat_ngram_size=2
    )
    summary = tokenizer.decode(outputs[0], skip_special_tokens=True)
    sentences = [s.strip() for s in summary.split(".") if len(s.strip()) > 10]

    print(f"\n{'='*55}")
    print(f"MEETING NOTES: {title}")
    print('='*55)
    for s in sentences:
        print(f"{flag_priority(s)} {s}.")
    print('='*55)

clean_and_flag("Budget/Engineering Notes", """
uh yeah so john mentioned the budget thing needs to be done asap,
sara said design review is next week maybe tuesday,
dev team flagged api delays as critical blocker,
marketing wants launch pushed to q2,
need to followup with legal on contract
""")

clean_and_flag("Product Meeting", """
Speaker A: So we need to decide on the remote control interface by end of week.
Speaker B: I think we should go with the simple design, costs less to manufacture.
Speaker A: Agreed. Also the battery life needs to be at least six months.
Speaker C: Marketing says the target price point is twenty five euros.
Speaker B: That means production costs cannot exceed twelve fifty.
""")

clean_and_flag("HR Meeting", """
hiring plan update - need 3 engineers by q2, recruiter said pipeline is slow,
cto flagged this as critical for roadmap delivery,
hr to post jobs this week asap,
also performance reviews overdue for 4 team members
""")
