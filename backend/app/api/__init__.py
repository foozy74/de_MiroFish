"""
API-Routing-Modul
"""

from flask import Blueprint

graph_bp = Blueprint('graph', __name__)
simulation_bp = Blueprint('simulation', __name__)
report_bp = Blueprint('report', __name__)
tenant_bp = Blueprint('tenant_self_service', __name__)

from . import graph     # noqa: E402, F401
from . import simulation  # noqa: E402, F401
from . import report    # noqa: E402, F401
from . import tenant    # noqa: E402, F401

