"""
Tenant-Datenbankzugriff (MiroFish)

Stellt zwei Dienste bereit:
1. get_tenant_from_db() — synchroner psycopg3-Zugriff auf shared.*
2. get_tenant_db_url()  — DATABASE_URL mit search_path für direkte psycopg3-Nutzung

MiroFish verwendet kein async SQLAlchemy, daher kein Engine-Cache wie BettaFish.
Zukünftige Simulation-Tabellen (Phase 1) werden über get_tenant_db_url() erreichbar.
"""

import os
from typing import Dict, List, Optional

from app.utils.logger import get_logger

from .context import TenantContext
from .crypto import decrypt_value, encrypt_value

logger = get_logger("mirofish.tenant.db")

# Engine-Cache bleibt leer bis Phase 1 (Simulationstabellen)
_tenant_engines: Dict[str, object] = {}


def _get_db_url() -> str:
    """Liest DATABASE_URL aus der Umgebung (Pflichtfeld)."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("Umgebungsvariable DATABASE_URL ist nicht gesetzt.")
    return url


def get_tenant_db_url(schema_name: str) -> str:
    """
    Gibt eine DATABASE_URL zurück, bei der der search_path auf das Tenant-Schema
    gesetzt ist. Kann für psycopg3-Verbindungen direkt genutzt werden.

    Beispiel:
        conn_str = get_tenant_db_url(tenant.schema_name)
        with psycopg.connect(conn_str) as conn:
            ...

    Args:
        schema_name: PostgreSQL-Schema des Tenants (z.B. "tenant_meine_firma")

    Returns:
        DATABASE_URL mit options=-csearch_path=<schema>,shared,public
    """
    base_url = _get_db_url()
    search_path = f"{schema_name},shared,public"
    # psycopg3 / libpq: options=-csearch_path=... im Connection-String
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}options=-csearch_path%3D{search_path.replace(',', '%2C')}"


def get_tenant_from_db(org_id: str) -> Optional[TenantContext]:
    """
    Lädt Tenant-Metadaten und API-Key-Overrides aus dem shared-Schema.

    API-Keys werden via crypto.decrypt_value() entschlüsselt
    (Phase 1d: Klartext-Bytes; Phase 5: AES-256-GCM).

    Args:
        org_id: Clerk Organization ID (z.B. "org_abc123")

    Returns:
        TenantContext oder None wenn nicht gefunden/gesperrt
    """
    import psycopg          # lazy import: psycopg3 nur wenn DB verfügbar
    import psycopg.rows

    try:
        with psycopg.connect(_get_db_url()) as conn:
            with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                # Tenant-Zeile laden
                cur.execute(
                    """
                    SELECT id, clerk_org_id, clerk_org_slug, display_name,
                           schema_name, plan
                    FROM   shared.tenants
                    WHERE  clerk_org_id = %s
                    AND    status = 'active'
                    """,
                    (org_id,),
                )
                row = cur.fetchone()
                if not row:
                    logger.warning(f"Tenant nicht gefunden oder gesperrt: {org_id}")
                    return None

                # API-Key-Overrides laden
                cur.execute(
                    """
                    SELECT key_name, encrypted_value, iv
                    FROM   shared.tenant_api_keys
                    WHERE  tenant_id = %s
                    """,
                    (str(row["id"]),),
                )
                key_rows = cur.fetchall()

                config_overrides: Dict[str, str] = {}
                for kr in key_rows:
                    try:
                        config_overrides[kr["key_name"]] = decrypt_value(
                            bytes(kr["encrypted_value"]),
                            bytes(kr["iv"]),
                        )
                    except Exception as exc:
                        logger.warning(
                            f"API-Key Entschlüsselung fehlgeschlagen "
                            f"[tenant={org_id}, key={kr['key_name']}]: {exc}"
                        )

                return TenantContext(
                    tenant_id=str(row["id"]),
                    org_id=row["clerk_org_id"],
                    org_slug=row["clerk_org_slug"],
                    display_name=row["display_name"],
                    schema_name=row["schema_name"],
                    plan=row["plan"],
                    config_overrides=config_overrides,
                )

    except RuntimeError:
        raise
    except Exception as exc:
        logger.error(f"Tenant-DB-Abfrage fehlgeschlagen [{org_id}]: {exc}")
        return None


# ─── Self-Service: API-Keys schreiben / löschen ───────────────────────────────

def _mask_value(value: str) -> str:
    """Zeigt erste 4 + **** + letzte 4 Zeichen (oder nur **** wenn zu kurz)."""
    if len(value) > 12:
        return f"{value[:4]}****{value[-4:]}"
    return "****"


def upsert_tenant_api_key(tenant_id: str, key_name: str, plaintext: str) -> None:
    """Speichert oder aktualisiert einen API-Key eines Tenants (UPSERT)."""
    import psycopg

    encrypted, iv = encrypt_value(plaintext)
    try:
        with psycopg.connect(_get_db_url()) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO shared.tenant_api_keys
                        (tenant_id, key_name, encrypted_value, iv)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (tenant_id, key_name)
                    DO UPDATE SET
                        encrypted_value = EXCLUDED.encrypted_value,
                        iv              = EXCLUDED.iv,
                        updated_at      = NOW()
                    """,
                    (tenant_id, key_name, encrypted, iv),
                )
            conn.commit()
        logger.info(f"API-Key gespeichert: tenant={tenant_id}, key={key_name}")
    except Exception as exc:
        logger.error(f"API-Key UPSERT fehlgeschlagen [{tenant_id}/{key_name}]: {exc}")
        raise


