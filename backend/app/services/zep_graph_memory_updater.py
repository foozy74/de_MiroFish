"""
Zep-Graph-Speicher-Updater-Dienst
Aktualisiert Agent-Aktivitäten aus der Simulation dynamisch im Zep-Graphen
"""

import os
import time
import threading
import json
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
from queue import Queue, Empty

from zep_cloud.client import Zep


from ..utils.logger import get_logger

logger = get_logger('mirofish.zep_graph_memory_updater')


@dataclass
class AgentActivity:
    """Agent-Aktivitätsdatensatz"""
    platform: str           # twitter / reddit
    agent_id: int
    agent_name: str
    action_type: str        # CREATE_POST, LIKE_POST, etc.
    action_args: Dict[str, Any]
    round_num: int
    timestamp: str
    
    def to_episode_text(self) -> str:
        """
        Konvertiert die Aktivität in eine Textbeschreibung für Zep
        
        Verwendet ein natürliches Sprachformat, das es Zep ermöglicht, Entitäten
        und Beziehungen daraus zu extrahieren. Kein Simulationsbezogenes Präfix,
        um Fehlinformationen im Graph-Update zu vermeiden.
        """
        # Erstellt verschiedene Beschreibungen basierend auf dem Aktionstyp
        action_descriptions = {
            "CREATE_POST": self._describe_create_post,
            "LIKE_POST": self._describe_like_post,
            "DISLIKE_POST": self._describe_dislike_post,
            "REPOST": self._describe_repost,
            "QUOTE_POST": self._describe_quote_post,
            "FOLLOW": self._describe_follow,
            "CREATE_COMMENT": self._describe_create_comment,
            "LIKE_COMMENT": self._describe_like_comment,
            "DISLIKE_COMMENT": self._describe_dislike_comment,
            "SEARCH_POSTS": self._describe_search,
            "SEARCH_USER": self._describe_search_user,
            "MUTE": self._describe_mute,
        }
        
        describe_func = action_descriptions.get(self.action_type, self._describe_generic)
        description = describe_func()
        
        # Direkte Rückgabe im Format "agent_name: beschreibung", ohne Simulationspräfix
        return f"{self.agent_name}: {description}"
    
    def _describe_create_post(self) -> str:
        content = self.action_args.get("content", "")
        if content:
            return f"hat einen Beitrag veröffentlicht: «{content}»"
        return "hat einen Beitrag veröffentlicht"
    
    def _describe_like_post(self) -> str:
        """Beitrag liken - enthält Originalbeitrag und Autoreninformationen"""
        post_content = self.action_args.get("post_content", "")
        post_author = self.action_args.get("post_author_name", "")
        
        if post_content and post_author:
            return f"hat den Beitrag von {post_author} geliked: «{post_content}»"
        elif post_content:
            return f"hat einen Beitrag geliked: «{post_content}»"
        elif post_author:
            return f"hat einen Beitrag von {post_author} geliked"
        return "hat einen Beitrag geliked"
    
    def _describe_dislike_post(self) -> str:
        """Beitrag disliken - enthält Originalbeitrag und Autoreninformationen"""
        post_content = self.action_args.get("post_content", "")
        post_author = self.action_args.get("post_author_name", "")
        
        if post_content and post_author:
            return f"hat den Beitrag von {post_author} disliket: «{post_content}»"
        elif post_content:
            return f"hat einen Beitrag disliket: «{post_content}»"
        elif post_author:
            return f"hat einen Beitrag von {post_author} disliket"
        return "hat einen Beitrag disliket"
    
    def _describe_repost(self) -> str:
        """Beitrag reposten - enthält Originalbeitrag und Autoreninformationen"""
        original_content = self.action_args.get("original_content", "")
        original_author = self.action_args.get("original_author_name", "")
        
        if original_content and original_author:
            return f"hat den Beitrag von {original_author} repostet: «{original_content}»"
        elif original_content:
            return f"hat einen Beitrag repostet: «{original_content}»"
        elif original_author:
            return f"hat einen Beitrag von {original_author} repostet"
        return "hat einen Beitrag repostet"
    
    def _describe_quote_post(self) -> str:
        """Beitrag zitieren - enthält Originalbeitrag, Autoreninformationen und Zitatkommentar"""
        original_content = self.action_args.get("original_content", "")
        original_author = self.action_args.get("original_author_name", "")
        quote_content = self.action_args.get("quote_content", "") or self.action_args.get("content", "")
        
        base = ""
        if original_content and original_author:
            base = f"hat den Beitrag von {original_author} zitiert «{original_content}»"
        elif original_content:
            base = f"hat einen Beitrag zitiert «{original_content}»"
        elif original_author:
            base = f"hat einen Beitrag von {original_author} zitiert"
        else:
            base = "hat einen Beitrag zitiert"
        
        if quote_content:
            base += f" und kommentierte: «{quote_content}»"
        return base
    
    def _describe_follow(self) -> str:
        """Benutzer folgen - enthält den Namen des gefolgten Benutzers"""
        target_user_name = self.action_args.get("target_user_name", "")
        
        if target_user_name:
            return f"ist dem Benutzer «{target_user_name}» gefolgt"
        return "ist einem Benutzer gefolgt"
    
    def _describe_create_comment(self) -> str:
        """Kommentar erstellen - enthält Kommentarinhalt und Informationen zum kommentierten Beitrag"""
        content = self.action_args.get("content", "")
        post_content = self.action_args.get("post_content", "")
        post_author = self.action_args.get("post_author_name", "")
        
        if content:
            if post_content and post_author:
                return f"hat unter dem Beitrag von {post_author} «{post_content}» kommentiert: «{content}»"
            elif post_content:
                return f"hat unter dem Beitrag «{post_content}» kommentiert: «{content}»"
            elif post_author:
                return f"hat unter dem Beitrag von {post_author} kommentiert: «{content}»"
            return f"hat kommentiert: «{content}»"
        return "hat einen Kommentar verfasst"
    
    def _describe_like_comment(self) -> str:
        """Kommentar liken - enthält Kommentarinhalt und Autoreninformationen"""
        comment_content = self.action_args.get("comment_content", "")
        comment_author = self.action_args.get("comment_author_name", "")
        
        if comment_content and comment_author:
            return f"hat den Kommentar von {comment_author} geliked: «{comment_content}»"
        elif comment_content:
            return f"hat einen Kommentar geliked: «{comment_content}»"
        elif comment_author:
            return f"hat einen Kommentar von {comment_author} geliked"
        return "hat einen Kommentar geliked"
    
    def _describe_dislike_comment(self) -> str:
        """Kommentar disliken - enthält Kommentarinhalt und Autoreninformationen"""
        comment_content = self.action_args.get("comment_content", "")
        comment_author = self.action_args.get("comment_author_name", "")
        
        if comment_content and comment_author:
            return f"hat den Kommentar von {comment_author} disliket: «{comment_content}»"
        elif comment_content:
            return f"hat einen Kommentar disliket: «{comment_content}»"
        elif comment_author:
            return f"hat einen Kommentar von {comment_author} disliket"
        return "hat einen Kommentar disliket"
    
    def _describe_search(self) -> str:
        """Beiträge suchen - enthält Suchbegriffe"""
        query = self.action_args.get("query", "") or self.action_args.get("keyword", "")
        return f"hat nach «{query}» gesucht" if query else "hat eine Suche durchgeführt"
    
    def _describe_search_user(self) -> str:
        """Benutzer suchen - enthält Suchbegriffe"""
        query = self.action_args.get("query", "") or self.action_args.get("username", "")
        return f"hat nach dem Benutzer «{query}» gesucht" if query else "hat nach einem Benutzer gesucht"
    
    def _describe_mute(self) -> str:
        """Benutzer stummschalten - enthält den Namen des stummgeschalteten Benutzers"""
        target_user_name = self.action_args.get("target_user_name", "")
        
        if target_user_name:
            return f"hat den Benutzer «{target_user_name}» stummgeschaltet"
        return "hat einen Benutzer stummgeschaltet"
    
    def _describe_generic(self) -> str:
        # Für unbekannte Aktionstypen allgemeine Beschreibung generieren
        return f"hat {self.action_type} ausgeführt"


