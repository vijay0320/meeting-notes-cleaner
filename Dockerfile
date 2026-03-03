# Use Python 3.11 slim as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (layer caching — only reinstalls if requirements change)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy app files
COPY app_v2.py db.py benchmark.py rouge_eval.py .
COPY augment_data_v2.py train_v2.py infer_v2.py .
COPY README.md .

# Expose port
EXPOSE 8080

# Run the app
CMD ["python", "app_v2.py"]
