# Multi-Tenancy Implementierungsanleitung für MiroFish

## Zusammenfassung

MiroFish verfügt bereits über eine **vollständige Multi-Tenant-Infrastruktur**, die jedoch **teilweise inaktiv** ist. Dieses Dokument beschreibt den aktuellen Stand und die notwendigen Schritte zur vollständigen Aktivierung.

---

## 📊 Aktueller Implementierungsstand

### ✅ Bereits implementiert (Phase 1 abgeschlossen)

| Komponente | Status | Datei(en) |
|------------|--------|-----------|
| **JWT-Authentifizierung** | ✅ Vollständig | `app/tenant/jwt_validator.py` |
| **Tenant-Middleware** | ✅ Vollständig | `app/tenant/middleware.py` |
| **Tenant-Kontext** | ✅ Vollständig | `app/tenant/context.py` |
| **Config-Proxy** | ✅ Vollständig | `app/tenant/settings_override.py` |
| **API-Key Verschlüsselung** | ✅ Vollständig (AES-256-GCM) | `app/tenant/crypto.py` |
| **Datenbankzugriff** | ✅ Vollständig | `app/tenant/db.py` |
| **Self-Service API** | ✅ Vollständig | `app/api/tenant.py` |
| **Frontend Einstellungen** | ✅ Vollständig | `frontend/src/views/TenantSettingsView.vue` |

### ⚠️ Noch nicht aktiviert

| Bereich | Status | Problem |
|---------|--------|---------|
| API-Routen (`/api/simulation/*`) | ❌ Kein Tenant-Schutz | `@require_tenant` fehlt |
| API-Routen (`/api/report/*`) | ❌ Kein Tenant-Schutz | `@require_tenant` fehlt |
| API-Routen (`/api/graph/*`) | ❌ Kein Tenant-Schutz | `@require_tenant` fehlt |
| Services verwenden Config | ❌ Direkter Zugriff | `from ..config import Config` statt `TenantConfig` |
| Frontend API-Client | ❌ Keine Auth-Header | Axios-Interceptor leer |
| LLMClient | ⚠️ Falsche Config-Keys | `Config.OPENROUTER_*` existieren nicht |

---

## 🏗️ Architektur-Übersicht

### Tenant-Isolation Modell

```
┌─────────────────────────────────────────────────────────────┐
│                     Clerk Authentication                    │
│  (JWT mit org_id, org_slug, exp, sub Claims)                │
└────────────────────┬────────────────────────────────────────┘
                     │ Bearer Token
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Flask Request (mit @require_tenant)            │
│  1. JWT validieren (JWKS, RS256)                            │
│  2. org_id extrahieren                                      │
│  3. Tenant aus shared.tenants laden                         │
│  4. API-Keys entschlüsseln                                  │
│  5. flask.g.tenant = TenantContext                          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                 Service Layer (TenantConfig)                │
│  cfg = TenantConfig()                                       │
│  cfg.LLM_API_KEY  → Tenant-Override oder System-Default     │
│  cfg.ZEP_API_KEY  → Tenant-Override oder System-Default     │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Datenbank (PostgreSQL mit Schemas)             │
│  - shared.tenants (alle Mandanten)                          │
│  - shared.tenant_api_keys (verschlüsselte Keys)             │
│  - tenant_<schema>.simulations (Mandantendaten)             │
│  - tenant_<schema>.reports (Mandantendaten)                 │
└─────────────────────────────────────────────────────────────┘
```

### Datenbank-Schema

```sql
-- Shared Schema (alle Mandanten)
CREATE SCHEMA IF NOT EXISTS shared;

-- Tenant-Metadaten
CREATE TABLE shared.tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clerk_org_id TEXT UNIQUE NOT NULL,      -- z.B. "org_abc123"
    clerk_org_slug TEXT NOT NULL,            -- z.B. "meine-firma"
    display_name TEXT NOT NULL,
    schema_name TEXT UNIQUE NOT NULL,        -- z.B. "tenant_meine_firma"
    plan TEXT NOT NULL DEFAULT 'free',       -- free/starter/pro/enterprise
    status TEXT NOT NULL DEFAULT 'active',   -- active/suspended
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tenant API-Keys (verschlüsselt)
CREATE TABLE shared.tenant_api_keys (
    tenant_id UUID REFERENCES shared.tenants(id) ON DELETE CASCADE,
    key_name TEXT NOT NULL,                   -- z.B. "LLM_API_KEY"
    encrypted_value BYTEA NOT NULL,           -- AES-256-GCM verschlüsselt
    iv BYTEA NOT NULL,                        -- 12-byte Nonce
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (tenant_id, key_name)
);

-- Usage Limits pro Plan
CREATE TABLE shared.usage_limits (
    plan TEXT NOT NULL,
    service TEXT NOT NULL,                    -- "mirofish" | "bettafish"
    metric TEXT NOT NULL,                     -- "simulations_run" | "reports_generated"
    monthly_max INT NOT NULL,                 -- -1 für unbegrenzt
    PRIMARY KEY (plan, service, metric)
);

-- Daily Usage Tracking
CREATE TABLE shared.usage_daily (
    tenant_id UUID REFERENCES shared.tenants(id) ON DELETE CASCADE,
    service TEXT NOT NULL,
    metric TEXT NOT NULL,
    date DATE NOT NULL,
    value INT NOT NULL DEFAULT 0,
    PRIMARY KEY (tenant_id, service, metric, date),
    CHECK (date >= date_trunc('month', CURRENT_DATE))
);

-- Tenant-Schema (pro Mandant)
CREATE SCHEMA tenant_<name>;
-- Tabellen: simulations, reports, graphs, etc.
```

---

## 🔧 Implementierungsschritte

### Phase 1: LLMClient für TenantConfig kompatibilisieren

**Problem:** `LLMClient` verwendet `Config.OPENROUTER_*`, diese Keys existieren nicht.

**Lösung:** `LLMClient` so ändern, dass er `TenantConfig` verwendet.

#### Schritt 1.1: `app/utils/llm_client.py` aktualisieren

```python
"""
LLM-Client-Konfiguration
"""

import json
import re
from typing import Optional, Dict, Any, List
from openai import OpenAI

# NICHT mehr: from ..config import Config


class LLMClient:
    """LLM-Client mit TenantConfig-Unterstützung"""
    
    def __init__(
        self,
        api_key: str = None,
        base_url: str = None,
        model: str = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        timeout: int = 120
    ):
        """
        Initialisiert den LLM-Client.
        
        Priorität:
        1. Explizite Parameter (api_key, base_url, model)
        2. TenantConfig (wenn in Flask-Request)
        3. System-Defaults (app.config.Config)
        """
        # Lazy Import um Zirkelabhängigkeiten zu vermeiden
        from app.tenant.settings_override import TenantConfig
        
        cfg = TenantConfig()
        
        self.api_key = api_key or cfg.LLM_API_KEY
        self.base_url = base_url or cfg.LLM_BASE_URL
        self.model = model or cfg.LLM_MODEL_NAME
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        
        if not self.api_key:
            raise ValueError("LLM_API_KEY ist nicht konfiguriert")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout
        )
    
    # ... restliche Methoden unverändert (chat, chat_json)
```

**Änderungen:**
- `from ..config import Config` entfernen
- `TenantConfig` lazy importieren
- Fallback-Kette: Parameter → TenantConfig → Config
- Validierung hinzufügen

---

### Phase 2: Services auf TenantConfig umstellen

Alle Services die `Config.*` verwenden müssen auf `TenantConfig()` umgestellt werden.

#### Schritt 2.1: Betroffene Dateien identifizieren

```bash
# Suche nach Config-Verwendung in Services
grep -rn "from ..config import Config" backend/app/services/
```

**Betroffene Dateien:**
1. `app/services/graph_builder.py:16`
2. `app/services/oasis_profile_generator.py:21`
3. `app/services/report_agent.py:21`
4. `app/services/simulation_config_generator.py:23`
5. `app/services/simulation_manager.py:15`
6. `app/services/simulation_runner.py:21`
7. `app/services/zep_entity_reader.py:12`
8. `app/services/zep_graph_memory_updater.py:17`
9. `app/services/zep_tools.py:18`

#### Schritt 2.2: Beispiel-Refactoring für `graph_builder.py`

**Vorher:**
```python
from ..config import Config

class GraphBuilderService:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or Config.ZEP_API_KEY
        if not self.api_key:
            raise ValueError("ZEP_API_KEY ist nicht konfiguriert")
        self.client = Zep(api_key=self.api_key)
```

**Nachher:**
```python
from app.tenant.settings_override import TenantConfig

class GraphBuilderService:
    def __init__(self, api_key: Optional[str] = None):
        cfg = TenantConfig()
        self.api_key = api_key or cfg.ZEP_API_KEY
        if not self.api_key:
            raise ValueError("ZEP_API_KEY ist nicht konfiguriert")
        self.client = Zep(api_key=self.api_key)
```

#### Schritt 2.3: Refactoring für `oasis_profile_generator.py`

**Vorher:**
```python
from ..config import Config

class OasisProfileGenerator:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        zep_api_key: Optional[str] = None
    ):
        self.api_key = api_key or Config.LLM_API_KEY
        self.base_url = base_url or Config.LLM_BASE_URL
        self.model_name = model_name or Config.LLM_MODEL_NAME
        self.zep_api_key = zep_api_key or Config.ZEP_API_KEY
```

