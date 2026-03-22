"""
TenantConfig — Config-Proxy mit Tenant-spezifischen API-Key-Overrides (MiroFish)

MiroFish nutzt eine Klassen-basierte Config (nicht Pydantic). TenantConfig
legt sich darüber und überschreibt Attribute wenn ein Tenant-Override vorhanden ist.

Verwendung in Services:

    # Statt:
    from app.config import Config
    api_key = Config.LLM_API_KEY

    # Verwenden:
    from app.tenant.settings_override import TenantConfig
    cfg = TenantConfig()
    api_key = cfg.LLM_API_KEY    # Tenant-Key oder System-Default

    # Beim Erstellen eines LLMClient:
    from app.utils.llm_client import LLMClient
    from app.tenant.settings_override import TenantConfig

    def get_llm_client() -> LLMClient:
        cfg = TenantConfig()
        return LLMClient(
            api_key=cfg.LLM_API_KEY,
            base_url=cfg.LLM_BASE_URL,
            model=cfg.LLM_MODEL_NAME,
        )

Bekannte MiroFish Config-Keys (werden als config_overrides gespeichert):
    LLM_API_KEY
    LLM_BASE_URL
    LLM_MODEL_NAME
    ZEP_API_KEY
"""

from typing import Any, Optional

from app.utils.logger import get_logger

logger = get_logger("mirofish.tenant.settings")


def _get_tenant_override(key: str) -> Optional[str]:
    """
    Liest den Tenant-spezifischen Wert aus flask.g.tenant.

    Gibt None zurück wenn:
    - Kein Flask-Kontext vorhanden (außerhalb eines Requests)
    - g.tenant nicht gesetzt
    - Key nicht in config_overrides
    """
    try:
        from flask import g
        tenant = getattr(g, "tenant", None)
        if tenant and tenant.config_overrides:
            return tenant.config_overrides.get(key)
    except RuntimeError:
        # Außerhalb des Flask-Request-Kontexts (z.B. CLI)
        pass
    return None


class TenantConfig:
    """
    Read-only Proxy über app.config.Config mit Tenant-Overrides.

    Instanziiert werden muss die Klasse pro Request:
        cfg = TenantConfig()

    Attribute-Zugriff:
    1. Prüft flask.g.tenant.config_overrides auf einen Wert für den Key
    2. Fällt auf Config.KEY zurück (Klassen-Attribut)
    """

    def __getattr__(self, name: str) -> Any:
        override = _get_tenant_override(name)
        if override is not None:
            logger.debug(f"TenantConfig: Override für '{name}' aktiv")
            return override

        from app.config import Config
        try:
            return getattr(Config, name)
        except AttributeError:
            raise AttributeError(
                f"TenantConfig: '{name}' ist weder ein Tenant-Override "
                f"noch ein Config-Attribut."
            )

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError(
            "TenantConfig ist ein read-only Proxy. "
            "Schreibe direkt in shared.tenant_api_keys über die Admin-API."
        )

    def __repr__(self) -> str:
        return "TenantConfig(proxy über app.config.Config mit Tenant-Overrides)"
