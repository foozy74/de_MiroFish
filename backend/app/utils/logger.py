"""
Protokollierung-Konfigurationsmodul
Bietet eine einheitliche Protokollierungsverwaltung, die sowohl zur Konsole als auch zur Datei ausgibt
"""

import os
import sys
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler


def _ensure_utf8_stdout():
    """
    Stellt sicher, dass stdout/stderr UTF-8-Kodierung verwenden
    Löst das Problem der chinesischen Zeichen in der Windows-Konsole
    """
    if sys.platform == 'win32':
        # Konfiguriert Standardausgabe unter Windows auf UTF-8 um
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')


# Protokollierungsverzeichnis
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')


def setup_logger(name: str = 'mirofish', level: int = logging.DEBUG) -> logging.Logger:
    """
    Richtet den Logger ein
    
    Args:
        name: Logger-Name
        level: Protokollierungsstufe
        
    Returns:
        Konfigurierter Logger
    """
    # Stellt sicher, dass das Protokollierungsverzeichnis existiert
    os.makedirs(LOG_DIR, exist_ok=True)
    
    # Erstellt den Logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Verhindert die Weiterleitung von Protokollen an den Root-Logger, um doppelte Ausgaben zu vermeiden
    logger.propagate = False
    
    # Wenn bereits Handler vorhanden sind, werden keine weiteren hinzugefügt
    if logger.handlers:
        return logger
    
    # Protokollierungsformat
    detailed_formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s: %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # 1. Datei-Handler - Detaillierte Protokolle (nach Datum benannt, mit Rotation)
    try:
        log_filename = datetime.now().strftime('%Y-%m-%d') + '.log'
        file_path = os.path.join(LOG_DIR, log_filename)
        file_handler = RotatingFileHandler(
            file_path,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        # Wenn wir nicht in eine Datei schreiben können (z.B. Berechtigungsprobleme bei Bind-Mounts),
        # loggen wir nur auf die Konsole.
        print(f"WARNUNG: Konnte Datei-Logger nicht initialisieren (eventuell fehlende Schreibrechte): {e}")
    
    # 2. Konsolen-Handler - Kurzformat (INFO und höher)
    # Stellt sicher, dass unter Windows UTF-8-Kodierung verwendet wird, um Zeichencodierungsprobleme zu vermeiden
    _ensure_utf8_stdout()
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    
    # Fügt Handler hinzu
    logger.addHandler(console_handler)
    
    return logger


def get_logger(name: str = 'mirofish') -> logging.Logger:
    """
    Ruft den Logger ab (erstellt ihn, falls nicht vorhanden)
    
    Args:
        name: Logger-Name
        
    Returns:
        Logger-Instanz
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        return setup_logger(name)
    return logger


# Erstellt den Standard-Logger
logger = setup_logger()


# Hilfsmethoden
def debug(msg, *args, **kwargs):
    logger.debug(msg, *args, **kwargs)

def info(msg, *args, **kwargs):
    logger.info(msg, *args, **kwargs)

def warning(msg, *args, **kwargs):
    logger.warning(msg, *args, **kwargs)

def error(msg, *args, **kwargs):
    logger.error(msg, *args, **kwargs)

def critical(msg, *args, **kwargs):
    logger.critical(msg, *args, **kwargs)

