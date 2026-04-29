"""
Tenant-Datenbankzugriff (MiroFish) - SQLite Version

Stellt Dienste bereit um Tenant-Metadaten und API-Key-Overrides 
aus einer lokalen shared.db zu laden.
"""

import os
import sqlite3
import json
from typing import Dict, List, Optional
from datetime import datetime

from app.utils.logger import get_logger
from .context import TenantContext
from .crypto import decrypt_value, encrypt_value
from ..config import Config

logger = get_logger("mirofish.tenant.db")

def _get_shared_db_path() -> str:
    """Gibt den Pfad zur zentralen Shared-Datenbank zurück."""
    path = os.path.join(Config.UPLOAD_FOLDER, 'shared.db')
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    return path

def _get_conn():
    """Erstellt eine Verbindung zur shared.db."""
    try:
        conn = sqlite3.connect(_get_shared_db_path())
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        logger.error(f"Fehler beim Verbinden mit der shared.db: {e}")
        raise

def init_shared_db():
    """Initialisiert die Tabellen in der shared.db falls sie nicht existieren."""
    try:
        conn = _get_conn()
        try:
            cursor = conn.cursor()
            # Tabelle für Tenants
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tenants (
                    id TEXT PRIMARY KEY,
                    clerk_org_id TEXT UNIQUE NOT NULL,
                    clerk_org_slug TEXT,
                    display_name TEXT NOT NULL,
                    schema_name TEXT UNIQUE NOT NULL,
                    plan TEXT DEFAULT 'free',
                    status TEXT DEFAULT 'active',
                    config_overrides TEXT DEFAULT '{}',
                    created_at TEXT DEFAULT (datetime('now')),
                    updated_at TEXT DEFAULT (datetime('now'))
                )
            """)
            # Tabelle für verschlüsselte API-Keys
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tenant_api_keys (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT REFERENCES tenants(id) ON DELETE CASCADE,
                    key_name TEXT NOT NULL,
                    encrypted_value BLOB NOT NULL,
                    iv BLOB NOT NULL,
                    created_at TEXT DEFAULT (datetime('now')),
                    updated_at TEXT DEFAULT (datetime('now')),
                    UNIQUE(tenant_id, key_name)
                )
            """)
            conn.commit()
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Fehler bei der Initialisierung der shared.db: {e}")
        # Wir lassen den Fehler hier nicht die Anwendung komplett stoppen, 
        # damit der Healthcheck eventuell noch funktionieren kann (für Debugging)


def get_tenant_from_db(org_id: str) -> Optional[TenantContext]:
    """Lädt Tenant-Metadaten aus der lokalen SQLite shared.db."""
    init_shared_db() # Sicherstellen dass DB existiert
    
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, clerk_org_id, clerk_org_slug, display_name, schema_name, plan
            FROM tenants
            WHERE clerk_org_id = ? AND status = 'active'
        """, (org_id,))
        
        row = cursor.fetchone()
        if not row:
            # Automatisches Provisioning falls Tenant noch nicht existiert (optional)
            # Für jetzt: Warning und None
            logger.warning(f"Tenant nicht in shared.db gefunden: {org_id}")
            return None

        # API-Keys laden
        cursor.execute("""
            SELECT key_name, encrypted_value, iv
            FROM tenant_api_keys
            WHERE tenant_id = ?
        """, (row["id"],))
        key_rows = cursor.fetchall()

        config_overrides: Dict[str, str] = {}
        for kr in key_rows:
            try:
                config_overrides[kr["key_name"]] = decrypt_value(
                    kr["encrypted_value"],
                    kr["iv"]
                )
            except Exception as exc:
                logger.warning(f"Key-Entschlüsselung fehlgeschlagen [tenant={org_id}, key={kr['key_name']}]: {exc}")

        return TenantContext(
            tenant_id=row["id"],
            org_id=row["clerk_org_id"],
            org_slug=row["clerk_org_slug"],
            display_name=row["display_name"],
            schema_name=row["schema_name"],
            plan=row["plan"],
            config_overrides=config_overrides
        )
    finally:
        conn.close()

def upsert_tenant_api_key(tenant_id: str, key_name: str, plaintext: str) -> None:
    """Speichert einen verschlüsselten API-Key lokal."""
    init_shared_db()
    encrypted, iv = encrypt_value(plaintext)
    key_id = f"key_{os.urandom(8).hex()}"
    
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO tenant_api_keys (id, tenant_id, key_name, encrypted_value, iv, updated_at)
            VALUES (?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(tenant_id, key_name) DO UPDATE SET
                encrypted_value = excluded.encrypted_value,
                iv = excluded.iv,
                updated_at = datetime('now')
        """, (key_id, tenant_id, key_name, encrypted, iv))
        conn.commit()
    finally:
        conn.close()

