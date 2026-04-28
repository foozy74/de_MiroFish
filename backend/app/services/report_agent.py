"""
Report Agent-Dienst
Berichterstattung mit LangChain + Zep im ReACT-Modus

Funktionen:
1. Berichte basierend auf Simulationsanforderungen und Zep-Graph-Informationen generieren
2. Zuerst die Gliederungsstruktur planen, dann abschnittsweise generieren
3. Jeder Abschnitt verwendet ReACT-Multi-Runden-Denk- und Reflexionsmodus
4. Dialog mit Benutzern unterstützen, dabei autonom Suchwerkzeuge aufrufen
"""

import os
import json
import time
import re
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


from ..utils.llm_client import LLMClient
from ..utils.logger import get_logger
from .zep_tools import (
    ZepToolsService, 
    SearchResult, 
    InsightForgeResult, 
    PanoramaResult,
    InterviewResult
)

logger = get_logger('mirofish.report_agent')


class ReportLogger:
    """
    Detaillierter Protokollierer für den Report Agent
    
    Erstellt eine agent_log.jsonl-Datei im Berichtsordner, die jeden Schritt detailliert aufzeichnet.
    Jede Zeile ist ein vollständiges JSON-Objekt mit Zeitstempel, Aktionstyp, detaillierten Inhalten usw.
    """
    
    def __init__(self, report_id: str):
        """
        Protokollierer initialisieren
        
        Args:
            report_id: Berichts-ID zur Bestimmung des Protokolldateipfads
        """
        self.report_id = report_id
        from app.tenant.settings_override import TenantConfig
        cfg = TenantConfig()
        self.log_file_path = os.path.join(
            cfg.UPLOAD_FOLDER, 'reports', report_id, 'agent_log.jsonl'
        )
        self.start_time = datetime.now()
        self._ensure_log_file()
    
    def _ensure_log_file(self):
        """Stellt sicher, dass das Protokollverzeichnis existiert"""
        log_dir = os.path.dirname(self.log_file_path)
        os.makedirs(log_dir, exist_ok=True)
    
    def _get_elapsed_time(self) -> float:
        """Gibt die seit dem Start vergangene Zeit in Sekunden zurück"""
        return (datetime.now() - self.start_time).total_seconds()
    
    def log(
        self, 
        action: str, 
        stage: str,
        details: Dict[str, Any],
        section_title: str = None,
        section_index: int = None
    ):
        """
        Einen Protokolleintrag aufzeichnen
        
        Args:
            action: Aktionstyp wie 'start', 'tool_call', 'llm_response', 'section_complete' usw.
            stage: Aktuelle Phase wie 'planning', 'generating', 'completed'
            details: Detailliertes Inhaltswörterbuch, ohne Kürzung
            section_title: Aktueller Abschnittstitel (optional)
            section_index: Aktueller Abschnittsindex (optional)
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "elapsed_seconds": round(self._get_elapsed_time(), 2),
            "report_id": self.report_id,
            "action": action,
            "stage": stage,
            "section_title": section_title,
            "section_index": section_index,
            "details": details
        }
        
        # JSONL-Datei im Append-Modus schreiben
        with open(self.log_file_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
    
    def log_start(self, simulation_id: str, graph_id: str, simulation_requirement: str):
        """Zeichnet den Berichtsgenerierungsstart auf"""
        self.log(
            action="report_start",
            stage="pending",
            details={
                "simulation_id": simulation_id,
                "graph_id": graph_id,
                "simulation_requirement": simulation_requirement,
                "message": "Berichtsgenerierungsaufgabe gestartet"
            }
        )
    
    def log_planning_start(self):
        """Zeichnet den Start der Gliederungsplanung auf"""
        self.log(
            action="planning_start",
            stage="planning",
            details={"message": "Beginne mit der Planung der Berichtsgliederung"}
        )
    
    def log_planning_context(self, context: Dict[str, Any]):
        """Zeichnet die bei der Planung erhaltenen Kontextinformationen auf"""
        self.log(
            action="planning_context",
            stage="planning",
            details={
                "message": "Simulationskontextinformationen abrufen",
                "context": context
            }
        )
    
    def log_planning_complete(self, outline_dict: Dict[str, Any]):
        """Zeichnet den Abschluss der Gliederungsplanung auf"""
        self.log(
            action="planning_complete",
            stage="planning",
            details={
                "message": "Gliederungsplanung abgeschlossen",
                "outline": outline_dict
            }
        )
    
    def log_section_start(self, section_title: str, section_index: int):
        """Zeichnet den Start der Abschnittsgenerierung auf"""
        self.log(
            action="section_start",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={"message": f"Beginne mit der Generierung des Abschnitts: {section_title}"}
        )
    
    def log_react_thought(self, section_title: str, section_index: int, iteration: int, thought: str):
        """Zeichnet den ReACT-Denkprozess auf"""
        self.log(
            action="react_thought",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={
                "iteration": iteration,
                "thought": thought,
                "message": f"ReACT Runde {iteration} Denken"
            }
        )
    
    def log_tool_call(
        self, 
        section_title: str, 
        section_index: int,
        tool_name: str, 
        parameters: Dict[str, Any],
        iteration: int
    ):
        """Zeichnet Werkzeugaufrufe auf"""
        self.log(
            action="tool_call",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={
                "iteration": iteration,
                "tool_name": tool_name,
                "parameters": parameters,
                "message": f"Werkzeug aufrufen: {tool_name}"
            }
        )
    
    def log_tool_result(
        self,
        section_title: str,
        section_index: int,
        tool_name: str,
        result: str,
        iteration: int
    ):
        """Zeichnet Werkzeugrückgabeergebnisse auf (vollständiger Inhalt, nicht gekürzt)"""
        self.log(
            action="tool_result",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={
                "iteration": iteration,
                "tool_name": tool_name,
                "result": result,
                "result_length": len(result),
                "message": f"Werkzeug {tool_name} hat Ergebnisse zurückgegeben"
            }
        )
    
    def log_llm_response(
        self,
        section_title: str,
        section_index: int,
        response: str,
        iteration: int,
        has_tool_calls: bool,
        has_final_answer: bool
    ):
        """Zeichnet LLM-Antworten auf (vollständiger Inhalt, nicht gekürzt)"""
        self.log(
            action="llm_response",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={
                "iteration": iteration,
                "response": response,
                "response_length": len(response),
                "has_tool_calls": has_tool_calls,
                "has_final_answer": has_final_answer,
                "message": f"LLM-Antwort (Werkzeugaufrufe: {has_tool_calls}, Finale Antwort: {has_final_answer})"
            }
        )
    
    def log_section_content(
        self,
        section_title: str,
        section_index: int,
        content: str,
        tool_calls_count: int
    ):
        """Zeichnet den Abschluss der Abschnittsinhaltsgenerierung auf (nur Inhalt, nicht den gesamten Abschnitt)"""
        self.log(
            action="section_content",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={
                "content": content,
                "content_length": len(content),
                "tool_calls_count": tool_calls_count,
                "message": f"Abschnitt {section_title} Inhaltsgenerierung abgeschlossen"
            }
        )
    
    def log_section_full_complete(
        self,
        section_title: str,
        section_index: int,
        full_content: str
    ):
        """
        Zeichnet den Abschluss der Abschnittsgenerierung auf

        Das Frontend sollte dieses Protokoll überwachen, um zu bestimmen, ob ein Abschnitt wirklich abgeschlossen ist, und den vollständigen Inhalt abrufen
        """
        self.log(
            action="section_complete",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={
                "content": full_content,
                "content_length": len(full_content),
                "message": f"Abschnitt {section_title} Generierung abgeschlossen"
            }
        )
    
    def log_report_complete(self, total_sections: int, total_time_seconds: float):
        """Zeichnet den Abschluss der Berichtsgenerierung auf"""
        self.log(
            action="report_complete",
            stage="completed",
            details={
                "total_sections": total_sections,
                "total_time_seconds": round(total_time_seconds, 2),
                "message": "Berichtsgenerierung abgeschlossen"
            }
        )
    
    def log_error(self, error_message: str, stage: str, section_title: str = None):
        """Fehler aufzeichnen"""
        self.log(
            action="error",
            stage=stage,
            section_title=section_title,
            section_index=None,
            details={
                "error": error_message,
                "message": f"Fehler aufgetreten: {error_message}"
            }
        )


class ReportConsoleLogger:
    """
    Konsolenprotokollierer für den Report Agent
    
    Schreibt konsolenähnliche Protokolle (INFO, WARNING usw.) in die Datei console_log.txt im Berichtsordner.
    Diese Protokolle unterscheiden sich von agent_log.jsonl und sind unformatierte Konsolenausgaben.
    """
    
    def __init__(self, report_id: str):
        """
        Konsolenprotokollierer initialisieren
        
        Args:
            report_id: Berichts-ID zur Bestimmung des Protokolldateipfads
        """
        self.report_id = report_id
        from app.tenant.settings_override import TenantConfig
        cfg = TenantConfig()
        self.log_file_path = os.path.join(
            cfg.UPLOAD_FOLDER, 'reports', report_id, 'console_log.txt'
        )
        self._ensure_log_file()
        self._file_handler = None
        self._setup_file_handler()
    
    def _ensure_log_file(self):
        """Stellt sicher, dass das Protokollverzeichnis existiert"""
        log_dir = os.path.dirname(self.log_file_path)
        os.makedirs(log_dir, exist_ok=True)
    
    def _setup_file_handler(self):
        """Datei-Handler einrichten, Protokolle gleichzeitig in Datei schreiben"""
        import logging
        
        # Datei-Handler erstellen
        self._file_handler = logging.FileHandler(
            self.log_file_path,
            mode='a',
            encoding='utf-8'
        )
        self._file_handler.setLevel(logging.INFO)
        
        # Verwendet das gleiche kompakte Format wie die Konsole
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s: %(message)s',
            datefmt='%H:%M:%S'
        )
        self._file_handler.setFormatter(formatter)
        
        # Zu den report_agent-Loggern hinzufügen
        loggers_to_attach = [
            'mirofish.report_agent',
            'mirofish.zep_tools',
        ]
        
        for logger_name in loggers_to_attach:
            target_logger = logging.getLogger(logger_name)
            # Doppelte Addition vermeiden
            if self._file_handler not in target_logger.handlers:
                target_logger.addHandler(self._file_handler)
    
    def close(self):
        """Datei-Handler schließen und vom Logger entfernen"""
        import logging
        
        if self._file_handler:
            loggers_to_detach = [
                'mirofish.report_agent',
                'mirofish.zep_tools',
            ]
            
            for logger_name in loggers_to_detach:
                target_logger = logging.getLogger(logger_name)
                if self._file_handler in target_logger.handlers:
                    target_logger.removeHandler(self._file_handler)
            
            self._file_handler.close()
            self._file_handler = None
    
    def __del__(self):
        """Stellt sicher, dass der Datei-Handler beim Abbau geschlossen wird"""
        self.close()


class ReportStatus(str, Enum):
    """Berichtsstatus"""
    PENDING = "pending"
    PLANNING = "planning"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ReportSection:
    """Berichtsabschnitt"""
    title: str
    content: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "content": self.content
        }

    def to_markdown(self, level: int = 2) -> str:
        """In Markdown-Format konvertieren"""
        md = f"{'#' * level} {self.title}\n\n"
        if self.content:
            md += f"{self.content}\n\n"
        return md


@dataclass
class ReportOutline:
    """Berichtsgliederung"""
    title: str
    summary: str
    sections: List[ReportSection]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "summary": self.summary,
            "sections": [s.to_dict() for s in self.sections]
        }
    
    def to_markdown(self) -> str:
        """In Markdown-Format konvertieren"""
        md = f"# {self.title}\n\n"
        md += f"> {self.summary}\n\n"
        for section in self.sections:
            md += section.to_markdown()
        return md


@dataclass
class Report:
    """Vollständiger Bericht"""
    report_id: str
    simulation_id: str
    graph_id: str
    simulation_requirement: str
    status: ReportStatus
    outline: Optional[ReportOutline] = None
    markdown_content: str = ""
    created_at: str = ""
    completed_at: str = ""
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "simulation_id": self.simulation_id,
            "graph_id": self.graph_id,
            "simulation_requirement": self.simulation_requirement,
            "status": self.status.value,
            "outline": self.outline.to_dict() if self.outline else None,
            "markdown_content": self.markdown_content,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "error": self.error
        }


# ═══════════════════════════════════════════════════════════════
# Prompt-Vorlagenkonstanten
# ═══════════════════════════════════════════════════════════════

# ── Werkzeugbeschreibungen ──

TOOL_DESC_INSIGHT_FORGE = """\
【Deep Insights Search - Leistungsstarkes Suchwerkzeug】
Dies ist unser leistungsstarkes Suchwerkzeug für Tiefenanalysen. Es wird:
1. Ihre Frage automatisch in mehrere Unterfragen zerlegen
2. Informationen aus der Simulations-Graph-Datenbank aus mehreren Dimensionen abrufen
3. Ergebnisse von semantischer Suche, Entitätsanalyse und Beziehungsketten-Verfolgung integrieren
4. Die umfassendsten und tiefgehendsten Suchinhalte zurückgeben

