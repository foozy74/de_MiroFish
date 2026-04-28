import psycopg
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")

SQL = """
-- 1. Shared Schema erstellen
CREATE SCHEMA IF NOT EXISTS shared;

-- 2. Tabelle für Tenants
CREATE TABLE IF NOT EXISTS shared.tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clerk_org_id TEXT UNIQUE NOT NULL,
    clerk_org_slug TEXT,
    display_name TEXT NOT NULL,
    schema_name TEXT UNIQUE NOT NULL,
    plan TEXT DEFAULT 'free',
    status TEXT DEFAULT 'active',
    config_overrides JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Tabelle für verschlüsselte API-Keys
CREATE TABLE IF NOT EXISTS shared.tenant_api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES shared.tenants(id) ON DELETE CASCADE,
    key_name TEXT NOT NULL,
    encrypted_value BYTEA NOT NULL,
    iv BYTEA NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(tenant_id, key_name)
);

-- 4. Tabelle für Verbrauchsdaten
CREATE TABLE IF NOT EXISTS shared.usage_daily (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES shared.tenants(id),
    service TEXT NOT NULL,
    metric TEXT NOT NULL,
    value INT DEFAULT 0,
    date DATE DEFAULT CURRENT_DATE,
    UNIQUE(tenant_id, service, metric, date)
);
"""

try:
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(SQL)
        conn.commit()
    print("Supabase initialization successful.")
except Exception as e:
    print(f"Error: {e}")