**Nachher:**
```python
from app.tenant.settings_override import TenantConfig

class OasisProfileGenerator:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        zep_api_key: Optional[str] = None
    ):
        cfg = TenantConfig()
        self.api_key = api_key or cfg.LLM_API_KEY
        self.base_url = base_url or cfg.LLM_BASE_URL
        self.model_name = model_name or cfg.LLM_MODEL_NAME
        self.zep_api_key = zep_api_key or cfg.ZEP_API_KEY
```

#### Schritt 2.4: Refactoring für `zep_tools.py`

**Vorher:**
```python
from ..config import Config

class ZepToolsService:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or Config.ZEP_API_KEY
        self._llm_client = LLMClient()  # LLMClient verwendet jetzt TenantConfig
```

**Nachher:**
```python
from app.tenant.settings_override import TenantConfig

class ZepToolsService:
    def __init__(self, api_key: Optional[str] = None):
        cfg = TenantConfig()
        self.api_key = api_key or cfg.ZEP_API_KEY
        self._llm_client = LLMClient()  # LLMClient verwendet jetzt TenantConfig
```

**Hinweis:** `report_agent.py`, `simulation_config_generator.py` verwenden `Config` nur für Pfade (`Config.UPLOAD_FOLDER`), diese müssen **nicht** geändert werden.

---

### Phase 3: API-Routen mit Tenant-Schutz versehen

#### Schritt 3.1: `app/api/simulation.py` schützen

**Änderungen am Datei-Anfang:**
```python
# Hinzufügen nach den Imports:
from app.tenant.middleware import require_tenant
```

**Alle Routen-Funktionen mit `@require_tenant` dekorieren:**

```python
@simulation_bp.route('/entities/<graph_id>', methods=['GET'])
@require_tenant  # ← Hinzufügen
def get_graph_entities(graph_id: str):
    ...

@simulation_bp.route('/create', methods=['POST'])
@require_tenant  # ← Hinzufügen
def create_simulation():
    # Zugriff auf Tenant-Kontext:
    from flask import g
    tenant = g.tenant  # TenantContext
    schema = tenant.schema_name
    ...

@simulation_bp.route('/start', methods=['POST'])
@require_tenant  # ← Hinzufügen
def start_simulation():
    ...
```

**Betroffene Routen (ca. 20 Funktionen):**
- `get_graph_entities`
- `get_entity_detail`
- `get_entities_by_type`
- `create_simulation`
- `prepare_simulation`
- `get_prepare_status`
- `get_simulation`
- `list_simulations`
- `get_simulation_history`
- `get_simulation_profiles`
- `get_simulation_profiles_realtime`
- `get_simulation_config_realtime`
- `get_simulation_config`
- `download_simulation_config`
- `download_simulation_script`
- `generate_profiles`
- `start_simulation`
- `stop_simulation`
- `get_run_status`
- ... (alle weiteren Routen)

#### Schritt 3.2: `app/api/report.py` schützen

Gleiche Vorgehensweise wie bei `simulation.py`:

```python
from app.tenant.middleware import require_tenant

@report_bp.route('/generate', methods=['POST'])
@require_tenant
def generate_report():
    ...

@report_bp.route('/<report_id>', methods=['GET'])
@require_tenant
def get_report(report_id: str):
    ...
```

**Betroffene Routen (ca. 15 Funktionen):**
- `generate_report`
- `get_generate_status`
- `get_report`
- `get_report_by_simulation`
- `list_reports`
- `download_report`
- `delete_report`
- `chat_with_report_agent`
- `get_report_progress`
- `get_report_sections`
- `get_single_section`
- `check_report_status`
- `get_agent_log`
- `stream_agent_log`
- `get_console_log`
- `stream_console_log`
- `search_graph_tool`
- `get_graph_statistics_tool`

#### Schritt 3.3: `app/api/graph.py` schützen

```python
from app.tenant.middleware import require_tenant

@graph_bp.route('/project/<project_id>', methods=['GET'])
@require_tenant
def get_project(project_id: str):
    ...
```

**Betroffene Routen (ca. 10 Funktionen):**
- `get_project`
- `list_projects`
- `delete_project`
- `reset_project`
- `generate_ontology`
- `build_graph`
- `get_task`
- `list_tasks`
- `get_graph_data`
- `delete_graph`

---

### Phase 4: Frontend API-Client für Auth aktualisieren

#### Schritt 4.1: `frontend/src/api/index.js` aktualisieren

**Vorher:**
```javascript
// Request-Interceptor (leer)
service.interceptors.request.use(
  config => {
    return config
  },
  error => {
    console.error('Request error:', error)
    return Promise.reject(error)
  }
)
```

**Nachher:**
```javascript
// Request-Interceptor mit Auth-Header
service.interceptors.request.use(
  config => {
    // Clerk JWT aus localStorage oder Cookie holen
    const token = localStorage.getItem('clerk_session_token')
    
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    
    return config
  },
  error => {
    console.error('Request error:', error)
    return Promise.reject(error)
  }
)
```

#### Schritt 4.2: Clerk Session-Token speichern

Falls noch nicht vorhanden, muss das Frontend das Clerk-Token speichern.

**In `frontend/src/main.js` oder Auth-Provider:**
```javascript
import { useAuth } from '@clerk/clerk-vue'

// In der App-Initialisierung
const { getToken } = useAuth()

// Token beim Start speichern
const token = await getToken()
if (token) {
  localStorage.setItem('clerk_session_token', token)
}

// Token bei jedem Wechsel aktualisieren
watchEffect(async () => {
  const token = await getToken()
  if (token) {
    localStorage.setItem('clerk_session_token', token)
  } else {
    localStorage.removeItem('clerk_session_token')
  }
})
```

#### Schritt 4.3: Auth-Error-Handling

**Response-Interceptor erweitern:**
```javascript
service.interceptors.response.use(
  response => {
    const res = response.data
    if (!res.success && res.success !== undefined) {
      console.error('API Error:', res.error || res.message || 'Unknown error')
      return Promise.reject(new Error(res.error || res.message || 'Error'))
    }
    return res
  },
  error => {
    console.error('Response error:', error)
    
    // 401 = Token abgelaufen oder ungültig
    if (error.response?.status === 401) {
      console.error('Authentifizierung fehlgeschlagen - bitte neu anmelden')
      // Optional: Redirect zu Login
      // router.push('/login')
    }
    
    // 403 = Tenant nicht gefunden oder gesperrt
    if (error.response?.status === 403) {
      console.error('Zugriff verweigert - keine Berechtigung')
    }
    
    return Promise.reject(error)
  }
)
```

---

### Phase 5: Datenbank-Migration für Tenant-Schemas

#### Schritt 5.1: Migrationsskript erstellen

Erstelle `backend/migrations/001_multi_tenant.sql`:

```sql
-- Multi-Tenancy Schema-Migration
-- Ausführen mit: psql $DATABASE_URL -f backend/migrations/001_multi_tenant.sql

BEGIN;

-- 1. Shared Schema erstellen
CREATE SCHEMA IF NOT EXISTS shared;

-- 2. Tenants Tabelle
CREATE TABLE IF NOT EXISTS shared.tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clerk_org_id TEXT UNIQUE NOT NULL,
    clerk_org_slug TEXT NOT NULL,
    display_name TEXT NOT NULL,
    schema_name TEXT UNIQUE NOT NULL,
    plan TEXT NOT NULL DEFAULT 'free',
    status TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_tenants_clerk_org_id ON shared.tenants(clerk_org_id);
CREATE INDEX idx_tenants_status ON shared.tenants(status);

-- 3. Tenant API Keys
CREATE TABLE IF NOT EXISTS shared.tenant_api_keys (
    tenant_id UUID REFERENCES shared.tenants(id) ON DELETE CASCADE,
    key_name TEXT NOT NULL,
    encrypted_value BYTEA NOT NULL,
    iv BYTEA NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (tenant_id, key_name)
);

-- 4. Usage Limits
CREATE TABLE IF NOT EXISTS shared.usage_limits (
    plan TEXT NOT NULL,
    service TEXT NOT NULL,
    metric TEXT NOT NULL,
    monthly_max INT NOT NULL,
    PRIMARY KEY (plan, service, metric)
);

-- Default Limits einfügen
INSERT INTO shared.usage_limits (plan, service, metric, monthly_max) VALUES
    ('free', 'mirofish', 'simulations_run', 5),
    ('free', 'mirofish', 'reports_generated', 2),
    ('starter', 'mirofish', 'simulations_run', 20),
    ('starter', 'mirofish', 'reports_generated', 10),
    ('pro', 'mirofish', 'simulations_run', 100),
    ('pro', 'mirofish', 'reports_generated', 50),
    ('enterprise', 'mirofish', 'simulations_run', -1),
    ('enterprise', 'mirofish', 'reports_generated', -1)
ON CONFLICT (plan, service, metric) DO NOTHING;

-- 5. Daily Usage Tracking
CREATE TABLE IF NOT EXISTS shared.usage_daily (
    tenant_id UUID REFERENCES shared.tenants(id) ON DELETE CASCADE,
    service TEXT NOT NULL,
    metric TEXT NOT NULL,
    date DATE NOT NULL,
    value INT NOT NULL DEFAULT 0,
    PRIMARY KEY (tenant_id, service, metric, date)
);

CREATE INDEX idx_usage_daily_tenant_date ON shared.usage_daily(tenant_id, date);

-- 6. Trigger für automatische Updated-Aktualisierung
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tenants_updated_at
    BEFORE UPDATE ON shared.tenants
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER tenant_api_keys_updated_at
    BEFORE UPDATE ON shared.tenant_api_keys
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMIT;
```