def register_tenant(clerk_org_id: str, display_name: str, org_slug: str = None) -> str:
    """Registriert einen neuen Tenant in der shared.db."""
    init_shared_db()
    tenant_id = f"ten_{os.urandom(8).hex()}"
    schema_name = f"tenant_{clerk_org_id.lower().replace('org_', '')}"
    
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO tenants (id, clerk_org_id, clerk_org_slug, display_name, schema_name)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(clerk_org_id) DO UPDATE SET
                display_name = excluded.display_name,
                clerk_org_slug = excluded.clerk_org_slug,
                updated_at = datetime('now')
        """, (tenant_id, clerk_org_id, org_slug, display_name, schema_name))
        conn.commit()
        return tenant_id
    finally:
        conn.close()

def _mask_value(value: str) -> str:
    if len(value) > 12:
        return f"{value[:4]}****{value[-4:]}"
    return "****"

def list_tenant_api_keys_masked(tenant_id: str) -> List[Dict[str, object]]:
    try:
        conn = _get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT key_name, encrypted_value, iv FROM tenant_api_keys WHERE tenant_id = ?", (tenant_id,))
        result = []
        for kr in cursor.fetchall():
            try:
                plain = decrypt_value(kr["encrypted_value"], kr["iv"])
                masked = _mask_value(plain)
            except:
                masked = "****"
            result.append({"key_name": kr["key_name"], "masked": masked})
        conn.close()
        return result
    except Exception as exc:
        logger.error(f"API-Key-Liste fehlgeschlagen [{tenant_id}]: {exc}")
        return []

def delete_tenant_api_key(tenant_id: str, key_name: str) -> bool:
    """Löscht einen API-Key für einen Tenant."""
    try:
        conn = _get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM tenant_api_keys WHERE tenant_id = ? AND key_name = ?", 
            (tenant_id, key_name)
        )
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        return success
    except Exception as exc:
        logger.error(f"API-Key-Löschen fehlgeschlagen [{tenant_id}, {key_name}]: {exc}")
        return False

def get_tenant_usage(tenant_id: str) -> Dict[str, object]:
    """Berechnet die Nutzung für einen Tenant (Projekte, Simulationen)."""
    try:
        # Pfad zur data.db des Tenants ermitteln
        # Wir müssen den schema_name kennen um den Ordner zu finden
        conn = _get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT schema_name FROM tenants WHERE id = ?", (tenant_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return {"projects_count": 0, "simulations_count": 0}
            
        # Wir nutzen den Standard-Pfad: uploads/tenants/{tenant_id}/data.db
        # Da wir im Shared-DB-Kontext sind, ist tenant_id hier die interne ID
        db_path = os.path.join(Config.UPLOAD_FOLDER, 'tenants', tenant_id, 'data.db')
        
        if not os.path.exists(db_path):
            return {"projects_count": 0, "simulations_count": 0}
            
        t_conn = sqlite3.connect(db_path)
        t_cursor = t_conn.cursor()
        
        # Projekte zählen
        try:
            t_cursor.execute("SELECT COUNT(*) FROM projects")
            projects_count = t_cursor.fetchone()[0]
        except:
            projects_count = 0
            
        # Simulationen zählen
        try:
            t_cursor.execute("SELECT COUNT(*) FROM simulation_runs")
            simulations_count = t_cursor.fetchone()[0]
        except:
            simulations_count = 0
            
        t_conn.close()
        
        return {
            "projects_count": projects_count,
            "simulations_count": simulations_count,
            "storage_used_bytes": os.path.getsize(db_path) if os.path.exists(db_path) else 0
        }
    except Exception as exc:
        logger.error(f"Verbrauch-Abfrage fehlgeschlagen [{tenant_id}]: {exc}")
        return {"projects_count": 0, "simulations_count": 0, "error": str(exc)}
