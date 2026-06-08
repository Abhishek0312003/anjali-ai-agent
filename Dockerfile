# ── Base image — slim Python 3.11 (stable, not 3.14 edge) ──────────────────
FROM python:3.11-slim

# ── System deps ─────────────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# ── Working directory ────────────────────────────────────────────────────────
WORKDIR /app

# ── Install Python dependencies first (layer cache friendly) ─────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Copy source code ─────────────────────────────────────────────────────────
COPY app/ ./app/
COPY run.py .

# ── Non-root user for security ───────────────────────────────────────────────
RUN useradd -m -u 1000 anjali && chown -R anjali:anjali /app
USER anjali

# ── Port ─────────────────────────────────────────────────────────────────────
EXPOSE 8000

# ── Start ────────────────────────────────────────────────────────────────────
CMD ["python", "run.py"]