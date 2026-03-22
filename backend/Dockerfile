FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH="/root/.local/bin:${PATH}"

# System-Abhängigkeiten für PyMuPDF und CAMEL-AI
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        libgl1 \
        libglib2.0-0 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# uv installieren
RUN curl -LsSf --retry 3 --proto '=https' --tlsv1.2 \
        https://astral.sh/uv/install.sh | sh

WORKDIR /app

# Abhängigkeiten zuerst (Layer-Cache)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Anwendungscode
COPY . .

RUN mkdir -p uploads

EXPOSE 5001

CMD ["uv", "run", "python", "run.py"]
