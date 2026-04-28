"""
Tenant-Kontext-Datenstruktur für MiroFish

Wird pro Request in flask.g.tenant gespeichert.
"""

from dataclasses import dataclass, field
from typing import Dict


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
        config_overrides: Mapping von Settings-Key → Klartext-Wert
                          (z.B. {"LLM_API_KEY": "sk-...", "ZEP_API_KEY": "zep-..."})
    """

    tenant_id: str
    org_id: str = "default"
    org_slug: str = "default"
    display_name: str = "Default Tenant"
    schema_name: str = "public"
    plan: str = "free"
    config_overrides: Dict[str, str] = field(default_factory=dict)