class ZepGraphMemoryUpdater:
    """
    Zep-Graph-Speicher-Updater
    
    Überwacht die Actions-Logdateien der Simulation und aktualisiert neue
    Agent-Aktivitäten in Echtzeit im Zep-Graphen. Gruppiert nach Plattform,
    jeweils nach BATCH_SIZE-Aktivitäten im Batch an Zep gesendet.
    
    Alle bedeutsamen Aktionen werden an Zep gesendet, wobei action_args die
    vollständigen Kontextinformationen enthält:
    - Originaltext von geliketen/disliketen Beiträgen
    - Originaltext von reposteten/zitierten Beiträgen
    - Benutzernamen von gefolgten/gestummten Benutzern
    - Originaltext von geliketen/disliketen Kommentaren
    """
    
    # Batch-Größe für den Versand (pro Plattform werden Aktivitäten gesammelt bis zum Versand)
    BATCH_SIZE = 5
    
    # Plattform-Namensmapping (für Konsolenausgabe)
    PLATFORM_DISPLAY_NAMES = {
        'twitter': 'Welt 1',
        'reddit': 'Welt 2',
    }
    
    # Sendeintervall (Sekunden), um zu schnelle Anfragen zu vermeiden
    SEND_INTERVAL = 0.5
    
    # Retry-Konfiguration
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # Sekunden
    
    def __init__(self, graph_id: str, api_key: Optional[str] = None):
        """
        Initialisiert den Updater
        
        Args:
            graph_id: Zep-Graph-ID
            api_key: Zep-API-Key (optional, Standard aus Konfiguration)
        """
        self.graph_id = graph_id
        from app.tenant.settings_override import TenantConfig
        cfg = TenantConfig()
        self.api_key = api_key or cfg.ZEP_API_KEY
        
        if not self.api_key:
            raise ValueError("ZEP_API_KEY nicht konfiguriert")
        
        self.client = Zep(api_key=self.api_key)
        
        # Aktivitätswarteschlange
        self._activity_queue: Queue = Queue()
        
        # Nach Plattform gruppierte Aktivitätspuffer (jede Plattform sammelt bis BATCH_SIZE vor dem Batch-Versand)
        self._platform_buffers: Dict[str, List[AgentActivity]] = {
            'twitter': [],
            'reddit': [],
        }
        self._buffer_lock = threading.Lock()
        
        # Kontrollflags
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None
        
        # Statistiken
        self._total_activities = 0  # Tatsächlich zur Warteschlange hinzugefügte Aktivitäten
        self._total_sent = 0        # Erfolgreich an Zep gesendete Batches
        self._total_items_sent = 0  # Erfolgreich an Zep gesendete Aktivitäten
        self._failed_count = 0      # Gescheiterte Batch-Sendungen
        self._skipped_count = 0     # Herausgefilterte Aktivitäten (DO_NOTHING)
        
        logger.info(f"ZepGraphMemoryUpdater initialisiert: graph_id={graph_id}, batch_size={self.BATCH_SIZE}")
    
    def _get_platform_display_name(self, platform: str) -> str:
        """Gibt den Anzeigenamen der Plattform zurück"""
        return self.PLATFORM_DISPLAY_NAMES.get(platform.lower(), platform)
    
    def start(self):
        """Startet den Hintergrund-Worker-Thread"""
        if self._running:
            return
        
        self._running = True
        self._worker_thread = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name=f"ZepMemoryUpdater-{self.graph_id[:8]}"
        )
        self._worker_thread.start()
        logger.info(f"ZepGraphMemoryUpdater gestartet: graph_id={self.graph_id}")
    
    def stop(self):
        """Stoppt den Hintergrund-Worker-Thread"""
        self._running = False
        
        # Verbleibende Aktivitäten senden
        self._flush_remaining()
        
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=10)
        
        logger.info(f"ZepGraphMemoryUpdater gestoppt: graph_id={self.graph_id}, "
                   f"total_activities={self._total_activities}, "
                   f"batches_sent={self._total_sent}, "
                   f"items_sent={self._total_items_sent}, "
                   f"failed={self._failed_count}, "
                   f"skipped={self._skipped_count}")
    
    def add_activity(self, activity: AgentActivity):
        """
        Fügt eine Agent-Aktivität zur Warteschlange hinzu
        
        Alle bedeutsamen Aktionen werden zur Warteschlange hinzugefügt, einschließlich:
        - CREATE_POST (Beitrag erstellen)
        - CREATE_COMMENT (Kommentar erstellen)
        - QUOTE_POST (Beitrag zitieren)
        - SEARCH_POSTS (Beiträge suchen)
        - SEARCH_USER (Benutzer suchen)
        - LIKE_POST/DISLIKE_POST (Beitrag liken/disliken)
        - REPOST (Reposten)
        - FOLLOW (Folgen)
        - MUTE (Stummschalten)
        - LIKE_COMMENT/DISLIKE_COMMENT (Kommentar liken/disliken)
        
        action_args enthält die vollständigen Kontextinformationen (z.B. Beitragstext, Benutzernamen).
        
        Args:
            activity: Agent-Aktivitätsdatensatz
        """
        # DO_NOTHING-Aktivitäten überspringen
        if activity.action_type == "DO_NOTHING":
            self._skipped_count += 1
            return
        
        self._activity_queue.put(activity)
        self._total_activities += 1
        logger.debug(f"Aktivität zur Zep-Warteschlange hinzugefügt: {activity.agent_name} - {activity.action_type}")
    
    def add_activity_from_dict(self, data: Dict[str, Any], platform: str):
        """
        Fügt Aktivität aus Dictionary-Daten hinzu
        
        Args:
            data: Aus actions.jsonl geparste Dictionary-Daten
            platform: Plattformname (twitter/reddit)
        """
        # Ereignistyp-Einträge überspringen
        if "event_type" in data:
            return
        
        activity = AgentActivity(
            platform=platform,
            agent_id=data.get("agent_id", 0),
            agent_name=data.get("agent_name", ""),
            action_type=data.get("action_type", ""),
            action_args=data.get("action_args", {}),
            round_num=data.get("round", 0),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
        )
        
        self.add_activity(activity)
    
    def _worker_loop(self):
        """Hintergrund-Worker-Schleife - sendet Aktivitäten nach Plattform gruppiert an Zep"""
        while self._running or not self._activity_queue.empty():
            try:
                # Versucht, Aktivität aus der Warteschlange zu holen (Timeout 1 Sekunde)
                try:
                    activity = self._activity_queue.get(timeout=1)
                    
                    # Aktivität zum Puffer der entsprechenden Plattform hinzufügen
                    platform = activity.platform.lower()
                    with self._buffer_lock:
                        if platform not in self._platform_buffers:
                            self._platform_buffers[platform] = []
                        self._platform_buffers[platform].append(activity)
                        
                        # Prüfen, ob diese Plattform die Batch-Größe erreicht hat
                        if len(self._platform_buffers[platform]) >= self.BATCH_SIZE:
                            batch = self._platform_buffers[platform][:self.BATCH_SIZE]
                            self._platform_buffers[platform] = self._platform_buffers[platform][self.BATCH_SIZE:]
                            # Lock nach dem Senden freigeben
                            self._send_batch_activities(batch, platform)
                            # Sendeintervall, um zu schnelle Anfragen zu vermeiden
                            time.sleep(self.SEND_INTERVAL)
                    
                except Empty:
                    pass
                    
            except Exception as e:
                logger.error(f"Worker-Schleifen-Fehler: {e}")
                time.sleep(1)
    
    def _send_batch_activities(self, activities: List[AgentActivity], platform: str):
        """
        Sendet Aktivitäten als Batch an Zep-Graph (zusammengeführt zu einem Text)
        
        Args:
            activities: Liste der Agent-Aktivitäten
            platform: Plattformname
        """
        if not activities:
            return
        
        # Mehrere Aktivitäten zu einem Text zusammenführen, durch Zeilenumbrüche getrennt
        episode_texts = [activity.to_episode_text() for activity in activities]
        combined_text = "\n".join(episode_texts)
        
        # Senden mit Retry
        for attempt in range(self.MAX_RETRIES):
            try:
                self.client.graph.add(
                    graph_id=self.graph_id,
                    type="text",
                    data=combined_text
                )
                
                self._total_sent += 1
                self._total_items_sent += len(activities)
                display_name = self._get_platform_display_name(platform)
                logger.info(f"Erfolgreich {len(activities)} {display_name}-Aktivitäten an Graph {self.graph_id} gesendet")
                logger.debug(f"Batch-Vorschau: {combined_text[:200]}...")
                return
                
            except Exception as e:
                if attempt < self.MAX_RETRIES - 1:
                    logger.warning(f"Batch-Sendung an Zep fehlgeschlagen (Versuch {attempt + 1}/{self.MAX_RETRIES}): {e}")
                    time.sleep(self.RETRY_DELAY * (attempt + 1))
                else:
                    logger.error(f"Batch-Sendung an Zep fehlgeschlagen, {self.MAX_RETRIES} Versuche: {e}")
                    self._failed_count += 1
    
    def _flush_remaining(self):
        """Sendet verbleibende Aktivitäten aus Warteschlange und Puffern"""
        # Zuerst verbleibende Aktivitäten aus der Warteschlange verarbeiten und zu Puffern hinzufügen
        while not self._activity_queue.empty():
            try:
                activity = self._activity_queue.get_nowait()
                platform = activity.platform.lower()
                with self._buffer_lock:
                    if platform not in self._platform_buffers:
                        self._platform_buffers[platform] = []
                    self._platform_buffers[platform].append(activity)
            except Empty:
                break
        
        # Dann verbleibende Aktivitäten aus den Plattformpuffern senden (auch wenn weniger als BATCH_SIZE)
        with self._buffer_lock:
            for platform, buffer in self._platform_buffers.items():
                if buffer:
                    display_name = self._get_platform_display_name(platform)
                    logger.info(f"Sende {len(buffer)} verbleibende {display_name}-Aktivitäten")
                    self._send_batch_activities(buffer, platform)
            # Alle Puffer leeren
            for platform in self._platform_buffers:
                self._platform_buffers[platform] = []
    
    def get_stats(self) -> Dict[str, Any]:
        """Gibt Statistikinformationen zurück"""
        with self._buffer_lock:
            buffer_sizes = {p: len(b) for p, b in self._platform_buffers.items()}
        
        return {
            "graph_id": self.graph_id,
            "batch_size": self.BATCH_SIZE,
            "total_activities": self._total_activities,  # Gesamtzahl der zur Warteschlange hinzugefügten Aktivitäten
            "batches_sent": self._total_sent,            # Erfolgreich gesendete Batches
            "items_sent": self._total_items_sent,        # Erfolgreich gesendete Aktivitäten
            "failed_count": self._failed_count,          # Gescheiterte Batch-Sendungen
            "skipped_count": self._skipped_count,        # Herausgefilterte Aktivitäten (DO_NOTHING)
            "queue_size": self._activity_queue.qsize(),
            "buffer_sizes": buffer_sizes,                # Puffergrößen pro Plattform
            "running": self._running,
        }