#### Schritt 5.2: Tenant-Schema für existierende Daten

Falls bereits Daten in `public` existieren:

```sql
-- Bestehende Tabellen in Tenant-Schema verschieben
-- Beispiel für ersten Tenant:

-- 1. Tenant erstellen
INSERT INTO shared.tenants (clerk_org_id, clerk_org_slug, display_name, schema_name, plan)
VALUES ('org_default', 'default', 'Default Tenant', 'tenant_default', 'free');

-- 2. Schema erstellen
CREATE SCHEMA IF NOT EXISTS tenant_default;

-- 3. Tabellen duplizieren (Struktur kopieren)
CREATE TABLE tenant_default.simulations (LIKE public.simulations INCLUDING ALL);
CREATE TABLE tenant_default.reports (LIKE public.reports INCLUDING ALL);
CREATE TABLE tenant_default.graphs (LIKE public.graphs INCLUDING ALL);

-- 4. Daten migrieren (optional)
INSERT INTO tenant_default.simulations SELECT * FROM public.simulations;
INSERT INTO tenant_default.reports SELECT * FROM public.reports;
INSERT INTO tenant_default.graphs SELECT * FROM public.graphs;

-- 5. search_path setzen für Migration
SET search_path TO tenant_default, shared, public;
```

---

### Phase 6: Usage Tracking implementieren

#### Schritt 6.1: Usage-Counter in Services

In `app/services/simulation_runner.py`:

```python
from app.tenant.db import increment_usage

class SimulationRunner:
    def start_simulation(self, simulation_id: str, ...):
        # Tenant-Kontext holen
        from flask import g
        tenant = g.tenant
        
        # Usage incrementieren
        increment_usage(
            tenant_id=tenant.tenant_id,
            service='mirofish',
            metric='simulations_run',
            value=1
        )
        
        # ... restliche Logik
```

Helper-Funktion in `app/tenant/db.py` hinzufügen:

```python
def increment_usage(tenant_id: str, service: str, metric: str, value: int = 1) -> None:
    """Inkrementiert den täglichen Usage-Counter."""
    import psycopg
    
    try:
        with psycopg.connect(_get_db_url()) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO shared.usage_daily
                        (tenant_id, service, metric, date, value)
                    VALUES (%s, %s, %s, CURRENT_DATE, %s)
                    ON CONFLICT (tenant_id, service, metric, date)
                    DO UPDATE SET value = usage_daily.value + EXCLUDED.value
                    """,
                    (tenant_id, service, metric, value),
                )
            conn.commit()
    except Exception as exc:
        logger.error(f"Usage-Inkrement fehlgeschlagen: {exc}")
        # Nicht werfen - Usage-Tracking sollte nicht die Hauptfunktion blockieren
```

#### Schritt 6.2: Usage-Limits prüfen

Decorator für API-Routen:

```python
from functools import wraps
from flask import g, jsonify

def check_usage_limit(service: str, metric: str):
    """Prüft ob Usage-Limit erreicht ist."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            tenant = g.tenant
            
            # Aktuellen Verbrauch holen
            usage = get_tenant_usage(tenant.tenant_id, tenant.plan)
            for u in usage:
                if u['service'] == service and u['metric'] == metric:
                    if u['limit'] != -1 and u['current'] >= u['limit']:
                        return jsonify({
                            'error': 'Usage-Limit erreicht',
                            'current': u['current'],
                            'limit': u['limit'],
                            'upgrade_url': '/settings'
                        }), 429
            
            return f(*args, **kwargs)
        return decorated
    return decorator

# Verwendung:
@simulation_bp.route('/start', methods=['POST'])
@require_tenant
@check_usage_limit('mirofish', 'simulations_run')
def start_simulation():
    ...
```

---

## 🧪 Tests

### Unit-Tests für TenantConfig

```python
# backend/tests/test_tenant_config.py

import pytest
from unittest.mock import Mock, patch
from flask import Flask, g

from app.tenant.settings_override import TenantConfig
from app.tenant.context import TenantContext


class TestTenantConfig:
    
    def test_tenant_config_without_context(self):
        """TenantConfig ohne Flask-Kontext fällt auf Config zurück"""
        cfg = TenantConfig()
        assert cfg.LLM_API_KEY is not None  # System-Default
    
    def test_tenant_config_with_override(self):
        """TenantConfig mit Override verwendet Tenant-Wert"""
        app = Flask(__name__)
        with app.app_context():
            with app.test_request_context():
                g.tenant = TenantContext(
                    tenant_id='test-uuid',
                    org_id='org_test',
                    org_slug='test-org',
                    display_name='Test Org',
                    schema_name='tenant_test',
                    plan='pro',
                    config_overrides={'LLM_API_KEY': 'sk-tenant-key'}
                )
                
                cfg = TenantConfig()
                assert cfg.LLM_API_KEY == 'sk-tenant-key'
    
    def test_tenant_config_partial_override(self):
        """TenantConfig mit teilweisem Override"""
        app = Flask(__name__)
        with app.app_context():
            with app.test_request_context():
                g.tenant = TenantContext(
                    tenant_id='test-uuid',
                    org_id='org_test',
                    org_slug='test-org',
                    display_name='Test Org',
                    schema_name='tenant_test',
                    plan='pro',
                    config_overrides={'ZEP_API_KEY': 'zep-tenant-key'}
                )
                
                cfg = TenantConfig()
                assert cfg.ZEP_API_KEY == 'zep-tenant-key'
                # LLM_API_KEY sollte System-Default sein
                from app.config import Config
                assert cfg.LLM_API_KEY == Config.LLM_API_KEY
```

### Integration-Tests für API-Routen

```python
# backend/tests/test_tenant_api.py

import pytest
from flask import g
from app.tenant.middleware import require_tenant


class TestRequireTenant:
    
    def test_require_tenant_without_token(self, client):
        """Route ohne Token gibt 401"""
        response = client.get('/api/simulation/list')
        assert response.status_code == 401
        assert 'Authentifizierung' in response.json['error']
    
    def test_require_tenant_with_valid_token(self, client, mock_tenant):
        """Route mit gültigem Token funktioniert"""
        response = client.get(
            '/api/simulation/list',
            headers={'Authorization': 'Bearer valid-token'}
        )
        assert response.status_code == 200
    
    def test_require_tenant_without_org_id(self, client):
        """Token ohne org_id gibt 403"""
        response = client.get(
            '/api/simulation/list',
            headers={'Authorization': 'Bearer token-without-org'}
        )
        assert response.status_code == 403
        assert 'Organisations-Kontext' in response.json['error']
```

---

## 📋 Checkliste für vollständige Aktivierung

### Backend

- [ ] `app/utils/llm_client.py` auf TenantConfig umstellen
- [ ] Alle Services auf TenantConfig umstellen (9 Dateien)
- [ ] `app/api/simulation.py` mit `@require_tenant` schützen (20+ Routen)
- [ ] `app/api/report.py` mit `@require_tenant` schützen (15+ Routen)
- [ ] `app/api/graph.py` mit `@require_tenant` schützen (10+ Routen)
- [ ] Usage-Tracking implementieren
- [ ] Usage-Limit-Checks hinzufügen
- [ ] Datenbank-Migration ausführen

### Frontend

- [ ] Axios-Interceptor für Auth-Header aktualisieren
- [ ] Clerk Session-Token speichern
- [ ] Auth-Error-Handling (401, 403)
- [ ] Tenant-Info in UI anzeigen (Plan, Usage)
- [ ] API-Key-Management UI testen

### Infrastruktur

- [ ] `DERFISH_MASTER_KEY` setzen (32-byte Base64)
- [ ] `CLERK_JWKS_URL` setzen
- [ ] Datenbank-Migration ausführen
- [ ] Ersten Tenant manuell erstellen

### Tests

- [ ] Unit-Tests für TenantConfig
- [ ] Integration-Tests für API-Routen
- [ ] E2E-Tests mit Clerk Auth

---

## 🔐 Sicherheitshinweise

### API-Key Verschlüsselung

- **Entwicklungsmodus:** Ohne `DERFISH_MASTER_KEY` werden Keys im Klartext gespeichert
- **Produktion:** `DERFISH_MASTER_KEY` muss gesetzt sein (32-byte Base64)
- **Key-Generierung:** `openssl rand -base64 32`

### JWT-Validierung

- Clerk JWTs werden mit RS256 signiert
- JWKS-Keys werden 5 Minuten gecacht
- 30 Sekunden Uhrzeit-Toleranz für `exp` Claim

### Tenant-Isolation

- Jeder Tenant hat eigenes PostgreSQL-Schema
- `search_path` wird pro Request gesetzt
- Shared-Tabellen nur für Metadaten und API-Keys

---

## 🚀 Deployment

### Umgebungsvariablen (Produktion)

```bash
# Clerk Authentication
CLERK_JWKS_URL=https://<your-frontend-api>.clerk.accounts.dev/.well-known/jwks.json

# Master Key für API-Key Verschlüsselung
DERFISH_MASTER_KEY=<32-byte-base64>

# System-Defaults (Fallback wenn Tenant keine Keys hat)
LLM_API_KEY=sk-system-default
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL_NAME=gpt-4o-mini
ZEP_API_KEY=zep-system-default

# Datenbank
DATABASE_URL=postgresql://user:pass@host:5432/mirofish
```