def delete_tenant_api_key(tenant_id: str, key_name: str) -> bool:
    """Löscht einen API-Key. Gibt True zurück wenn etwas gelöscht wurde."""
    import psycopg

    try:
        with psycopg.connect(_get_db_url()) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM shared.tenant_api_keys WHERE tenant_id = %s AND key_name = %s",
                    (tenant_id, key_name),
                )
                deleted = cur.rowcount > 0
            conn.commit()
        return deleted
    except Exception as exc:
        logger.error(f"API-Key DELETE fehlgeschlagen [{tenant_id}/{key_name}]: {exc}")
        raise


def get_tenant_usage(tenant_id: str, plan: str) -> List[Dict[str, object]]:
    """Gibt Monatsverbrauch + Limits für einen Tenant zurück."""
    import psycopg
    import psycopg.rows

    try:
        with psycopg.connect(_get_db_url()) as conn:
            with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                cur.execute(
                    """
                    SELECT
                        ul.service,
                        ul.metric,
                        COALESCE(SUM(ud.value), 0)::INT AS current,
                        ul.monthly_max                  AS limit
                    FROM   shared.usage_limits ul
                    LEFT   JOIN shared.usage_daily ud
                           ON  ud.tenant_id = %s
                           AND ud.service   = ul.service
                           AND ud.metric    = ul.metric
                           AND ud.date >= date_trunc('month', CURRENT_DATE)
                    WHERE  ul.plan = %s
                    GROUP  BY ul.service, ul.metric, ul.monthly_max
                    ORDER  BY ul.service, ul.metric
                    """,
                    (tenant_id, plan),
                )
                return [dict(r) for r in cur.fetchall()]
    except Exception as exc:
        logger.error(f"Usage-Abfrage fehlgeschlagen [{tenant_id}]: {exc}")
        return []


def list_tenant_api_keys_masked(tenant_id: str) -> List[Dict[str, object]]:
    """Gibt API-Keys mit maskierten Werten zurück."""
    import psycopg
    import psycopg.rows

    try:
        with psycopg.connect(_get_db_url()) as conn:
            with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                cur.execute(
                    """
                    SELECT key_name, encrypted_value, iv
                    FROM   shared.tenant_api_keys
                    WHERE  tenant_id = %s
                    ORDER  BY key_name
                    """,
                    (tenant_id,),
                )
                result = []
                for kr in cur.fetchall():
                    try:
                        plain = decrypt_value(bytes(kr["encrypted_value"]), bytes(kr["iv"]))
                        masked = _mask_value(plain)
                    except Exception:
                        masked = "****"
                    result.append({"key_name": kr["key_name"], "masked": masked})
                return result
    except Exception as exc:
        logger.error(f"API-Key-Liste fehlgeschlagen [{tenant_id}]: {exc}")
        return []