class ZepGraphMemoryManager:
    """
    Verwaltet mehrere Zep-Graph-Speicher-Updater für Simulationen
    
    Jede Simulation kann ihre eigene Updater-Instanz haben
    """
    
    _updaters: Dict[str, ZepGraphMemoryUpdater] = {}
    _lock = threading.Lock()
    
    @classmethod
    def create_updater(cls, simulation_id: str, graph_id: str) -> ZepGraphMemoryUpdater:
        """
        Erstellt einen Graph-Speicher-Updater für eine Simulation
        
        Args:
            simulation_id: Simulations-ID
            graph_id: Zep-Graph-ID
            
        Returns:
            ZepGraphMemoryUpdater-Instanz
        """
        with cls._lock:
            # Falls bereits vorhanden, zuerst den alten stoppen
            if simulation_id in cls._updaters:
                cls._updaters[simulation_id].stop()
            
            updater = ZepGraphMemoryUpdater(graph_id)
            updater.start()
            cls._updaters[simulation_id] = updater
            
            logger.info(f"Graph-Speicher-Updater erstellt: simulation_id={simulation_id}, graph_id={graph_id}")
            return updater
    
    @classmethod
    def get_updater(cls, simulation_id: str) -> Optional[ZepGraphMemoryUpdater]:
        """Gibt den Updater der Simulation zurück"""
        return cls._updaters.get(simulation_id)
    
    @classmethod
    def stop_updater(cls, simulation_id: str):
        """Stoppt und entfernt den Updater der Simulation"""
        with cls._lock:
            if simulation_id in cls._updaters:
                cls._updaters[simulation_id].stop()
                del cls._updaters[simulation_id]
                logger.info(f"Graph-Speicher-Updater gestoppt: simulation_id={simulation_id}")
    
    # Flag, um wiederholte stop_all-Aufrufe zu verhindern
    _stop_all_done = False
    
    @classmethod
    def stop_all(cls):
        """Stoppt alle Updater"""
        # Verhindert wiederholte Aufrufe
        if cls._stop_all_done:
            return
        cls._stop_all_done = True
        
        with cls._lock:
            if cls._updaters:
                for simulation_id, updater in list(cls._updaters.items()):
                    try:
                        updater.stop()
                    except Exception as e:
                        logger.error(f"Updater-Stopp fehlgeschlagen: simulation_id={simulation_id}, error={e}")
                cls._updaters.clear()
            logger.info("Alle Graph-Speicher-Updater gestoppt")
    
    @classmethod
    def get_all_stats(cls) -> Dict[str, Dict[str, Any]]:
        """Gibt Statistiken für alle Updater zurück"""
        return {
            sim_id: updater.get_stats() 
            for sim_id, updater in cls._updaters.items()
        }
