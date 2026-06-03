# Aut_Sci_Write Docker Image
# Multi-stage build for optimized image size

# Stage 1: Build dependencies
FROM swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/python:3.11-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 20 LTS
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g npm@latest

WORKDIR /build

# Copy dependency files first (for layer caching)
COPY requirements.txt package.json ./

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Install Node.js dependencies (no lock file exists)
RUN npm install --production --ignore-scripts

# Stage 2: Runtime image
FROM swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr tesseract-ocr-eng tesseract-ocr-chi-sim \
    libgl1-mesa-glx libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js (runtime only)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 scientist && \
    mkdir -p /app /data && \
    chown -R scientist:scientist /app /data

WORKDIR /app

# Copy Python packages from builder
COPY --from=builder --chown=scientist:scientist /root/.local /home/scientist/.local

# Copy application files
COPY --chown=scientist:scientist . .

# Make entrypoint executable
RUN chmod +x /app/docker-entrypoint.sh

# Set environment variables
ENV PATH="/home/scientist/.local/bin:${PATH}" \
    TESSERACT_CMD="/usr/bin/tesseract" \
    PYTHONUNBUFFERED=1 \
    NODE_ENV=production

USER scientist

# Initialize .env files
RUN node init-env.js

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" && node -e "process.exit(0)"

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["/bin/bash"]