### Docker Compose

```yaml
services:
  mirofish-backend:
    build: ./backend
    environment:
      - CLERK_JWKS_URL=${CLERK_JWKS_URL}
      - DERFISH_MASTER_KEY=${DERFISH_MASTER_KEY}
      - LLM_API_KEY=${LLM_API_KEY}
      - ZEP_API_KEY=${ZEP_API_KEY}
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/mirofish
    depends_on:
      - db
  
  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=mirofish
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backend/migrations/001_multi_tenant.sql:/docker-entrypoint-initdb.d/001_multi_tenant.sql

volumes:
  postgres_data:
```

---

## 📈 Nächste Schritte nach Implementierung

1. **Monitoring:** Usage-Dashboard für Tenant-Verbrauch
2. **Billing:** Stripe-Integration für Plan-Upgrades
3. **Self-Service:** Tenant-Registrierung ohne manuelle DB-Einträge
4. **Feature-Flags:** Pro-Plan Features freischalten
5. **Analytics:** Tenant-übergreifende Nutzungsstatistiken

---

## 📞 Support

Bei Fragen zur Implementierung:
- Tenant-Middleware: `app/tenant/middleware.py`
- Config-Proxy: `app/tenant/settings_override.py`
- API-Key Encryption: `app/tenant/crypto.py`
- Datenbank: `app/tenant/db.py`

---

## 🌍 Multi-Sprache-Unterstützung (Option 1: Tenant-Sprache)

### Zusammenfassung

MiroFish kann mandantenspezifische Standardsprachen für alle LLM-Ausgaben unterstützen. Jeder Tenant wählt eine Sprache (Deutsch, Englisch, etc.), die automatisch in alle System-Prompts injiziert wird.

---

### 📊 Aktueller Stand

**Problem:** Alle LLM-Prompts sind aktuell auf Chinesisch, was zu chinesischen Log-Ausgaben und Reports führt.

**Beispiele chinesischer Prompts:**
- `app/services/zep_tools.py:1513` - Interview-Planning (中文)
- `app/services/oasis_profile_generator.py` - Persona-Generierung (中文)
- `app/services/simulation_config_generator.py` - Simulations-Konfiguration (中文)
- `app/services/report_agent.py` - Report-Generierung (中文)

---

### 🏗️ Architektur

```
┌─────────────────────────────────────────────────────────────┐
│              shared.tenants Tabelle                         │
│  - id, clerk_org_id, schema_name, ...                       │
│  - language TEXT DEFAULT 'de'  ← NEUE Spalte                │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              TenantContext (flask.g.tenant)                 │
│  - language: str = 'de'                                     │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              LLMClient mit Sprach-Support                   │
│  - LANGUAGE_INSTRUCTIONS[language]                          │
│  - Fügt Sprach-Anweisung zu jedem System-Prompt hinzu       │
│  - Beispiel: "[ANTWORTE AUF DEUTSCH]"                       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              LLM Ausgabe                                    │
│  - Alle Antworten in Tenant-Sprache                         │
│  - Konsistente Sprachausgabe pro Organisation               │
└─────────────────────────────────────────────────────────────┘
```

---

### 🔧 Implementierungsschritte

#### Phase 1: Datenbank-Migration

**Schritt 1.1: Spalte hinzufügen**

```sql
-- Migration: 002_tenant_language.sql
-- Ausführen mit: psql $DATABASE_URL -f backend/migrations/002_tenant_language.sql

BEGIN;

-- Sprache-Spalte zu tenants hinzufügen
ALTER TABLE shared.tenants 
ADD COLUMN IF NOT EXISTS language TEXT NOT NULL DEFAULT 'de';

-- Kommentar hinzufügen
COMMENT ON COLUMN shared.tenants.language IS 
'Standardsprache für LLM-Ausgaben (ISO 639-1: de, en, fr, es, it, zh, ja, ...)';

-- Index für schnelle Abfragen
CREATE INDEX IF NOT EXISTS idx_tenants_language ON shared.tenants(language);

COMMIT;
```

**Schritt 1.2: TenantContext erweitern**

```python
# app/tenant/context.py
@dataclass
class TenantContext:
    """
    Enthält alle mandantenspezifischen Daten für einen Request.

    Attribute:
        tenant_id:        UUID aus shared.tenants
        org_id:           Clerk Organization ID (z.B. "org_abc123")
        org_slug:         Clerk Organization Slug (z.B. "meine-firma")
        display_name:     Anzeigename der Organisation
        schema_name:      PostgreSQL-Schema (z.B. "tenant_meine_firma")
        plan:             Tarif (free / starter / pro / enterprise)
        language:         Standardsprache (de, en, fr, es, ...)
        config_overrides: Mapping von Settings-Key → Klartext-Wert
                          (z.B. {"LLM_API_KEY": "sk-...", "ZEP_API_KEY": "zep-..."})
    """

    tenant_id: str
    org_id: str
    org_slug: str
    display_name: str
    schema_name: str
    plan: str
    language: str = 'de'  # NEU: Default Deutsch
    config_overrides: Dict[str, str] = field(default_factory=dict)
```

**Schritt 1.3: db.py aktualisieren**

```python
# app/tenant/db.py - In get_tenant_from_db():

return TenantContext(
    tenant_id=str(row["id"]),
    org_id=row["clerk_org_id"],
    org_slug=row["clerk_org_slug"],
    display_name=row["display_name"],
    schema_name=row["schema_name"],
    plan=row["plan"],
    language=row.get("language", "de"),  # NEU: Sprache laden
    config_overrides=config_overrides,
)
```

---

#### Phase 2: LLMClient mit Sprach-Support

**Schritt 2.1: Sprach-Anweisungen definieren**

```python
# app/utils/llm_client.py

LANGUAGE_INSTRUCTIONS = {
    'de': (
        '\n\n[SPRACHE: Antworte ausschließlich auf Deutsch. '
        'Verwende keine englischen oder chinesischen Begriffe. '
        'Alle Fachbegriffe auf Deutsch übersetzen.]'
    ),
    'en': (
        '\n\n[LANGUAGE: Respond exclusively in English. '
        'Do not use any Chinese or other language terms. '
        'Translate all technical terms to English.]'
    ),
    'fr': (
        '\n\n[LANGUE: Répondez exclusivement en français. '
        'N\'utilisez aucun terme chinois ou autre. '
        'Traduisez tous les termes techniques en français.]'
    ),
    'es': (
        '\n\n[IDIOMA: Responda exclusivamente en español. '
        'No use términos en chino u otro idioma. '
        'Traduzca todos los términos técnicos al español.]'
    ),
    'it': (
        '\n\n[LINGUA: Rispondi esclusivamente in italiano. '
        'Non usare termini cinesi o di altre lingue. '
        'Traduci tutti i termini tecnici in italiano.]'
    ),
    'zh': (
        '\n\n[语言：仅用中文回答。不要使用英文或其他语言术语。'
        '所有专业术语翻译成中文。]'
    ),
    'ja': (
        '\n\n[言語：日本語のみで回答してください。'
        '中国語や他の言語の用語は使用しないでください。'
        'すべての専門用語を日本語に翻訳してください。]'
    ),
}

SUPPORTED_LANGUAGES = ['de', 'en', 'fr', 'es', 'it', 'zh', 'ja']
```

**Schritt 2.2: LLMClient erweitern**

```python
# app/utils/llm_client.py

class LLMClient:
    """LLM-Client mit Multi-Sprache-Unterstützung"""
    
    def __init__(
        self,
        api_key: str = None,
        base_url: str = None,
        model: str = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        timeout: int = 120,
        language: str = None  # NEU: Sprachparameter
    ):
        """
        Initialisiert den LLM-Client.
        
        Priorität:
        1. Explizite Parameter (api_key, base_url, model, language)
        2. TenantConfig (wenn in Flask-Request)
        3. System-Defaults (app.config.Config)
        """
        from app.tenant.settings_override import TenantConfig
        
        cfg = TenantConfig()
        
        self.api_key = api_key or cfg.LLM_API_KEY
        self.base_url = base_url or cfg.LLM_BASE_URL
        self.model = model or cfg.LLM_MODEL_NAME
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        
        # Sprache bestimmen: Parameter > Tenant > Config > Default
        self.language = (
            language or 
            getattr(cfg, 'language', None) or 
            getattr(cfg, 'DEFAULT_LANGUAGE', 'de')
        )
        
        if self.language not in SUPPORTED_LANGUAGES:
            logger.warning(f"Nicht unterstützte Sprache: {self.language}, verwende 'de'")
            self.language = 'de'
        
        if not self.api_key:
            raise ValueError("LLM_API_KEY ist nicht konfiguriert")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout
        )
    
    def _add_language_instruction(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Fügt Sprach-Anweisung zum System-Prompt hinzu.
        
        Args:
            messages: Original-Nachrichtenliste
            
        Returns:
            Nachrichtenliste mit Sprach-Anweisung
        """
        instruction = LANGUAGE_INSTRUCTIONS.get(self.language, '')
        if not instruction:
            return messages
        
        # Kopie erstellen um Original nicht zu modifizieren
        messages = [msg.copy() for msg in messages]
        
        # Sprach-Anweisung zum System-Prompt hinzufügen
        if messages and messages[0]['role'] == 'system':
            messages[0]['content'] += instruction
            logger.debug(f"Sprach-Anweisung hinzugefügt: {self.language}")
        
        return messages
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096,
        response_format: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Sendet Chat-Anfrage mit Sprach-Unterstützung
        
        Args:
            messages: Nachrichtenliste
            temperature: Temperaturparameter
            max_tokens: Maximale Token-Anzahl
            response_format: Antwortformat (z.B. JSON-Modus)
            
        Returns:
            Modell-Antworttext in Tenant-Sprache
        """
        # Sprach-Anweisung hinzufügen
        messages = self._add_language_instruction(messages)
        
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        if response_format:
            kwargs["response_format"] = response_format
        
        response = self.client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content
        # Einige Modelle (wie MiniMax M2.5) enthalten思考内容 im content, die entfernt werden müssen
        content = re.sub(r'<think>[\s\S]*?</think>', '', content).strip()
        return content
    
    # chat_json() ebenfalls anpassen
    def chat_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096
    ) -> Dict[str, Any]:
        """
        Sendet eine Chat-Anfrage und gibt JSON zurück.
        """
        # Sprach-Anweisung hinzufügen
        messages = self._add_language_instruction(messages)
        
        response = self.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"}
        )
        # Markdown-Codeblock-Marker bereinigen
        cleaned_response = response.strip()
        cleaned_response = re.sub(r'^```(?:json)?\s*\n?', '', cleaned_response, flags=re.IGNORECASE)
        cleaned_response = re.sub(r'\n?```\s*$', '', cleaned_response)
        cleaned_response = cleaned_response.strip()

        try:
            return json.loads(cleaned_response)
        except json.JSONDecodeError:
            raise ValueError(f"Ungültiges JSON-Format vom LLM zurückgegeben: {cleaned_response}")
