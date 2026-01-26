FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .
COPY graph/ ./graph/
COPY agents/ ./agents/
COPY encoders/ ./encoders/
COPY recommender/ ./recommender/
COPY tools/ ./tools/

# Create non-root user for security (required by HF Spaces)
RUN useradd -m -u 1000 user
USER user

# HF Spaces expects port 7860
EXPOSE 7860

# Run the FastAPI app
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
