FROM python:3.11-slim AS backend

# Install system dependencies including Node.js
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    portaudio19-dev \
    ffmpeg \
    alsa-utils \
    pulseaudio \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and build whisper.cpp
COPY whisper.cpp/ ./whisper.cpp/
WORKDIR /app/whisper.cpp
RUN make

# Back to app directory
WORKDIR /app

# Copy Python requirements and install
COPY requirements.txt* ./
RUN pip install --no-cache-dir -r requirements.txt || pip install fastapi uvicorn websockets python-multipart aiofiles

# Copy Python source code
COPY src/ ./src/
COPY configs/ ./configs/
COPY scripts/ ./scripts/

# Create output directories
RUN mkdir -p output/batch output/hybrid output/live output/.transient

# Set permissions
RUN chmod +x scripts/*.sh

# Expose ports
EXPOSE 8000 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command - run both backend
CMD ["sh", "-c", "cd /app/src && python api_server.py"]