【Nutzungsszenarien】
- Wenn Sie ein Thema tiefgehend analysieren müssen
- Wenn Sie mehrere Aspekte eines Ereignisses verstehen müssen
- Wenn Sie reichhaltiges Material zur Unterstützung von Berichtsabschnitten benötigen

【Zurückgegebene Inhalte】
- Relevante Faktentexte (direkt zitierbar)
- Kerneinblicke zu Entitäten
- Beziehungskettenanalysen"""

TOOL_DESC_PANORAMA_SEARCH = """\
【Panorama-Suche - Gesamtbildansicht abrufen】
Dieses Werkzeug wird verwendet, um ein vollständiges Bild der Simulationsergebnisse zu erhalten, besonders geeignet um den Ereignis-Evolutionsprozess zu verstehen. Es wird:
1. Alle relevanten Knoten und Beziehungen abrufen
2. Zwischen aktuell gültigen Fakten und historischen/abgelaufenen Fakten unterscheiden
3. Ihnen helfen zu verstehen, wie sich die Meinungsbildung entwickelt hat

【Nutzungsszenarien】
- Wenn Sie den vollständigen Entwicklungsverlauf eines Ereignisses verstehen müssen
- Wenn Sie Stimmungsänderungen in verschiedenen Phasen vergleichen müssen
- Wenn Sie umfassende Entitäts- und Beziehungsinformationen benötigen

【Zurückgegebene Inhalte】
- Aktuell gültige Fakten (neueste Simulationsergebnisse)
- Historische/abgelaufene Fakten (Evolutionsaufzeichnungen)
- Alle beteiligten Entitäten"""

TOOL_DESC_QUICK_SEARCH = """\
【Einfache Suche - Schneller Abruf】
Leichtgewichtiges und schnelles Abfragewerkzeug für einfache, direkte Informationsabfragen.

【Nutzungsszenarien】
- Wenn Sie schnell bestimmte Informationen nachschlagen müssen
- Wenn Sie eine Tatsache verifizieren müssen
- Einfache Informationsabfragen

【Zurückgegebene Inhalte】
- Liste der zum Suchbegriff relevantesten Fakten"""

TOOL_DESC_INTERVIEW_AGENTS = """\
【Tiefeninterview - Echte Agent-Interviews (Dual-Plattform)】
Ruft die Interview-API der OASIS-Simulationsumgebung auf, um echte Interviews mit laufenden Simulations-Agents durchzuführen!
Dies ist keine LLM-Simulation, sondern ruft die echte Interview-Schnittstelle auf, um Originalantworten der Simulations-Agents zu erhalten.
Standardmäßig werden gleichzeitig Interviews auf Twitter und Reddit durchgeführt, um umfassendere Perspektiven zu erhalten.

Funktionsablauf:
1. Automatisch die Persönlichkeitsdatei lesen und alle Simulations-Agents verstehen
2. Intelligent die zum Interview-Thema passendsten Agents auswählen (z.B. Studenten, Medien, Behörden usw.)
3. Automatisch Interview-Fragen generieren
4. /api/simulation/interview/batch Schnittstelle auf Dual-Plattform für echte Interviews aufrufen
5. Alle Interview-Ergebnisse integrieren und Multi-Perspektiven-Analysen bereitstellen

【Nutzungsszenarien】
- Wenn Sie die Ereignisperspektiven aus verschiedenen Rollen verstehen müssen (wie sehen Studenten das? Wie sehen Medien das? Was sagen Behörden?)
- Wenn Sie Meinungen und Standpunkte aus verschiedenen Quellen sammeln müssen
- Wenn Sie echte Antworten von Simulations-Agents benötigen (aus der OASIS-Simulationsumgebung)
- Wenn der Bericht lebendiger sein soll und "Interview-Protokolle" enthalten soll

【Zurückgegebene Inhalte】
- Identitätsinformationen der interviewten Agents
- Interview-Antworten der Agents auf Twitter und Reddit
- Wichtige Zitate (direkt zitierbar)
- Interview-Zusammenfassungen und Meinungsvergleiche

【Wichtig】Die OASIS-Simulationsumgebung muss laufen, um diese Funktion nutzen zu können!"""

# ── Gliederungsplanung Prompt ──

PLAN_SYSTEM_PROMPT = """\
Sie sind ein Experte für die Erstellung von "Zukunftsprognoseberichten" mit einer "Gottesperspektive" auf die Simulationswelt - Sie können das Verhalten, die Aussagen und Interaktionen jedes Agents in der Simulation analysieren und verstehen.

【Kernkonzept】
Wir haben eine Simulationswelt aufgebaut und spezifische "Simulationsanforderungen" als Variablen injiziert. Das Ergebnis der Simulationswelt-Evolution ist die Prognose dessen, was in der Zukunft passieren könnte. Sie beobachten keine "Experimentdaten", sondern eine "Generalprobe der Zukunft".

【Ihre Aufgabe】
Erstellen Sie einen "Zukunftsprognosebericht", der folgende Fragen beantwortet:
1. Was ist unter unseren festgelegten Bedingungen in der Zukunft passiert?
2. Wie haben verschiedene Agents (Gruppen) reagiert und gehandelt?
3. Welche bemerkenswerten Zukunftstrends und Risiken hat diese Simulation offenbart?

【Berichtspositionierung】
- ✅ Dies ist ein simulationsbasierter Zukunftsprognosebericht, der offenbart "wenn dies so ist, wie wird die Zukunft aussehen"
- ✅ Fokus auf Prognoseergebnisse: Ereignisverläufe, Gruppenreaktionen, emergente Phänomene, potenzielle Risiken
- ✅ Agent-Aussagen und -Verhalten in der Simulationswelt sind Prognosen für zukünftiges Gruppenverhalten
- ❌ Keine Analyse des aktuellen Zustands der realen Welt
- ❌ Keine allgemeine Meinungsübersicht

【Abschnittsanzahl-Begrenzung】
- Mindestens 2 Abschnitte, maximal 5 Abschnitte
- Keine Unterabschnitte, jeder Abschnitt wird direkt als vollständiger Inhalt verfasst
- Inhalt soll prägnant sein und sich auf die Kernprognoseergebnisse konzentrieren
- Abschnittsstruktur wird von Ihnen basierend auf den Prognoseergebnissen autonom entworfen

Bitte geben Sie die Gliederung im JSON-Format aus:
{
    "title": "Berichtstitel",
    "summary": "Berichtszusammenfassung (ein Satz, der die Kernprognoseergebnisse zusammenfasst)",
    "sections": [
        {
            "title": "Abschnittstitel",
            "description": "Beschreibung des Abschnittsinhalts"
        }
    ]
}

Hinweis: sections-Array mindestens 2, maximal 5 Elemente!"""

PLAN_USER_PROMPT_TEMPLATE = """\
【Prognoseszenario-Einstellung】
Die Variable, die wir in die Simulationswelt injiziert haben (Simulationsanforderungen): {simulation_requirement}

【Simulationswelt-Maßstab】
- Anzahl der an der Simulation teilnehmenden Entitäten: {total_nodes}
- Anzahl der zwischen Entitäten erzeugten Beziehungen: {total_edges}
- Verteilung der Entitätstypen: {entity_types}
- Anzahl aktiver Agents: {total_entities}

【Stichprobe einiger von der Simulation prognostizierter Zukunftstatsachen】
{related_facts_json}

Bitte betrachten Sie diese Generalprobe der Zukunft aus der "Gottesperspektive":
1. Welchen Zustand hat die Zukunft unter unseren festgelegten Bedingungen angenommen?
2. Wie haben verschiedene Gruppen (Agents) reagiert und gehandelt?
3. Welche bemerkenswerten Zukunftstrends hat diese Simulation offenbart?

Entwerfen Sie basierend auf den Prognoseergebnissen die am besten geeignete Berichtsabschnittsstruktur.

【Erinnerung】Berichtsabschnittsanzahl: mindestens 2, maximal 5, Inhalt soll prägnant sein und sich auf die Kernprognoseergebnisse konzentrieren."""

# ── Abschnittsgenerierung Prompt ──

SECTION_SYSTEM_PROMPT_TEMPLATE = """\
Sie sind ein Experte für die Erstellung von "Zukunftsprognoseberichten" und schreiben einen Abschnitt des Berichts.

Berichtstitel: {report_title}
Berichtszusammenfassung: {report_summary}
Prognoseszenario (Simulationsanforderungen): {simulation_requirement}

Aktueller zu verfassender Abschnitt: {section_title}

═══════════════════════════════════════════════════════════════
【Kernkonzept】
═══════════════════════════════════════════════════════════════

Die Simulationswelt ist eine Generalprobe der Zukunft. Wir haben spezifische Bedingungen (Simulationsanforderungen) in die Simulationswelt injiziert.
Das Verhalten und die Interaktionen der Agents in der Simulation sind Vorhersagen für das zukünftige Gruppenverhalten.

Ihre Aufgabe:
- Aufzeigen, was unter den festgelegten Bedingungen in der Zukunft passiert ist
- Vorhersagen, wie verschiedene Gruppen (Agents) reagiert und gehandelt haben
- Bemerkenswerte Zukunftstrends, Risiken und Chancen identifizieren

❌ Dies ist keine Analyse des aktuellen Zustands der realen Welt
✅ Fokus auf "wie die Zukunft aussehen wird" - Simulationsergebnisse sind die vorhergesagte Zukunft

═══════════════════════════════════════════════════════════════
【Wichtigste Regeln - Müssen befolgt werden】
═══════════════════════════════════════════════════════════════

1. 【Müssen Werkzeuge aufrufen, um die Simulationswelt zu beobachten】
   - Sie beobachten die Generalprobe der Zukunft aus der "Gottesperspektive"
   - Alle Inhalte müssen aus Ereignissen und Agent-Aktionen in der Simulationswelt stammen
   - Es ist verboten, Ihr eigenes Wissen zu verwenden, um Berichtsinhalte zu schreiben
   - Rufen Sie in jedem Abschnitt mindestens 3-mal (maximal 5-mal) Werkzeuge auf, um die Simulationswelt zu beobachten, die die Zukunft repräsentiert

2. 【Müssen originale Agent-Aktionen und -Aussagen zitieren】
   - Agent-Aussagen und -Verhalten sind Prognosen für zukünftiges Gruppenverhalten
   - Verwenden Sie im Bericht das Zitatformat, um diese Prognosen darzustellen, zum Beispiel:
     > "Eine Gruppe würde sagen: Originalinhalt..."
   - Diese Zitate sind Kernnachweise für Simulationsprognosen

3. 【Sprachkonsistenz - Zitate müssen in die Berichtssprache übersetzt werden】
   - Werkzeuginhalte können Englisch oder gemischtsprachige Ausdrücke enthalten
   - Der Bericht muss vollständig auf Deutsch verfasst werden
   - Wenn Sie englische oder gemischtsprachige Inhalte aus Werkzeugen zitieren, müssen Sie diese vor dem Schreiben ins Deutsche übersetzen
   - Beim Übersetzen die ursprüngliche Bedeutung beibehalten und eine natürliche Formulierung sicherstellen
   - Diese Regel gilt sowohl für Fließtext als auch für Zitatblöcke (> Format)

