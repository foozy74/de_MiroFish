"""
OASIS Twitter-Simulationsskript
Dieses Skript liest Parameter aus der Konfigurationsdatei aus, um die Simulation automatisch auszuführen

Funktionen:
- Nach Simulationsende nicht sofort beenden, sondern in Befehlswarte-Modus wechseln
- Unterstützung für Interview-Befehle über IPC
- Einzelne Agent-Interviews und Batch-Interviews
- Remote-Befehl zum Schließen der Umgebung

Verwendung:
    python run_twitter_simulation.py --config /path/to/simulation_config.json
    python run_twitter_simulation.py --config /path/to/simulation_config.json --no-wait  # Nach Fertigstellung sofort beenden
"""

import argparse
import asyncio
import json
import logging
import os
import random
import signal
import sys
import sqlite3
from datetime import datetime
from typing import Dict, Any, List, Optional

# Globale Variablen: für Signalverarbeitung
_shutdown_event = None
_cleanup_done = False

# Backend-Verzeichnis zum Pfad hinzufügen
_scripts_dir = os.path.dirname(os.path.abspath(__file__))
_backend_dir = os.path.abspath(os.path.join(_scripts_dir, '..'))
_project_root = os.path.abspath(os.path.join(_backend_dir, '..'))
sys.path.insert(0, _scripts_dir)
sys.path.insert(0, _backend_dir)

# .env-Datei im Projektstammverzeichnis laden (enthält LLM_API_KEY usw.)
from dotenv import load_dotenv
_env_file = os.path.join(_project_root, '.env')
if os.path.exists(_env_file):
    load_dotenv(_env_file)
else:
    _backend_env = os.path.join(_backend_dir, '.env')
    if os.path.exists(_backend_env):
        load_dotenv(_backend_env)


import re


class UnicodeFormatter(logging.Formatter):
    """Benutzerdefinierter Formatter, der Unicode-Escape-Sequenzen in lesbare Zeichen umwandelt"""
    
    UNICODE_ESCAPE_PATTERN = re.compile(r'\\u([0-9a-fA-F]{4})')
    
    def format(self, record):
        result = super().format(record)
        
        def replace_unicode(match):
            try:
                return chr(int(match.group(1), 16))
            except (ValueError, OverflowError):
                return match.group(0)
        
        return self.UNICODE_ESCAPE_PATTERN.sub(replace_unicode, result)


class MaxTokensWarningFilter(logging.Filter):
    """Filtert camel-ai-Warnungen zu max_tokens (wir setzen absichtlich kein max_tokens, damit das Modell selbst entscheidet)"""
    
    def filter(self, record):
        # Warnungen mit max_tokens herausfiltern
        if "max_tokens" in record.getMessage() and "Invalid or missing" in record.getMessage():
            return False
        return True


# Filter sofort beim Modul-Laden hinzufügen, um sicherzustellen, dass er vor der camel-Code-Ausführung aktiv ist
logging.getLogger().addFilter(MaxTokensWarningFilter())


def setup_oasis_logging(log_dir: str):
    """OASIS-Protokollierung konfigurieren, mit festen Protokolldateinamen"""
    os.makedirs(log_dir, exist_ok=True)
    
    # Alte Protokolldateien bereinigen
    for f in os.listdir(log_dir):
        old_log = os.path.join(log_dir, f)
        if os.path.isfile(old_log) and f.endswith('.log'):
            try:
                os.remove(old_log)
            except OSError:
                pass
    
    formatter = UnicodeFormatter("%(levelname)s - %(asctime)s - %(name)s - %(message)s")
    
    loggers_config = {
        "social.agent": os.path.join(log_dir, "social.agent.log"),
        "social.twitter": os.path.join(log_dir, "social.twitter.log"),
        "social.rec": os.path.join(log_dir, "social.rec.log"),
        "oasis.env": os.path.join(log_dir, "oasis.env.log"),
        "table": os.path.join(log_dir, "table.log"),
    }
    
    for logger_name, log_file in loggers_config.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)
        logger.handlers.clear()
        file_handler = logging.FileHandler(log_file, encoding='utf-8', mode='w')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.propagate = False


try:
    from camel.models import ModelFactory
    from camel.types import ModelPlatformType
    import oasis
    from oasis import (
        ActionType,
        LLMAction,
        ManualAction,
        generate_twitter_agent_graph
    )
