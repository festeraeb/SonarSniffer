# Minimal container for SonarSniffer web UI + API
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

# System deps (runtime tools needed for full pipeline: ffmpeg, gstreamer, and GDAL)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    git \
    ffmpeg \
    gstreamer1.0-tools \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    gdal-bin \
    libgdal-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copy only required files to keep image small
COPY requirements.txt /app/requirements.txt

# Install Python deps early so they are cached when only code changes
RUN pip install --upgrade pip && pip install --no-cache-dir -r /app/requirements.txt

# Copy source and scripts only
COPY src/ /app/src/
COPY scripts/ /app/scripts/
COPY LICENSE README.md /app/

# Expose port
EXPOSE 8081

ENV SONARS_OUTPUT_DIR=/app/outputs
ENV PYTHONPATH=/app/src

# Start uvicorn
CMD ["uvicorn","sonarsniffer.web:app","--host","0.0.0.0","--port","8081","--lifespan","on"]