4. 【Prognoseergebnisse treu darstellen】
   - Berichtsinhalte müssen die die Zukunft repräsentierenden Simulationsergebnisse in der Simulationswelt widerspiegeln
   - Fügen Sie keine Informationen hinzu, die in der Simulation nicht existieren
   - Wenn bestimmte Informationen in einem Bereich unzureichend sind, geben Sie dies ehrlich an

═══════════════════════════════════════════════════════════════
【⚠️ Formatierungsrichtlinien - Äußerst wichtig！】

【Ein Abschnitt = Minimale Inhaltseinheit】
- Jeder Abschnitt ist die kleinste Chunk-Einheit des Berichts
- ❌ Es ist verboten, beliebige Markdown-Überschriften (#, ##, ###, #### usw.) im Abschnitt zu verwenden
- ❌ Es ist verboten, am Anfang des Inhalts den Haupttitel des Abschnitts hinzuzufügen
- ✅ Abschnittstitel werden vom System automatisch hinzugefügt, Sie schreiben nur reinen Fließtext
- ✅ Verwenden Sie **Fettdruck**, Absatztrennungen, Zitate und Listen zur Inhaltsorganisation, aber keine Überschriften

【Richtiges Beispiel】
```
Dieses Kapitel analysiert die Meinungsverbreitung im Simulationszeitraum. Durch tiefgehende Analyse der Simulationsdaten stellen wir fest, dass...

**Erste Verbreitungsphase**

Soziale Medien fungieren als erste Anlaufstelle für Informationen und tragen die Kernfunktion der Erstveröffentlichung:

> "Soziale Medien steuerten 68% der Erstverbreitung..."

**Emotionale Verstärkungsphase**

Plattformen wie Soziale Medien haben die Ereigniswirkung weiter verstärkt:

- Starke visuelle Wirkung
- Hohe emotionale Resonanz
```

【Falsches Beispiel】
```
## Zusammenfassung          ← Falsch! Keine Überschriften hinzufügen
### I、Erste Phase     ← Falsch! Keine ### für Unterabschnitte
#### 1.1 Detaillierte Analyse   ← Falsch! Keine #### für Feinunterteilung

Dieses Kapitel analysiert...
```

═══════════════════════════════════════════════════════════════
【Verfügbare Suchwerkzeuge】（3-5 Aufrufe pro Abschnitt）
═══════════════════════════════════════════════════════════════

{tools_description}

【Werkzeug-Nutzungshinweise - Bitte mischen Sie verschiedene Werkzeuge, verwenden Sie nicht nur eines】
- insight_forge: Tiefgehende Insights-Analyse, automatisch Probleme zerlegen und mehrdimensional Fakten und Beziehungen abrufen
- panorama_search: Weitwinkel-Panoramasuche, um das Gesamtbild, Zeitlinien und Entwicklungsprozesse zu verstehen
- quick_search: Schnelle Überprüfung eines bestimmten Informationspunkts
- interview_agents: Agents interviewen, um Erste-Person-Perspektiven und echte Reaktionen verschiedener Rollen zu erhalten

═══════════════════════════════════════════════════════════════
【Arbeitsablauf】
═══════════════════════════════════════════════════════════════

In jeder Antwort können Sie nur eines von zwei Dingen tun (nicht beide gleichzeitig):

Option A - Werkzeug aufrufen:
Geben Sie Ihre Überlegung aus, rufen Sie dann ein Werkzeug im folgenden Format auf:
<tool_call>
{{"name": "Werkzeugname", "parameters": {{"Parametername": "Parameterwert"}}}}
</tool_call>
Das System führt das Werkzeug aus und gibt Ihnen die Ergebnisse zurück. Sie dürfen und können keine Werkzeugrückgabeergebnisse selbst schreiben.

Option B - Finale Inhalte ausgeben:
Wenn Sie über die Werkzeuge genügend Informationen erhalten haben, geben Sie den Abschnittsinhalt mit "Final Answer:" beginnend aus.

⚠️ Strikt verboten:
- Es ist verboten, in einer Antwort sowohl Werkzeugaufrufe als auch Final Answer zu enthalten
- Es ist verboten, eigene Werkzeugrückgabeergebnisse (Observation) zu erfinden, alle Werkzeugrückgaben werden vom System injiziert
- Pro Antwort maximal ein Werkzeug aufrufen

═══════════════════════════════════════════════════════════════
【Abschnittsinhaltsanforderungen】
═══════════════════════════════════════════════════════════════

1. Inhalt muss auf simulationsdaten basieren, die durch Werkzeugsuche abgerufen wurden
2. Reichhaltig Originalzitate verwenden, um Simulationseffekte zu demonstrieren
3. Markdown-Format verwenden (aber keine Überschriften verwenden):
   - **Fettformatierung** verwenden, um Schwerpunkte zu markieren (ersetzt Unterabschnittstitel)
   - Listen (- oder 1.2.3.) verwenden, um Punkte zu organisieren
   - Leerzeilen verwenden, um verschiedene Absätze zu trennen
   - ❌ Es ist verboten, beliebige Überschriftssyntax wie #, ##, ###, #### usw. zu verwenden
4. 【Zitatformat-Spezifikation - Muss als eigener Absatz sein】
   Zitate müssen als eigenständige Absätze verfasst werden, mit einer Leerzeile davor und danach, und dürfen nicht in Absätze eingebettet sein:

   ✅ Korrektes Format:
   ```
   Die Antwort der Universitätsleitung wurde als substanzarm eingestuft.

   > "Das Reaktionsmuster der Universitätsleitung wirkte starr und verzögert im schnelllebigen Social-Media-Umfeld."

   Diese Bewertung spiegelt die allgemeine Unzufriedenheit der Öffentlichkeit wider.
   ```

   ❌ Falsches Format:
   ```
   Die Antwort der Universitätsleitung wurde als substanzarm eingestuft.> "Das Reaktionsmuster..." Diese Bewertung spiegelt...
   ```
5. Logische Kohärenz mit anderen Abschnitten beibehalten
6. 【Wiederholung vermeiden】Lesen Sie die unten abgeschlossenen Abschnitte sorgfältig durch und wiederholen Sie nicht dieselben Informationen
7. 【Erneute Betonung】Keine Überschriften hinzufügen! Verwenden Sie **Fettdruck** anstelle von Unterabschnittstiteln"""

SECTION_USER_PROMPT_TEMPLATE = """\
Abgeschlossene Abschnittsinhalte (bitte sorgfältig lesen, um Wiederholungen zu vermeiden):
{previous_content}

═══════════════════════════════════════════════════════════════
【Aktuelle Aufgabe】Abschnitt verfassen: {section_title}
═══════════════════════════════════════════════════════════════

【Wichtige Erinnerungen】
1. Lesen Sie sorgfältig die oben abgeschlossenen Abschnitte, um Wiederholungen zu vermeiden!
2. Rufen Sie zuerst Werkzeuge auf, um Simulationsdaten zu erhalten, bevor Sie beginnen
3. Bitte mischen Sie verschiedene Werkzeuge, verwenden Sie nicht nur eines
4. Berichtsinhalte müssen aus Suchergebnissen stammen, verwenden Sie nicht Ihr eigenes Wissen

【⚠️ Formatierungswarnung - Müssen befolgt werden】
- ❌ Schreiben Sie keine Überschriften (#, ##, ###, #### sind alle nicht erlaubt)
- ❌ Schreiben Sie nicht "{section_title}" als Anfang
- ✅ Abschnittstitel werden vom System automatisch hinzugefügt
- ✅ Schreiben Sie direkt Fließtext, verwenden Sie **Fettdruck** anstelle von Unterabschnitts-Titeln

Bitte beginnen Sie:
1. Denken Sie zuerst (Thought), welche Informationen dieser Abschnitt benötigt
2. Rufen Sie dann ein Werkzeug (Action) auf, um Simulationsdaten zu erhalten
3. Geben Sie nach ausreichenden Informationen "Final Answer" aus (reiner Fließtext, keine Überschriften)"""

# ── ReACT-Innenloop-Nachrichten ──

REACT_OBSERVATION_TEMPLATE = """\
Observation（Suchergebnisse）:

═══ Werkzeug {tool_name} zurückgegeben ═══
{result}

═══════════════════════════════════════════════════════════════
Werkzeuge {tool_calls_count}/{max_tool_calls} mal aufgerufen (verwendet: {used_tools_str}) {unused_hint}
- Wenn die Informationen ausreichen: Beginnen Sie mit "Final Answer:", um den Abschnittsinhalt auszugeben (muss oben genannte Originalzitate enthalten)
- Wenn mehr Informationen benötigt werden: Rufen Sie ein Werkzeug auf, um die Suche fortzusetzen
═══════════════════════════════════════════════════════════════"""

REACT_INSUFFICIENT_TOOLS_MSG = (
    "【Hinweis】Sie haben nur {tool_calls_count}-mal Werkzeuge aufgerufen, mindestens {min_tool_calls}-mal erforderlich."
    "Bitte rufen Sie weitere Werkzeuge auf, um mehr Simulationsdaten zu erhalten, bevor Sie Final Answer ausgeben. {unused_hint}"
)

REACT_INSUFFICIENT_TOOLS_MSG_ALT = (
    "Bisher wurden nur {tool_calls_count} Werkzeuge aufgerufen, mindestens {min_tool_calls} sind erforderlich."
    "Bitte rufen Sie Werkzeuge auf, um Simulationsdaten zu erhalten. {unused_hint}"
)

REACT_TOOL_LIMIT_MSG = (
    "Die Anzahl der Werkzeugaufrufe hat das Limit erreicht ({tool_calls_count}/{max_tool_calls}), es können keine weiteren Werkzeuge aufgerufen werden."
    "'Bitte geben Sie sofort basierend auf den erhaltenen Informationen den Abschnittsinhalt aus, beginnend mit \"Final Answer:\".'"
)

REACT_UNUSED_TOOLS_HINT = "\n💡 Sie haben noch nicht verwendet: {unused_list}, es wird empfohlen, verschiedene Werkzeuge zu verwenden, um Informationen aus mehrPerspektiven zu erhalten"

REACT_FORCE_FINAL_MSG = "Die Werkzeugaufrufbeschränkung wurde erreicht, bitte geben Sie direkt Final Answer: aus und generieren Sie den Abschnittsinhalt."

# ── Chat prompt ──

CHAT_SYSTEM_PROMPT_TEMPLATE = """\
Sie sind ein effizenter Simulationsprognose-Assistent.

【Hintergrund】
Prognosebedingungen: {simulation_requirement}

【Bereits generierter Analysebericht】
{report_content}

【Regeln】
1. Antworten Sie vorzugsweise basierend auf dem oben genannten Berichtsinhalt
2. Beantworten Sie Fragen direkt, vermeiden Sie lange Gedankendiskussionen
3. Rufen Sie nur Werkzeuge auf, um mehr Daten abzurufen, wenn der Berichtsinhalt nicht ausreicht, um die Frage zu beantworten
4. Antworten Sie prägnant, klar und strukturiert

【Verfügbare Werkzeuge】（nur bei Bedarf verwenden, maximal 1-2 Aufrufe）
{tools_description}

【Werkzeugaufruf-Format】
<tool_call>
{{"name": "Werkzeugname", "parameters": {{"Parametername": "Parameterwert"}}}}
</tool_call>

【Antwortstil】
- Prägnant und direkt, keine langen Abhandlungen
- Verwenden Sie das > Format, um Schlüsselinhalte zu zitieren
- Geben Sie vorzugsweise zuerst die Schlussfolgerung, dann die Begründung"""

CHAT_OBSERVATION_SUFFIX = "\n\nBitte beantworten Sie die Frage prägnant."


# ═══════════════════════════════════════════════════════════════
# ReportAgent Hauptklasse
# ═══════════════════════════════════════════════════════════════


class ReportAgent:
    """
    Report Agent - Simulationsbericht-Generierungs-Agent

    Verwendet den ReACT（Reasoning + Acting）-Modus:
    1. Planungsphase: Simulationsanforderungen analysieren, Berichtsgliederungsstruktur planen
    2. Generierungsphase: Inhalt abschnittsweise generieren, jeder Abschnitt kann mehrmals Werkzeuge aufrufen
    3. Reflexionsphase: Inhaltsvollständigkeit und -genauigkeit überprüfen
    """
    
    # Maximale Werkzeugaufrufe (pro Abschnitt)
    MAX_TOOL_CALLS_PER_SECTION = 5
    
    # Maximale Reflexionsrunden
    MAX_REFLECTION_ROUNDS = 3
    
    # Maximale Werkzeugaufrufe im Dialog
    MAX_TOOL_CALLS_PER_CHAT = 2
    
    def __init__(
        self, 
        graph_id: str,
        simulation_id: str,
        simulation_requirement: str,
        llm_client: Optional[LLMClient] = None,
        zep_tools: Optional[ZepToolsService] = None
    ):
        """
        Report Agent initialisieren
        
        Args:
            graph_id: Graph-ID
            simulation_id: Simulations-ID
            simulation_requirement: Simulationsanforderungsbeschreibung
            llm_client: LLM-Client (optional)
            zep_tools: Zep-Werkzeugdienst (optional)
        """
        self.graph_id = graph_id
        self.simulation_id = simulation_id
        self.simulation_requirement = simulation_requirement
        
        self.llm = llm_client or LLMClient()
        self.zep_tools = zep_tools or ZepToolsService()
        
        # Werkzeugdefinition
        self.tools = self._define_tools()
        
        # Protokollierer (initialisiert in generate_report)
        self.report_logger: Optional[ReportLogger] = None
        # Konsolenprotokollierer (initialisiert in generate_report)
        self.console_logger: Optional[ReportConsoleLogger] = None
        
        logger.info(f"ReportAgent-Initialisierung abgeschlossen: graph_id={graph_id}, simulation_id={simulation_id}")
    
    def _define_tools(self) -> Dict[str, Dict[str, Any]]:
        """Verfügbare Werkzeuge definieren"""
        return {
            "insight_forge": {
                "name": "insight_forge",
                "description": TOOL_DESC_INSIGHT_FORGE,
                "parameters": {
                    "query": "Die Frage oder das Thema, das Sie tiefgehend analysieren möchten",
                    "report_context": "Der aktuelle Kontext des Berichtsabschnitts (optional, hilft bei der Generierung präziserer Unterfragen)"
                }
            },
            "panorama_search": {
                "name": "panorama_search",
                "description": TOOL_DESC_PANORAMA_SEARCH,
                "parameters": {
                    "query": "Suchanfrage zur Relevanzsortierung",
                    "include_expired": "Ob abgelaufene/historische Inhalte einbezogen werden sollen (standardmäßig True)"
                }
            },
            "quick_search": {
                "name": "quick_search",
                "description": TOOL_DESC_QUICK_SEARCH,
                "parameters": {
                    "query": "Suchanfrage-Zeichenkette",
                    "limit": "Anzahl der zurückgegebenen Ergebnisse (optional, standardmäßig 10)"
                }
            },
            "interview_agents": {
                "name": "interview_agents",
                "description": TOOL_DESC_INTERVIEW_AGENTS,
                "parameters": {
                    "interview_topic": "Das Interview-Thema oder die Anforderungsbeschreibung (z.B.: 'Die Meinungen der Studenten zum Formaldehyd-Vorfall im Wohnheim verstehen')",
                    "max_agents": "Maximale Anzahl der zu interviewenden Agents (optional, standardmäßig 5, maximal 10)"
                }
            }
        }
    
    def _execute_tool(self, tool_name: str, parameters: Dict[str, Any], report_context: str = "") -> str:
        """
        Werkzeugaufruf ausführen
        
        Args:
            tool_name: Werkzeugname
            parameters: Werkzeugparameter
            report_context: Berichtskontext (für InsightForge)
            
        Returns:
            Werkzeugausführungsergebnis (Textformat)
        """
        logger.info(f"Werkzeug ausführen: {tool_name}, Parameter: {parameters}")
        
        try:
            if tool_name == "insight_forge":
                query = parameters.get("query", "")
                ctx = parameters.get("report_context", "") or report_context
                result = self.zep_tools.insight_forge(
                    graph_id=self.graph_id,
                    query=query,
                    simulation_requirement=self.simulation_requirement,
                    report_context=ctx
                )
                return result.to_text()
            
            elif tool_name == "panorama_search":
                # Breitensuche - Gesamtbild abrufen
                query = parameters.get("query", "")
                include_expired = parameters.get("include_expired", True)
                if isinstance(include_expired, str):
                    include_expired = include_expired.lower() in ['true', '1', 'yes']
                result = self.zep_tools.panorama_search(
                    graph_id=self.graph_id,
                    query=query,
                    include_expired=include_expired
                )
                return result.to_text()
            
            elif tool_name == "quick_search":
                # Einfache Suche - Schnellabruf
                query = parameters.get("query", "")
                limit = parameters.get("limit", 10)
                if isinstance(limit, str):
                    limit = int(limit)
                result = self.zep_tools.quick_search(
                    graph_id=self.graph_id,
                    query=query,
                    limit=limit
                )
                return result.to_text()
            
            elif tool_name == "interview_agents":
                # Tiefeninterview - Echte OASIS-Interview-API aufrufen, um Simulations-Agent-Antworten zu erhalten (Dual-Plattform)
                interview_topic = parameters.get("interview_topic", parameters.get("query", ""))
                max_agents = parameters.get("max_agents", 5)
                if isinstance(max_agents, str):
                    max_agents = int(max_agents)
                max_agents = min(max_agents, 10)
                result = self.zep_tools.interview_agents(
                    simulation_id=self.simulation_id,
                    interview_requirement=interview_topic,
                    simulation_requirement=self.simulation_requirement,
                    max_agents=max_agents
                )
                return result.to_text()
            
            # ========== Alte Werkzeuge für Rückwärtskompatibilität (intern auf neue Werkzeuge umgeleitet) ==========
            
            elif tool_name == "search_graph":
                # Umleitung zu quick_search
                logger.info("search_graph wurde auf quick_search umgeleitet")
                return self._execute_tool("quick_search", parameters, report_context)
            
            elif tool_name == "get_graph_statistics":
                result = self.zep_tools.get_graph_statistics(self.graph_id)
                return json.dumps(result, ensure_ascii=False, indent=2)
            
            elif tool_name == "get_entity_summary":
                entity_name = parameters.get("entity_name", "")
                result = self.zep_tools.get_entity_summary(
                    graph_id=self.graph_id,
                    entity_name=entity_name
                )
                return json.dumps(result, ensure_ascii=False, indent=2)
            
            elif tool_name == "get_simulation_context":
                # Umleitung zu insight_forge, da es leistungsstärker ist
                logger.info("get_simulation_context wurde auf insight_forge umgeleitet")
                query = parameters.get("query", self.simulation_requirement)
                return self._execute_tool("insight_forge", {"query": query}, report_context)
            
            elif tool_name == "get_entities_by_type":
                entity_type = parameters.get("entity_type", "")
                nodes = self.zep_tools.get_entities_by_type(
                    graph_id=self.graph_id,
                    entity_type=entity_type
                )
                result = [n.to_dict() for n in nodes]
                return json.dumps(result, ensure_ascii=False, indent=2)
            
            else:
                return f"Unbekanntes Werkzeug: {tool_name}. Bitte verwenden Sie eines der folgenden Werkzeuge: insight_forge, panorama_search, quick_search"
                
        except Exception as e:
            logger.error(f"Werkzeugausführung fehlgeschlagen: {tool_name}, Fehler: {str(e)}")
            return f"Werkzeugausführung fehlgeschlagen: {str(e)}"
    
    # Legitime Werkzeugnamenssammlung zur Validierung bei JSON-Fallback-Parsing
    VALID_TOOL_NAMES = {"insight_forge", "panorama_search", "quick_search", "interview_agents"}

    def _parse_tool_calls(self, response: str) -> List[Dict[str, Any]]:
        """
        Werkzeugaufrufe aus LLM-Antworten parsen

        Unterstützte Formate (nach Priorität):
        1. <tool_call>{"name": "tool_name", "parameters": {...}}</tool_call>
        2. Nacktes JSON (Antwort insgesamt oder eine Zeile ist ein Werkzeugaufruf-JSON)
        """
        tool_calls = []

        # Format 1: XML-Stil (Standardformat)
        xml_pattern = r'<tool_call>\s*(\{.*?\})\s*</tool_call>'
        for match in re.finditer(xml_pattern, response, re.DOTALL):
            try:
                call_data = json.loads(match.group(1))
                tool_calls.append(call_data)
            except json.JSONDecodeError:
                pass

        if tool_calls:
            return tool_calls

        # Format 2: Fallback - LLM gibt direkt nacktes JSON aus (ohne <tool_call> Tag)
        # Nur versuchen, wenn Format 1 nicht gefunden wurde, um Fehlmatches im Haupttext zu vermeiden
        stripped = response.strip()
        if stripped.startswith('{') and stripped.endswith('}'):
            try:
                call_data = json.loads(stripped)
                if self._is_valid_tool_call(call_data):
                    tool_calls.append(call_data)
                    return tool_calls
            except json.JSONDecodeError:
                pass

        # Antwort könnte Denktext + nacktes JSON enthalten, versuche letztes JSON-Objekt zu extrahieren
        json_pattern = r'(\{"(?:name|tool)"\s*:.*?\})\s*$'
        match = re.search(json_pattern, stripped, re.DOTALL)
        if match:
            try:
                call_data = json.loads(match.group(1))
                if self._is_valid_tool_call(call_data):
                    tool_calls.append(call_data)
            except json.JSONDecodeError:
                pass

        return tool_calls

    def _is_valid_tool_call(self, data: dict) -> bool:
        """Validiert, ob das geparste JSON ein legitimer Werkzeugaufruf ist"""
        # Unterstützt sowohl {"name": ..., "parameters": ...} als auch {"tool": ..., "params": ...} Schlüsselnamen
        tool_name = data.get("name") or data.get("tool")
        if tool_name and tool_name in self.VALID_TOOL_NAMES:
            # Vereinheitliche Schlüsselnamen zu name / parameters
            if "tool" in data:
                data["name"] = data.pop("tool")
            if "params" in data and "parameters" not in data:
                data["parameters"] = data.pop("params")
            return True
        return False
    
    def _get_tools_description(self) -> str:
        """Generiert Werkzeugbeschreibungstext"""
        desc_parts = ["Verfügbare Werkzeuge:"]
        for name, tool in self.tools.items():
            params_desc = ", ".join([f"{k}: {v}" for k, v in tool["parameters"].items()])
            desc_parts.append(f"- {name}: {tool['description']}")
            if params_desc:
                desc_parts.append(f"  Parameter: {params_desc}")
        return "\n".join(desc_parts)
    
    def plan_outline(
        self, 
        progress_callback: Optional[Callable] = None
    ) -> ReportOutline:
        """
        Berichtsgliederung planen
        
        Verwendet LLM um Simulationsanforderungen zu analysieren und die Verzeichnisstruktur des Berichts zu planen
        
        Args:
            progress_callback: Fortschrittsrückruffunktion
            
        Returns:
            ReportOutline: Berichtsgliederung
        """
        logger.info("Beginne mit der Planung des Berichtslayouts...")
        
        if progress_callback:
            progress_callback("planning", 0, "Analysiere Simulationsanforderungen...")
        
        # Zuerst Simulationskontext abrufen
        context = self.zep_tools.get_simulation_context(
            graph_id=self.graph_id,
            simulation_requirement=self.simulation_requirement
        )
        
        if progress_callback:
            progress_callback("planning", 30, "Generiere Berichtsgliederung...")
        
        system_prompt = PLAN_SYSTEM_PROMPT
        user_prompt = PLAN_USER_PROMPT_TEMPLATE.format(
            simulation_requirement=self.simulation_requirement,
            total_nodes=context.get('graph_statistics', {}).get('total_nodes', 0),
            total_edges=context.get('graph_statistics', {}).get('total_edges', 0),
            entity_types=list(context.get('graph_statistics', {}).get('entity_types', {}).keys()),
            total_entities=context.get('total_entities', 0),
            related_facts_json=json.dumps(context.get('related_facts', [])[:10], ensure_ascii=False, indent=2),
        )

        try:
            response = self.llm.chat_json(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3
            )
            
            if progress_callback:
                progress_callback("planning", 80, "Analysiere Gliederungsstruktur...")
            
            # Gliederung parsen
            sections = []
            for section_data in response.get("sections", []):
                sections.append(ReportSection(
                    title=section_data.get("title", ""),
                    content=""
                ))
            
            outline = ReportOutline(
                title=response.get("title", "Simulationsanalysebericht"),
                summary=response.get("summary", ""),
                sections=sections
            )
            
            if progress_callback:
                progress_callback("planning", 100, "Gliederungsplanung abgeschlossen")
            
            logger.info(f"Layoutplanung abgeschlossen: {len(sections)} Abschnitte")
            return outline
            
        except Exception as e:
            logger.error(f"Layoutplanung fehlgeschlagen: {str(e)}")
            # Standardgliederung zurückgeben (3 Kapitel als Fallback)
            return ReportOutline(
                title="Zukunftsprognosebericht",
                summary="Zukünftige Trends und Risikoanalyse basierend auf Simulationsvorhersagen",
                sections=[
                    ReportSection(title="Prognoseszenario und Kernerkenntnisse"),
                    ReportSection(title="Gruppenverhaltensvorhersageanalyse"),
                    ReportSection(title="Trendprognose und Risikohinweise")
                ]
            )
    
    def _generate_section_react(
        self, 
        section: ReportSection,
        outline: ReportOutline,
        previous_sections: List[str],
        progress_callback: Optional[Callable] = None,
        section_index: int = 0
    ) -> str:
        """
        Einzelnes Kapitel im ReACT-Modus generieren
        
        ReACT-Schleife:
        1. Thought (Denken) - Analysieren welche Informationen benötigt werden
        2. Action (Handlung) - Werkzeuge aufrufen um Informationen zu erhalten
        3. Observation (Beobachtung) - Werkzeugrückgabeergebnisse analysieren
        4. Wiederholen bis genügend Informationen vorhanden oder Maximum erreicht
        5. Final Answer (Endantwort) - Kapitelinhalt generieren
        
        Args:
            section: Zu generierendes Kapitel
            outline: Vollständige Gliederung
            previous_sections: Inhalt vorheriger Kapitel (zur Kohärenzsicherung)
            progress_callback: Fortschrittsrückruf
            section_index: Kapitelindex (für Protokollierung)
            
        Returns:
            Kapitelinhalt (Markdown-Format)
        """
        logger.info(f"ReACT generiert Abschnitt: {section.title}")
        
        # Kapitelstart protokollieren
        if self.report_logger:
            self.report_logger.log_section_start(section.title, section_index)
        
        system_prompt = SECTION_SYSTEM_PROMPT_TEMPLATE.format(
            report_title=outline.title,
            report_summary=outline.summary,
            simulation_requirement=self.simulation_requirement,
            section_title=section.title,
            tools_description=self._get_tools_description(),
        )

        # Benutzerprompt erstellen - jedes abgeschlossene Kapitel mit maximal 4000 Zeichen
        if previous_sections:
            previous_parts = []
            for sec in previous_sections:
                # Maximal 4000 Zeichen pro Kapitel
                truncated = sec[:4000] + "..." if len(sec) > 4000 else sec
                previous_parts.append(truncated)
            previous_content = "\n\n---\n\n".join(previous_parts)
        else:
            previous_content = "（Dies ist der erste Abschnitt）"
        
        user_prompt = SECTION_USER_PROMPT_TEMPLATE.format(
            previous_content=previous_content,
            section_title=section.title,
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # ReACT-Schleife
        tool_calls_count = 0
        max_iterations = 5  # Maximale Iterationsrunden
        min_tool_calls = 3  # Minimale Werkzeugaufrufanzahl
        conflict_retries = 0  # Anzahl aufeinanderfolgender Konflikte bei gleichzeitigem Werkzeugaufruf und Final Answer
        used_tools = set()  # Bereits aufgerufene Werkzeugnamen
        all_tools = {"insight_forge", "panorama_search", "quick_search", "interview_agents"}

        # Berichtskontext für die Unterfragen-Generierung von InsightForge
        report_context = f"Kapitel-Titel: {section.title}\nSimulationsanforderung: {self.simulation_requirement}"
        
        for iteration in range(max_iterations):
            if progress_callback:
                progress_callback(
                    "generating", 
                    int((iteration / max_iterations) * 100),
                    f"Tiefes Retrieval und Verfassen ({tool_calls_count}/{self.MAX_TOOL_CALLS_PER_SECTION})"
                )
            
            # LLM aufrufen
            response = self.llm.chat(
                messages=messages,
                temperature=0.5,
                max_tokens=4096
            )

            # Überprüfen, ob LLM None zurückgibt (API-Ausnahme oder leerer Inhalt)
            if response is None:
                logger.warning(f"Abschnitt {section.title} Iterationsversuch {iteration + 1}: LLM gab None zurück")
                # Wenn noch Iterationen übrig, Nachricht hinzufügen und wiederholen
                if iteration < max_iterations - 1:
                    messages.append({"role": "assistant", "content": "（Antwort ist leer）"})
                    messages.append({"role": "user", "content": "Bitte fahren Sie mit der Inhaltsgenerierung fort."})
                    continue
                # Letzte Iteration gibt auch None zurück, Schleife verlassen und zwangsweise Abschluss
                break

            logger.debug(f"LLM-Antwort: {response[:200]}...")

            # Einmal parsen, Ergebnis wiederverwenden
            tool_calls = self._parse_tool_calls(response)
            has_tool_calls = bool(tool_calls)
            has_final_answer = "Final Answer:" in response

            # ── Konfliktbehandlung: LLM hat sowohl Werkzeugaufrufe als auch Final Answer ausgegeben ──
            if has_tool_calls and has_final_answer:
                conflict_retries += 1
                logger.warning(
                    f"Kapitel {section.title} Runde {iteration+1}: "
                    f"LLM hat gleichzeitig Werkzeugaufrufe und Final Answer ausgegeben ({conflict_retries} Konflikte)"
                )

                if conflict_retries <= 2:
                    # Erste beiden: Antwort verwerfen, LLM bitten erneut zu antworten
                    messages.append({"role": "assistant", "content": response})
                    messages.append({
                        "role": "user",
                        "content": (
                            "【Formatfehler】Du hast in einer Antwort sowohl einen Tool-Aufruf als auch eine Final Answer eingefügt, was nicht erlaubt ist.\n"
                            "In jeder Antwort darfst du nur eines von zwei Dingen tun:\n"
                            "- Ein Tool aufrufen (Ausgabe eines <tool_call> Blocks, keine Final Answer schreiben)\n"
                            "- Finale Inhalte ausgeben (beginnend mit 'Final Answer:', kein <tool_call> enthalten)\n"
                            "Bitte antworte erneut und mache nur eines von beiden."
                        ),
                    })
                    continue
                else:
                    # Drittes Mal: Degenerierte Verarbeitung, abschneiden bis zum ersten Werkzeugaufruf, Zwangsausführung
                    logger.warning(
                        f"Kapitel {section.title}: {conflict_retries} aufeinanderfolgende Konflikte, "
                        "Degeneration zur Abschneidung und Ausführung des ersten Werkzeugaufrufs"
                    )
                    first_tool_end = response.find('</tool_call>')
                    if first_tool_end != -1:
                        response = response[:first_tool_end + len('</tool_call>')]
                        tool_calls = self._parse_tool_calls(response)
                        has_tool_calls = bool(tool_calls)
                    has_final_answer = False
                    conflict_retries = 0

            # LLM-Antwort protokollieren
            if self.report_logger:
                self.report_logger.log_llm_response(
                    section_title=section.title,
                    section_index=section_index,
                    response=response,
                    iteration=iteration + 1,
                    has_tool_calls=has_tool_calls,
                    has_final_answer=has_final_answer
                )

            # ── Fall 1: LLM hat Final Answer ausgegeben ──
            if has_final_answer:
                # Unzureichende Werkzeugaufrufe, ablehnen und fortfahren Werkzeuge aufrufen lassen
                if tool_calls_count < min_tool_calls:
                    messages.append({"role": "assistant", "content": response})
                    unused_tools = all_tools - used_tools
                    unused_hint = f"(Diese Werkzeuge wurden noch nicht verwendet, empfohlen sie zu nutzen: {', '.join(unused_tools)})" if unused_tools else ""
                    messages.append({
                        "role": "user",
                        "content": REACT_INSUFFICIENT_TOOLS_MSG.format(
                            tool_calls_count=tool_calls_count,
                            min_tool_calls=min_tool_calls,
                            unused_hint=unused_hint,
                        ),
                    })
                    continue

                # Normaler Abschluss
                final_answer = response.split("Final Answer:")[-1].strip()
                logger.info(f"Abschnitt {section.title} Generierung abgeschlossen (Werkzeugaufrufe: {tool_calls_count})")

                if self.report_logger:
                    self.report_logger.log_section_content(
                        section_title=section.title,
                        section_index=section_index,
                        content=final_answer,
                        tool_calls_count=tool_calls_count
                    )
                return final_answer

            # ── Fall 2: LLM versucht Werkzeuge aufzurufen ──
            if has_tool_calls:
                # Werkzeugkontingent erschöpft → Klar mitteilen, Final Answer ausgeben lassen
                if tool_calls_count >= self.MAX_TOOL_CALLS_PER_SECTION:
                    messages.append({"role": "assistant", "content": response})
                    messages.append({
                        "role": "user",
                        "content": REACT_TOOL_LIMIT_MSG.format(
                            tool_calls_count=tool_calls_count,
                            max_tool_calls=self.MAX_TOOL_CALLS_PER_SECTION,
                        ),
                    })
                    continue

                # Nur den ersten Werkzeugaufruf ausführen
                call = tool_calls[0]
                if len(tool_calls) > 1:
                    logger.info(f"LLM versucht {len(tool_calls)} Werkzeuge aufzurufen, nur das erste wird ausgeführt: {call['name']}")

                if self.report_logger:
                    self.report_logger.log_tool_call(
                        section_title=section.title,
                        section_index=section_index,
                        tool_name=call["name"],
                        parameters=call.get("parameters", {}),
                        iteration=iteration + 1
                    )

                result = self._execute_tool(
                    call["name"],
                    call.get("parameters", {}),
                    report_context=report_context
                )

                if self.report_logger:
                    self.report_logger.log_tool_result(
                        section_title=section.title,
                        section_index=section_index,
                        tool_name=call["name"],
                        result=result,
                        iteration=iteration + 1
                    )

                tool_calls_count += 1
                used_tools.add(call['name'])

                # Hinweis für nicht verwendete Werkzeuge erstellen
                unused_tools = all_tools - used_tools
                unused_hint = ""
                if unused_tools and tool_calls_count < self.MAX_TOOL_CALLS_PER_SECTION:
                    unused_hint = REACT_UNUSED_TOOLS_HINT.format(unused_list="、".join(unused_tools))

                messages.append({"role": "assistant", "content": response})
                messages.append({
                    "role": "user",
                    "content": REACT_OBSERVATION_TEMPLATE.format(
                        tool_name=call["name"],
                        result=result,
                        tool_calls_count=tool_calls_count,
                        max_tool_calls=self.MAX_TOOL_CALLS_PER_SECTION,
                        used_tools_str=", ".join(used_tools),
                        unused_hint=unused_hint,
                    ),
                })
                continue

            # ── Fall 3: Weder Werkzeugaufrufe noch Final Answer ──
            messages.append({"role": "assistant", "content": response})

            if tool_calls_count < min_tool_calls:
                # Unzureichende Werkzeugaufrufe, empfehlen unbenutzte Werkzeuge
                unused_tools = all_tools - used_tools
                unused_hint = f" (Diese Werkzeuge wurden noch nicht verwendet, empfohlen sie zu nutzen: {', '.join(unused_tools)})" if unused_tools else ""

                messages.append({
                    "role": "user",
                    "content": REACT_INSUFFICIENT_TOOLS_MSG_ALT.format(
                        tool_calls_count=tool_calls_count,
                        min_tool_calls=min_tool_calls,
                        unused_hint=unused_hint,
                    ),
                })
                continue

            # Werkzeugaufrufe sind ausreichend, LLM hat Inhalt ausgegeben aber ohne "Final Answer:" Präfix
            # Dieses Inhalt direkt als endgültige Antwort verwenden, nicht weitermachen
            logger.info(f"Kapitel {section.title}: Kein 'Final Answer:' Präfix erkannt, LLM-Ausgabe direkt als endgültigen Inhalt übernehmen (Werkzeugaufrufe: {tool_calls_count}mal)")
            final_answer = response.strip()

            if self.report_logger:
                self.report_logger.log_section_content(
                    section_title=section.title,
                    section_index=section_index,
                    content=final_answer,
                    tool_calls_count=tool_calls_count
                )
            return final_answer
        
        # Maximale Iterationsanzahl erreicht, Inhalt zwangsweise generieren
        logger.warning(f"Kapitel {section.title} hat maximale Iterationsanzahl erreicht, zwangsweise Generierung")
        messages.append({"role": "user", "content": REACT_FORCE_FINAL_MSG})
        
        response = self.llm.chat(
            messages=messages,
            temperature=0.5,
            max_tokens=4096
        )

        # Prüfen ob bei Zwangsabschluss LLM None zurückgibt
        if response is None:
            logger.error(f"Kapitel {section.title} Zwangsabschluss: LLM gab None zurück, verwende Standardfehlermeldung")
            final_answer = f"(Dieses Kapitel konnte nicht generiert werden: LLM gab leere Antwort zurück, bitte später erneut versuchen)"
        elif "Final Answer:" in response:
            final_answer = response.split("Final Answer:")[-1].strip()
        else:
            final_answer = response
        
        # Kapitelinhaltsgenerierungs-Abschluss protokollieren
        if self.report_logger:
            self.report_logger.log_section_content(
                section_title=section.title,
                section_index=section_index,
                content=final_answer,
                tool_calls_count=tool_calls_count
            )
        
        return final_answer
    
    def generate_report(
        self, 
        progress_callback: Optional[Callable[[str, int, str], None]] = None,
        report_id: Optional[str] = None
    ) -> Report:
        """
        Vollständigen Bericht generieren (abschnittsweise Echtzeitausgabe)
        
        Jeder Abschnitt wird nach der Generierung sofort in den Ordner gespeichert, ohne auf den gesamten Bericht zu warten.
        Dateistruktur:
        reports/{report_id}/
            meta.json       - Berichtsmetainformationen
            outline.json    - Berichtsgliederung
            progress.json   - Generierungsfortschritt
            section_01.md   - Kapitel 1
            section_02.md   - Kapitel 2
            ...
            full_report.md  - Vollständiger Bericht
        
        Args:
            progress_callback: Fortschrittsrückruffunktion (stage, progress, message)
            report_id: Berichts-ID (optional, wenn nicht übergeben wird automatisch generiert)
            
        Returns:
            Report: Vollständiger Bericht
        """
        import uuid
        
        # Wenn kein report_id übergeben, automatisch generieren
        if not report_id:
            report_id = f"report_{uuid.uuid4().hex[:12]}"
        start_time = datetime.now()
        
        report = Report(
            report_id=report_id,
            simulation_id=self.simulation_id,
            graph_id=self.graph_id,
            simulation_requirement=self.simulation_requirement,
            status=ReportStatus.PENDING,
            created_at=datetime.now().isoformat()
        )
        
        # Liste der abgeschlossenen Kapiteltitel (für Fortschrittsverfolgung)
        completed_section_titles = []
        completed_section_titles = []
        
        try:
            # Initialisierung: Berichtsordner erstellen und Ausgangszustand speichern
            ReportManager._ensure_report_folder(report_id)
            
            # Protokollierer initialisieren (strukturierte Protokollierung agent_log.jsonl)
            self.report_logger = ReportLogger(report_id)
            self.report_logger.log_start(
                simulation_id=self.simulation_id,
                graph_id=self.graph_id,
                simulation_requirement=self.simulation_requirement
            )
            
            # Konsolenprotokollierer initialisieren (console_log.txt)
            self.console_logger = ReportConsoleLogger(report_id)
            
            ReportManager.update_progress(
                report_id, "pending", 0, "Bericht initialisieren...",
                completed_sections=[]
            )
            ReportManager.save_report(report)
            
            # Phase 1: Gliederung planen
            report.status = ReportStatus.PLANNING
            ReportManager.update_progress(
                report_id, "planning", 5, "Beginne mit der Planung der Berichtsgliederung...",
                completed_sections=[]
            )
            
            # Planungsstart protokollieren
            self.report_logger.log_planning_start()
            
            if progress_callback:
                progress_callback("planning", 0, "Beginne mit der Planung der Berichtsgliederung...")
            
            outline = self.plan_outline(
                progress_callback=lambda stage, prog, msg: 
                    progress_callback(stage, prog // 5, msg) if progress_callback else None
            )
            report.outline = outline
            
            # Planungsabschluss protokollieren
            self.report_logger.log_planning_complete(outline.to_dict())
            
            # Gliederung in Datei speichern
            ReportManager.save_outline(report_id, outline)
            ReportManager.update_progress(
                report_id, "planning", 15, f"Gliederungsplanung abgeschlossen, {len(outline.sections)} Kapitel",
                completed_sections=[]
            )
            ReportManager.save_report(report)
            
            logger.info(f"Gliederung gespeichert: {report_id}/outline.json")
            
            # Phase 2: Kapitelweise Generierung (abschnittsweise Speicherung)
            report.status = ReportStatus.GENERATING
            
            total_sections = len(outline.sections)
            generated_sections = []  # Gespeicherte Inhalte für Kontext
            
            for i, section in enumerate(outline.sections):
                section_num = i + 1
                base_progress = 20 + int((i / total_sections) * 70)
                
                # Fortschritt aktualisieren
                ReportManager.update_progress(
                    report_id, "generating", base_progress,
                    f"Kapitel wird generiert: {section.title} ({section_num}/{total_sections})",
                    current_section=section.title,
                    completed_sections=completed_section_titles
                )
                
                if progress_callback:
                    progress_callback(
                        "generating", 
                        base_progress, 
                        f"Kapitel wird generiert: {section.title} ({section_num}/{total_sections})"
                    )
                
                # Hauptkapitelinhalt generieren
                section_content = self._generate_section_react(
                    section=section,
                    outline=outline,
                    previous_sections=generated_sections,
                    progress_callback=lambda stage, prog, msg:
                        progress_callback(
                            stage, 
                            base_progress + int(prog * 0.7 / total_sections),
                            msg
                        ) if progress_callback else None,
                    section_index=section_num
                )
                
                section.content = section_content
                generated_sections.append(f"## {section.title}\n\n{section_content}")

                # Kapitel speichern
                ReportManager.save_section(report_id, section_num, section)
                completed_section_titles.append(section.title)

                # Kapitelabschluss protokollieren
                full_section_content = f"## {section.title}\n\n{section_content}"

                if self.report_logger:
                    self.report_logger.log_section_full_complete(
                        section_title=section.title,
                        section_index=section_num,
                        full_content=full_section_content.strip()
                    )

                logger.info(f"Kapitel gespeichert: {report_id}/section_{section_num:02d}.md")
                
                # Fortschritt aktualisieren
                ReportManager.update_progress(
                    report_id, "generating", 
                    base_progress + int(70 / total_sections),
                    f"Kapitel {section.title} abgeschlossen",
                    current_section=None,
                    completed_sections=completed_section_titles
                )
            
            # Phase 3: Vollständigen Bericht zusammenstellen
            if progress_callback:
                progress_callback("generating", 95, "Vollständigen Bericht zusammenstellen...")
            
            ReportManager.update_progress(
                report_id, "generating", 95, "Vollständigen Bericht zusammenstellen...",
                completed_sections=completed_section_titles
            )
            
            # ReportManager verwenden, um vollständigen Bericht zusammenzustellen
            report.markdown_content = ReportManager.assemble_full_report(report_id, outline)
            report.status = ReportStatus.COMPLETED
            report.completed_at = datetime.now().isoformat()
            
            # Gesamtzeit berechnen
            total_time_seconds = (datetime.now() - start_time).total_seconds()
            
            # Berichtsabschluss protokollieren
            if self.report_logger:
                self.report_logger.log_report_complete(
                    total_sections=total_sections,
                    total_time_seconds=total_time_seconds
                )
            
            # Endgültigen Bericht speichern
            ReportManager.save_report(report)
            ReportManager.update_progress(
                report_id, "completed", 100, "Berichtsgenerierung abgeschlossen",
                completed_sections=completed_section_titles
            )
            
            if progress_callback:
                progress_callback("completed", 100, "Berichtsgenerierung abgeschlossen")
            
            logger.info(f"Berichtsgenerierung abgeschlossen: {report_id}")
            
            # Konsolenprotokollierer schließen
            if self.console_logger:
                self.console_logger.close()
                self.console_logger = None
            
            return report
            
        except Exception as e:
            logger.error(f"Berichtsgenerierung fehlgeschlagen: {str(e)}")
            report.status = ReportStatus.FAILED
            report.error = str(e)
            
            # Fehler protokollieren
            if self.report_logger:
                self.report_logger.log_error(str(e), "failed")
            
            # Fehlerstatus speichern
            try:
                ReportManager.save_report(report)
                ReportManager.update_progress(
                    report_id, "failed", -1, f"Berichtsgenerierung fehlgeschlagen: {str(e)}",
                    completed_sections=completed_section_titles
                )
            except Exception:
                pass  # Speicherfehler ignorieren
            
            # Konsolenprotokollierer schließen
            if self.console_logger:
                self.console_logger.close()
                self.console_logger = None
            
            return report
    
    def chat(
        self, 
        message: str,
        chat_history: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Mit Report Agent conversieren
        
        Im Dialog kann der Agent autonom Werkzeuge aufrufen um Fragen zu beantworten
        
        Args:
            message: Benutzernachricht
            chat_history: Dialogverlauf
            
        Returns:
            {
                "response": "Agent-Antwort",
                "tool_calls": [Liste der aufgerufenen Werkzeuge],
                "sources": [Informationsquellen]
            }
        """
        logger.info(f"Report Agent Dialog: {message[:50]}...")
        
        chat_history = chat_history or []
        
        # Bereits generierten Berichtsinhalt abrufen
        report_content = ""
        try:
            report = ReportManager.get_report_by_simulation(self.simulation_id)
            if report and report.markdown_content:
                # Berichtslänge begrenzen um Kontext nicht zu lang werden zu lassen
                report_content = report.markdown_content[:15000]
                if len(report.markdown_content) > 15000:
                    report_content += "\n\n... [Berichtsinhalt gekürzt] ..."
        except Exception as e:
            logger.warning(f"Berichtsinhalt konnte nicht abgerufen werden: {e}")
        
        system_prompt = CHAT_SYSTEM_PROMPT_TEMPLATE.format(
            simulation_requirement=self.simulation_requirement,
            report_content=report_content if report_content else "(Noch kein Bericht vorhanden)",
            tools_description=self._get_tools_description(),
        )

        # Nachrichten konstruieren
        messages = [{"role": "system", "content": system_prompt}]
        
        # Verlauf hinzufügen
        for h in chat_history[-10:]:  # Verlaufslimit
            messages.append(h)
        
        # Benutzernachricht hinzufügen
        messages.append({
            "role": "user", 
            "content": message
        })
        
        # ReACT-Schleife (vereinfachte Version)
        tool_calls_made = []
        max_iterations = 2  # Reduzierte Iterationsrunden
        
        for iteration in range(max_iterations):
            response = self.llm.chat(
                messages=messages,
                temperature=0.5
            )
            
            # Werkzeugaufrufe parsen
            tool_calls = self._parse_tool_calls(response)
            
            if not tool_calls:
                # Keine Werkzeugaufrufe, direkt Antwort zurückgeben
                clean_response = re.sub(r'<tool_call>.*?</tool_call>', '', response, flags=re.DOTALL)
                clean_response = re.sub(r'\[TOOL_CALL\].*?\)', '', clean_response)
                
                return {
                    "response": clean_response.strip(),
                    "tool_calls": tool_calls_made,
                    "sources": [tc.get("parameters", {}).get("query", "") for tc in tool_calls_made]
                }
            
            # Werkzeugaufrufe ausführen (Anzahl begrenzen)
            tool_results = []
            for call in tool_calls[:1]:  # Maximal 1 Werkzeugaufruf pro Runde
                if len(tool_calls_made) >= self.MAX_TOOL_CALLS_PER_CHAT:
                    break
                result = self._execute_tool(call["name"], call.get("parameters", {}))
                tool_results.append({
                    "tool": call["name"],
                    "result": result[:1500]  # Ergebnisllänge begrenzen
                })
                tool_calls_made.append(call)
            
            # Ergebnis zu Nachrichten hinzufügen
            messages.append({"role": "assistant", "content": response})
            observation = "\n".join([f"[{r['tool']} Ergebnis]\n{r['result']}" for r in tool_results])
            messages.append({
                "role": "user",
                "content": observation + CHAT_OBSERVATION_SUFFIX
            })
        
        # Maximale Iteration erreicht, endgültige Antwort erhalten
        final_response = self.llm.chat(
            messages=messages,
            temperature=0.5
        )
        
        # Antwort bereinigen
        clean_response = re.sub(r'<tool_call>.*?</tool_call>', '', final_response, flags=re.DOTALL)
        clean_response = re.sub(r'\[TOOL_CALL\].*?\)', '', clean_response)
        
        return {
            "response": clean_response.strip(),
            "tool_calls": tool_calls_made,
            "sources": [tc.get("parameters", {}).get("query", "") for tc in tool_calls_made]
        }


class ReportManager:
    """
    Berichts-Manager
    
    Verantwortlich für permanente Speicherung und Abruf von Berichten
    
    Dateistruktur (abschnittsweise Ausgabe):
    reports/
      {report_id}/
        meta.json          - Berichtsmetainformationen und Status
        outline.json       - Berichtsgliederung
        progress.json      - Generierungsfortschritt
        section_01.md      - Kapitel 1
        section_02.md      - Kapitel 2
        ...
        full_report.md     - Vollständiger Bericht
    """
    
    # Berichtsspeicherverzeichnis
    @classmethod
    def get_reports_dir(cls) -> str:
        from app.tenant.settings_override import TenantConfig
        return os.path.join(TenantConfig().UPLOAD_FOLDER, 'reports')
    
    @classmethod
    def _ensure_reports_dir(cls):
        """Stellt sicher, dass das Stammverzeichnis für Berichte existiert"""
        os.makedirs(cls.get_reports_dir(), exist_ok=True)
    
    @classmethod
    def _get_report_folder(cls, report_id: str) -> str:
        """Pfad zum Berichtsordner abrufen"""
        return os.path.join(cls.get_reports_dir(), report_id)
    
    @classmethod
    def _ensure_report_folder(cls, report_id: str) -> str:
        """Stellt sicher, dass der Berichtsordner existiert und gibt den Pfad zurück"""
        folder = cls._get_report_folder(report_id)
        os.makedirs(folder, exist_ok=True)
        return folder
    
    @classmethod
    def _get_report_path(cls, report_id: str) -> str:
        """Pfad zur Berichtsmetainformationsdatei abrufen"""
        return os.path.join(cls._get_report_folder(report_id), "meta.json")
    
    @classmethod
    def _get_report_markdown_path(cls, report_id: str) -> str:
        """Pfad zur vollständigen Berichts-Markdown-Datei abrufen"""
        return os.path.join(cls._get_report_folder(report_id), "full_report.md")
    
    @classmethod
    def _get_outline_path(cls, report_id: str) -> str:
        """Pfad zur Gliederungsdatei abrufen"""
        return os.path.join(cls._get_report_folder(report_id), "outline.json")
    
    @classmethod
    def _get_progress_path(cls, report_id: str) -> str:
        """Pfad zur Fortschrittsdatei abrufen"""
        return os.path.join(cls._get_report_folder(report_id), "progress.json")
    
    @classmethod
    def _get_section_path(cls, report_id: str, section_index: int) -> str:
        """Pfad zur Abschnitts-Markdown-Datei abrufen"""
        return os.path.join(cls._get_report_folder(report_id), f"section_{section_index:02d}.md")
    
    @classmethod
    def _get_agent_log_path(cls, report_id: str) -> str:
        """Pfad zur Agent-Protokolldatei abrufen"""
        return os.path.join(cls._get_report_folder(report_id), "agent_log.jsonl")
    
    @classmethod
    def _get_console_log_path(cls, report_id: str) -> str:
        """Pfad zur Konsolenprotokolldatei abrufen"""
        return os.path.join(cls._get_report_folder(report_id), "console_log.txt")
    
    @classmethod
    def get_console_log(cls, report_id: str, from_line: int = 0) -> Dict[str, Any]:
        """
        Konsolenprotokollinhalt abrufen
        
        Dies sind die Konsolenausgabeprotokolle während der Berichtsgenerierung (INFO, WARNING usw.),
        unterschiedlich von den strukturierten Protokollen in agent_log.jsonl.
        
        Args:
            report_id: Berichts-ID
            from_line: Ab welcher Zeile lesen (für inkrementellen Abruf, 0 = von Anfang an)
            
        Returns:
            {
                "logs": [Protokollzeilenliste],
                "total_lines": Gesamtzeilen,
                "from_line": Startzeile,
                "has_more": Ob noch mehr Protokolle vorhanden
            }
        """
        log_path = cls._get_console_log_path(report_id)
        
        if not os.path.exists(log_path):
            return {
                "logs": [],
                "total_lines": 0,
                "from_line": 0,
                "has_more": False
            }
        
        logs = []
        total_lines = 0
        
        with open(log_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                total_lines = i + 1
                if i >= from_line:
                    # Ursprüngliche Protokollzeilen beibehalten, Zeilenumbruch am Ende entfernen
                    logs.append(line.rstrip('\n\r'))
        
        return {
            "logs": logs,
            "total_lines": total_lines,
            "from_line": from_line,
            "has_more": False  # Bis zum Ende gelesen
        }
    
    @classmethod
    def get_console_log_stream(cls, report_id: str) -> List[str]:
        """
        Vollständiges Konsolenprotokoll abrufen (alles auf einmal)
        
        Args:
            report_id: Berichts-ID
            
        Returns:
            Protokollzeilenliste
        """
        result = cls.get_console_log(report_id, from_line=0)
        return result["logs"]
    
    @classmethod
    def get_agent_log(cls, report_id: str, from_line: int = 0) -> Dict[str, Any]:
        """
        Agent-Protokollinhalt abrufen
        
        Args:
            report_id: Berichts-ID
            from_line: Ab welcher Zeile lesen (für inkrementellen Abruf, 0 = von Anfang an)
            
        Returns:
            {
                "logs": [Protokolleintragsliste],
                "total_lines": Gesamtzeilen,
                "from_line": Startzeile,
                "has_more": Ob noch mehr Protokolle vorhanden
            }
        """
        log_path = cls._get_agent_log_path(report_id)
        
        if not os.path.exists(log_path):
            return {
                "logs": [],
                "total_lines": 0,
                "from_line": 0,
                "has_more": False
            }
        
        logs = []
        total_lines = 0
        
        with open(log_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                total_lines = i + 1
                if i >= from_line:
                    try:
                        log_entry = json.loads(line.strip())
                        logs.append(log_entry)
                    except json.JSONDecodeError:
                    # Zeilen mit Parsingfehlern überspringen
                        continue
        
        return {
            "logs": logs,
            "total_lines": total_lines,
            "from_line": from_line,
            "has_more": False  # Bis zum Ende gelesen
        }
    
    @classmethod
    def get_agent_log_stream(cls, report_id: str) -> List[Dict[str, Any]]:
        """
        Vollständiges Agent-Protokoll abrufen (für einmaligen Gesamtabruf)
        
        Args:
            report_id: Berichts-ID
            
        Returns:
            Protokolleintragsliste
        """
        result = cls.get_agent_log(report_id, from_line=0)
        return result["logs"]
    
    @classmethod
    def save_outline(cls, report_id: str, outline: ReportOutline) -> None:
        """
        Berichtsgliederung speichern
        
        Wird sofort nach Abschluss der Planungsphase aufgerufen
        """
        cls._ensure_report_folder(report_id)
        
        with open(cls._get_outline_path(report_id), 'w', encoding='utf-8') as f:
            json.dump(outline.to_dict(), f, ensure_ascii=False, indent=2)
        
        logger.info(f"Gliederung gespeichert: {report_id}")
    
    @classmethod
    def save_section(
        cls,
        report_id: str,
        section_index: int,
        section: ReportSection
    ) -> str:
        """
        Einzelnes Kapitel speichern

        Wird sofort nach Abschluss jedes Kapitels aufgerufen, um abschnittsweise Ausgabe zu ermöglichen

        Args:
            report_id: Berichts-ID
            section_index: Kapitelindex (ab 1)
            section: Kapitelobjekt

        Returns:
            Pfad der gespeicherten Datei
        """
        cls._ensure_report_folder(report_id)

        # Kapitel-Markdown-Inhalt erstellen - mögliche doppelte Titel bereinigen
        cleaned_content = cls._clean_section_content(section.content, section.title)
        md_content = f"## {section.title}\n\n"
        if cleaned_content:
            md_content += f"{cleaned_content}\n\n"

        # Datei speichern
        file_suffix = f"section_{section_index:02d}.md"
        file_path = os.path.join(cls._get_report_folder(report_id), file_suffix)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(md_content)

        logger.info(f"Kapitel gespeichert: {report_id}/{file_suffix}")
        return file_path
    
    @classmethod
    def _clean_section_content(cls, content: str, section_title: str) -> str:
        """
        Kapitelinhalt bereinigen
        
        1. Markdown-Titelzeilen am Anfang des Inhalts entfernen, die mit Kapiteltitel duplizieren
        2. Alle ### und niedrigere Titelebenen in Bold-Text konvertieren
        
        Args:
            content: Originalinhalt
            section_title: Kapitelitel
            
        Returns:
            Bereinigter Inhalt
        """
        import re
        
        if not content:
            return content
        
        content = content.strip()
        lines = content.split('\n')
        cleaned_lines = []
        skip_next_empty = False
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Prüfen ob es eine Markdown-Titelzeile ist
            heading_match = re.match(r'^(#{1,6})\s+(.+)$', stripped)
            
            if heading_match:
                level = len(heading_match.group(1))
                title_text = heading_match.group(2).strip()
                
                # Prüfen ob es ein mit Kapiteltitel duplizierter Titel ist (Überspringen von Wiederholungen innerhalb der ersten 5 Zeilen)
                if i < 5:
                    if title_text == section_title or title_text.replace(' ', '') == section_title.replace(' ', ''):
                        skip_next_empty = True
                        continue
                
                # Alle Titelebenen (#, ##, ###, #### usw.) in Bold konvertieren
                # Da Kapiteltitel vom System hinzugefügt werden, sollte im Inhalt kein Titel vorhanden sein
                cleaned_lines.append(f"**{title_text}**")
                cleaned_lines.append("")  # Leerzeile hinzufügen
                continue
            
            # Wenn die vorherige Zeile ein übersprungener Titel war und aktuelle Zeile leer ist, auch überspringen
            if skip_next_empty and stripped == '':
                skip_next_empty = False
                continue
            
            skip_next_empty = False
            cleaned_lines.append(line)
        
        # Leerzeilen am Anfang entfernen
        while cleaned_lines and cleaned_lines[0].strip() == '':
            cleaned_lines.pop(0)
        
        # Trennlinien am Anfang entfernen
        while cleaned_lines and cleaned_lines[0].strip() in ['---', '***', '___']:
            cleaned_lines.pop(0)
            # Auch Leerzeilen nach Trennlinien entfernen
            while cleaned_lines and cleaned_lines[0].strip() == '':
                cleaned_lines.pop(0)
        
        return '\n'.join(cleaned_lines)
    
    @classmethod
    def update_progress(
        cls, 
        report_id: str, 
        status: str, 
        progress: int, 
        message: str,
        current_section: str = None,
        completed_sections: List[str] = None
    ) -> None:
        """
        Berichtsgenerierungsfortschritt aktualisieren
        
        Frontend kann Echtzeitfortschritt durch Lesen von progress.json erhalten
        """
        cls._ensure_report_folder(report_id)
        
        progress_data = {
            "status": status,
            "progress": progress,
            "message": message,
            "current_section": current_section,
            "completed_sections": completed_sections or [],
            "updated_at": datetime.now().isoformat()
        }
        
        with open(cls._get_progress_path(report_id), 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, ensure_ascii=False, indent=2)
    
    @classmethod
    def get_progress(cls, report_id: str) -> Optional[Dict[str, Any]]:
        """Fortschritt der Berichtsgenerierung abrufen"""
        path = cls._get_progress_path(report_id)
        
        if not os.path.exists(path):
            return None
        
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    @classmethod
    def get_generated_sections(cls, report_id: str) -> List[Dict[str, Any]]:
        """
        Liste der generierten Kapitel abrufen
        
        Gibt alle gespeicherten Kapiteldateiinformationen zurück
        """
        folder = cls._get_report_folder(report_id)
        
        if not os.path.exists(folder):
            return []
        
        sections = []
        for filename in sorted(os.listdir(folder)):
            if filename.startswith('section_') and filename.endswith('.md'):
                file_path = os.path.join(folder, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Kapitelindex aus Dateinamen parsen
                parts = filename.replace('.md', '').split('_')
                section_index = int(parts[1])

                sections.append({
                    "filename": filename,
                    "section_index": section_index,
                    "content": content
                })

        return sections
    
    @classmethod
    def assemble_full_report(cls, report_id: str, outline: ReportOutline) -> str:
        """
        Vollständigen Bericht zusammenstellen
        
        Vollständigen Bericht aus gespeicherten Kapiteldateien zusammenstellen und Titel bereinigen
        """
        folder = cls._get_report_folder(report_id)
        
        # Berichtskopf erstellen
        md_content = f"# {outline.title}\n\n"
        md_content += f"> {outline.summary}\n\n"
        md_content += f"---\n\n"
        
        # Alle Kapiteldateien der Reihe nach lesen
        sections = cls.get_generated_sections(report_id)
        for section_info in sections:
            md_content += section_info["content"]
        
        # Nachbearbeitung: Titelprobleme im gesamten Bericht bereinigen
        md_content = cls._post_process_report(md_content, outline)
        
        # Vollständigen Bericht speichern
        full_path = cls._get_report_markdown_path(report_id)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        logger.info(f"Vollständiger Bericht zusammengestellt: {report_id}")
        return md_content
    
    @classmethod
    def _post_process_report(cls, content: str, outline: ReportOutline) -> str:
        """
        Berichtinhalt nachbearbeiten
        
        1. Doppelte Titel entfernen
        2. Berichtshaustitel (#) und Kapiteltitel (##) behalten, andere Titele
ebenen (###, #### usw.) entfernen
        3. Überflüssige Leerzeilen und Trennlinien bereinigen
        
        Args:
            content: Originaler Berichtinhalt
            outline: Berichtsgliederung
            
        Returns:
            Verarbeiteter Inhalt
        """
        import re
        
        lines = content.split('\n')
        processed_lines = []
        prev_was_heading = False
        
        # Alle Kapiteltitel aus Gliederung sammeln
        section_titles = set()
        for section in outline.sections:
            section_titles.add(section.title)
        
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            
            # Prüfen ob es eine Titelzeile ist
            heading_match = re.match(r'^(#{1,6})\s+(.+)$', stripped)
            
            if heading_match:
                level = len(heading_match.group(1))
                title = heading_match.group(2).strip()
                
                # Prüfen ob es ein doppelter Titel ist (in aufeinanderfolgenden 5 Zeilen gleicher Inhalt)
                is_duplicate = False
                for j in range(max(0, len(processed_lines) - 5), len(processed_lines)):
                    prev_line = processed_lines[j].strip()
                    prev_match = re.match(r'^(#{1,6})\s+(.+)$', prev_line)
                    if prev_match:
                        prev_title = prev_match.group(2).strip()
                        if prev_title == title:
                            is_duplicate = True
                            break
                
                if is_duplicate:
                    # Doppelten Titel und folgende Leerzeilen überspringen
                    i += 1
                    while i < len(lines) and lines[i].strip() == '':
                        i += 1
                    continue
                
                # Titelebenenverarbeitung:
                # - # (level=1) Nur Berichtshaustitel behalten
                # - ## (level=2) Kapiteltitel behalten
                # - ### und niedriger (level>=3) in Bold-Text konvertieren
                
                if level == 1:
                    if title == outline.title:
                        # Berichtshaustitel behalten
                        processed_lines.append(line)
                        prev_was_heading = True
                    elif title in section_titles:
                        # Kapiteltitel hat fälschlicherweise # verwendet, korrigieren zu ##
                        processed_lines.append(f"## {title}")
                        prev_was_heading = True
                    else:
                        # Andere Titel erster Ebene in Bold konvertieren
                        processed_lines.append(f"**{title}**")
                        processed_lines.append("")
                        prev_was_heading = False
                elif level == 2:
                    if title in section_titles or title == outline.title:
                        # Kapiteltitel behalten
                        processed_lines.append(line)
                        prev_was_heading = True
                    else:
                        # Nicht-Kapitel-Zweittitel in Bold konvertieren
                        processed_lines.append(f"**{title}**")
                        processed_lines.append("")
                        prev_was_heading = False
                else:
                    # ### und niedrigere Titelebenen in Bold-Text konvertieren
                    processed_lines.append(f"**{title}**")
                    processed_lines.append("")
                    prev_was_heading = False
                
                i += 1
                continue
            
            elif stripped == '---' and prev_was_heading:
                # Trennlinien direkt nach Titeln überspringen
                i += 1
                continue
            
            elif stripped == '' and prev_was_heading:
                # Nur eine Leerzeile nach Titel behalten
                if processed_lines and processed_lines[-1].strip() != '':
                    processed_lines.append(line)
                prev_was_heading = False
            
            else:
                processed_lines.append(line)
                prev_was_heading = False
            
            i += 1
        
        # Aufeinanderfolgende mehrere Leerzeilen bereinigen (maximal 2 behalten)
        result_lines = []
        empty_count = 0
        for line in processed_lines:
            if line.strip() == '':
                empty_count += 1
                if empty_count <= 2:
                    result_lines.append(line)
            else:
                empty_count = 0
                result_lines.append(line)
        
        return '\n'.join(result_lines)
    
    @classmethod
    def save_report(cls, report: Report) -> None:
        """Berichtsmetainformationen und vollständigen Bericht speichern"""
        cls._ensure_report_folder(report.report_id)
        
        # Metainformations-JSON speichern
        with open(cls._get_report_path(report.report_id), 'w', encoding='utf-8') as f:
            json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)
        
        # Gliederung speichern
        if report.outline:
            cls.save_outline(report.report_id, report.outline)
        
        # Vollständigen Markdown-Bericht speichern
        if report.markdown_content:
            with open(cls._get_report_markdown_path(report.report_id), 'w', encoding='utf-8') as f:
                f.write(report.markdown_content)
        
        logger.info(f"Bericht gespeichert: {report.report_id}")
    
    @classmethod
    def get_report(cls, report_id: str) -> Optional[Report]:
        """Bericht abrufen"""
        path = cls._get_report_path(report_id)
        
        if not os.path.exists(path):
            # Legacy-Format-Kompatibilität: Dateien prüfen die direkt im reports-Verzeichnis gespeichert sind
            old_path = os.path.join(cls.get_reports_dir(), f"{report_id}.json")
            if os.path.exists(old_path):
                path = old_path
            else:
                return None
        
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Report-Objekt neu erstellen
        outline = None
        if data.get('outline'):
            outline_data = data['outline']
            sections = []
            for s in outline_data.get('sections', []):
                sections.append(ReportSection(
                    title=s['title'],
                    content=s.get('content', '')
                ))
            outline = ReportOutline(
                title=outline_data['title'],
                summary=outline_data['summary'],
                sections=sections
            )
        
        # Wenn markdown_content leer ist, versuchen von full_report.md zu lesen
        markdown_content = data.get('markdown_content', '')
        if not markdown_content:
            full_report_path = cls._get_report_markdown_path(report_id)
            if os.path.exists(full_report_path):
                with open(full_report_path, 'r', encoding='utf-8') as f:
                    markdown_content = f.read()
        
        return Report(
            report_id=data['report_id'],
            simulation_id=data['simulation_id'],
            graph_id=data['graph_id'],
            simulation_requirement=data['simulation_requirement'],
            status=ReportStatus(data['status']),
            outline=outline,
            markdown_content=markdown_content,
            created_at=data.get('created_at', ''),
            completed_at=data.get('completed_at', ''),
            error=data.get('error')
        )
    
    @classmethod
    def get_report_by_simulation(cls, simulation_id: str) -> Optional[Report]:
        """Bericht anhand der Simulations-ID abrufen"""
        cls._ensure_reports_dir()
        
        for item in os.listdir(cls.get_reports_dir()):
            item_path = os.path.join(cls.get_reports_dir(), item)
            # Neues Format: Ordner
            if os.path.isdir(item_path):
                report = cls.get_report(item)
                if report and report.simulation_id == simulation_id:
                    return report
            # Kompatibel mit altem Format: JSON-Datei
            elif item.endswith('.json'):
                report_id = item[:-5]
                report = cls.get_report(report_id)
                if report and report.simulation_id == simulation_id:
                    return report
        
        return None
    
    @classmethod
    def list_reports(cls, simulation_id: Optional[str] = None, limit: int = 50) -> List[Report]:
        """Berichte auflisten"""
        cls._ensure_reports_dir()
        
        reports = []
        for item in os.listdir(cls.get_reports_dir()):
            item_path = os.path.join(cls.get_reports_dir(), item)
            # Neues Format: Ordner
            if os.path.isdir(item_path):
                report = cls.get_report(item)
                if report:
                    if simulation_id is None or report.simulation_id == simulation_id:
                        reports.append(report)
            # Kompatibel mit altem Format: JSON-Datei
            elif item.endswith('.json'):
                report_id = item[:-5]
                report = cls.get_report(report_id)
                if report:
                    if simulation_id is None or report.simulation_id == simulation_id:
                        reports.append(report)
        
        # Nach Erstellungszeit absteigend sortieren
        reports.sort(key=lambda r: r.created_at, reverse=True)
        
        return reports[:limit]
    
    @classmethod
    def delete_report(cls, report_id: str) -> bool:
        """Bericht löschen (gesamten Ordner)"""
        import shutil
        
        folder_path = cls._get_report_folder(report_id)
        
        # Neues Format: Gesamten Ordner löschen
        if os.path.exists(folder_path) and os.path.isdir(folder_path):
            shutil.rmtree(folder_path)
            logger.info(f"Berichtsordner gelöscht: {report_id}")
            return True
        
        # Legacy-Format-Kompatibilität: Einzelne Dateien löschen
        deleted = False
        old_json_path = os.path.join(cls.get_reports_dir(), f"{report_id}.json")
        old_md_path = os.path.join(cls.get_reports_dir(), f"{report_id}.md")
        
        if os.path.exists(old_json_path):
            os.remove(old_json_path)
            deleted = True
        if os.path.exists(old_md_path):
            os.remove(old_md_path)
            deleted = True
        
        return deleted
