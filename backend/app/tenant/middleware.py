"""
Flask Tenant-Middleware (MiroFish)

Stellt den require_tenant-Dekorator bereit.
Unterstützt JWT-Validierung via Clerk sowie einen lokalen Entwicklungs-Fallback.
"""

import os
from functools import wraps
from typing import Optional

import jwt as pyjwt
from flask import g, jsonify, request

from app.utils.logger import get_logger
from .db import get_tenant_from_db
from .jwt_validator import validate_clerk_token

logger = get_logger("mirofish.tenant.middleware")

def _is_development_mode() -> bool:
    """Prüft ob wir uns im Entwicklungsmodus befinden."""
    # Wir prüfen verschiedene gängige Variablen
    flask_debug = os.environ.get("FLASK_DEBUG", "true").lower() == "true"
    flask_env = os.environ.get("FLASK_ENV", "").lower() == "development"
    miro_env = os.environ.get("MIROFISH_ENV", "").lower() == "development"
    return flask_debug or flask_env or miro_env

def require_tenant(f):
    """
    Flask-Dekorator: Validiert Clerk JWT und lädt den Tenant-Kontext.
    Unterstützt lokalen Fallback für Entwicklung.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        org_id = None
        
        # 1. Versuch: Bearer Token (Clerk JWT)
        if auth_header.startswith("Bearer "):
            token = auth_header[len("Bearer "):]
            jwks_url = os.environ.get("CLERK_JWKS_URL", "")
            if jwks_url:
                try:
                    payload = validate_clerk_token(token, jwks_url)
                    org_id = payload.get("org_id")
                except Exception as exc:
                    logger.warning(f"JWT-Validierung fehlgeschlagen: {exc}")
                    # Wenn ein Token da war aber ungültig ist, lehnen wir ab
                    return jsonify({"error": f"Ungültiges Token: {str(exc)}"}), 401
        
        # 2. Versuch: Direkte org_id im Header (für lokale API-Tests via Postman/Curl)
        if not org_id and auth_header and not auth_header.startswith("Bearer "):
            org_id = auth_header
            logger.debug(f"Nutze direkte org_id aus Header: {org_id}")
        
        # 3. Versuch: Automatischer Fallback in lokaler Umgebung
        if not org_id:
            if _is_development_mode():
                org_id = "org_test_local"
                logger.debug(f"Automatischer Fallback auf Tenant: {org_id}")
            else:
                logger.warning("Keine Authentifizierung im Header und kein Entwicklungsmodus aktiv")
                return jsonify({"error": "Authentifizierung erforderlich"}), 401

        # Tenant-Daten aus shared.db laden
        tenant = get_tenant_from_db(org_id)
        if not tenant:
            logger.warning(f"Mandant nicht gefunden: {org_id}")
            return jsonify({
                "error": "Mandant nicht gefunden oder gesperrt",
                "org_id": org_id,
            }), 403

        # Kontext im globalen Flask-Objekt speichern
        g.tenant = tenant
        return f(*args, **kwargs)

    return decorated
