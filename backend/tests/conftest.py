"""
pytest conftest für MiroFish Backend Tests

Mockt schwere externe Abhängigkeiten (openai, camel-ai, zep-cloud, PyMuPDF)
die nicht in der Test-Umgebung installiert sein müssen.
Die Tests für das Tenant-Modul benötigen nur flask, loguru, PyJWT.
"""

import sys
from unittest.mock import MagicMock

# Externe Abhängigkeiten die im Tenant-Modul selbst NICHT benötigt werden,
# aber über den app.*-Importpfad eingebunden würden.
_EXTERNAL_MODULES = [
    "flask_cors",
    "openai",
    "zep_cloud",
    "camel",
    "camel.agents",
    "camel.societies",
    "oasis",
    "camel_oasis",
    "fitz",          # PyMuPDF
    "chardet",
    "charset_normalizer",
]

for _mod in _EXTERNAL_MODULES:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()
