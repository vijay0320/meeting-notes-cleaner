import json
import torch
import warnings
warnings.filterwarnings("ignore")
from transformers import T5ForConditionalGeneration, T5Tokenizer
from rouge_score import rouge_scorer

print("Loading model...")
device = torch.device("cpu")
tokenizer = T5Tokenizer.from_pretrained("my_meeting_model_v2")
model = T5ForConditionalGeneration.from_pretrained("my_meeting_model_v2").to(device)
model.eval()
print("Model ready.")

with open("ami_test.json") as f:
    test_data = json.load(f)
print(f"Test samples: {len(test_data)}")

def generate_summary(input_text):
    inputs = tokenizer(
        input_text[:512], return_tensors="pt",  # limit input size
        max_length=128, truncation=True          # reduced from 256
    )
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_length=80,       # reduced from 150
            num_beams=2,         # reduced from 4
            early_stopping=True
        )
    return tokenizer.decode(outputs[0], skip_special_tokens=True)

scorer = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=True)
scores = {"rouge1": [], "rouge2": [], "rougeL": []}

for i, sample in enumerate(test_data):
    print(f"Sample {i+1}/{len(test_data)}...", flush=True)
    reference  = sample["target"]
    prediction = generate_summary(sample["input"])
    result = scorer.score(reference, prediction)
    scores["rouge1"].append(result["rouge1"].fmeasure)
    scores["rouge2"].append(result["rouge2"].fmeasure)
    scores["rougeL"].append(result["rougeL"].fmeasure)
    print(f"  ROUGE-1: {result['rouge1'].fmeasure:.3f} | pred: {prediction[:80]}", flush=True)

avg = {k: round(sum(v)/len(v), 4) for k, v in scores.items()}
print("\n" + "="*50)
print("FINAL ROUGE SCORES")
print("="*50)
print(f"ROUGE-1: {avg['rouge1']}")
print(f"ROUGE-2: {avg['rouge2']}")
print(f"ROUGE-L: {avg['rougeL']}")
