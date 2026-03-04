FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y gcc ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install lighter dependencies first, torch separately
RUN pip install --no-cache-dir flask fastapi uvicorn python-multipart \
    sentencepiece scikit-learn rouge-score pytest pytest-flask

RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

RUN pip install --no-cache-dir transformers openai-whisper

COPY app_v2.py db.py extract_actions.py .
COPY static/ static/

EXPOSE 8080

CMD ["python", "app_v2.py"]

HEALTHCHECK --interval=30s --timeout=60s --start-period=300s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"