except ImportError as e:
    print(f"Fehler: Fehlende Abhängigkeit {e}")
    print("Bitte zuerst installieren: pip install oasis-ai camel-ai")
    sys.exit(1)


# IPC-bezogene Konstanten
IPC_COMMANDS_DIR = "ipc_commands"
IPC_RESPONSES_DIR = "ipc_responses"
ENV_STATUS_FILE = "env_status.json"

class CommandType:
    """Befehlstyp-Konstanten"""
    INTERVIEW = "interview"
    BATCH_INTERVIEW = "batch_interview"
    CLOSE_ENV = "close_env"


class IPCHandler:
    """IPC-Befehlsprozessor"""
    
    def __init__(self, simulation_dir: str, env, agent_graph):
        self.simulation_dir = simulation_dir
        self.env = env
        self.agent_graph = agent_graph
        self.commands_dir = os.path.join(simulation_dir, IPC_COMMANDS_DIR)
        self.responses_dir = os.path.join(simulation_dir, IPC_RESPONSES_DIR)
        self.status_file = os.path.join(simulation_dir, ENV_STATUS_FILE)
        self._running = True
        
        # Sicherstellen, dass das Verzeichnis existiert
        os.makedirs(self.commands_dir, exist_ok=True)
        os.makedirs(self.responses_dir, exist_ok=True)
    
    def update_status(self, status: str):
        """Umgebungsstatus aktualisieren"""
        with open(self.status_file, 'w', encoding='utf-8') as f:
            json.dump({
                "status": status,
                "timestamp": datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=2)
    
    def poll_command(self) -> Optional[Dict[str, Any]]:
        """Befehle abrufen (Polling)"""
        if not os.path.exists(self.commands_dir):
            return None
        
        # Befehlsdateien abrufen (nach Zeit sortiert)
        command_files = []
        for filename in os.listdir(self.commands_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(self.commands_dir, filename)
                command_files.append((filepath, os.path.getmtime(filepath)))
        
        command_files.sort(key=lambda x: x[1])
        
        for filepath, _ in command_files:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                continue
        
        return None
    
    def send_response(self, command_id: str, status: str, result: Dict = None, error: str = None):
        """Antwort senden"""
        response = {
            "command_id": command_id,
            "status": status,
            "result": result,
            "error": error,
            "timestamp": datetime.now().isoformat()
        }
        
        response_file = os.path.join(self.responses_dir, f"{command_id}.json")
        with open(response_file, 'w', encoding='utf-8') as f:
            json.dump(response, f, ensure_ascii=False, indent=2)
        
        # Befehlsdatei löschen
        command_file = os.path.join(self.commands_dir, f"{command_id}.json")
        try:
            os.remove(command_file)
        except OSError:
            pass
    
    async def handle_interview(self, command_id: str, agent_id: int, prompt: str) -> bool:
        """
        Einzelnen Agent-Interview-Befehl verarbeiten
        
        Returns:
            True bei Erfolg, False bei Fehler
        """
        try:
            # Agent abrufen
            agent = self.agent_graph.get_agent(agent_id)
            
            # Interview-Aktion erstellen
            interview_action = ManualAction(
                action_type=ActionType.INTERVIEW,
                action_args={"prompt": prompt}
            )
            
            # Interview ausführen
            actions = {agent: interview_action}
            await self.env.step(actions)
            
            # Ergebnis aus DB abrufen
            result = self._get_interview_result(agent_id)
            
            self.send_response(command_id, "completed", result=result)
            print(f"  Interview abgeschlossen: agent_id={agent_id}")
            return True
            
        except Exception as e:
            error_msg = str(e)
            print(f"  Interview fehlgeschlagen: agent_id={agent_id}, error={error_msg}")
            self.send_response(command_id, "failed", error=error_msg)
            return False
    
    async def handle_batch_interview(self, command_id: str, interviews: List[Dict]) -> bool:
        """
        Batch-Interview-Befehl verarbeiten
        
        Args:
            interviews: [{"agent_id": int, "prompt": str}, ...]
        """
        try:
            # Aktions-Wörterbuch erstellen
            actions = {}
            agent_prompts = {}  # Prompt jedes Agenten aufzeichnen
            
            for interview in interviews:
                agent_id = interview.get("agent_id")
                prompt = interview.get("prompt", "")
                
                try:
                    agent = self.agent_graph.get_agent(agent_id)
                    actions[agent] = ManualAction(
                        action_type=ActionType.INTERVIEW,
                        action_args={"prompt": prompt}
                    )
                    agent_prompts[agent_id] = prompt
                except Exception as e:
                    print(f"  Warnung: Agent {agent_id} konnte nicht abgerufen werden: {e}")
            
            if not actions:
                self.send_response(command_id, "failed", error="Keine gültigen Agenten")
                return False
            
            # Batch-Interview ausführen
            await self.env.step(actions)
            
            # Alle Ergebnisse abrufen
            results = {}
            for agent_id in agent_prompts.keys():
                result = self._get_interview_result(agent_id)
                results[agent_id] = result
            
            self.send_response(command_id, "completed", result={
                "interviews_count": len(results),
                "results": results
            })
            print(f"  Batch-Interview abgeschlossen: {len(results)} Agenten")
            return True
            
        except Exception as e:
            error_msg = str(e)
            print(f"  Batch-Interview fehlgeschlagen: {error_msg}")
            self.send_response(command_id, "failed", error=error_msg)
            return False
    
    def _get_interview_result(self, agent_id: int) -> Dict[str, Any]:
        """Neuestes Interview-Ergebnis aus der Datenbank abrufen"""
        db_path = os.path.join(self.simulation_dir, "twitter_simulation.db")
        
        result = {
            "agent_id": agent_id,
            "response": None,
            "timestamp": None
        }
        
        if not os.path.exists(db_path):
            return result
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Neuesten Interview-Datensatz abfragen
            cursor.execute("""
                SELECT user_id, info, created_at
                FROM trace
                WHERE action = ? AND user_id = ?
                ORDER BY created_at DESC
                LIMIT 1
            """, (ActionType.INTERVIEW.value, agent_id))
            
            row = cursor.fetchone()
            if row:
                user_id, info_json, created_at = row
                try:
                    info = json.loads(info_json) if info_json else {}
                    result["response"] = info.get("response", info)
                    result["timestamp"] = created_at
                except json.JSONDecodeError:
                    result["response"] = info_json
            
            conn.close()
            
        except Exception as e:
            print(f"  Interview-Ergebnis konnte nicht gelesen werden: {e}")
        
        return result
    
    async def process_commands(self) -> bool:
        """
        Alle ausstehenden Befehle verarbeiten
        
        Returns:
            True bedeutet weiterlaufen, False bedeutet beenden
        """
        command = self.poll_command()
        if not command:
            return True
        
        command_id = command.get("command_id")
        command_type = command.get("command_type")
        args = command.get("args", {})
        
        print(f"\nIPC-Befehl erhalten: {command_type}, id={command_id}")
        
        if command_type == CommandType.INTERVIEW:
            await self.handle_interview(
                command_id,
                args.get("agent_id", 0),
                args.get("prompt", "")
            )
            return True
            
        elif command_type == CommandType.BATCH_INTERVIEW:
            await self.handle_batch_interview(
                command_id,
                args.get("interviews", [])
            )
            return True
            
        elif command_type == CommandType.CLOSE_ENV:
            print("Schließen-der-Umgebung-Befehl erhalten")
            self.send_response(command_id, "completed", result={"message": "Umgebung wird geschlossen"})
            return False
        
        else:
            self.send_response(command_id, "failed", error=f"Unbekannter Befehlstyp: {command_type}")
            return True


class TwitterSimulationRunner:
    """Twitter-Simulationsausführer"""
    
    # Twitter verfügbare Aktionen (ohne INTERVIEW, INTERVIEW kann nur manuell über ManualAction ausgelöst werden)
    AVAILABLE_ACTIONS = [
        ActionType.CREATE_POST,
        ActionType.LIKE_POST,
        ActionType.REPOST,
        ActionType.FOLLOW,
        ActionType.DO_NOTHING,
        ActionType.QUOTE_POST,
    ]
    
    def __init__(self, config_path: str, wait_for_commands: bool = True):
        """
        Simulationsausführer initialisieren
        
        Args:
            config_path: Pfad zur Konfigurationsdatei (simulation_config.json)
            wait_for_commands: Ob nach Simulationsende auf Befehle warten (standardmäßig True)
        """
        self.config_path = config_path
        self.config = self._load_config()
        self.simulation_dir = os.path.dirname(config_path)
        self.wait_for_commands = wait_for_commands
        self.env = None
        self.agent_graph = None
        self.ipc_handler = None
        
    def _load_config(self) -> Dict[str, Any]:
        """Konfigurationsdatei laden"""
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _get_profile_path(self) -> str:
        """Profildateipfad abrufen (OASIS Twitter verwendet CSV-Format)"""
        return os.path.join(self.simulation_dir, "twitter_profiles.csv")
    
    def _get_db_path(self) -> str:
        """Datenbankpfad abrufen"""
        return os.path.join(self.simulation_dir, "twitter_simulation.db")
    
    def _create_model(self):
        """
        LLM-Modell erstellen
        
        Verwendung der Konfiguration aus der .env Datei im Projektstammverzeichnis (höchste Priorität):
        - LLM_API_KEY: API-Schlüssel
        - LLM_BASE_URL: API-Basis-URL
        - LLM_MODEL_NAME: Modellname
        """
        # Bevorzugt Konfiguration aus .env abrufen
        llm_api_key = os.environ.get("LLM_API_KEY", "")
        llm_base_url = os.environ.get("LLM_BASE_URL", "")
        llm_model = os.environ.get("LLM_MODEL_NAME", "")
        
        # Wenn .env keinen Modellnamen hat, config als Fallback verwenden
        if not llm_model:
            llm_model = self.config.get("llm_model", "gpt-4o-mini")
        
        # Umgebungsvariablen für camel-ai setzen
        if llm_api_key:
            os.environ["OPENAI_API_KEY"] = llm_api_key
        
        if not os.environ.get("OPENAI_API_KEY"):
            raise ValueError("API-Schlüssel fehlt, bitte LLM_API_KEY in der .env Datei im Projektstammverzeichnis setzen")
        
        if llm_base_url:
            os.environ["OPENAI_API_BASE_URL"] = llm_base_url
        
        print(f"LLM-Konfiguration: model={llm_model}, base_url={llm_base_url[:40] if llm_base_url else 'Standard'}...")
        
        return ModelFactory.create(
            model_platform=ModelPlatformType.OPENAI,
            model_type=llm_model,
        )
    
    def _get_active_agents_for_round(
        self, 
        env, 
        current_hour: int,
        round_num: int
    ) -> List:
        """
        Basierend auf Zeit und Konfiguration entscheiden, welche Agenten in dieser Runde aktiviert werden
        
        Args:
            env: OASIS-Umgebung
            current_hour: Aktuelle Simulationsstunde (0-23)
            round_num: Aktuelle Runden-Nummer
            
        Returns:
            Liste der aktiven Agenten
        """
        time_config = self.config.get("time_config", {})
        agent_configs = self.config.get("agent_configs", [])
        
        # Basis-Aktivierungsanzahl
        base_min = time_config.get("agents_per_hour_min", 5)
        base_max = time_config.get("agents_per_hour_max", 20)
        
        # Nach Zeitraum anpassen
        peak_hours = time_config.get("peak_hours", [9, 10, 11, 14, 15, 20, 21, 22])
        off_peak_hours = time_config.get("off_peak_hours", [0, 1, 2, 3, 4, 5])
        
        if current_hour in peak_hours:
            multiplier = time_config.get("peak_activity_multiplier", 1.5)
        elif current_hour in off_peak_hours:
            multiplier = time_config.get("off_peak_activity_multiplier", 0.3)
        else:
            multiplier = 1.0
        
        target_count = int(random.uniform(base_min, base_max) * multiplier)
        
        # Aktivierungswahrscheinlichkeit basierend auf jeder Agent-Konfiguration berechnen
        candidates = []
        for cfg in agent_configs:
            agent_id = cfg.get("agent_id", 0)
            active_hours = cfg.get("active_hours", list(range(8, 23)))
            activity_level = cfg.get("activity_level", 0.5)
            
            # Prüfen, ob in aktiver Zeit
            if current_hour not in active_hours:
                continue
            
            # Wahrscheinlichkeit basierend auf Aktivitätsniveau berechnen
            if random.random() < activity_level:
                candidates.append(agent_id)
        
        # Zufällig auswählen
        selected_ids = random.sample(
            candidates, 
            min(target_count, len(candidates))
        ) if candidates else []
        
        # In Agent-Objekte umwandeln
        active_agents = []
        for agent_id in selected_ids:
            try:
                agent = env.agent_graph.get_agent(agent_id)
                active_agents.append((agent_id, agent))
            except Exception:
                pass
        
        return active_agents
    
    async def run(self, max_rounds: int = None):
        """Twitter-Simulation ausführen
        
        Args:
            max_rounds: Maximale Simulationsrunden (optional, zum Kürzen zu langer Simulationen)
        """
        print("=" * 60)
        print("OASIS Twitter-Simulation")
        print(f"Konfigurationsdatei: {self.config_path}")
        print(f"Simulations-ID: {self.config.get('simulation_id', 'unknown')}")
        print(f"Befehlswarte-Modus: {'Aktiviert' if self.wait_for_commands else 'Deaktiviert'}")
        print("=" * 60)
        
        # Zeitkonfiguration laden
        time_config = self.config.get("time_config", {})
        total_hours = time_config.get("total_simulation_hours", 72)
        minutes_per_round = time_config.get("minutes_per_round", 30)
        
        # Gesamtrunden berechnen
        total_rounds = (total_hours * 60) // minutes_per_round
        
        # Wenn maximale Runden angegeben, dann kürzen
        if max_rounds is not None and max_rounds > 0:
            original_rounds = total_rounds
            total_rounds = min(total_rounds, max_rounds)
            if total_rounds < original_rounds:
                print(f"\nRunden gekürzt: {original_rounds} -> {total_rounds} (max_rounds={max_rounds})")
        
        print(f"\nSimulationsparameter:")
        print(f"  - Gesamte Simulationsdauer: {total_hours} Stunden")
        print(f"  - Zeit pro Runde: {minutes_per_round} Minuten")
        print(f"  - Gesamtrunden: {total_rounds}")
        if max_rounds:
            print(f"  - Maximale Rundenbegrenzung: {max_rounds}")
        print(f"  - Agent-Anzahl: {len(self.config.get('agent_configs', []))}")
        
        print("\nLLM-Modell initialisieren...")
        model = self._create_model()
        
        # Agent-Graph laden
        print("Agent Profile laden...")
        profile_path = self._get_profile_path()
        if not os.path.exists(profile_path):
            print(f"Fehler: Profildatei existiert nicht: {profile_path}")
            return
        
        self.agent_graph = await generate_twitter_agent_graph(
            profile_path=profile_path,
            model=model,
            available_actions=self.AVAILABLE_ACTIONS,
        )
        
        db_path = self._get_db_path()
        if os.path.exists(db_path):
            os.remove(db_path)
            print(f"Alte Datenbank gelöscht: {db_path}")
        
        print("OASIS-Umgebung erstellen...")
        self.env = oasis.make(
            agent_graph=self.agent_graph,
            platform=oasis.DefaultPlatformType.TWITTER,
            database_path=db_path,
            semaphore=30,  # Maximale gleichzeitige LLM-Anfragen begrenzen, um API-Überlastung zu verhindern
        )
        
        await self.env.reset()
        print("Umgebungsinitialisierung abgeschlossen\n")
        
        # IPC-Prozessor initialisieren
        self.ipc_handler = IPCHandler(self.simulation_dir, self.env, self.agent_graph)
        self.ipc_handler.update_status("running")
        
        # Initiale Ereignisse ausführen
        event_config = self.config.get("event_config", {})
        initial_posts = event_config.get("initial_posts", [])
        
        if initial_posts:
            print(f"Initiale Ereignisse ausführen ({len(initial_posts)} initiale Posts)...")
            initial_actions = {}
            for post in initial_posts:
                agent_id = post.get("poster_agent_id", 0)
                content = post.get("content", "")
                try:
                    agent = self.env.agent_graph.get_agent(agent_id)
                    initial_actions[agent] = ManualAction(
                        action_type=ActionType.CREATE_POST,
                        action_args={"content": content}
                    )
                except Exception as e:
                    print(f"  Warnung: Initializer Post für Agent {agent_id} konnte nicht erstellt werden: {e}")
            
            if initial_actions:
                await self.env.step(initial_actions)
                print(f"  {len(initial_actions)} initiale Posts veröffentlicht")
        
        # Hauptsimulationsschleife
        print("\nSimulationsschleife starten...")
        start_time = datetime.now()
        
        for round_num in range(total_rounds):
            # Aktuelle Simulationszeit berechnen
            simulated_minutes = round_num * minutes_per_round
            simulated_hour = (simulated_minutes // 60) % 24
            simulated_day = simulated_minutes // (60 * 24) + 1
            
            # Agenten dieser Runde abrufen
            active_agents = self._get_active_agents_for_round(
                self.env, simulated_hour, round_num
            )
            
            if not active_agents:
                continue
            
            # Aktionen erstellen
            actions = {
                agent: LLMAction()
                for _, agent in active_agents
            }
            
            # Aktionen ausführen
            await self.env.step(actions)
            
            # Fortschritt ausgeben
            if (round_num + 1) % 10 == 0 or round_num == 0:
                elapsed = (datetime.now() - start_time).total_seconds()
                progress = (round_num + 1) / total_rounds * 100
                print(f"  [Day {simulated_day}, {simulated_hour:02d}:00] "
                      f"Round {round_num + 1}/{total_rounds} ({progress:.1f}%) "
                      f"- {len(active_agents)} agents active "
                      f"- elapsed: {elapsed:.1f}s")
        
        total_elapsed = (datetime.now() - start_time).total_seconds()
        print(f"\nSimulationsschleife abgeschlossen!")
        print(f"  - Gesamtdauer: {total_elapsed:.1f} Sekunden")
        print(f"  - Datenbank: {db_path}")
        
        # In Befehlswarte-Modus wechseln
        if self.wait_for_commands:
            print("\n" + "=" * 60)
            print("Befehlswarte-Modus aktiv - Umgebung bleibt aktiv")
            print("Unterstützte Befehle: interview, batch_interview, close_env")
            print("=" * 60)
            
            self.ipc_handler.update_status("alive")
            
            # Befehlsverarbeitungsschleife (mit globalem _shutdown_event)
            try:
                while not _shutdown_event.is_set():
                    should_continue = await self.ipc_handler.process_commands()
                    if not should_continue:
                        break
                    try:
                        await asyncio.wait_for(_shutdown_event.wait(), timeout=0.5)
                        break  # Beendigungssignal erhalten
                    except asyncio.TimeoutError:
                        pass
            except KeyboardInterrupt:
                print("\nUnterbrechungssignal erhalten")
            except asyncio.CancelledError:
                print("\nAufgabe abgebrochen")
            except Exception as e:
                print(f"\nBefehlsverarbeitung fehlgeschlagen: {e}")
            
            print("\nUmgebung schließen...")
        
        self.ipc_handler.update_status("stopped")
        await self.env.close()
        
        print("Umgebung geschlossen")
        print("=" * 60)


async def main():
    parser = argparse.ArgumentParser(description='OASIS Twitter-Simulation')
    parser.add_argument(
        '--config', 
        type=str, 
        required=True,
        help='Pfad zur Konfigurationsdatei (simulation_config.json)'
    )
    parser.add_argument(
        '--max-rounds',
        type=int,
        default=None,
        help='Maximale Simulationsrunden (optional, zum Kürzen zu langer Simulationen)'
    )
    parser.add_argument(
        '--no-wait',
        action='store_true',
        default=False,
        help='Umgebung nach Simulationsende sofort schließen, nicht in Befehlswarte-Modus wechseln'
    )
    
    args = parser.parse_args()
    
    # shutdown Event beim Start der main Funktion erstellen
    global _shutdown_event
    _shutdown_event = asyncio.Event()
    
    if not os.path.exists(args.config):
        print(f"Fehler: Konfigurationsdatei existiert nicht: {args.config}")
        sys.exit(1)
    
    # Protokollierungskonfiguration initialisieren (feste Dateinamen, alte Protokolle bereinigen)
    simulation_dir = os.path.dirname(args.config) or "."
    setup_oasis_logging(os.path.join(simulation_dir, "log"))
    
    runner = TwitterSimulationRunner(
        config_path=args.config,
        wait_for_commands=not args.no_wait
    )
    await runner.run(max_rounds=args.max_rounds)


def setup_signal_handlers():
    """
    Signalprozessor einrichten, um bei SIGTERM/SIGINT korrekt zu beenden
    Dem Programm die Möglichkeit geben, Ressourcen ordnungsgemäß zu bereinigen (DB, Umgebung usw.)
    """
    def signal_handler(signum, frame):
        global _cleanup_done
        sig_name = "SIGTERM" if signum == signal.SIGTERM else "SIGINT"
        print(f"\n{sig_name} Signal erhalten, wird beendet...")
        if not _cleanup_done:
            _cleanup_done = True
            if _shutdown_event:
                _shutdown_event.set()
        else:
            # Bei wiederholtem Signal dann erzwungen beenden
            print("Erzwungenes Beenden...")
            sys.exit(1)
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)


if __name__ == "__main__":
    setup_signal_handlers()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgramm unterbrochen")
    except SystemExit:
        pass
    finally:
        print("Simulationsprozess beendet")
