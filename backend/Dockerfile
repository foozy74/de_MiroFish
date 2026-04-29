# ─── Production Stage ─────────────────────────────────────────────────────────
FROM python:3.11-slim AS production

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONFAULTHANDLER=1 \
    UV_SYSTEM_PYTHON=1

# Non-root Benutzer erstellen (Sicherheit)
RUN groupadd --gid 1000 mirofish \
    && useradd --uid 1000 --gid mirofish --shell /bin/false --create-home mirofish

WORKDIR /app
RUN chown mirofish:mirofish /app

# Nur notwendige System-Abhängigkeiten
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        curl \
        gcc \
        python3-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# uv installieren
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Abhängigkeiten exportieren und installieren
COPY pyproject.toml uv.lock ./
RUN uv export --frozen --no-dev -o requirements.txt && \
    uv pip install --system --no-cache -r requirements.txt

# Anwendungscode kopieren
COPY --chown=mirofish:mirofish . .

# Non-root Benutzer
USER mirofish

# Erforderliche Verzeichnisse erstellen
RUN mkdir -p uploads logs

EXPOSE 5001

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:5001/health || exit 1

CMD ["python", "run.py"]
