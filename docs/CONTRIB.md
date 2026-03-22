# Entwickler-Handbuch -- MiroFish

**Letzte Aktualisierung:** 2026-03-20

## Voraussetzungen

| Werkzeug | Version | Zweck |
|----------|---------|-------|
| Node.js | 18+ | Frontend-Laufzeit (inkl. npm) |
| Python | 3.11 -- 3.12 | Backend-Laufzeit |
| uv | aktuell | Python-Paketverwaltung |
| Docker (optional) | aktuell | Container-Deployment |

## Umgebung einrichten

### 1. Repository klonen und Verzeichnis wechseln

```bash
git clone <repository-url>
cd de_MiroFish
```

### 2. Umgebungsvariablen konfigurieren

```bash
cp .env.example .env
```

Pflichtfelder in `.env`:

| Variable | Beschreibung |
|----------|-------------|
| `LLM_API_KEY` | API-Schluessel fuer LLM (OpenAI-Format) |
| `LLM_BASE_URL` | API-Endpunkt (Standard: Alibaba DashScope) |
| `LLM_MODEL_NAME` | Modellname (empfohlen: `qwen-plus`) |
| `ZEP_API_KEY` | Zep Cloud fuer Agent-Gedaechtnis |

Optionale Felder:

| Variable | Beschreibung |
|----------|-------------|
| `LLM_BOOST_API_KEY` | Beschleunigtes LLM (separater Anbieter) |
| `LLM_BOOST_BASE_URL` | Endpunkt fuer Boost-LLM |
| `LLM_BOOST_MODEL_NAME` | Modellname fuer Boost-LLM |

Hinweis: Wenn die Boost-Variablen nicht benoetigt werden, diese Zeilen komplett aus der `.env` entfernen (nicht nur leer lassen).

### 3. Abhaengigkeiten installieren

**Alles auf einmal:**
```bash
npm run setup:all
```

**Oder schrittweise:**
```bash
npm run setup           # Root + Frontend (Node.js)
npm run setup:backend   # Backend (Python via uv)
```

## Verfuegbare npm-Skripte

| Skript | Befehl | Beschreibung |
|--------|--------|-------------|
| `setup` | `npm install && cd frontend && npm install` | Node-Abhaengigkeiten installieren |
| `setup:backend` | `cd backend && uv sync` | Python-Abhaengigkeiten installieren |
| `setup:all` | `npm run setup && npm run setup:backend` | Alle Abhaengigkeiten installieren |
| `dev` | `concurrently ...` | Frontend + Backend gleichzeitig starten |
| `backend` | `cd backend && uv run python run.py` | Nur Backend starten |
| `frontend` | `cd frontend && npm run dev` | Nur Frontend starten |
| `build` | `cd frontend && npm run build` | Frontend fuer Produktion bauen |

## Entwicklungs-Workflow

### Dienste starten

```bash
# Frontend + Backend gleichzeitig (empfohlen)
npm run dev

# Einzeln starten
npm run backend    # Backend auf http://localhost:5001
npm run frontend   # Frontend auf http://localhost:3000
```

### Frontend bauen

```bash
npm run build
```

Das Frontend nutzt Vue 3 + Vite + vue-router + d3 + axios.

## Projektstruktur

```
de_MiroFish/
  package.json          # Root-npm-Konfiguration (concurrently)
  docker-compose.yml    # Docker-Konfiguration
  Dockerfile            # Multi-Stage Docker Build
  .env.example          # Umgebungsvariablen-Vorlage
  frontend/             # Vue 3 + Vite (Port 3000)
    src/                # Vue-Quellcode
    public/             # Statische Dateien
    vite.config.js      # Vite-Konfiguration
    package.json        # Frontend-Abhaengigkeiten
  backend/              # Flask API (Port 5001)
    app/                # Hauptanwendungs-Module
    run.py              # Einstiegspunkt
    scripts/            # Hilfsskripte
    pyproject.toml      # Python-Abhaengigkeiten (uv/hatch)
    uv.lock             # Gesperrte Abhaengigkeiten
  static/               # Statische Medien
```

### Wichtige Backend-Abhaengigkeiten

| Paket | Zweck |
|-------|-------|
| `flask` + `flask-cors` | Web-Framework + CORS |
| `openai` | LLM-API-Client (OpenAI-kompatibles Format) |
| `camel-oasis` + `camel-ai` | OASIS Schwarm-Simulations-Engine |
| `zep-cloud` | Agent-Gedaechtnis und -Graphen |
| `PyMuPDF` | PDF/Dokument-Verarbeitung |
| `pydantic` | Datenvalidierung |

## Tests

### Backend-Tests

```bash
cd backend
uv run pytest -v

# Mit async-Unterstuetzung
uv run pytest --asyncio-mode=auto -v
```

Dev-Abhaengigkeiten installieren:
```bash
cd backend
uv sync --group dev
```

## Branch- und Commit-Konventionen

- Branch-Benennung: `feature/xxx`, `fix/xxx`, `docs/xxx`
- Commit-Format: [Conventional Commits](https://www.conventionalcommits.org/)
- Ziel-Branch fuer PRs: `main`

## Docker-Entwicklung

```bash
cp .env.example .env
docker compose up -d
```

Dienste:
- `mirofish` -- Gesamte Anwendung (Ports 3000 + 5001)

Volume: `backend/uploads/` wird persistiert.

Lizenz: AGPL-3.0