```

---

#### Phase 3: Config erweitern

**Schritt 3.1: DEFAULT_LANGUAGE hinzufügen**

```python
# app/config.py

class Config:
    """Flask-Konfigurationsklasse"""

    # Flask-Konfiguration
    SECRET_KEY = os.environ.get('SECRET_KEY', 'mirofish-secret-key')
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    # Sprache-Konfiguration
    DEFAULT_LANGUAGE = os.environ.get('DEFAULT_LANGUAGE', 'de')  # NEU
    SUPPORTED_LANGUAGES = ['de', 'en', 'fr', 'es', 'it', 'zh', 'ja']  # NEU
    
    # JSON-Konfiguration
    JSON_AS_ASCII = False
    
    # ... restliche Config unverändert ...
```

---

#### Phase 4: Services aktualisieren

**Alle Services die LLMClient erstellen müssen Sprache übergeben:**

**Schritt 4.1: report_agent.py**

```python
# app/services/report_agent.py

class ReportAgent:
    def __init__(
        self,
        simulation_id: str,
        report_id: str,
        llm_client: Optional[LLMClient] = None,
        language: str = None  # NEU
    ):
        # ...
        self.llm = llm_client or LLMClient(language=language)
```

**Schritt 4.2: oasis_profile_generator.py**

```python
# app/services/oasis_profile_generator.py

class OasisProfileGenerator:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        zep_api_key: Optional[str] = None,
        language: str = None  # NEU
    ):
        cfg = TenantConfig()
        self.api_key = api_key or cfg.LLM_API_KEY
        self.base_url = base_url or cfg.LLM_BASE_URL
        self.model_name = model_name or cfg.LLM_MODEL_NAME
        self.zep_api_key = zep_api_key or cfg.ZEP_API_KEY
        self.language = language or getattr(cfg, 'language', 'de')
        
        self.llm_client = LLMClient(
            api_key=self.api_key,
            base_url=self.base_url,
            model=self.model_name,
            language=self.language  # NEU
        )
```

**Schritt 4.3: simulation_config_generator.py**

```python
# app/services/simulation_config_generator.py

class SimulationConfigGenerator:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        language: str = None  # NEU
    ):
        cfg = TenantConfig()
        self.api_key = api_key or cfg.LLM_API_KEY
        self.base_url = base_url or cfg.LLM_BASE_URL
        self.model_name = model_name or cfg.LLM_MODEL_NAME
        self.language = language or getattr(cfg, 'language', 'de')
        
        self.llm_client = LLMClient(
            api_key=self.api_key,
            base_url=self.base_url,
            model=self.model_name,
            language=self.language  # NEU
        )
```

**Schritt 4.4: graph_builder.py (Ontologie-Generierung)**

```python
# app/services/graph_builder.py

class GraphBuilderService:
    def generate_ontology(
        self,
        text: str,
        language: str = None  # NEU: Sprache für Ontologie
    ):
        cfg = TenantConfig()
        lang = language or getattr(cfg, 'language', 'de')
        
        llm = LLMClient(language=lang)
        # ...
```

---

#### Phase 5: API-Routen für Sprache

**Schritt 5.1: Tenant-Info API erweitern**

```python
# app/api/tenant.py

@tenant_bp.get("/info")
@require_tenant
def tenant_info():
    """Gibt Tenant-Metadaten, gemaskerte Keys, Verbrauch und Sprache zurück."""
    tenant = g.tenant
    keys = list_tenant_api_keys_masked(tenant.tenant_id)
    usage = get_tenant_usage(tenant.tenant_id, tenant.plan)
    
    return jsonify({
        "tenant": {
            "id":           tenant.tenant_id,
            "display_name": tenant.display_name,
            "plan":         tenant.plan,
            "org_slug":     tenant.org_slug,
            "language":     tenant.language,  # NEU
        },
        "keys":  keys,
        "usage": usage,
    })
```

**Schritt 5.2: Sprache aktualisieren API**

```python
# app/api/tenant.py

