# Meeting Notes Cleaner

A local, no-API meeting notes cleaner that takes raw messy notes and returns clean prioritized action items.

## How it works
- Fine-tuned `flan-t5-small` on the AMI Meeting Corpus + synthetic data
- Rule-based priority engine flags items as HIGH / MEDIUM / LOW
- Flask web UI — runs fully locally

## Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install torch transformers flask sentencepiece
```

## Run
```bash
python app.py
# open http://127.0.0.1:8080
```

## Retrain model (optional)
```bash
# 1. Download AMI annotations
curl -O https://groups.inf.ed.ac.uk/ami/AMICorpusAnnotations/ami_public_manual_1.6.2.zip
unzip ami_public_manual_1.6.2.zip -d ami_annotations

# 2. Generate training data
python augment_data_v2.py

# 3. Train
python train_v2.py
```

## Stack
- Model: google/flan-t5-small fine-tuned on AMI corpus
- Backend: Flask
- Frontend: Vanilla HTML/CSS/JS
