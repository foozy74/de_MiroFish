"""
Tests für das MiroFish Tenant-Modul

Getestet werden:
- crypto.py: AES-256-GCM + Klartext-Modus
- context.py: TenantContext Datenstruktur
- settings_override.py: TenantConfig Proxy
- middleware.py: require_tenant Dekorator (Flask-Testclient)
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Sicherstellen, dass 'app' als Package gefunden wird
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

_VALID_MASTER_KEY = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="  # 32 Null-Bytes in Base64


# ─── crypto ───────────────────────────────────────────────────────────────────

class TestCrypto(unittest.TestCase):

    def setUp(self):
        import app.tenant.crypto as c
        c._cached_key = None
        c._cached_key_b64 = None

    def tearDown(self):
        os.environ.pop("DERFISH_MASTER_KEY", None)
        import app.tenant.crypto as c
        c._cached_key = None
        c._cached_key_b64 = None

    # ── Klartext-Modus ────────────────────────────────────────

    def test_encrypt_decrypt_roundtrip_no_master_key(self):
        from app.tenant.crypto import decrypt_value, encrypt_value

        plaintext = "sk-mirofish-test-key"
        enc_bytes, iv = encrypt_value(plaintext)
        self.assertEqual(decrypt_value(enc_bytes, iv), plaintext)

    def test_encrypt_produces_utf8_bytes_without_master_key(self):
        from app.tenant.crypto import encrypt_value

        enc_bytes, iv = encrypt_value("mykey")
        self.assertEqual(enc_bytes, b"mykey")
        self.assertEqual(iv, b"\x00" * 16)

    # ── Legacy-Kompatibilität ─────────────────────────────────

    def test_decrypt_legacy_null_iv_with_master_key(self):
        """Null-IV = Klartext, auch wenn MASTER_KEY gesetzt."""
        from app.tenant.crypto import decrypt_value

        os.environ["DERFISH_MASTER_KEY"] = _VALID_MASTER_KEY
        self.assertEqual(decrypt_value(b"legacy-value", b"\x00" * 16), "legacy-value")

    # ── AES-256-GCM ───────────────────────────────────────────

    def test_encrypt_decrypt_roundtrip_with_master_key(self):
        from app.tenant.crypto import decrypt_value, encrypt_value

        os.environ["DERFISH_MASTER_KEY"] = _VALID_MASTER_KEY
        plaintext = "sk-prod-zep-key"
        enc_bytes, iv = encrypt_value(plaintext)

        self.assertEqual(len(iv), 12)
        self.assertNotEqual(enc_bytes, plaintext.encode())
        self.assertEqual(decrypt_value(enc_bytes, iv), plaintext)

    def test_encrypt_uses_random_iv(self):
        from app.tenant.crypto import encrypt_value

        os.environ["DERFISH_MASTER_KEY"] = _VALID_MASTER_KEY
        _, iv1 = encrypt_value("same")
        _, iv2 = encrypt_value("same")
        self.assertNotEqual(iv1, iv2)

    def test_tampered_ciphertext_raises(self):
        from app.tenant.crypto import decrypt_value, encrypt_value

        os.environ["DERFISH_MASTER_KEY"] = _VALID_MASTER_KEY
        enc_bytes, iv = encrypt_value("secret")
        tampered = bytes([enc_bytes[0] ^ 0xFF]) + enc_bytes[1:]
        with self.assertRaises(Exception):
            decrypt_value(tampered, iv)

    def test_invalid_base64_master_key_raises(self):
        from app.tenant.crypto import encrypt_value

        os.environ["DERFISH_MASTER_KEY"] = "nicht-base64!!!"
        with self.assertRaises(ValueError):
            encrypt_value("x")

    def test_wrong_length_master_key_raises(self):
        import base64
        from app.tenant.crypto import encrypt_value

        os.environ["DERFISH_MASTER_KEY"] = base64.b64encode(b"\x00" * 16).decode()
        with self.assertRaises(ValueError):
            encrypt_value("x")


# ─── context ──────────────────────────────────────────────────────────────────

class TestTenantContext(unittest.TestCase):

    def test_context_creation(self):
        from app.tenant.context import TenantContext

        ctx = TenantContext(
            tenant_id="uuid-miro",
            org_id="org_miro",
            org_slug="mirofish-org",
            display_name="MiroFish GmbH",
            schema_name="tenant_mirofish_org",
            plan="pro",
            config_overrides={
                "LLM_API_KEY": "sk-tenant-key",
                "ZEP_API_KEY": "zep-tenant-key",
            },
        )
        self.assertEqual(ctx.plan, "pro")
        self.assertEqual(ctx.config_overrides["LLM_API_KEY"], "sk-tenant-key")

    def test_context_defaults_empty_overrides(self):
        from app.tenant.context import TenantContext

        ctx = TenantContext(
            tenant_id="u",
            org_id="o",
            org_slug="s",
            display_name="T",
            schema_name="tenant_t",
            plan="free",
        )
        self.assertEqual(ctx.config_overrides, {})


# ─── settings_override ────────────────────────────────────────────────────────

class TestTenantConfig(unittest.TestCase):

    def test_falls_back_to_config_outside_flask_context(self):
        """Außerhalb Flask-Kontext → Config-Klassenattribute."""
        from app.tenant.settings_override import TenantConfig
        # app.config.Config.LLM_API_KEY ist None wenn kein .env geladen
        cfg = TenantConfig()
        # Darf keine Exception werfen, fällt auf Config.LLM_API_KEY zurück
        try:
            val = cfg.LLM_API_KEY
        except AttributeError:
            self.fail("TenantConfig.LLM_API_KEY sollte kein AttributeError werfen")

    def test_override_within_flask_context(self):
        from flask import Flask
        from app.tenant.context import TenantContext
        from app.tenant.settings_override import TenantConfig

        app = Flask(__name__)
        cfg = TenantConfig()

        with app.test_request_context("/"):
            from flask import g
            g.tenant = TenantContext(
                tenant_id="uuid-t",
                org_id="org_t",
                org_slug="t",
                display_name="T",
                schema_name="tenant_t",
                plan="pro",
                config_overrides={
                    "LLM_API_KEY": "sk-override",
                    "ZEP_API_KEY": "zep-override",
                },
            )
            self.assertEqual(cfg.LLM_API_KEY, "sk-override")
            self.assertEqual(cfg.ZEP_API_KEY, "zep-override")

    def test_partial_override_falls_back_for_missing_keys(self):
        from flask import Flask
        from app.tenant.context import TenantContext
        from app.tenant.settings_override import TenantConfig

        app = Flask(__name__)
        cfg = TenantConfig()

        with app.test_request_context("/"):
            from flask import g
            g.tenant = TenantContext(
                tenant_id="u",
                org_id="o",
                org_slug="s",
                display_name="T",
                schema_name="tenant_t",
                plan="free",
                config_overrides={"LLM_API_KEY": "sk-override"},
            )
            # LLM_API_KEY überschrieben
            self.assertEqual(cfg.LLM_API_KEY, "sk-override")
            # LLM_BASE_URL nicht überschrieben → Config.LLM_BASE_URL
            from app.config import Config
            self.assertEqual(cfg.LLM_BASE_URL, Config.LLM_BASE_URL)

    def test_setattr_raises(self):
        from app.tenant.settings_override import TenantConfig

        cfg = TenantConfig()
        with self.assertRaises(AttributeError):
            cfg.LLM_API_KEY = "neuer-key"

    def test_unknown_attribute_raises(self):
        from app.tenant.settings_override import TenantConfig

        cfg = TenantConfig()
        with self.assertRaises(AttributeError):
            _ = cfg.DOES_NOT_EXIST


# ─── middleware ───────────────────────────────────────────────────────────────

class TestRequireTenantDecorator(unittest.TestCase):

    def _make_app(self):
        from flask import Flask, g, jsonify
        from app.tenant.middleware import require_tenant

        app = Flask(__name__)

        @app.route("/api/sim", methods=["GET"])
        @require_tenant
        def sim():
            return jsonify({"schema": g.tenant.schema_name, "plan": g.tenant.plan})

        return app

    def test_missing_auth_header_returns_401(self):
        app = self._make_app()
        resp = app.test_client().get("/api/sim")
        self.assertEqual(resp.status_code, 401)
        self.assertIn("Authentifizierung", resp.get_json()["error"])

    def test_missing_jwks_url_returns_500(self):
        os.environ.pop("CLERK_JWKS_URL", None)
        app = self._make_app()
        resp = app.test_client().get("/api/sim", headers={"Authorization": "Bearer tok"})
        self.assertEqual(resp.status_code, 500)

    @patch("app.tenant.middleware.validate_clerk_token")
    @patch("app.tenant.middleware.get_tenant_from_db")
    def test_valid_token_sets_g_tenant(self, mock_db, mock_jwt):
        from app.tenant.context import TenantContext

        mock_jwt.return_value = {"sub": "user_1", "org_id": "org_miro"}
        mock_db.return_value = TenantContext(
            tenant_id="u1",
            org_id="org_miro",
            org_slug="miro",
            display_name="Miro",
            schema_name="tenant_miro",
            plan="pro",
        )
        os.environ["CLERK_JWKS_URL"] = "https://example.clerk.dev/.well-known/jwks.json"
        app = self._make_app()
        resp = app.test_client().get("/api/sim", headers={"Authorization": "Bearer valid"})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["schema"], "tenant_miro")
        self.assertEqual(data["plan"], "pro")

    @patch("app.tenant.middleware.validate_clerk_token")
    def test_token_without_org_id_returns_403(self, mock_jwt):
        mock_jwt.return_value = {"sub": "user_1"}  # kein org_id
        os.environ["CLERK_JWKS_URL"] = "https://example.clerk.dev/.well-known/jwks.json"
        resp = self._make_app().test_client().get(
            "/api/sim", headers={"Authorization": "Bearer tok"}
        )
        self.assertEqual(resp.status_code, 403)

    @patch("app.tenant.middleware.validate_clerk_token")
    @patch("app.tenant.middleware.get_tenant_from_db")
    def test_unknown_tenant_returns_403(self, mock_db, mock_jwt):
        mock_jwt.return_value = {"sub": "u", "org_id": "org_unknown"}
        mock_db.return_value = None
        os.environ["CLERK_JWKS_URL"] = "https://example.clerk.dev/.well-known/jwks.json"
        resp = self._make_app().test_client().get(
            "/api/sim", headers={"Authorization": "Bearer tok"}
        )
        self.assertEqual(resp.status_code, 403)

    @patch("app.tenant.middleware.validate_clerk_token")
    def test_expired_token_returns_401(self, mock_jwt):
        import jwt as pyjwt
        mock_jwt.side_effect = pyjwt.ExpiredSignatureError("abgelaufen")
        os.environ["CLERK_JWKS_URL"] = "https://example.clerk.dev/.well-known/jwks.json"
        resp = self._make_app().test_client().get(
            "/api/sim", headers={"Authorization": "Bearer expired"}
        )
        self.assertEqual(resp.status_code, 401)
        self.assertIn("abgelaufen", resp.get_json()["error"])

    @patch("app.tenant.middleware.validate_clerk_token")
    def test_invalid_token_returns_401(self, mock_jwt):
        import jwt as pyjwt
        mock_jwt.side_effect = pyjwt.InvalidTokenError("bad sig")
        os.environ["CLERK_JWKS_URL"] = "https://example.clerk.dev/.well-known/jwks.json"
        resp = self._make_app().test_client().get(
            "/api/sim", headers={"Authorization": "Bearer bad"}
        )
        self.assertEqual(resp.status_code, 401)


# ─── db helpers ───────────────────────────────────────────────────────────────

class TestTenantDbHelpers(unittest.TestCase):

    def test_get_tenant_db_url_appends_search_path(self):
        from app.tenant.db import get_tenant_db_url

        os.environ["DATABASE_URL"] = "postgresql://user:pass@host:5432/db"
        url = get_tenant_db_url("tenant_myorg")
        self.assertIn("search_path", url)
        self.assertIn("tenant_myorg", url)
        self.assertIn("shared", url)

    def test_get_tenant_db_url_missing_database_url(self):
        from app.tenant.db import get_tenant_db_url

        os.environ.pop("DATABASE_URL", None)
        with self.assertRaises(RuntimeError):
            get_tenant_db_url("tenant_x")


if __name__ == "__main__":
    unittest.main()