@tenant_bp.put("/language")
@require_tenant
def update_language():
    """Aktualisiert die Tenant-Sprache."""
    import psycopg
    from app.tenant.db import _get_db_url
    
    tenant = g.tenant
    body = request.get_json(silent=True) or {}
    language = body.get("language", "").strip()
    
    # Validierung
    if not language:
        return jsonify({"error": "language fehlt"}), 400
    
    from app.config import Config
    if language not in Config.SUPPORTED_LANGUAGES:
        return jsonify({
            "error": f"Sprache '{language}' nicht unterstützt",
            "supported": Config.SUPPORTED_LANGUAGES
        }), 400
    
    # Datenbank aktualisieren
    try:
        with psycopg.connect(_get_db_url()) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE shared.tenants
                    SET language = %s, updated_at = NOW()
                    WHERE id = %s
                    """,
                    (language, tenant.tenant_id),
                )
            conn.commit()
        
        logger.info(f"Sprache aktualisiert: tenant={tenant.tenant_id}, language={language}")
        return jsonify({"ok": True, "language": language}), 200
    
    except Exception as exc:
        logger.error(f"Sprache-Update fehlgeschlagen: {exc}")
        return jsonify({"error": "Datenbankfehler"}), 500
```

---

#### Phase 6: Frontend erweitern

**Schritt 6.1: TenantSettingsView.vue - Language Selector**

```vue
<!-- frontend/src/views/TenantSettingsView.vue -->

<template>
  <div class="tenant-settings">
    <!-- ... existing code ... -->

    <!-- ─── Sprache ──────────────────────────────────────── -->
    <section class="card">
      <h2 class="card-title">Sprache</h2>
      <div class="language-selector">
        <select v-model="selectedLanguage" @change="updateLanguage">
          <option value="de">🇩🇪 Deutsch</option>
          <option value="en">🇬🇧 English</option>
          <option value="fr">🇫🇷 Français</option>
          <option value="es">🇪🇸 Español</option>
          <option value="it">🇮🇹 Italiano</option>
          <option value="zh">🇨🇳 中文</option>
          <option value="ja">🇯🇵 日本語</option>
        </select>
        <p class="help-text">
          Legt die Standardsprache für alle LLM-Ausgaben fest (Berichte, Simulationen, Interviews).
        </p>
      </div>
    </section>

    <!-- ... existing code ... -->
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

// ... existing state ...
const selectedLanguage = ref('de')

// ─── Sprache aktualisieren ───────────────────────────────
async function updateLanguage() {
  saving.value = true
  try {
    const res = await fetch(`${API_BASE}/tenant/language`, {
      method:  'PUT',
      headers: { 'Content-Type': 'application/json', ...getAuthHeader() },
      body:    JSON.stringify({ language: selectedLanguage.value }),
    })
    const data = await res.json()
    if (!res.ok) {
      showToast(data.error ?? 'Sprache-Update fehlgeschlagen', 'error')
      selectedLanguage.value = tenant.value.language  // Reset
      return
    }
    showToast('Sprache aktualisiert.')
    await loadInfo()  // Reload tenant info
  } catch (e) {
    showToast(e.message, 'error')
  } finally {
    saving.value = false
  }
}

// ─── Datenladen ───────────────────────────────────────────
async function loadInfo() {
  loading.value = true
  error.value   = null
  try {
    const res = await fetch(`${API_BASE}/tenant/info`, {
      headers: { ...getAuthHeader() },
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    tenant.value = data.tenant
    selectedLanguage.value = data.tenant.language || 'de'  // NEU
    keys.value   = data.keys   ?? []
    usage.value  = data.usage  ?? []
  } catch (e) {
    error.value = `Laden fehlgeschlagen: ${e.message}`
  } finally {
    loading.value = false
  }
}

onMounted(loadInfo)
</script>

<style scoped>
.language-selector {
  margin-top: 1rem;
}

.language-selector select {
  width: 100%;
  padding: 0.75rem;
  background: #1f2937;
  border: 1px solid #374151;
  border-radius: 0.5rem;
  color: #e5e7eb;
  font-size: 1rem;
  cursor: pointer;
}

.language-selector select:focus {
  outline: 2px solid #3b82f6;
  border-color: transparent;
}

.language-selector .help-text {
  margin-top: 0.5rem;
  font-size: 0.875rem;
  color: #9ca3af;
}
</style>
```

**Schritt 6.2: API-Client erweitern**

```javascript
// frontend/src/api/tenant.js

import service from './index'

/**
 * Tenant-Info laden
 */
export const getTenantInfo = () => {
  return service.get('/api/tenant/info')
}

/**
 * API-Key speichern
 */
export const saveApiKey = (keyName, value) => {
  return service.put('/api/tenant/keys', { key_name: keyName, value })
}

/**
 * API-Key löschen
 */
export const deleteApiKey = (keyName) => {
  return service.delete(`/api/tenant/keys/${keyName}`)
}

/**
 * Sprache aktualisieren (NEU)
 */
export const updateLanguage = (language) => {
  return service.put('/api/tenant/language', { language })
}
```

---

### 📋 Checkliste

#### Datenbank

- [ ] Migration `002_tenant_language.sql` erstellen
- [ ] Migration ausführen
- [ ] `language` Spalte zu `shared.tenants` hinzufügen
- [ ] Bestehende Tenants auf 'de' setzen

#### Backend

- [ ] `TenantContext` um `language` Feld erweitern
- [ ] `app/tenant/db.py` aktualisieren (Tenant laden)
- [ ] `LLMClient` mit Sprach-Support erweitern
- [ ] `LANGUAGE_INSTRUCTIONS` für alle Sprachen definieren
- [ ] `app/config.py` um `DEFAULT_LANGUAGE` erweitern
- [ ] Alle Services aktualisieren (report_agent, oasis_profile_generator, etc.)
- [ ] API-Route `/api/tenant/language` hinzufügen
- [ ] `/api/tenant/info` um Sprache erweitern

#### Frontend

- [ ] Language-Selector in TenantSettingsView.vue
- [ ] `updateLanguage()` Funktion implementieren
- [ ] API-Client für Language-Update
- [ ] Tenant-Info um Sprache erweitern
- [ ] UI-Tests für Language-Switcher

#### Tests

- [ ] Unit-Test: LLMClient mit verschiedenen Sprachen
- [ ] Integration-Test: Language-Update API
- [ ] E2E-Test: Report auf Deutsch vs. Englisch
- [ ] Prompt-Test: Sprach-Anweisung wird injiziert

#### Dokumentation

- [ ] README.md um Sprache-Feature erweitern
- [ ] API-Dokumentation aktualisieren
- [ ] User-Guide für Language-Switcher

---

### 🎯 Unterstützte Sprachen (Phase 1)

| Code | Sprache | Status |
|------|---------|--------|
| `de` | Deutsch | ✅ Voll unterstützt |
| `en` | English | ✅ Voll unterstützt |
| `fr` | Français | 🟡 Teilweise |
| `es` | Español | 🟡 Teilweise |
| `it` | Italiano | 🟡 Teilweise |
| `zh` | 中文 | 🟡 Teilweise |
| `ja` | 日本語 | 🟡 Teilweise |

**Erweiterung:** Weitere Sprachen durch Hinzufügen zu `LANGUAGE_INSTRUCTIONS` möglich.

---

### 🔍 Debugging

**Sprache wird nicht angewendet?**

1. **Tenant-Sprache prüfen:**
   ```sql
   SELECT clerk_org_id, language FROM shared.tenants;
   ```

2. **LLMClient Sprache loggen:**
   ```python
   logger.debug(f"LLMClient Sprache: {self.language}")
   ```

3. **Prompt-Injection prüfen:**
   ```python
   # In _add_language_instruction():
   logger.debug(f"Sprach-Anweisung: {instruction[:100]}...")
   ```

4. **Frontend Request prüfen:**
   ```javascript
   console.log('Selected language:', selectedLanguage.value)
   ```

---

### 📈 Nächste Schritte (Phase 2+)

1. **Report-spezifische Sprache:** Sprache pro Report einstellbar
2. **User-Preferences:** Sprache pro User speicherbar
3. **Vollständige i18n:** Alle UI-Texte übersetzen
4. **Auto-Translation:** Bestehende chinesische Reports übersetzen
5. **Sprache-Erkennung:** Automatische Erkennung der User-Sprache

---

### 💡 Best Practices

1. **Immer Fallback auf 'de':** Wenn Sprache nicht gesetzt/ungültig
2. **Sprach-Anweisung kurz halten:** Maximal 2-3 Sätze
3. **Konsistente Terminologie:** Fachbegriffe einheitlich übersetzen
4. **Testing mit allen Sprachen:** Jede Sprache testen vor Release
5. **Dokumentation mehrsprachig:** README auf DE/EN verfügbar

---

## 📞 Support Multi-Sprache

Bei Fragen zur Sprach-Implementierung:
- LLMClient: `app/utils/llm_client.py`
- Tenant-Sprache: `app/tenant/context.py`, `app/tenant/db.py`
- Frontend: `frontend/src/views/TenantSettingsView.vue`
- API: `app/api/tenant.py`

---

## 🌍 Multi-Sprache-Unterstützung (Option 1: Tenant-Sprache)

### Zusammenfassung

MiroFish kann mandantenspezifische Standardsprachen für alle LLM-Ausgaben unterstützen. Jeder Tenant wählt eine Sprache (Deutsch, Englisch, etc.), die automatisch in alle System-Prompts injiziert wird.

---

### 📊 Aktueller Stand

**Problem:** Alle LLM-Prompts sind aktuell auf Chinesisch, was zu chinesischen Log-Ausgaben und Reports führt.

**Beispiele chinesischer Prompts:**
- `app/services/zep_tools.py:1513` - Interview-Planning (中文)
- `app/services/oasis_profile_generator.py` - Persona-Generierung (中文)
- `app/services/simulation_config_generator.py` - Simulations-Konfiguration (中文)
- `app/services/report_agent.py` - Report-Generierung (中文)

---

### 🏗️ Architektur

```
┌─────────────────────────────────────────────────────────────┐
│              shared.tenants Tabelle                         │
│  - id, clerk_org_id, schema_name, ...                       │
│  - language TEXT DEFAULT 'de'  ← NEUE Spalte                │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              TenantContext (flask.g.tenant)                 │
│  - language: str = 'de'                                     │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              LLMClient mit Sprach-Support                   │
│  - LANGUAGE_INSTRUCTIONS[language]                          │
│  - Fügt Sprach-Anweisung zu jedem System-Prompt hinzu       │
│  - Beispiel: "[ANTWORTE AUF DEUTSCH]"                       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              LLM Ausgabe                                    │
│  - Alle Antworten in Tenant-Sprache                         │
│  - Konsistente Sprachausgabe pro Organisation               │
└─────────────────────────────────────────────────────────────┘
```

---

### 🔧 Implementierungsschritte

#### Phase 1: Datenbank-Migration

**Schritt 1.1: Spalte hinzufügen**

```sql
-- Migration: 002_tenant_language.sql
-- Ausführen mit: psql $DATABASE_URL -f backend/migrations/002_tenant_language.sql

BEGIN;

-- Sprache-Spalte zu tenants hinzufügen
ALTER TABLE shared.tenants 
ADD COLUMN IF NOT EXISTS language TEXT NOT NULL DEFAULT 'de';

-- Kommentar hinzufügen
COMMENT ON COLUMN shared.tenants.language IS 
'Standardsprache für LLM-Ausgaben (ISO 639-1: de, en, fr, es, it, zh, ja, ...)';

-- Index für schnelle Abfragen
CREATE INDEX IF NOT EXISTS idx_tenants_language ON shared.tenants(language);

COMMIT;
```

**Schritt 1.2: TenantContext erweitern**

```python
# app/tenant/context.py
@dataclass
class TenantContext:
    """
    Enthält alle mandantenspezifischen Daten für einen Request.

    Attribute:
        tenant_id:        UUID aus shared.tenants
        org_id:           Clerk Organization ID (z.B. "org_abc123")
        org_slug:         Clerk Organization Slug (z.B. "meine-firma")
        display_name:     Anzeigename der Organisation
        schema_name:      PostgreSQL-Schema (z.B. "tenant_meine_firma")
        plan:             Tarif (free / starter / pro / enterprise)
        language:         Standardsprache (de, en, fr, es, ...)
        config_overrides: Mapping von Settings-Key → Klartext-Wert
                          (z.B. {"LLM_API_KEY": "sk-...", "ZEP_API_KEY": "zep-..."})
    """

    tenant_id: str
    org_id: str
    org_slug: str
    display_name: str
    schema_name: str
    plan: str
    language: str = 'de'  # NEU: Default Deutsch
    config_overrides: Dict[str, str] = field(default_factory=dict)
```

**Schritt 1.3: db.py aktualisieren**

```python
# app/tenant/db.py - In get_tenant_from_db():

return TenantContext(
    tenant_id=str(row["id"]),
    org_id=row["clerk_org_id"],
    org_slug=row["clerk_org_slug"],
    display_name=row["display_name"],
    schema_name=row["schema_name"],
    plan=row["plan"],
    language=row.get("language", "de"),  # NEU: Sprache laden
    config_overrides=config_overrides,
)
```

---

#### Phase 2: LLMClient mit Sprach-Support

**Schritt 2.1: Sprach-Anweisungen definieren**

```python
# app/utils/llm_client.py

LANGUAGE_INSTRUCTIONS = {
    'de': (
        '\n\n[SPRACHE: Antworte ausschließlich auf Deutsch. '
        'Verwende keine englischen oder chinesischen Begriffe. '
        'Alle Fachbegriffe auf Deutsch übersetzen.]'
    ),
    'en': (
        '\n\n[LANGUAGE: Respond exclusively in English. '
        'Do not use any Chinese or other language terms. '
        'Translate all technical terms to English.]'
    ),
    'fr': (
        '\n\n[LANGUE: Répondez exclusivement en français. '
        'N\'utilisez aucun terme chinois ou autre. '
        'Traduisez tous les termes techniques en français.]'
    ),
    'es': (
        '\n\n[IDIOMA: Responda exclusivamente en español. '
        'No use términos en chino u otro idioma. '
        'Traduzca todos los términos técnicos al español.]'
    ),
    'it': (
        '\n\n[LINGUA: Rispondi esclusivamente in italiano. '
        'Non usare termini cinesi o di altre lingue. '
        'Traduci tutti i termini tecnici in italiano.]'
    ),
    'zh': (
        '\n\n[语言：仅用中文回答。不要使用英文或其他语言术语。'
        '所有专业术语翻译成中文。]'
    ),
    'ja': (
        '\n\n[言語：日本語のみで回答してください。'
        '中国語や他の言語の用語は使用しないでください。'
        'すべての専門用語を日本語に翻訳してください。]'
    ),
}

SUPPORTED_LANGUAGES = ['de', 'en', 'fr', 'es', 'it', 'zh', 'ja']
```

**Schritt 2.2: LLMClient erweitern**

```python
# app/utils/llm_client.py

class LLMClient:
    """LLM-Client mit Multi-Sprache-Unterstützung"""
    
    def __init__(
        self,
        api_key: str = None,
        base_url: str = None,
        model: str = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        timeout: int = 120,
        language: str = None  # NEU: Sprachparameter
    ):
        """
        Initialisiert den LLM-Client.
        
        Priorität:
        1. Explizite Parameter (api_key, base_url, model, language)
        2. TenantConfig (wenn in Flask-Request)
        3. System-Defaults (app.config.Config)
        """
        from app.tenant.settings_override import TenantConfig
        
        cfg = TenantConfig()
        
        self.api_key = api_key or cfg.LLM_API_KEY
        self.base_url = base_url or cfg.LLM_BASE_URL
        self.model = model or cfg.LLM_MODEL_NAME
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        
        # Sprache bestimmen: Parameter > Tenant > Config > Default
        self.language = (
            language or 
            getattr(cfg, 'language', None) or 
            getattr(cfg, 'DEFAULT_LANGUAGE', 'de')
        )
        
        if self.language not in SUPPORTED_LANGUAGES:
            logger.warning(f"Nicht unterstützte Sprache: {self.language}, verwende 'de'")
            self.language = 'de'
        
        if not self.api_key:
            raise ValueError("LLM_API_KEY ist nicht konfiguriert")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout
        )
    
    def _add_language_instruction(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Fügt Sprach-Anweisung zum System-Prompt hinzu.
        
        Args:
            messages: Original-Nachrichtenliste
            
        Returns:
            Nachrichtenliste mit Sprach-Anweisung
        """
        instruction = LANGUAGE_INSTRUCTIONS.get(self.language, '')
        if not instruction:
            return messages
        
        # Kopie erstellen um Original nicht zu modifizieren
        messages = [msg.copy() for msg in messages]
        
        # Sprach-Anweisung zum System-Prompt hinzufügen
        if messages and messages[0]['role'] == 'system':
            messages[0]['content'] += instruction
            logger.debug(f"Sprach-Anweisung hinzugefügt: {self.language}")
        
        return messages
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096,
        response_format: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Sendet Chat-Anfrage mit Sprach-Unterstützung
        
        Args:
            messages: Nachrichtenliste
            temperature: Temperaturparameter
            max_tokens: Maximale Token-Anzahl
            response_format: Antwortformat (z.B. JSON-Modus)
            
        Returns:
            Modell-Antworttext in Tenant-Sprache
        """
        # Sprach-Anweisung hinzufügen
        messages = self._add_language_instruction(messages)
        
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        if response_format:
            kwargs["response_format"] = response_format
        
        response = self.client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content
        # Einige Modelle (wie MiniMax M2.5) enthalten思考内容 im content, die entfernt werden müssen
        content = re.sub(r'<think>[\s\S]*?</think>', '', content).strip()
        return content
    
    # chat_json() ebenfalls anpassen
    def chat_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096
    ) -> Dict[str, Any]:
        """
        Sendet eine Chat-Anfrage und gibt JSON zurück.
        """
        # Sprach-Anweisung hinzufügen
        messages = self._add_language_instruction(messages)
        
        response = self.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"}
        )
        # Markdown-Codeblock-Marker bereinigen
        cleaned_response = response.strip()
        cleaned_response = re.sub(r'^```(?:json)?\s*\n?', '', cleaned_response, flags=re.IGNORECASE)
        cleaned_response = re.sub(r'\n?```\s*$', '', cleaned_response)
        cleaned_response = cleaned_response.strip()

        try:
            return json.loads(cleaned_response)
        except json.JSONDecodeError:
            raise ValueError(f"Ungültiges JSON-Format vom LLM zurückgegeben: {cleaned_response}")
```

---

#### Phase 3: Config erweitern

**Schritt 3.1: DEFAULT_LANGUAGE hinzufügen**

```python
# app/config.py

class Config:
    """Flask-Konfigurationsklasse"""

    # Flask-Konfiguration
    SECRET_KEY = os.environ.get('SECRET_KEY', 'mirofish-secret-key')
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    # Sprache-Konfiguration
    DEFAULT_LANGUAGE = os.environ.get('DEFAULT_LANGUAGE', 'de')  # NEU
    SUPPORTED_LANGUAGES = ['de', 'en', 'fr', 'es', 'it', 'zh', 'ja']  # NEU
    
    # JSON-Konfiguration
    JSON_AS_ASCII = False
    
    # ... restliche Config unverändert ...
```

---

#### Phase 4: Services aktualisieren

**Alle Services die LLMClient erstellen müssen Sprache übergeben:**

**Schritt 4.1: report_agent.py**

```python
# app/services/report_agent.py

class ReportAgent:
    def __init__(
        self,
        simulation_id: str,
        report_id: str,
        llm_client: Optional[LLMClient] = None,
        language: str = None  # NEU
    ):
        # ...
        self.llm = llm_client or LLMClient(language=language)
```

**Schritt 4.2: oasis_profile_generator.py**

```python
# app/services/oasis_profile_generator.py

class OasisProfileGenerator:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        zep_api_key: Optional[str] = None,
        language: str = None  # NEU
    ):
        cfg = TenantConfig()
        self.api_key = api_key or cfg.LLM_API_KEY
        self.base_url = base_url or cfg.LLM_BASE_URL
        self.model_name = model_name or cfg.LLM_MODEL_NAME
        self.zep_api_key = zep_api_key or cfg.ZEP_API_KEY
        self.language = language or getattr(cfg, 'language', 'de')
        
        self.llm_client = LLMClient(
            api_key=self.api_key,
            base_url=self.base_url,
            model=self.model_name,
            language=self.language  # NEU
        )
```

**Schritt 4.3: simulation_config_generator.py**

```python
# app/services/simulation_config_generator.py

class SimulationConfigGenerator:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        language: str = None  # NEU
    ):
        cfg = TenantConfig()
        self.api_key = api_key or cfg.LLM_API_KEY
        self.base_url = base_url or cfg.LLM_BASE_URL
        self.model_name = model_name or cfg.LLM_MODEL_NAME
        self.language = language or getattr(cfg, 'language', 'de')
        
        self.llm_client = LLMClient(
            api_key=self.api_key,
            base_url=self.base_url,
            model=self.model_name,
            language=self.language  # NEU
        )
```

**Schritt 4.4: graph_builder.py (Ontologie-Generierung)**

```python
# app/services/graph_builder.py

class GraphBuilderService:
    def generate_ontology(
        self,
        text: str,
        language: str = None  # NEU: Sprache für Ontologie
    ):
        cfg = TenantConfig()
        lang = language or getattr(cfg, 'language', 'de')
        
        llm = LLMClient(language=lang)
        # ...
```

---

#### Phase 5: API-Routen für Sprache

**Schritt 5.1: Tenant-Info API erweitern**

```python
# app/api/tenant.py

@tenant_bp.get("/info")
@require_tenant
def tenant_info():
    """Gibt Tenant-Metadaten, gemaskerte Keys, Verbrauch und Sprache zurück."""
    tenant = g.tenant
    keys = list_tenant_api_keys_masked(tenant.tenant_id)
    usage = get_tenant_usage(tenant.tenant_id, tenant.plan)
    
    return jsonify({
        "tenant": {
            "id":           tenant.tenant_id,
            "display_name": tenant.display_name,
            "plan":         tenant.plan,
            "org_slug":     tenant.org_slug,
            "language":     tenant.language,  # NEU
        },
        "keys":  keys,
        "usage": usage,
    })
```

**Schritt 5.2: Sprache aktualisieren API**

```python
# app/api/tenant.py

@tenant_bp.put("/language")
@require_tenant
def update_language():
    """Aktualisiert die Tenant-Sprache."""
    import psycopg
    from app.tenant.db import _get_db_url
    
    tenant = g.tenant
    body = request.get_json(silent=True) or {}
    language = body.get("language", "").strip()
    
    # Validierung
    if not language:
        return jsonify({"error": "language fehlt"}), 400
    
    from app.config import Config
    if language not in Config.SUPPORTED_LANGUAGES:
        return jsonify({
            "error": f"Sprache '{language}' nicht unterstützt",
            "supported": Config.SUPPORTED_LANGUAGES
        }), 400
    
    # Datenbank aktualisieren
    try:
        with psycopg.connect(_get_db_url()) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE shared.tenants
                    SET language = %s, updated_at = NOW()
                    WHERE id = %s
                    """,
                    (language, tenant.tenant_id),
                )
            conn.commit()
        
        logger.info(f"Sprache aktualisiert: tenant={tenant.tenant_id}, language={language}")
        return jsonify({"ok": True, "language": language}), 200
    
    except Exception as exc:
        logger.error(f"Sprache-Update fehlgeschlagen: {exc}")
        return jsonify({"error": "Datenbankfehler"}), 500
