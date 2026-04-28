"""
Intelligenter Simulationskonfigurations-Generator
Verwendet LLM, um basierend auf Simulationsanforderungen, Dokumentinhalten und Graph-Informationen
automatisch detaillierte Simulationsparameter zu generieren
Implementiert vollständige Automatisierung ohne manuelle Parametereinstellung

Verwendet eine schrittweise Generierungsstrategie, um zu vermeiden, dass zu lange Inhalte
auf einmal generiert werden:
1. Zeitkonfiguration generieren
2. Ereigniskonfiguration generieren
3. Agent-Konfigurationen stapelweise generieren
4. Plattformkonfiguration generieren
"""

import json
import math
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime

from openai import OpenAI


from ..utils.logger import get_logger
from .zep_entity_reader import EntityNode, ZepEntityReader

logger = get_logger('mirofish.simulation_config')

# Chinesische Zeitzonenkfiguration (Pekinger Zeit)
CHINA_TIMEZONE_CONFIG = {
    # Tote Stunden (kaum Aktivität)
    "dead_hours": [0, 1, 2, 3, 4, 5],
    # Morgenstunden (allmähliches Aufwachen)
    "morning_hours": [6, 7, 8],
    # Arbeitsstunden
    "work_hours": [9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
    # Abendspitzen (am aktivsten)
    "peak_hours": [19, 20, 21, 22],
    # Nachtstunden (Aktivität nimmt ab)
    "night_hours": [23],
    # Aktivitätskoeffizienten
    "activity_multipliers": {
        "dead": 0.05,      # Tief in der Nacht kaum jemand
        "morning": 0.4,    # Morgens allmählich aktiver
        "work": 0.7,       # Arbeitsstunden mittel
        "peak": 1.5,       # Abendliche Spitzenzeit
        "night": 0.5       # Nachts Rückgang
    }
}


@dataclass
class AgentActivityConfig:
    """Aktivitätskonfiguration für einen einzelnen Agent"""
    agent_id: int
    entity_uuid: str
    entity_name: str
    entity_type: str
    
    # Aktivitätskonfiguration (0.0-1.0)
    activity_level: float = 0.5  # Gesamte Aktivität
    
    # Posting-Häufigkeit (erwartete Anzahl pro Stunde)
    posts_per_hour: float = 1.0
    comments_per_hour: float = 2.0
    
    # Aktive Stunden (24-Stunden-Format, 0-23)
    active_hours: List[int] = field(default_factory=lambda: list(range(8, 23)))
    
    # Reaktionsgeschwindigkeit (Reaktionsverzögerung auf Hot-Events, Einheit: Simulationsminuten)
    response_delay_min: int = 5
    response_delay_max: int = 60
    
    # Stimmungsbias (-1.0 bis 1.0, negativ bis positiv)
    sentiment_bias: float = 0.0
    
    # Haltung (Einstellung zu bestimmten Themen)
    stance: str = "neutral"  # supportive, opposing, neutral, observer
    
    # Einflussgewicht (bestimmt die Wahrscheinlichkeit, dass andere Agenten seinen Beitrag sehen)
    influence_weight: float = 1.0


@dataclass  
class TimeSimulationConfig:
    """Zeitsimulationskonfiguration (basierend auf chinesischen Lebensgewohnheiten)"""
    # Gesamte Simulationsdauer (Simulationsstunden)
    total_simulation_hours: int = 72  # Standard 72 Stunden (3 Tage)
    
    # Zeit pro Runde (Simulationsminuten) - Standard 60 Minuten (1 Stunde), beschleunigter Zeitfluss
    minutes_per_round: int = 60
    
    # Anzahl der pro Stunde aktivierten Agenten
    agents_per_hour_min: int = 5
    agents_per_hour_max: int = 20
    
    # Spitzenstunden (19-22 Uhr abends, wenn Chinesen am aktivsten sind)
    peak_hours: List[int] = field(default_factory=lambda: [19, 20, 21, 22])
    peak_activity_multiplier: float = 1.5
    
    # Nebenzeiten (0-5 Uhr nachts, kaum Aktivität)
    off_peak_hours: List[int] = field(default_factory=lambda: [0, 1, 2, 3, 4, 5])
    off_peak_activity_multiplier: float = 0.05  # Sehr geringe Aktivität früh morgens
    
    # Morgenstunden
    morning_hours: List[int] = field(default_factory=lambda: [6, 7, 8])
    morning_activity_multiplier: float = 0.4
    
    # Arbeitsstunden
    work_hours: List[int] = field(default_factory=lambda: [9, 10, 11, 12, 13, 14, 15, 16, 17, 18])
    work_activity_multiplier: float = 0.7


@dataclass
class EventConfig:
    """Ereigniskonfiguration"""
    # Anfangsereignisse (ausgelöste Ereignisse beim Simulationsstart)
    initial_posts: List[Dict[str, Any]] = field(default_factory=list)
    
    # Geplante Ereignisse (zu bestimmten Zeiten ausgelöste Ereignisse)
    scheduled_events: List[Dict[str, Any]] = field(default_factory=list)
    
    # Stichwörter für Hot-Topics
    hot_topics: List[str] = field(default_factory=list)
    
    # Richtung der öffentlichen Meinung
    narrative_direction: str = ""


@dataclass
class PlatformConfig:
    """Plattformspezifische Konfiguration"""
    platform: str  # twitter or reddit
    
    # Gewichtung des Empfehlungsalgorithmus
    recency_weight: float = 0.4  # Zeitliche Frische
    popularity_weight: float = 0.3  # Popularität
    relevance_weight: float = 0.3  # Relevanz
    
    # Viralitätsschwelle (ab wie vielen Interaktionen eine Verbreitung ausgelöst wird)
    viral_threshold: int = 10
    
    # Echo-Kammer-Effektstärke (Grad der Ähnlichkeit von Meinungsgruppen)
    echo_chamber_strength: float = 0.5


@dataclass
class SimulationParameters:
    """Vollständige Simulationsparameterkonfiguration"""
    # Grundinformationen
    simulation_id: str
    project_id: str
    graph_id: str
    simulation_requirement: str
    
    # Zeitkonfiguration
    time_config: TimeSimulationConfig = field(default_factory=TimeSimulationConfig)
    
    # Agent-Konfigurationsliste
    agent_configs: List[AgentActivityConfig] = field(default_factory=list)
    
    # Ereigniskonfiguration
    event_config: EventConfig = field(default_factory=EventConfig)
    
    # Plattformkonfiguration
    twitter_config: Optional[PlatformConfig] = None
    reddit_config: Optional[PlatformConfig] = None
    
    # LLM-Konfiguration
    llm_model: str = ""
    llm_base_url: str = ""
    
    # Generierungsmetadaten
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    generation_reasoning: str = ""  # LLM-Erklärungen
    
    def to_dict(self) -> Dict[str, Any]:
        """In Dictionary konvertieren"""
        time_dict = asdict(self.time_config)
        return {
            "simulation_id": self.simulation_id,
            "project_id": self.project_id,
            "graph_id": self.graph_id,
            "simulation_requirement": self.simulation_requirement,
            "time_config": time_dict,
            "agent_configs": [asdict(a) for a in self.agent_configs],
            "event_config": asdict(self.event_config),
            "twitter_config": asdict(self.twitter_config) if self.twitter_config else None,
            "reddit_config": asdict(self.reddit_config) if self.reddit_config else None,
            "llm_model": self.llm_model,
            "llm_base_url": self.llm_base_url,
            "generated_at": self.generated_at,
            "generation_reasoning": self.generation_reasoning,
        }
    
    def to_json(self, indent: int = 2) -> str:
        """In JSON-String konvertieren"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)


class SimulationConfigGenerator:
    """
    Intelligenter Simulationskonfigurations-Generator
    
    Verwendet LLM, um Simulationsanforderungen, Dokumentinhalte und Graph-Entitätsinformationen
    zu analysieren und automatisch optimale Simulationsparameterkonfigurationen zu generieren
    
    Verwendet eine schrittweise Generierungsstrategie:
    1. Zeit- und Ereigniskonfiguration generieren (leichtgewichtig)
    2. Agent-Konfigurationen stapelweise generieren (jeweils 10-20)
    3. Plattformkonfiguration generieren
    """
    
    # Maximale Zeichenanzahl für Kontext
    MAX_CONTEXT_LENGTH = 50000
    # Anzahl der Agenten pro Stapel
    AGENTS_PER_BATCH = 15
    
    # Kontext-Abschneidelänge für jeden Schritt (Zeichenanzahl)
    TIME_CONFIG_CONTEXT_LENGTH = 10000   # Zeitkonfiguration
    EVENT_CONFIG_CONTEXT_LENGTH = 8000   # Ereigniskonfiguration
    ENTITY_SUMMARY_LENGTH = 300          # Entitätszusammenfassung
    AGENT_SUMMARY_LENGTH = 300           # Entitätszusammenfassung in Agent-Konfiguration
    ENTITIES_PER_TYPE_DISPLAY = 20       # Angezeigte Entitäten pro Typ
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None
    ):
        from app.tenant.settings_override import TenantConfig
        cfg = TenantConfig()
        self.api_key = api_key or cfg.LLM_API_KEY
        self.base_url = base_url or cfg.LLM_BASE_URL
        self.model_name = model_name or cfg.LLM_MODEL_NAME
        
        if not self.api_key:
            raise ValueError("LLM_API_KEY ist nicht konfiguriert")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
    
    def generate_config(
        self,
        simulation_id: str,
        project_id: str,
        graph_id: str,
        simulation_requirement: str,
        document_text: str,
        entities: List[EntityNode],
        enable_twitter: bool = True,
        enable_reddit: bool = True,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> SimulationParameters:
        """
        Intelligente Generierung einer vollständigen Simulationskonfiguration (schrittweise)
        
        Args:
            simulation_id: Simulations-ID
            project_id: Projekt-ID
            graph_id: Graph-ID
            simulation_requirement: Simulationsanforderungsbeschreibung
            document_text: Originaler Dokumentinhalt
            entities: Gefilterte Entitätsliste
            enable_twitter: Ob Twitter aktiviert werden soll
            enable_reddit: Ob Reddit aktiviert werden soll
            progress_callback: Fortschritts-Rückruffunktion (current_step, total_steps, message)
            
        Returns:
            SimulationParameters: Vollständige Simulationsparameter
        """
        logger.info(f"Starte intelligente Simulationskonfigurationsgenerierung: simulation_id={simulation_id}, Entitäten={len(entities)}")
        
        # Gesamtschrittanzahl berechnen
        num_batches = math.ceil(len(entities) / self.AGENTS_PER_BATCH)
        total_steps = 3 + num_batches  # Zeitkonfiguration + Ereigniskonfiguration + N Agent-Stapel + Plattformkonfiguration
        current_step = 0
        
        def report_progress(step: int, message: str):
            nonlocal current_step
            current_step = step
            if progress_callback:
                progress_callback(step, total_steps, message)
            logger.info(f"[{step}/{total_steps}] {message}")
        
        # 1. Basiskontextinformationen aufbauen
        context = self._build_context(
            simulation_requirement=simulation_requirement,
            document_text=document_text,
            entities=entities
        )
        
        reasoning_parts = []
        
        # ========== Schritt 1: Zeitkonfiguration generieren ==========
        report_progress(1, "Generiere Zeitkonfiguration...")
        num_entities = len(entities)
        time_config_result = self._generate_time_config(context, num_entities)
        time_config = self._parse_time_config(time_config_result, num_entities)
        reasoning_parts.append(f"Zeitkonfiguration: {time_config_result.get('reasoning', 'Erfolgreich')}")
        
        # ========== Schritt 2: Ereigniskonfiguration generieren ==========
        report_progress(2, "Generiere Ereigniskonfiguration und Hot-Topics...")
        event_config_result = self._generate_event_config(context, simulation_requirement, entities)
        event_config = self._parse_event_config(event_config_result)
        reasoning_parts.append(f"Ereigniskonfiguration: {event_config_result.get('reasoning', 'Erfolgreich')}")
        
        # ========== Schritte 3-N: Agent-Konfigurationen stapelweise generieren ==========
        all_agent_configs = []
        for batch_idx in range(num_batches):
            start_idx = batch_idx * self.AGENTS_PER_BATCH
            end_idx = min(start_idx + self.AGENTS_PER_BATCH, len(entities))
            batch_entities = entities[start_idx:end_idx]
            
            report_progress(
                3 + batch_idx,
                f"Generiere Agent-Konfigurationen ({start_idx + 1}-{end_idx}/{len(entities)})..."
            )
            
            batch_configs = self._generate_agent_configs_batch(
                context=context,
                entities=batch_entities,
                start_idx=start_idx,
                simulation_requirement=simulation_requirement
            )
            all_agent_configs.extend(batch_configs)
        
        reasoning_parts.append(f"Agent-Konfiguration: Erfolgreich {len(all_agent_configs)} generiert")
        
        # ========== Publisher-Agent für Initialbeiträge zuweisen ==========
        logger.info("Geeigneten Publisher-Agent für Initialbeiträge zuweisen...")
        event_config = self._assign_initial_post_agents(event_config, all_agent_configs)
        assigned_count = len([p for p in event_config.initial_posts if p.get("poster_agent_id") is not None])
        reasoning_parts.append(f"Initialbeitrags-Zuordnung: {assigned_count} Beiträge wurden Veröffenltichern zugewiesen")
        
        # ========== Letzter Schritt: Plattformkonfiguration generieren ==========
        report_progress(total_steps, "Generiere Plattformkonfiguration...")
        twitter_config = None
        reddit_config = None
        
        if enable_twitter:
            twitter_config = PlatformConfig(
                platform="twitter",
                recency_weight=0.4,
                popularity_weight=0.3,
                relevance_weight=0.3,
                viral_threshold=10,
                echo_chamber_strength=0.5
            )
        
        if enable_reddit:
            reddit_config = PlatformConfig(
                platform="reddit",
                recency_weight=0.3,
                popularity_weight=0.4,
                relevance_weight=0.3,
                viral_threshold=15,
                echo_chamber_strength=0.6
            )
        
        # Finale Parameter aufbauen
        params = SimulationParameters(
            simulation_id=simulation_id,
            project_id=project_id,
            graph_id=graph_id,
            simulation_requirement=simulation_requirement,
            time_config=time_config,
            agent_configs=all_agent_configs,
            event_config=event_config,
            twitter_config=twitter_config,
            reddit_config=reddit_config,
            llm_model=self.model_name,
            llm_base_url=self.base_url,
            generation_reasoning=" | ".join(reasoning_parts)
        )
        
        logger.info(f"Simulationskonfigurationsgenerierung abgeschlossen: {len(params.agent_configs)} Agent-Konfigurationen")
        
        return params
    
    def _build_context(
        self,
        simulation_requirement: str,
        document_text: str,
        entities: List[EntityNode]
    ) -> str:
        """LLM-Kontext erstellen, auf maximale Länge gekürzt"""
        
        # Entitätszusammenfassung
        entity_summary = self._summarize_entities(entities)
        
        # Kontext erstellen
        context_parts = [
            f"## Simulationsanforderung\n{simulation_requirement}",
            f"\n## Entitätsinformationen ({len(entities)})\n{entity_summary}",
        ]
        
        current_length = sum(len(p) for p in context_parts)
        remaining_length = self.MAX_CONTEXT_LENGTH - current_length - 500  # 500 Zeichen Reserve lassen
        
        if remaining_length > 0 and document_text:
            doc_text = document_text[:remaining_length]
            if len(document_text) > remaining_length:
                doc_text += "\n...(Dokument wurde gekürzt)"
            context_parts.append(f"\n## Originaler Dokumentinhalt\n{doc_text}")
        
        return "\n".join(context_parts)
    
    def _summarize_entities(self, entities: List[EntityNode]) -> str:
        """Entitätszusammenfassung generieren"""
        lines = []
        
        # Nach Typ gruppieren
        by_type: Dict[str, List[EntityNode]] = {}
        for e in entities:
            t = e.get_entity_type() or "Unknown"
            if t not in by_type:
                by_type[t] = []
            by_type[t].append(e)
        
        for entity_type, type_entities in by_type.items():
            lines.append(f"\n### {entity_type} ({len(type_entities)})")
            # Anzeigeanzahl und Zusammenfassungslänge aus Konfiguration verwenden
            display_count = self.ENTITIES_PER_TYPE_DISPLAY
            summary_len = self.ENTITY_SUMMARY_LENGTH
            for e in type_entities[:display_count]:
                summary_preview = (e.summary[:summary_len] + "...") if len(e.summary) > summary_len else e.summary
                lines.append(f"- {e.name}: {summary_preview}")
            if len(type_entities) > display_count:
                lines.append(f"  ... noch {len(type_entities) - display_count} weitere")
        
        return "\n".join(lines)
    
    def _call_llm_with_retry(self, prompt: str, system_prompt: str) -> Dict[str, Any]:
        """LLM-Aufruf mit Retry, einschließlich JSON-Reparaturlogik"""
        import re
        
        max_attempts = 3
        last_error = None
        
        for attempt in range(max_attempts):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.7 - (attempt * 0.1)  # Bei jedem Retry die Temperatur senken
                    # Kein max_tokens setzen, LLM frei agieren lassen
                )
                
                content = response.choices[0].message.content
                finish_reason = response.choices[0].finish_reason
                
                # Prüfen, ob abgeschnitten
                if finish_reason == 'length':
                    logger.warning(f"LLM-Ausgabe abgeschnitten (Versuch {attempt+1})")
                    content = self._fix_truncated_json(content)
                
                # JSON zu parsen versuchen
                try:
                    return json.loads(content)
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON-Parsing fehlgeschlagen (Versuch {attempt+1}): {str(e)[:80]}")
                    
                    # JSON zu reparieren versuchen
                    fixed = self._try_fix_config_json(content)
                    if fixed:
                        return fixed
                    
                    last_error = e
                    
            except Exception as e:
                logger.warning(f"LLM-Aufruf fehlgeschlagen (Versuch {attempt+1}): {str(e)[:80]}")
                last_error = e
                import time
                time.sleep(2 * (attempt + 1))
        
        raise last_error or Exception("LLM-Aufruf fehlgeschlagen")
    
    def _fix_truncated_json(self, content: str) -> str:
        """Truncated JSON reparieren"""
        content = content.strip()
        
        # Ungeschlossene Klammern berechnen
        open_braces = content.count('{') - content.count('}')
        open_brackets = content.count('[') - content.count(']')
        
        # Prüfen, ob ungeschlossene Strings vorhanden sind
        if content and content[-1] not in '",}]':
            content += '"'
        
        # Klammern schließen
        content += ']' * open_brackets
        content += '}' * open_braces
        
        return content
    
    def _try_fix_config_json(self, content: str) -> Optional[Dict[str, Any]]:
        """Versuchen, Konfigurations-JSON zu reparieren"""
        import re
        
        # Truncated JSON reparieren
        content = self._fix_truncated_json(content)
        
        # JSON-Teil extrahieren
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            json_str = json_match.group()
            
            # Zeilenumbrüche in Strings entfernen
            def fix_string(match):
                s = match.group(0)
                s = s.replace('\n', ' ').replace('\r', ' ')
                s = re.sub(r'\s+', ' ', s)
                return s
            
            json_str = re.sub(r'"[^"\\]*(?:\\.[^"\\]*)*"', fix_string, json_str)
            
            try:
                return json.loads(json_str)
            except:
                # Versuchen, alle Kontrollzeichen zu entfernen
                json_str = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', json_str)
                json_str = re.sub(r'\s+', ' ', json_str)
                try:
                    return json.loads(json_str)
                except:
                    pass
        
        return None
    
    def _generate_time_config(self, context: str, num_entities: int) -> Dict[str, Any]:
        """Zeitkonfiguration generieren"""
        # Kontext auf konfigurierte Länge kürzen
        context_truncated = context[:self.TIME_CONFIG_CONTEXT_LENGTH]
        
        # Maximal zulässigen Wert berechnen (80% der Agentenanzahl)
        max_agents_allowed = max(1, int(num_entities * 0.9))
        
        prompt = f"""Basierend auf den folgenden Simulationsanforderungen Zeitkonfiguration generieren.

{context_truncated}

## Aufgabe
Bitte Zeitkonfiguration als JSON generieren.

### Grundprinzipien (nur zur Referenz, müssen je nach Ereignis und Teilnehmergruppe angepasst werden):
- Benutzergruppe sind Chinesen, müssen dem Peking-Zeit Tagesablauf entsprechen
- 0-5 Uhr nachts kaum Aktivität (Aktivitätskoeffizient 0.05)
- 6-8 Uhr morgens allmählich aktiver (Aktivitätskoeffizient 0.4)
- Arbeitszeit 9-18 Uhr mittlere Aktivität (Aktivitätskoeffizient 0.7)
- 19-22 Uhr abends Spitzenzeit (Aktivitätskoeffizient 1.5)
- Nach 23 Uhr sinkende Aktivität (Aktivitätskoeffizient 0.5)
- Allgemeine Regel: Nachts niedrige Aktivität, morgens ansteigend, Arbeitstage mittel, abends Spitzen
- **Wichtig**: Die folgenden Beispielwerte dienen nur zur Referenz. Sie müssen die spezifischen Zeiträume gemäß Ereignisart und Teilnehmergruppe anpassen
  - Beispiel: Studentengruppe Spitzenzeit kann 21-23 Uhr sein; Medien ganztägig aktiv; offizielle Stellen nur während Arbeitszeit
  - Beispiel: Aktuelle Hotspots können auch nachts Diskussionen verursachen, off_peak_hours kann entsprechend verkürzt werden

### JSON-Rückgabeformat (kein Markdown)

Beispiel:
{{
    "total_simulation_hours": 72,
    "minutes_per_round": 60,
    "agents_per_hour_min": 5,
    "agents_per_hour_max": 50,
    "peak_hours": [19, 20, 21, 22],
    "off_peak_hours": [0, 1, 2, 3, 4, 5],
    "morning_hours": [6, 7, 8],
    "work_hours": [9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
    "reasoning": "Erklärung zur Zeitkonfiguration für dieses Ereignis"
}}

Feldbeschreibungen:
- total_simulation_hours (int): Gesamtsimulationsdauer, 24-168 Stunden, kurze für Notfälle, längere für andauernde Themen
- minutes_per_round (int): Dauer pro Runde, 30-120 Minuten, 60 Minuten empfohlen
- agents_per_hour_min (int): Minimale Anzahl aktivierter Agenten pro Stunde (Wertebereich: 1-{max_agents_allowed})
- agents_per_hour_max (int): Maximale Anzahl aktivierter Agenten pro Stunde (Wertebereich: 1-{max_agents_allowed})
- peak_hours (int-Array): Spitzenzeiten, angepasst nach Ereignisteilnehmergruppe
- off_peak_hours (int-Array): Nebenzeiten, normalerweise spät nachts/früh morgens
- morning_hours (int-Array): Morgenstunden
- work_hours (int-Array): Arbeitsstunden
- reasoning (string): Kurze Erklärung warum diese Konfiguration"""

        system_prompt = "Sie sind Social-Media-Simulationsexperte. Geben Sie reines JSON-Format zurück, Zeitkonfiguration muss dem chinesischen Tagesablauf entsprechen."
        
        try:
            return self._call_llm_with_retry(prompt, system_prompt)
        except Exception as e:
            logger.warning(f"Zeitkonfigurations-LLM-Generierung fehlgeschlagen: {e}, verwende Standardkonfiguration")
            return self._get_default_time_config(num_entities)
    
    def _get_default_time_config(self, num_entities: int) -> Dict[str, Any]:
        """Standard-Zeitkonfiguration abrufen (chinesischer Tagesablauf)"""
        return {
            "total_simulation_hours": 72,
            "minutes_per_round": 60,  # Jede Runde 1 Stunde, beschleunigter Zeitfluss
            "agents_per_hour_min": max(1, num_entities // 15),
            "agents_per_hour_max": max(5, num_entities // 5),
            "peak_hours": [19, 20, 21, 22],
            "off_peak_hours": [0, 1, 2, 3, 4, 5],
            "morning_hours": [6, 7, 8],
            "work_hours": [9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
            "reasoning": "Standard chinesischer Tagesablauf (jede Runde 1 Stunde)"
        }
    
    def _parse_time_config(self, result: Dict[str, Any], num_entities: int) -> TimeSimulationConfig:
        """Zeitkonfigurationsergebnis parsen und agents_per_hour-Werte gegen Gesamtanzahl validieren"""
        # Rohwerte abrufen
        agents_per_hour_min = result.get("agents_per_hour_min", max(1, num_entities // 15))
        agents_per_hour_max = result.get("agents_per_hour_max", max(5, num_entities // 5))
        
        # Validieren und korrigieren: Sicherstellen, dass Gesamtanzahl nicht überschritten wird
        if agents_per_hour_min > num_entities:
            logger.warning(f"agents_per_hour_min ({agents_per_hour_min}) überschreitet Gesamt-Agent-Anzahl ({num_entities}), korrigiert")
            agents_per_hour_min = max(1, num_entities // 10)
        
        if agents_per_hour_max > num_entities:
            logger.warning(f"agents_per_hour_max ({agents_per_hour_max}) überschreitet Gesamt-Agent-Anzahl ({num_entities}), korrigiert")
            agents_per_hour_max = max(agents_per_hour_min + 1, num_entities // 2)
        
        # Sicherstellen, dass min < max
        if agents_per_hour_min >= agents_per_hour_max:
            agents_per_hour_min = max(1, agents_per_hour_max // 2)
            logger.warning(f"agents_per_hour_min >= max, korrigiert auf {agents_per_hour_min}")
        
        return TimeSimulationConfig(
            total_simulation_hours=result.get("total_simulation_hours", 72),
            minutes_per_round=result.get("minutes_per_round", 60),  # Standardmäßig jede Runde 1 Stunde
            agents_per_hour_min=agents_per_hour_min,
            agents_per_hour_max=agents_per_hour_max,
            peak_hours=result.get("peak_hours", [19, 20, 21, 22]),
            off_peak_hours=result.get("off_peak_hours", [0, 1, 2, 3, 4, 5]),
            off_peak_activity_multiplier=0.05,  # Nachts kaum Aktivität
            morning_hours=result.get("morning_hours", [6, 7, 8]),
            morning_activity_multiplier=0.4,
            work_hours=result.get("work_hours", list(range(9, 19))),
            work_activity_multiplier=0.7,
            peak_activity_multiplier=1.5
        )
    
    def _generate_event_config(
        self, 
        context: str, 
        simulation_requirement: str,
        entities: List[EntityNode]
    ) -> Dict[str, Any]:
        """Ereigniskonfiguration generieren"""
        
        # Liste verfügbarer Entitätstypen abrufen, als Referenz für LLM
        entity_types_available = list(set(
            e.get_entity_type() or "Unknown" for e in entities
        ))
        
        # Für jeden Typ repräsentative Entitätsnamen auflisten
        type_examples = {}
        for e in entities:
            etype = e.get_entity_type() or "Unknown"
            if etype not in type_examples:
                type_examples[etype] = []
            if len(type_examples[etype]) < 3:
                type_examples[etype].append(e.name)
        
        type_info = "\n".join([
            f"- {t}: {', '.join(examples)}" 
            for t, examples in type_examples.items()
        ])
        
        # Kontext auf konfigurierte Länge kürzen
        context_truncated = context[:self.EVENT_CONFIG_CONTEXT_LENGTH]
        
        prompt = f"""Basierend auf den folgenden Simulationsanforderungen Ereigniskonfiguration generieren.

Simulationsanforderung: {simulation_requirement}

{context_truncated}

## Verfügbare Entitätstypen und Beispiele
{type_info}

## Aufgabe
Bitte Ereigniskonfiguration als JSON generieren:
- Hot-Topic-Schlüsselwörter extrahieren
- Öffentliche Meinungsentwicklungsrichtung beschreiben
- Initiale Post-Inhalte entwerfen, **jeder Post muss poster_type (Veröffentlichertyp) angeben**

**Wichtig**: poster_type muss aus den oben genannten "verfügbaren Entitätstypen" ausgewählt werden, damit initiale Posts dem richtigen Agent zugewiesen werden können.
Beispiel: Offizielle Stellungnahmen sollten von Official/University-Typ veröffentlicht werden, Nachrichten von MediaOutlet, Studentenmeinungen von Student.

JSON-Rückgabeformat (kein Markdown):
{{
    "hot_topics": ["Schlüsselwort1", "Schlüsselwort2", ...],
    "narrative_direction": "<Beschreibung der Öffentlichen Meinungsentwicklungsrichtung>",
    "initial_posts": [
        {{"content": "Post-Inhalt", "poster_type": "Entitätstyp (muss aus verfügbaren Typen ausgewählt werden)"}},
        ...
    ],
    "reasoning": "<Kurze Erklärung>"
}}"""

        system_prompt = "Sie sind Öffentliche-Meinung-Analytikexperte. Geben Sie reines JSON-Format zurück. poster_type muss exakt mit verfügbaren Entitätstypen übereinstimmen."
        
        try:
            return self._call_llm_with_retry(prompt, system_prompt)
        except Exception as e:
            logger.warning(f"Ereigniskonfigurations-LLM-Generierung fehlgeschlagen: {e}, verwende Standardkonfiguration")
            return {
                "hot_topics": [],
                "narrative_direction": "",
                "initial_posts": [],
                "reasoning": "Standardkonfiguration verwendet"
            }
    
    def _parse_event_config(self, result: Dict[str, Any]) -> EventConfig:
        """Ereigniskonfigurationsergebnis parsen"""
        return EventConfig(
            initial_posts=result.get("initial_posts", []),
            scheduled_events=[],
            hot_topics=result.get("hot_topics", []),
            narrative_direction=result.get("narrative_direction", "")
        )
    
    def _assign_initial_post_agents(
        self,
        event_config: EventConfig,
        agent_configs: List[AgentActivityConfig]
    ) -> EventConfig:
        """
       Geeigneten Publisher-Agent für initiale Posts zuweisen
        
       Basierend auf dem poster_type jedes Posts den am besten passenden agent_id zuordnen
        """
        if not event_config.initial_posts:
            return event_config
        
        # Agent-Index nach Entitätstyp erstellen
        agents_by_type: Dict[str, List[AgentActivityConfig]] = {}
        for agent in agent_configs:
            etype = agent.entity_type.lower()
            if etype not in agents_by_type:
                agents_by_type[etype] = []
            agents_by_type[etype].append(agent)
        
        # Typ-Alias-Tabelle (verarbeitet verschiedene Formate, die LLM ausgeben könnte)
        type_aliases = {
            "official": ["official", "university", "governmentagency", "government"],
            "university": ["university", "official"],
            "mediaoutlet": ["mediaoutlet", "media"],
            "student": ["student", "person"],
            "professor": ["professor", "expert", "teacher"],
            "alumni": ["alumni", "person"],
            "organization": ["organization", "ngo", "company", "group"],
            "person": ["person", "student", "alumni"],
        }
        
        # Index der pro Typ bereits verwendeten Agenten aufzeichnen, um Wiederverwendung desselben Agenten zu vermeiden
        used_indices: Dict[str, int] = {}
        
        updated_posts = []
        for post in event_config.initial_posts:
            poster_type = post.get("poster_type", "").lower()
            content = post.get("content", "")
            
            # Versuchen, passenden Agenten zu finden
            matched_agent_id = None
            
            # 1. Direkte Übereinstimmung
            if poster_type in agents_by_type:
                agents = agents_by_type[poster_type]
                idx = used_indices.get(poster_type, 0) % len(agents)
                matched_agent_id = agents[idx].agent_id
                used_indices[poster_type] = idx + 1
            else:
                # 2. Alias-Übereinstimmung verwenden
                for alias_key, aliases in type_aliases.items():
                    if poster_type in aliases or alias_key == poster_type:
                        for alias in aliases:
                            if alias in agents_by_type:
                                agents = agents_by_type[alias]
                                idx = used_indices.get(alias, 0) % len(agents)
                                matched_agent_id = agents[idx].agent_id
                                used_indices[alias] = idx + 1
                                break
                    if matched_agent_id is not None:
                        break
            
            # 3. Wenn immer noch nicht gefunden, Agent mit höchstem Einfluss verwenden
            if matched_agent_id is None:
                logger.warning(f"Kein passender Agent für Typ '{poster_type}' gefunden, verwende Agent mit höchstem Einfluss")
                if agent_configs:
                    # Nach Einfluss sortieren, Agent mit höchstem Einfluss auswählen
                    sorted_agents = sorted(agent_configs, key=lambda a: a.influence_weight, reverse=True)
                    matched_agent_id = sorted_agents[0].agent_id
                else:
                    matched_agent_id = 0
            
            updated_posts.append({
                "content": content,
                "poster_type": post.get("poster_type", "Unknown"),
                "poster_agent_id": matched_agent_id
            })
            
            logger.info(f"Initialbeitrags-Zuordnung: poster_type='{poster_type}' -> agent_id={matched_agent_id}")
        
        event_config.initial_posts = updated_posts
        return event_config
    
    def _generate_agent_configs_batch(
        self,
        context: str,
        entities: List[EntityNode],
        start_idx: int,
        simulation_requirement: str
    ) -> List[AgentActivityConfig]:
        """Agent-Konfigurationen stapelweise generieren"""
        
        # Entitätsinformationen aufbauen (mit konfigurierter Zusammenfassungslänge)
        entity_list = []
        summary_len = self.AGENT_SUMMARY_LENGTH
        for i, e in enumerate(entities):
            entity_list.append({
                "agent_id": start_idx + i,
                "entity_name": e.name,
                "entity_type": e.get_entity_type() or "Unknown",
                "summary": e.summary[:summary_len] if e.summary else ""
            })
        
        prompt = f"""Basierend auf den folgenden Informationen für jede Entität Social-Media-Aktivitätskonfiguration generieren.

Simulationsanforderung: {simulation_requirement}

## Entitätsliste
```json
{json.dumps(entity_list, ensure_ascii=False, indent=2)}
```

## Aufgabe
Für jede Entität Aktivitätskonfiguration generieren, beachten:
- **Zeiten entsprechen dem chinesischen Tagesablauf**: Nachts 0-5 Uhr kaum Aktivität, abends 19-22 Uhr am aktivsten
- **Offizielle Stellen** (University/GovernmentAgency): Niedrige Aktivität(0.1-0.3), Arbeitszeit(9-17) aktiv, langsame Reaktion(60-240 Minuten), hoher Einfluss(2.5-3.0)
- **Medien** (MediaOutlet): Mittlere Aktivität(0.4-0.6), ganztägig aktiv(8-23), schnelle Reaktion(5-30 Minuten), hoher Einfluss(2.0-2.5)
- **Personen** (Student/Person/Alumni): Hohe Aktivität(0.6-0.9), hauptsächlich abends aktiv(18-23), schnelle Reaktion(1-15 Minuten), niedriger Einfluss(0.8-1.2)
- **Prominente/Experten**: Mittlere Aktivität(0.4-0.6), mittlerer bis hoher Einfluss(1.5-2.0)

JSON-Rückgabeformat (kein Markdown):
{{
    "agent_configs": [
        {{
            "agent_id": <muss mit Eingabe übereinstimmen>,
            "activity_level": <0.0-1.0>,
            "posts_per_hour": <Postfrequenz>,
            "comments_per_hour": <Kommentarfrequenz>,
            "active_hours": [<Liste aktiver Stunden, chinesischen Tagesablauf berücksichtigen>],
            "response_delay_min": <Minimale Antwortverzögerung Minuten>,
            "response_delay_max": <Maximale Antwortverzögerung Minuten>,
            "sentiment_bias": <-1.0 bis 1.0>,
            "stance": "<supportive/opposing/neutral/observer>",
            "influence_weight": <Einflussgewicht>
        }},
        ...
    ]
}}"""

        system_prompt = "Sie sind Social-Media-Verhaltensanalyseexperte. Geben Sie reines JSON zurück, Konfiguration muss dem chinesischen Tagesablauf entsprechen."
        
        try:
            result = self._call_llm_with_retry(prompt, system_prompt)
            llm_configs = {cfg["agent_id"]: cfg for cfg in result.get("agent_configs", [])}
        except Exception as e:
            logger.warning(f"Agent-Konfigurations-Chargen-LLM-Generierung fehlgeschlagen: {e}, verwende Regelgenerierung")
            llm_configs = {}
        
        # AgentActivityConfig-Objekte aufbauen
        configs = []
        for i, entity in enumerate(entities):
            agent_id = start_idx + i
            cfg = llm_configs.get(agent_id, {})
            
            # Wenn LLM keine Konfiguration generiert hat, regelbasiert generieren
            if not cfg:
                cfg = self._generate_agent_config_by_rule(entity)
            
            config = AgentActivityConfig(
                agent_id=agent_id,
                entity_uuid=entity.uuid,
                entity_name=entity.name,
                entity_type=entity.get_entity_type() or "Unknown",
                activity_level=cfg.get("activity_level", 0.5),
                posts_per_hour=cfg.get("posts_per_hour", 0.5),
                comments_per_hour=cfg.get("comments_per_hour", 1.0),
                active_hours=cfg.get("active_hours", list(range(9, 23))),
                response_delay_min=cfg.get("response_delay_min", 5),
                response_delay_max=cfg.get("response_delay_max", 60),
                sentiment_bias=cfg.get("sentiment_bias", 0.0),
                stance=cfg.get("stance", "neutral"),
                influence_weight=cfg.get("influence_weight", 1.0)
            )
            configs.append(config)
        
        return configs
    
    def _generate_agent_config_by_rule(self, entity: EntityNode) -> Dict[str, Any]:
        """Regelbasierte Generierung einzelner Agent-Konfiguration (chinesischer Tagesablauf)"""
        entity_type = (entity.get_entity_type() or "Unknown").lower()
        
        if entity_type in ["university", "governmentagency", "ngo"]:
            # Offizielle Stellen: Aktiv während Arbeitszeit, niedrige Frequenz, hoher Einfluss
            return {
                "activity_level": 0.2,
                "posts_per_hour": 0.1,
                "comments_per_hour": 0.05,
                "active_hours": list(range(9, 18)),  # 9:00-17:59
                "response_delay_min": 60,
                "response_delay_max": 240,
                "sentiment_bias": 0.0,
                "stance": "neutral",
                "influence_weight": 3.0
            }
        elif entity_type in ["mediaoutlet"]:
            # Medien: Ganztägig aktiv, mittlere Frequenz, hoher Einfluss
            return {
                "activity_level": 0.5,
                "posts_per_hour": 0.8,
                "comments_per_hour": 0.3,
                "active_hours": list(range(7, 24)),  # 7:00-23:59
                "response_delay_min": 5,
                "response_delay_max": 30,
                "sentiment_bias": 0.0,
                "stance": "observer",
                "influence_weight": 2.5
            }
        elif entity_type in ["professor", "expert", "official"]:
            # Experten/Professoren: Aktiv während Arbeit und Abend, mittlere Frequenz
            return {
                "activity_level": 0.4,
                "posts_per_hour": 0.3,
                "comments_per_hour": 0.5,
                "active_hours": list(range(8, 22)),  # 8:00-21:59
                "response_delay_min": 15,
                "response_delay_max": 90,
                "sentiment_bias": 0.0,
                "stance": "neutral",
                "influence_weight": 2.0
            }
        elif entity_type in ["student"]:
            # Studenten: Hauptsächlich abends, hohe Frequenz
            return {
                "activity_level": 0.8,
                "posts_per_hour": 0.6,
                "comments_per_hour": 1.5,
                "active_hours": [8, 9, 10, 11, 12, 13, 18, 19, 20, 21, 22, 23],  # Morgens+Abends
                "response_delay_min": 1,
                "response_delay_max": 15,
                "sentiment_bias": 0.0,
                "stance": "neutral",
                "influence_weight": 0.8
            }
        elif entity_type in ["alumni"]:
            # Alumni: Hauptsächlich abends
            return {
                "activity_level": 0.6,
                "posts_per_hour": 0.4,
                "comments_per_hour": 0.8,
                "active_hours": [12, 13, 19, 20, 21, 22, 23],  # Mittagspause+Abends
                "response_delay_min": 5,
                "response_delay_max": 30,
                "sentiment_bias": 0.0,
                "stance": "neutral",
                "influence_weight": 1.0
            }
        else:
            # Normalos: Abends Spitzenzeit
            return {
                "activity_level": 0.7,
                "posts_per_hour": 0.5,
                "comments_per_hour": 1.2,
                "active_hours": [9, 10, 11, 12, 13, 18, 19, 20, 21, 22, 23],  # Tagsüber+Abends
                "response_delay_min": 2,
                "response_delay_max": 20,
                "sentiment_bias": 0.0,
                "stance": "neutral",
                "influence_weight": 1.0
            }
    

