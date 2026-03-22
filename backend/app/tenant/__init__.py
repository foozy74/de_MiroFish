"""
MiroFish Tenant-Modul

Stellt Tenant-Isolation für Multi-Tenant-Betrieb bereit:
- JWT-Validierung via Clerk JWKS
- Tenant-Kontext (schema_name, plan, config_overrides)
- TenantConfig-Proxy für LLM_* und ZEP_API_KEY Overrides

Verwendung:
    from app.tenant.middleware import require_tenant
    from app.tenant.context import TenantContext
    from app.tenant.settings_override import TenantConfig
    from flask import g

    @simulation_bp.route("/start", methods=["POST"])
    @require_tenant
    def start_simulation():
        tenant: TenantContext = g.tenant
        cfg = TenantConfig()
        # cfg.LLM_API_KEY, cfg.ZEP_API_KEY → Tenant-Keys oder System-Defaults
        ...
"""

__all__ = ["TenantContext", "require_tenant", "TenantConfig"]


def __getattr__(name: str):
    if name == "TenantContext":
        from .context import TenantContext
        return TenantContext
    if name == "require_tenant":
        from .middleware import require_tenant
        return require_tenant
    if name == "TenantConfig":
        from .settings_override import TenantConfig
        return TenantConfig
    raise AttributeError(f"module 'app.tenant' hat kein Attribut '{name}'")
