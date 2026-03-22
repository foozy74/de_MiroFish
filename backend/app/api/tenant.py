"""
Tenant Self-Service API (MiroFish)

Routen (alle mit @require_tenant geschützt):
    GET  /api/tenant/info            → Tenant-Info + gemaskerte Keys + Verbrauch
    PUT  /api/tenant/keys            → API-Key speichern / aktualisieren
    DELETE /api/tenant/keys/<name>   → API-Key entfernen
"""

from flask import g, jsonify, request

from . import tenant_bp
from ..tenant.middleware import require_tenant
from ..tenant.db import (
    delete_tenant_api_key,
    get_tenant_usage,
    list_tenant_api_keys_masked,
    upsert_tenant_api_key,
)

ALLOWED_KEY_NAMES: frozenset = frozenset({
    "LLM_API_KEY",
    "LLM_BASE_URL",
    "LLM_MODEL_NAME",
    "ZEP_API_KEY",
})


@tenant_bp.get("/info")
@require_tenant
def tenant_info():
    """Gibt Tenant-Metadaten, gemaskerte Keys und Monatsverbrauch zurück."""
    tenant = g.tenant
    keys = list_tenant_api_keys_masked(tenant.tenant_id)
    usage = get_tenant_usage(tenant.tenant_id, tenant.plan)
    return jsonify({
        "tenant": {
            "id":           tenant.tenant_id,
            "display_name": tenant.display_name,
            "plan":         tenant.plan,
            "org_slug":     tenant.org_slug,
        },
        "keys":  keys,
        "usage": usage,
    })


@tenant_bp.put("/keys")
@require_tenant
def upsert_key():
    """Speichert oder aktualisiert einen API-Key."""
    tenant = g.tenant
    body = request.get_json(silent=True) or {}
    key_name = body.get("key_name", "").strip()
    value = body.get("value", "").strip()

    if not key_name:
        return jsonify({"error": "key_name fehlt"}), 400
    if key_name not in ALLOWED_KEY_NAMES:
        return jsonify({"error": f"key_name '{key_name}' nicht erlaubt"}), 400
    if not value:
        return jsonify({"error": "value darf nicht leer sein"}), 400
    if len(value) > 512:
        return jsonify({"error": "value zu lang (max. 512 Zeichen)"}), 400

    upsert_tenant_api_key(tenant.tenant_id, key_name, value)
    return jsonify({"ok": True, "key_name": key_name}), 200


@tenant_bp.delete("/keys/<key_name>")
@require_tenant
def delete_key(key_name: str):
    """Löscht einen API-Key des Tenants."""
    tenant = g.tenant
    key_name = key_name.strip()

    if key_name not in ALLOWED_KEY_NAMES:
        return jsonify({"error": f"key_name '{key_name}' nicht erlaubt"}), 400

    deleted = delete_tenant_api_key(tenant.tenant_id, key_name)
    if not deleted:
        return jsonify({"error": "Key nicht gefunden"}), 404
    return jsonify({"ok": True, "key_name": key_name}), 200
