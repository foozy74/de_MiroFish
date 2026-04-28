"""
OASIS-Simulations-Manager
Verwaltet Twitter- und Reddit-Dual-Plattform-Parallel-Simulationen
Verwendet voreingestellte Skripte + LLM-intelligente Konfigurationsparameter-Generierung
"""

import os
import json
import shutil
import sqlite3
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


from ..config import Config
from ..utils.logger import get_logger
from .zep_entity_reader import ZepEntityReader, FilteredEntities
from .oasis_profile_generator import OasisProfileGenerator, OasisAgentProfile
from .simulation_config_generator import SimulationConfigGenerator, SimulationParameters

logger = get_logger('mirofish.simulation')


class SimulationStatus(str, Enum):
    """Simulationsstatus"""
    CREATED = "created"
    PREPARING = "preparing"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"      # Simulation wurde manuell gestoppt
    COMPLETED = "completed"  # Simulation natürlich abgeschlossen
    FAILED = "failed"


class PlatformType(str, Enum):
    """Plattformtyp"""
    TWITTER = "twitter"
    REDDIT = "reddit"


@dataclass
class SimulationState:
    """Simulationsstatus"""
    simulation_id: str
    project_id: str
    graph_id: str
    
    # Plattform-Aktivierungstatus
    enable_twitter: bool = True
    enable_reddit: bool = True
    
    # Status
    status: SimulationStatus = SimulationStatus.CREATED
    
    # Vorbereitungsphasendaten
    entities_count: int = 0
    profiles_count: int = 0
    entity_types: List[str] = field(default_factory=list)
    
    # Konfigurationsgenerierungsinformationen
    profiles_generated: bool = False
    config_generated: bool = False
    config_reasoning: str = ""
    
    # Laufzeitdaten
    current_round: int = 0
    twitter_status: str = "not_started"
    reddit_status: str = "not_started"
    
    # Zeitstempel
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # Fehlerinformationen
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Vollständiger Status-Dictionary (interner Gebrauch)"""
        return {
            "simulation_id": self.simulation_id,
            "project_id": self.project_id,
            "graph_id": self.graph_id,
            "enable_twitter": self.enable_twitter,
            "enable_reddit": self.enable_reddit,
            "status": self.status.value,
            "entities_count": self.entities_count,
            "profiles_count": self.profiles_count,
            "entity_types": self.entity_types,
            "profiles_generated": self.profiles_generated,
            "config_generated": self.config_generated,
            "config_reasoning": self.config_reasoning,
            "current_round": self.current_round,
            "twitter_status": self.twitter_status,
            "reddit_status": self.reddit_status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "error": self.error,
        }
    
    def to_simple_dict(self) -> Dict[str, Any]:
        """vereinfachter Status-Dictionary (für API-Rückgabe)"""
        return {
            "simulation_id": self.simulation_id,
            "project_id": self.project_id,
            "graph_id": self.graph_id,
            "status": self.status.value,
            "entities_count": self.entities_count,
            "profiles_count": self.profiles_count,
            "entity_types": self.entity_types,
            "profiles_generated": self.profiles_generated,
            "config_generated": self.config_generated,
            "error": self.error,
        }


class SimulationManager:
    """
    Simulations-Manager
    
    Kernfunktionen:
    1. Entitäten aus dem Zep-Graph lesen und filtern
    2. OASIS Agent Profile generieren
    3. Simulationskonfigurationsparameter intelligent mit LLM generieren
    4. Alle für voreingestellte Skripte erforderlichen Dateien vorbereiten
    """

    _simulations: Dict[str, SimulationState] = {}
    
    @classmethod
    def get_tenant_dir(cls) -> str:
        """Tenant-Verzeichnis abrufen"""
        from flask import g
        tenant_id = g.tenant.tenant_id if (hasattr(g, 'tenant') and g.tenant) else 'default'
        path = os.path.join(Config.UPLOAD_FOLDER, 'tenants', tenant_id)
        os.makedirs(path, exist_ok=True)
        return path

    def get_simulation_dir(self, simulation_id: str) -> str:
        """Simulationsdatenverzeichnis abrufen (im Tenant-Pfad)"""
        sim_dir = os.path.join(self.get_tenant_dir(), 'simulations', simulation_id)
        os.makedirs(sim_dir, exist_ok=True)
        return sim_dir
    
    def _get_conn(self):
        """SQLite Verbindung für den aktuellen Tenant"""
        from flask import g
        tenant_id = g.tenant.tenant_id if g.tenant else 'default'
        db_path = os.path.join(self.get_tenant_dir(), 'data.db')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_tables(self, conn):
        """Simulationstabellen in data.db sicherstellen"""
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS simulation_runs (
                simulation_id TEXT PRIMARY KEY,
                project_id TEXT,
                graph_id TEXT,
                enable_twitter BOOLEAN,
                enable_reddit BOOLEAN,
                status TEXT,
                entities_count INTEGER,
                profiles_count INTEGER,
                entity_types TEXT,
                profiles_generated BOOLEAN,
                config_generated BOOLEAN,
                config_reasoning TEXT,
                current_round INTEGER,
                total_rounds INTEGER,
                simulated_hours INTEGER,
                total_simulation_hours INTEGER,
                twitter_status TEXT,
                reddit_status TEXT,
                created_at TEXT,
                started_at TEXT,
                updated_at TEXT,
                completed_at TEXT,
                error TEXT,
                process_pid INTEGER
            )
        """)
        
        # Ensure new columns exist (for existing databases)
        columns_to_add = [
            ("profiles_generated", "BOOLEAN DEFAULT 0"),
            ("total_rounds", "INTEGER DEFAULT 0"),
            ("simulated_hours", "INTEGER DEFAULT 0"),
            ("total_simulation_hours", "INTEGER DEFAULT 0"),
            ("started_at", "TEXT"),
            ("completed_at", "TEXT")
        ]
        for col_name, col_def in columns_to_add:
            try:
                cursor.execute(f"ALTER TABLE simulation_runs ADD COLUMN {col_name} {col_def}")
            except:
                pass # Column already exists
        
        conn.commit()
            
        conn.commit()

    def _save_simulation_state(self, state: SimulationState):
        """Simulationsstatus in SQLite speichern"""
        conn = self._get_conn()
        try:
            self._ensure_tables(conn)
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            state.updated_at = now
            
            cursor.execute("""
                INSERT INTO simulation_runs (
                    simulation_id, project_id, graph_id, enable_twitter, enable_reddit,
                    status, entities_count, profiles_count, entity_types,
                    profiles_generated, config_generated, config_reasoning, current_round,
                    twitter_status, reddit_status, created_at, updated_at, error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(simulation_id) DO UPDATE SET
                    status = excluded.status,
                    entities_count = excluded.entities_count,
                    profiles_count = excluded.profiles_count,
                    entity_types = excluded.entity_types,
                    profiles_generated = excluded.profiles_generated,
                    config_generated = excluded.config_generated,
                    config_reasoning = excluded.config_reasoning,
                    current_round = excluded.current_round,
                    twitter_status = excluded.twitter_status,
                    reddit_status = excluded.reddit_status,
                    updated_at = excluded.updated_at,
                    error = excluded.error
            """, (
                state.simulation_id, state.project_id, state.graph_id, 
                state.enable_twitter, state.enable_reddit, state.status.value,
                state.entities_count, state.profiles_count, json.dumps(state.entity_types),
                state.profiles_generated, state.config_generated, state.config_reasoning, 
                state.current_round, state.twitter_status, state.reddit_status, 
                state.created_at, state.updated_at, state.error
            ))
            conn.commit()
        finally:
            conn.close()
            
        # Auch in state.json speichern (für Kompatibilität mit bestehenden API-Endpunkten)
        try:
            sim_dir = self.get_simulation_dir(state.simulation_id)
            state_file = os.path.join(sim_dir, "state.json")
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(state.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Speichern von state.json fehlgeschlagen: {e}")
        
        self._simulations[state.simulation_id] = state
    
    def _load_simulation_state(self, simulation_id: str) -> Optional[SimulationState]:
        """Simulationsstatus aus SQLite laden"""
        if simulation_id in self._simulations:
            return self._simulations[simulation_id]
        
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM simulation_runs WHERE simulation_id = ?", (simulation_id,))
            row = cursor.fetchone()
            if not row:
                return None
            
            data = dict(row)
            state = SimulationState(
                simulation_id=simulation_id,
                project_id=data.get("project_id", ""),
                graph_id=data.get("graph_id", ""),
                enable_twitter=bool(data.get("enable_twitter", True)),
                enable_reddit=bool(data.get("enable_reddit", True)),
                status=SimulationStatus(data.get("status", "created")),
                entities_count=data.get("entities_count", 0),
                profiles_count=data.get("profiles_count", 0),
                entity_types=json.loads(data.get("entity_types", "[]")),
                profiles_generated=bool(data.get("profiles_generated", False)),
                config_generated=bool(data.get("config_generated", False)),
                config_reasoning=data.get("config_reasoning", ""),
                current_round=data.get("current_round", 0),
                twitter_status=data.get("twitter_status", "not_started"),
                reddit_status=data.get("reddit_status", "not_started"),
                created_at=data.get("created_at", datetime.now().isoformat()),
                updated_at=data.get("updated_at", datetime.now().isoformat()),
                error=data.get("error"),
            )
            
            self._simulations[simulation_id] = state
            return state
        finally:
            conn.close()
    
    def create_simulation(
        self,
        project_id: str,
        graph_id: str,
        enable_twitter: bool = True,
        enable_reddit: bool = True,
    ) -> SimulationState:
        """
        Neue Simulation erstellen
        
        Args:
            project_id: Projekt-ID
            graph_id: Zep-Graph-ID
            enable_twitter: Twitter-Simulation aktivieren
            enable_reddit: Reddit-Simulation aktivieren
            
        Returns:
            SimulationState
        """
        import uuid
        simulation_id = f"sim_{uuid.uuid4().hex[:12]}"
        
        state = SimulationState(
            simulation_id=simulation_id,
            project_id=project_id,
            graph_id=graph_id,
            enable_twitter=enable_twitter,
            enable_reddit=enable_reddit,
            status=SimulationStatus.CREATED,
        )
        
        self._save_simulation_state(state)
        logger.info(f"Simulation erstellt: {simulation_id}, project={project_id}, graph={graph_id}")
        
        return state
    
    def prepare_simulation(
        self,
        simulation_id: str,
        simulation_requirement: str,
        document_text: str,
        defined_entity_types: Optional[List[str]] = None,
        use_llm_for_profiles: bool = True,
        progress_callback: Optional[callable] = None,
        parallel_profile_count: int = 3
    ) -> SimulationState:
        """
        Simulationsumgebung vorbereiten (vollständig automatisiert)
        
        Schritte:
        1. Entitäten aus Zep-Graph lesen und filtern
        2. OASIS Agent Profile für jede Entität generieren (optionale LLM-Verbesserung, Parallelität unterstützt)
        3. Simulationskonfigurationsparameter intelligent mit LLM generieren (Zeit, Aktivität, Posting-Häufigkeit usw.)
        4. Konfigurationsdateien und Profile-Dateien speichern
        5. Voreingestellte Skripte in Simulationsverzeichnis kopieren
        
        Args:
            simulation_id: Simulations-ID
            simulation_requirement: Simulationsanforderungsbeschreibung (zur LLM-Konfigurationsgenerierung)
            document_text: Originaldokumentinhalt (zurLLM-Hintergrundverständnis)
            defined_entity_types: Vordefinierte Entitätstypen (optional)
            use_llm_for_profiles: LLM zur detaillierten Persönlichkeitsgenerierung verwenden
            progress_callback: Fortschritts-Callback-Funktion (stage, progress, message)
            parallel_profile_count: Anzahl der parallel generierten Persönlichkeiten, Standard 3
            
        Returns:
            SimulationState
        """
        state = self._load_simulation_state(simulation_id)
        if not state:
            raise ValueError(f"Simulation existiert nicht: {simulation_id}")
        
        try:
            state.status = SimulationStatus.PREPARING
            self._save_simulation_state(state)
            
            sim_dir = self.get_simulation_dir(simulation_id)
            
            # ========== Phase 1: Knoten lesen und filtern ==========
            if progress_callback:
                progress_callback("reading", 0, "Verbindung zum Zep-Graph wird hergestellt...")
            
            reader = ZepEntityReader()
            
            if progress_callback:
                progress_callback("reading", 30, "Knotendaten werden gelesen...")
            
            filtered = reader.filter_defined_entities(
                graph_id=state.graph_id,
                defined_entity_types=defined_entity_types,
                enrich_with_edges=True
            )
            
            state.entities_count = filtered.filtered_count
            state.entity_types = list(filtered.entity_types)
            
            if progress_callback:
                progress_callback(
                    "reading", 100, 
                    f"Fertig, insgesamt {filtered.filtered_count} Entitäten",
                    current=filtered.filtered_count,
                    total=filtered.filtered_count
                )
            
            if filtered.filtered_count == 0:
                state.status = SimulationStatus.FAILED
                state.error = "Keine qualifizierenden Entitäten gefunden, bitte überprüfen Sie, ob der Graph korrekt erstellt wurde"
                self._save_simulation_state(state)
                return state
            
            # ========== Phase 2: Agent Profile generieren ==========
            total_entities = len(filtered.entities)
            
            if progress_callback:
                progress_callback(
                    "generating_profiles", 0, 
                    "Beginne mit der Generierung...",
                    current=0,
                    total=total_entities
                )
            
            # graph_id übergeben, um Zep-Abruffunktion zu aktivieren, um reichhaltigeren Kontext zu erhalten
            generator = OasisProfileGenerator(graph_id=state.graph_id)
            
            def profile_progress(current, total, msg):
                if progress_callback:
                    progress_callback(
                        "generating_profiles", 
                        int(current / total * 100), 
                        msg,
                        current=current,
                        total=total,
                        item_name=msg
                    )
            
            # Dateipfad für Echtzeit-Speicherung festlegen (Reddit JSON-Format priorisiert)
            realtime_output_path = None
            realtime_platform = "reddit"
            if state.enable_reddit:
                realtime_output_path = os.path.join(sim_dir, "reddit_profiles.json")
                realtime_platform = "reddit"
            elif state.enable_twitter:
                realtime_output_path = os.path.join(sim_dir, "twitter_profiles.csv")
                realtime_platform = "twitter"
            
            profiles = generator.generate_profiles_from_entities(
                entities=filtered.entities,
                use_llm=use_llm_for_profiles,
                progress_callback=profile_progress,
                graph_id=state.graph_id,  # graph_id für Zep-Abruf übergeben
                parallel_count=parallel_profile_count,  # Anzahl paralleler Generierungen
                realtime_output_path=realtime_output_path,  # Echtzeit-Speicherpfad
                output_platform=realtime_platform  # Ausgabeformat
            )
            
            state.profiles_count = len(profiles)
            
            # Profile-Dateien speichern (Hinweis: Twitter verwendet CSV-Format, Reddit verwendet JSON-Format)
            # Reddit wurde bereits während der Generierung in Echtzeit gespeichert, hier nochmals zur Sicherheit speichern
            if progress_callback:
                progress_callback(
                    "generating_profiles", 95, 
                    "Profile-Datei wird gespeichert...",
                    current=total_entities,
                    total=total_entities
                )
            
            if state.enable_reddit:
                generator.save_profiles(
                    profiles=profiles,
                    file_path=os.path.join(sim_dir, "reddit_profiles.json"),
                    platform="reddit"
                )
            
            if state.enable_twitter:
                # Twitter verwendet CSV-Format! Dies ist die Anforderung von OASIS
                generator.save_profiles(
                    profiles=profiles,
                    file_path=os.path.join(sim_dir, "twitter_profiles.csv"),
                    platform="twitter"
                )
            
            if progress_callback:
                progress_callback(
                    "generating_profiles", 100, 
                    f"Fertig, insgesamt {len(profiles)} Profile",
                    current=len(profiles),
                    total=len(profiles)
                )
            
            state.profiles_generated = True
            self._save_simulation_state(state)
            
            # ========== Phase 3: LLM-intelligente Simulationskonfigurationsgenerierung ==========
            if progress_callback:
                progress_callback(
                    "generating_config", 0, 
                    "Simulationsanforderungen werden analysiert...",
                    current=0,
                    total=3
                )
            
            config_generator = SimulationConfigGenerator()
            
            if progress_callback:
                progress_callback(
                    "generating_config", 30, 
                    "LLM wird aufgerufen für Konfigurationsgenerierung...",
                    current=1,
                    total=3
                )
            
            # Wrapper für progress_callback, um das Format an SimulationConfigGenerator anzupassen
            def config_progress_wrapper(current_step, total_steps, message):
                # Map internal steps to stages for better UI feedback
                if "Ereignis" in message or "Hot-Topics" in message or current_step == 2:
                    stage = "orchestration"
                else:
                    stage = "generating_config"
                    
                # Berechne Prozentsatz innerhalb der Phase (0-100)
                stage_progress = int(current_step / total_steps * 100)
                if progress_callback:
                    progress_callback(stage, stage_progress, message, current=current_step, total=total_steps)

            sim_params = config_generator.generate_config(
                simulation_id=simulation_id,
                project_id=state.project_id,
                graph_id=state.graph_id,
                simulation_requirement=simulation_requirement,
                document_text=document_text,
                entities=filtered.entities,
                enable_twitter=state.enable_twitter,
                enable_reddit=state.enable_reddit,
                progress_callback=config_progress_wrapper
            )
            
            if progress_callback:
                progress_callback(
                    "generating_config", 70, 
                    "Konfigurationsdatei wird gespeichert...",
                    current=2,
                    total=3
                )
            
            # Konfigurationsdatei speichern
            config_path = os.path.join(sim_dir, "simulation_config.json")
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(sim_params.to_json())
            
            state.config_generated = True
            state.config_reasoning = sim_params.generation_reasoning
            
            if progress_callback:
                progress_callback(
                    "generating_config", 100, 
                    "Konfigurationsgenerierung abgeschlossen",
                    current=3,
                    total=3
                )
            
            # Hinweis: Laufskripte verbleiben im backend/scripts/ Verzeichnis, nicht mehr ins Simulationsverzeichnis kopieren
            # Beim Starten der Simulation führt simulation_runner die Skripte aus dem scripts/ Verzeichnis aus
            
            # Status aktualisieren
            state.status = SimulationStatus.READY
            self._save_simulation_state(state)
            
            logger.info(f"Simulationsvorbereitung abgeschlossen: {simulation_id}, "
                       f"entities={state.entities_count}, profiles={state.profiles_count}")
            
            return state
            
        except Exception as e:
            logger.error(f"Simulationsvorbereitung fehlgeschlagen: {simulation_id}, error={str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            state.status = SimulationStatus.FAILED
            state.error = str(e)
            self._save_simulation_state(state)
            raise
    
    def get_simulation(self, simulation_id: str) -> Optional[SimulationState]:
        """Simulationsstatus abrufen"""
        return self._load_simulation_state(simulation_id)
    
    def list_simulations(self, project_id: Optional[str] = None) -> List[SimulationState]:
        """Alle Simulationen auflisten"""
        simulations = []
        
        sim_base_dir = os.path.join(self.get_tenant_dir(), 'simulations')
        if os.path.exists(sim_base_dir):
            for sim_id in os.listdir(sim_base_dir):
                # Versteckte Dateien überspringen (z.B. .DS_Store) und Nicht-Verzeichnis-Dateien
                sim_path = os.path.join(sim_base_dir, sim_id)
                if sim_id.startswith('.') or not os.path.isdir(sim_path):
                    continue
                
                state = self._load_simulation_state(sim_id)
                if state:
                    if project_id is None or state.project_id == project_id:
                        simulations.append(state)
        
        return simulations
    
    def get_profiles(self, simulation_id: str, platform: str = "reddit") -> List[Dict[str, Any]]:
        """Agent Profile der Simulation abrufen"""
        state = self._load_simulation_state(simulation_id)
        if not state:
            raise ValueError(f"Simulation existiert nicht: {simulation_id}")
        
        sim_dir = self.get_simulation_dir(simulation_id)
        profile_path = os.path.join(sim_dir, f"{platform}_profiles.json")
        
        if not os.path.exists(profile_path):
            return []
        
        with open(profile_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def get_simulation_config(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        """Simulationskonfiguration abrufen"""
        sim_dir = self.get_simulation_dir(simulation_id)
        config_path = os.path.join(sim_dir, "simulation_config.json")
        
        if not os.path.exists(config_path):
            return None
        
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def get_run_instructions(self, simulation_id: str) -> Dict[str, str]:
        """Laufanweisungen abrufen"""
        sim_dir = self.get_simulation_dir(simulation_id)
        config_path = os.path.join(sim_dir, "simulation_config.json")
        scripts_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../scripts'))
        
        return {
            "simulation_dir": sim_dir,
            "scripts_dir": scripts_dir,
            "config_file": config_path,
            "commands": {
                "twitter": f"python {scripts_dir}/run_twitter_simulation.py --config {config_path}",
                "reddit": f"python {scripts_dir}/run_reddit_simulation.py --config {config_path}",
                "parallel": f"python {scripts_dir}/run_parallel_simulation.py --config {config_path}",
            },
            "instructions": (
                f"1. Conda-Umgebung aktivieren: conda activate MiroFish\n"
                f"2. Simulation ausführen (Skripte befinden sich in {scripts_dir}):\n"
                f"   - Twitter separat ausführen: python {scripts_dir}/run_twitter_simulation.py --config {config_path}\n"
                f"   - Reddit separat ausführen: python {scripts_dir}/run_reddit_simulation.py --config {config_path}\n"
                f"   - Beide Plattformen parallel ausführen: python {scripts_dir}/run_parallel_simulation.py --config {config_path}"
            )
        }
