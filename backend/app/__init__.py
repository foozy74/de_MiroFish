"""
MiroFish Backend - Flask-Anwendungsfabrik
"""

import os
import warnings

# Unterdrückt Warnungen von multiprocessing resource_tracker (von Bibliotheken von Drittanbietern wie transformers)
# Muss vor allen anderen Importen eingestellt werden
warnings.filterwarnings("ignore", message=".*resource_tracker.*")

from flask import Flask, request
from flask_cors import CORS
from dotenv import load_dotenv

# .env laden
load_dotenv()

from .config import Config
from .utils.logger import setup_logger, get_logger


def create_app(config_class=Config):
    """Flask-Anwendungsfabrikfunktion"""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # JSON-Kodierung einstellen: Stellt sicher, dass chinesische Zeichen direkt angezeigt werden
    # Flask >= 2.3 verwendet app.json.ensure_ascii, ältere Versionen verwenden JSON_AS_ASCII Konfiguration
    if hasattr(app, 'json') and hasattr(app.json, 'ensure_ascii'):
        app.json.ensure_ascii = False
    
    # Protokollierung einrichten
    logger = setup_logger('mirofish')
    
    # Startinformationen nur im reloader-Unterprozess drucken (vermeidet doppeltes Drucken im debug-Modus)
    is_reloader_process = os.environ.get('WERKZEUG_RUN_MAIN') == 'true'
    debug_mode = app.config.get('DEBUG', False)
    should_log_startup = not debug_mode or is_reloader_process
    
    if should_log_startup:
        logger.info("=" * 50)
        logger.info("MiroFish Backend wird gestartet...")
        logger.info("=" * 50)
    
    # CORS aktivieren
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    # Simulationsprozess-Bereinigungsfunktion registrieren (stellt sicher, dass alle Simulationsprozesse beendet werden, wenn der Server herunterfährt)
    from .services.simulation_runner import SimulationRunner
    SimulationRunner.register_cleanup()
    if should_log_startup:
        logger.info("Simulationsprozess-Bereinigungsfunktion registriert")
    
    # Anfrage-Protokoll-Middleware
    @app.before_request
    def log_request():
        logger = get_logger('mirofish.request')
        logger.debug(f"Anfrage: {request.method} {request.path}")
        if request.content_type and 'json' in request.content_type:
            logger.debug(f"Anfrageinhalt: {request.get_json(silent=True)}")
    
    @app.after_request
    def log_response(response):
        logger = get_logger('mirofish.request')
        logger.debug(f"Antwort: {response.status_code}")
        return response
    
    # Blueprint registrieren
    from .api import graph_bp, simulation_bp, report_bp, tenant_bp
    app.register_blueprint(graph_bp, url_prefix='/api/graph')
    app.register_blueprint(simulation_bp, url_prefix='/api/simulation')
    app.register_blueprint(report_bp, url_prefix='/api/report')
    app.register_blueprint(tenant_bp, url_prefix='/api/tenant')
    
    # Gesundheitsprüfung
    @app.route('/health')
    def health():
        return {'status': 'ok', 'service': 'MiroFish Backend'}
    
    if should_log_startup:
        logger.info("MiroFish Backend Start abgeschlossen")
    
    return app

