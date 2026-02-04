# Minimal container for SonarSniffer web UI + API
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

# System deps (add as needed for production like gstreamer, ffmpeg etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy project
COPY . /app

# Install Python deps
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Expose port
EXPOSE 8081

ENV SONARS_OUTPUT_DIR=/app/outputs

# Start uvicorn
CMD ["uvicorn","sonarsniffer.web:app","--host","0.0.0.0","--port","8081","--lifespan","on"]
