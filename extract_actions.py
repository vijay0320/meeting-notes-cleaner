import re

ACTION_VERBS = [
    "will", "need to", "needs to", "must", "should", "going to",
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

def extract_speaker_lines(transcript):
    lines = transcript.strip().split('\n')
    speaker_lines = []
    for line in lines:
        line = line.strip()
        m = SPEAKER_PATTERN.match(line)
        if m:
            speaker = m.group(1)
            text = m.group(2).strip()
            speaker_lines.append((speaker, text))
    return speaker_lines

def has_action(text):
    text_lower = text.lower()
    has_verb = any(verb in text_lower for verb in ACTION_VERBS)
    has_deadline = any(d in text_lower for d in DEADLINE_WORDS)
    is_question = text.strip().endswith('?')
    is_short = len(text.split()) < 6
    return (has_verb or has_deadline) and not is_question and not is_short

def normalize_pronouns(text, speaker):
    text = re.sub(r"\bI'll\b", f"{speaker} will", text)
    text = re.sub(r"\bI will\b", f"{speaker} will", text)
    text = re.sub(r"\bI can\b", f"{speaker} can", text)
    text = re.sub(r"\bI'd\b", f"{speaker} would", text)
    text = re.sub(r"\bmy\b", f"{speaker}'s", text)
    text = re.sub(r"\bWe'll\b", "the team will", text)
    text = re.sub(r"\bwe'll\b", "the team will", text)
    text = re.sub(r"\bwe will\b", "the team will", text)
    text = re.sub(r"\bwe need\b", "the team needs", text)
    text = re.sub(r"\bwe may\b", "the team may", text)
    text = re.sub(r"\bwe can\b", "the team can", text)
    text = re.sub(r"\bour\b", "the team's", text)
    return text

def extract_action_items(transcript):
    speaker_lines = extract_speaker_lines(transcript)
    action_items = []
    seen = set()

    for speaker, text in speaker_lines:
        if has_action(text):
            normalized = normalize_pronouns(text, speaker)
            # Deduplicate
            key = normalized[:50].lower()
            if key not in seen:
                seen.add(key)
                action_items.append({
                    "speaker": speaker,
                    "raw": text,
                    "text": normalized
                })

    return action_items

if __name__ == "__main__":
    transcript = open('test_transcript.txt').read() if __import__('os').path.exists('test_transcript.txt') else """Jordan: From the engineering side we've been focusing mainly on the API integration work. The current estimate is that we'll need about two additional weeks before everything is stable enough for wider testing.
Alex: If the launch timeline shifts by two weeks, we may need to adjust the marketing schedule as well.
Jordan: If analytics usage continues to grow, we may need to optimize some of the query performance.
Jordan: I'll review the engineering backlog and see what changes we can make without affecting the integration work.
Priya: I can also run another analysis on where users drop off during onboarding.
Alex: I'll prepare a draft campaign proposal before the next meeting.
Sarah: So maybe we should add onboarding improvements as a short-term priority."""

    items = extract_action_items(transcript)
    for item in items:
        print(f"[{item['speaker']}] {item['text']}")
