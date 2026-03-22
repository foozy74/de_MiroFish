# Betriebshandbuch (Runbook) -- MiroFish

**Letzte Aktualisierung:** 2026-03-20

## Deployment

### Docker-Deployment (empfohlen)

```bash
# 1. Umgebungsvariablen vorbereiten
cp .env.example .env
# .env mit LLM_API_KEY, LLM_BASE_URL, LLM_MODEL_NAME, ZEP_API_KEY befuellen

# 2. Dienste starten
docker compose up -d

# 3. Logs pruefen
docker compose logs -f mirofish
```

**Ports:**
- `3000` -- Vue-Frontend
- `5001` -- Flask-Backend-API

**Docker-Images:**
- `ghcr.io/666ghj/mirofish:latest` (Haupt-Image)
- `ghcr.nju.edu.cn/666ghj/mirofish:latest` (Spiegel fuer schnelleren Download)

### Manuelles Deployment

```bash
# Alle Abhaengigkeiten installieren
npm run setup:all

# Starten
npm run dev
```

### Produktions-Build

```bash
npm run build    # Frontend bauen (Vite)
npm run backend  # Backend separat starten
```

Fuer Produktion: Das gebaute Frontend aus `frontend/dist/` mit einem Webserver (nginx, etc.) ausliefern und das Backend als Daemon betreiben.

## Ueberwachung

### Health-Check

```bash
# Frontend erreichbar?
curl -s http://localhost:3000 | head -5

# Backend erreichbar?
curl -s http://localhost:5001/

# Docker-Status
docker compose ps
docker compose logs --tail=50 mirofish
```

### Dateien und Uploads

Hochgeladene Dateien liegen unter `backend/uploads/`. Dieses Verzeichnis wird als Docker-Volume persistiert.

## Haeufige Probleme und Loesungen

### Port bereits belegt

**Symptom:** `EADDRINUSE` (Frontend) oder `Address already in use` (Backend).

**Loesung:**
```bash
lsof -i :3000    # Frontend-Port pruefen
lsof -i :5001    # Backend-Port pruefen
kill <PID>
```

### LLM-API-Fehler

**Symptom:** Timeouts, Authentifizierungsfehler, leere Simulationsergebnisse.

**Pruefschritte:**
1. `LLM_API_KEY` in `.env` gueltig?
2. `LLM_BASE_URL` erreichbar? `curl <LLM_BASE_URL>/models`
3. `LLM_MODEL_NAME` korrekt?
4. Hinweis: Die Simulation verbraucht viele Token. Fuer erste Tests weniger als 40 Runden verwenden.

### Zep Cloud Verbindungsfehler

**Symptom:** `ZepApiError` oder Verbindungstimeout.

**Pruefschritte:**
1. `ZEP_API_KEY` gueltig? Pruefen unter https://app.getzep.com/
2. Freies monatliches Kontingent ausgeschoepft?
3. Netzwerkverbindung zu Zep Cloud vorhanden?

### Boost-LLM Konfigurationsfehler

**Symptom:** Fehler trotz korrekter Haupt-LLM-Konfiguration.

**Loesung:** Wenn die Boost-Variablen (`LLM_BOOST_*`) nicht verwendet werden, muessen sie komplett aus der `.env`-Datei entfernt werden -- nicht nur leer lassen.

### Frontend startet nicht

**Symptom:** `Module not found` oder `vite: command not found`.

**Loesung:**
```bash
npm run setup    # Node-Abhaengigkeiten neu installieren
```

### Backend startet nicht

**Symptom:** `ModuleNotFoundError` in Python.

**Loesung:**
```bash
npm run setup:backend    # Python-Abhaengigkeiten via uv sync
```

Python-Version pruefen: Es wird 3.11 oder 3.12 benoetigt.

## Rollback-Verfahren

### Docker-Rollback

```bash
# 1. Aktuelle Container stoppen
docker compose down

# 2. Aelteres Image verwenden
# In docker-compose.yml das Image-Tag aendern

# 3. Neu starten
docker compose up -d
```

### Code-Rollback

```bash
# Letzten funktionierenden Commit finden
git log --oneline -10

# Zuruecksetzen
git checkout <commit-hash>
npm run setup:all
npm run dev
```

### Upload-Daten sichern

```bash
# Backup der hochgeladenen Dateien
cp -r backend/uploads/ backup/uploads_$(date +%Y%m%d)/
```

## Sicherheitshinweise

- API-Schluessel niemals in den Code committen -- immer `.env` verwenden
- `.env` ist in `.gitignore` eingetragen
- Zep Cloud speichert Agent-Gedaechtnis extern -- Datenschutzrichtlinien beachten
- LLM-Aufrufe koennen sensible Seed-Daten enthalten -- nur vertrauenswuerdige Anbieter nutzen
- Lizenz: AGPL-3.0 -- abgeleitete Werke muessen ebenfalls unter AGPL veroeffentlicht werden