```

---

#### Phase 6: Frontend erweitern

**Schritt 6.1: TenantSettingsView.vue - Language Selector**

```vue
<!-- frontend/src/views/TenantSettingsView.vue -->

<template>
  <div class="tenant-settings">
    <!-- ... existing code ... -->

    <!-- ─── Sprache ──────────────────────────────────────── -->
    <section class="card">
      <h2 class="card-title">Sprache</h2>
      <div class="language-selector">
        <select v-model="selectedLanguage" @change="updateLanguage">
          <option value="de">🇩🇪 Deutsch</option>
          <option value="en">🇬🇧 English</option>
          <option value="fr">🇫🇷 Français</option>
          <option value="es">🇪🇸 Español</option>
          <option value="it">🇮🇹 Italiano</option>
          <option value="zh">🇨🇳 中文</option>
          <option value="ja">🇯🇵 日本語</option>
        </select>
        <p class="help-text">
          Legt die Standardsprache für alle LLM-Ausgaben fest (Berichte, Simulationen, Interviews).
        </p>
      </div>
    </section>

    <!-- ... existing code ... -->
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

// ... existing state ...
const selectedLanguage = ref('de')

// ─── Sprache aktualisieren ───────────────────────────────
async function updateLanguage() {
  saving.value = true
  try {
    const res = await fetch(`${API_BASE}/tenant/language`, {
      method:  'PUT',
      headers: { 'Content-Type': 'application/json', ...getAuthHeader() },
      body:    JSON.stringify({ language: selectedLanguage.value }),
    })
    const data = await res.json()
    if (!res.ok) {
      showToast(data.error ?? 'Sprache-Update fehlgeschlagen', 'error')
      selectedLanguage.value = tenant.value.language  // Reset
      return
    }
    showToast('Sprache aktualisiert.')
    await loadInfo()  // Reload tenant info
  } catch (e) {
    showToast(e.message, 'error')
  } finally {
    saving.value = false
  }
}

