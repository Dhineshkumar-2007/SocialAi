FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create uploads directory
RUN mkdir -p uploads

# Set environment variables with defaults
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV AI_ENABLED=true
ENV SOCIALAI_SKIP_WARMUP=0
ENV DATABASE_URL=sqlite:///societal_ai.db
ENV SECRET_KEY=dev-secret-change-me
ENV UPLOAD_DIR=uploads
ENV MAX_CONTENT_LENGTH=10485760
ENV CORS_ORIGINS=*
ENV BGE_MODEL=sentence-transformers/all-MiniLM-L6-v2
ENV CLASSIFIER_MODEL=MoritzLaurer/distilbert-base-mnli
ENV VISION_MODEL=nlpconnect/vit-gpt2-image-captioning

EXPOSE 7860

CMD ["gunicorn", "-b", "0.0.0.0:7860", "--timeout", "120", "--keep-alive", "65", "--workers", "1", "--threads", "2", "--access-logfile", "-", "--error-logfile", "-", "app:app"]