// ─── Datenladen ───────────────────────────────────────────
async function loadInfo() {
  loading.value = true
  error.value   = null
  try {
    const res = await fetch(`${API_BASE}/tenant/info`, {
      headers: { ...getAuthHeader() },
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    tenant.value = data.tenant
    selectedLanguage.value = data.tenant.language || 'de'  // NEU
    keys.value   = data.keys   ?? []
    usage.value  = data.usage  ?? []
  } catch (e) {
    error.value = `Laden fehlgeschlagen: ${e.message}`
  } finally {
    loading.value = false
  }
}

onMounted(loadInfo)
</script>

<style scoped>
.language-selector {
  margin-top: 1rem;
}

.language-selector select {
  width: 100%;
  padding: 0.75rem;
  background: #1f2937;
  border: 1px solid #374151;
  border-radius: 0.5rem;
  color: #e5e7eb;
  font-size: 1rem;
  cursor: pointer;
}

.language-selector select:focus {
  outline: 2px solid #3b82f6;
  border-color: transparent;
}

.language-selector .help-text {
  margin-top: 0.5rem;
  font-size: 0.875rem;
  color: #9ca3af;
}
</style>
```

**Schritt 6.2: API-Client erweitern**

```javascript
// frontend/src/api/tenant.js

import service from './index'

/**
 * Tenant-Info laden
 */
export const getTenantInfo = () => {
  return service.get('/api/tenant/info')
}

/**
 * API-Key speichern
 */
export const saveApiKey = (keyName, value) => {
  return service.put('/api/tenant/keys', { key_name: keyName, value })
}

/**
 * API-Key löschen
 */
export const deleteApiKey = (keyName) => {
  return service.delete(`/api/tenant/keys/${keyName}`)
}

/**
 * Sprache aktualisieren (NEU)
 */
export const updateLanguage = (language) => {
  return service.put('/api/tenant/language', { language })
}
```

---

### 📋 Checkliste

#### Datenbank

- [ ] Migration `002_tenant_language.sql` erstellen
- [ ] Migration ausführen
- [ ] `language` Spalte zu `shared.tenants` hinzufügen
- [ ] Bestehende Tenants auf 'de' setzen

#### Backend

- [ ] `TenantContext` um `language` Feld erweitern
- [ ] `app/tenant/db.py` aktualisieren (Tenant laden)
- [ ] `LLMClient` mit Sprach-Support erweitern
- [ ] `LANGUAGE_INSTRUCTIONS` für alle Sprachen definieren
- [ ] `app/config.py` um `DEFAULT_LANGUAGE` erweitern
- [ ] Alle Services aktualisieren (report_agent, oasis_profile_generator, etc.)
- [ ] API-Route `/api/tenant/language` hinzufügen
- [ ] `/api/tenant/info` um Sprache erweitern

#### Frontend

- [ ] Language-Selector in TenantSettingsView.vue
- [ ] `updateLanguage()` Funktion implementieren
- [ ] API-Client für Language-Update
- [ ] Tenant-Info um Sprache erweitern
- [ ] UI-Tests für Language-Switcher

#### Tests

- [ ] Unit-Test: LLMClient mit verschiedenen Sprachen
- [ ] Integration-Test: Language-Update API
- [ ] E2E-Test: Report auf Deutsch vs. Englisch
- [ ] Prompt-Test: Sprach-Anweisung wird injiziert

#### Dokumentation

- [ ] README.md um Sprache-Feature erweitern
- [ ] API-Dokumentation aktualisieren
- [ ] User-Guide für Language-Switcher

---

### 🎯 Unterstützte Sprachen (Phase 1)

| Code | Sprache | Status |
|------|---------|--------|
| `de` | Deutsch | ✅ Voll unterstützt |
| `en` | English | ✅ Voll unterstützt |
| `fr` | Français | 🟡 Teilweise |
| `es` | Español | 🟡 Teilweise |
| `it` | Italiano | 🟡 Teilweise |
| `zh` | 中文 | 🟡 Teilweise |
| `ja` | 日本語 | 🟡 Teilweise |

**Erweiterung:** Weitere Sprachen durch Hinzufügen zu `LANGUAGE_INSTRUCTIONS` möglich.

---

### 🔍 Debugging

**Sprache wird nicht angewendet?**

1. **Tenant-Sprache prüfen:**
   ```sql
   SELECT clerk_org_id, language FROM shared.tenants;
   ```

2. **LLMClient Sprache loggen:**
   ```python
   logger.debug(f"LLMClient Sprache: {self.language}")
   ```

3. **Prompt-Injection prüfen:**
   ```python
   # In _add_language_instruction():
   logger.debug(f"Sprach-Anweisung: {instruction[:100]}...")
   ```

4. **Frontend Request prüfen:**
   ```javascript
   console.log('Selected language:', selectedLanguage.value)
   ```

---

### 📈 Nächste Schritte (Phase 2+)

1. **Report-spezifische Sprache:** Sprache pro Report einstellbar
2. **User-Preferences:** Sprache pro User speicherbar
3. **Vollständige i18n:** Alle UI-Texte übersetzen
4. **Auto-Translation:** Bestehende chinesische Reports übersetzen
5. **Sprache-Erkennung:** Automatische Erkennung der User-Sprache

---

### 💡 Best Practices

1. **Immer Fallback auf 'de':** Wenn Sprache nicht gesetzt/ungültig
2. **Sprach-Anweisung kurz halten:** Maximal 2-3 Sätze
3. **Konsistente Terminologie:** Fachbegriffe einheitlich übersetzen
4. **Testing mit allen Sprachen:** Jede Sprache testen vor Release
5. **Dokumentation mehrsprachig:** README auf DE/EN verfügbar

---

## 📞 Support Multi-Sprache

Bei Fragen zur Sprach-Implementierung:
- LLMClient: `app/utils/llm_client.py`
- Tenant-Sprache: `app/tenant/context.py`, `app/tenant/db.py`
- Frontend: `frontend/src/views/TenantSettingsView.vue`
- API: `app/api/tenant.py`
