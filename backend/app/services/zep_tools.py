"""
Zep-Abfrage-Tool-Service
Kapselt Graph-Suche, Knotenlesen, Kantelabfrage und andere Tools zur Verwendung durch den Report Agent

Kernabfrage-Tools (optimierte Version):
1. InsightForge (Tiefenblick-Suche) - Leistungsstärkste Hybridsuche, generiert automatisch Unterfragen und multidimensionale Suche
2. PanoramaSearch (Breitensuche) - Vollständige Übersicht, einschließlich abgelaufener Inhalte
3. QuickSearch (Einfache Suche) - Schnelle Suche
"""

import time
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from zep_cloud.client import Zep


from ..utils.logger import get_logger
from ..utils.llm_client import LLMClient
from ..utils.zep_paging import fetch_all_nodes, fetch_all_edges

logger = get_logger('mirofish.zep_tools')


@dataclass
class SearchResult:
    """Suchergebnis"""
    facts: List[str]
    edges: List[Dict[str, Any]]
    nodes: List[Dict[str, Any]]
    query: str
    total_count: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "facts": self.facts,
            "edges": self.edges,
            "nodes": self.nodes,
            "query": self.query,
            "total_count": self.total_count
        }
    
    def to_text(self) -> str:
        """Konvertiert zu Textformat für LLM-Verständnis"""
        text_parts = [f"Suchanfrage: {self.query}", f"Gefunden {self.total_count} relevante Informationen"]
        
        if self.facts:
            text_parts.append("\n### Verwandte Fakten:")
            for i, fact in enumerate(self.facts, 1):
                text_parts.append(f"{i}. {fact}")
        
        return "\n".join(text_parts)


@dataclass
class NodeInfo:
    """Knoteninformation"""
    uuid: str
    name: str
    labels: List[str]
    summary: str
    attributes: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "uuid": self.uuid,
            "name": self.name,
            "labels": self.labels,
            "summary": self.summary,
            "attributes": self.attributes
        }
    
    def to_text(self) -> str:
        """Konvertiert zu Textformat"""
        entity_type = next((l for l in self.labels if l not in ["Entity", "Node"]), "Unbekannter Typ")
        return f"Entität: {self.name} (Typ: {entity_type})\nZusammenfassung: {self.summary}"


@dataclass
class EdgeInfo:
    """Kanteninformation"""
    uuid: str
    name: str
    fact: str
    source_node_uuid: str
    target_node_uuid: str
    source_node_name: Optional[str] = None
    target_node_name: Optional[str] = None
    # Zeitinformationen
    created_at: Optional[str] = None
    valid_at: Optional[str] = None
    invalid_at: Optional[str] = None
    expired_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "uuid": self.uuid,
            "name": self.name,
            "fact": self.fact,
            "source_node_uuid": self.source_node_uuid,
            "target_node_uuid": self.target_node_uuid,
            "source_node_name": self.source_node_name,
            "target_node_name": self.target_node_name,
            "created_at": self.created_at,
            "valid_at": self.valid_at,
            "invalid_at": self.invalid_at,
            "expired_at": self.expired_at
        }
    
    def to_text(self, include_temporal: bool = False) -> str:
        """Konvertiert zu Textformat"""
        source = self.source_node_name or self.source_node_uuid[:8]
        target = self.target_node_name or self.target_node_uuid[:8]
        base_text = f"Beziehung: {source} --[{self.name}]--> {target}\nTatsache: {self.fact}"
        
        if include_temporal:
            valid_at = self.valid_at or "Unbekannt"
            invalid_at = self.invalid_at or "Bis jetzt"
            base_text += f"\nZeitlich gültig: {valid_at} - {invalid_at}"
            if self.expired_at:
                base_text += f" (Abgelaufen: {self.expired_at})"
        
        return base_text
    
    @property
    def is_expired(self) -> bool:
        """Ob bereits abgelaufen"""
        return self.expired_at is not None
    
    @property
    def is_invalid(self) -> bool:
        """Ob bereits ungültig"""
        return self.invalid_at is not None


@dataclass
class InsightForgeResult:
    """
    Tiefenblick-Suchergebnis (InsightForge)
    Enthält Suchergebnisse mehrerer Unterfragen sowie eine umfassende Analyse
    """
    query: str
    simulation_requirement: str
    sub_queries: List[str]
    
    # Suchergebnisse nach Dimension
    semantic_facts: List[str] = field(default_factory=list)  # Semantische Suchergebnisse
    entity_insights: List[Dict[str, Any]] = field(default_factory=list)  # Entitäts-Einblicke
    relationship_chains: List[str] = field(default_factory=list)  # Beziehungsketten
    
    # Statistikinformationen
    total_facts: int = 0
    total_entities: int = 0
    total_relationships: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "simulation_requirement": self.simulation_requirement,
            "sub_queries": self.sub_queries,
            "semantic_facts": self.semantic_facts,
            "entity_insights": self.entity_insights,
            "relationship_chains": self.relationship_chains,
            "total_facts": self.total_facts,
            "total_entities": self.total_entities,
            "total_relationships": self.total_relationships
        }
    
    def to_text(self) -> str:
        """Konvertiert zu detailliertem Textformat für LLM-Verständnis und Berichtszitate"""
        text_parts = [
            f"## Tiefgehende Prognoseanalyse",
            f"Analysiertes Problem: {self.query}",
            f"Prognoseszenario: {self.simulation_requirement}",
            f"\n### Prognosedaten-Statistik",
            f"- Relevante Prognosefakten: {self.total_facts}",
            f"- Beteiligte Entitäten: {self.total_entities}",
            f"- Beziehungsketten: {self.total_relationships}"
        ]
        
        # Unterfragen
        if self.sub_queries:
            text_parts.append(f"\n### Analysierte Unterfragen")
            for i, sq in enumerate(self.sub_queries, 1):
                text_parts.append(f"{i}. {sq}")
        
        # Semantische Suchergebnisse
        if self.semantic_facts:
            text_parts.append(f"\n### 【Schlüsselfakten】（Bitte im Bericht diese Originalzitate verwenden）")
            for i, fact in enumerate(self.semantic_facts, 1):
                text_parts.append(f"{i}. \"{fact}\"")
        
        # Entitäts-Insights
        if self.entity_insights:
            text_parts.append(f"\n### 【Kernentitäten】")
            for entity in self.entity_insights:
                text_parts.append(f"- **{entity.get('name', 'Unbekannt')}** ({entity.get('type', 'Entität')})")
                if entity.get('summary'):
                    text_parts.append(f"  Zusammenfassung: \"{entity.get('summary')}\"")
                if entity.get('related_facts'):
                    text_parts.append(f"  Zugehörige Fakten: {len(entity.get('related_facts', []))}")
        
        # Beziehungsketten
        if self.relationship_chains:
            text_parts.append(f"\n### 【Beziehungsketten】")
            for chain in self.relationship_chains:
                text_parts.append(f"- {chain}")
        
        return "\n".join(text_parts)


@dataclass
class PanoramaResult:
    """
    Breitensuchergebnis (Panorama)
    Enthält alle verwandten Informationen, einschließlich abgelaufener Inhalte
    """
    query: str
    
    # Alle Knoten
    all_nodes: List[NodeInfo] = field(default_factory=list)
    # Alle Kanten (einschließlich abgelaufener)
    all_edges: List[EdgeInfo] = field(default_factory=list)
    # Aktuell gültige Fakten
    active_facts: List[str] = field(default_factory=list)
    # Abgelaufene/ungültige Fakten (Historienaufzeichnungen)
    historical_facts: List[str] = field(default_factory=list)
    
    # Statistik
    total_nodes: int = 0
    total_edges: int = 0
    active_count: int = 0
    historical_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "all_nodes": [n.to_dict() for n in self.all_nodes],
            "all_edges": [e.to_dict() for e in self.all_edges],
            "active_facts": self.active_facts,
            "historical_facts": self.historical_facts,
            "total_nodes": self.total_nodes,
            "total_edges": self.total_edges,
            "active_count": self.active_count,
            "historical_count": self.historical_count
        }
    
    def to_text(self) -> str:
        """Konvertiert zu Textformat（Vollständige Version, nicht gekürzt）"""
        text_parts = [
            f"## Breitensuchergebnisse (Panorama-Ansicht der Zukunft)",
            f"Suchanfrage: {self.query}",
            f"\n### Statistik",
            f"- Gesamtknoten: {self.total_nodes}",
            f"- Gesamtkanten: {self.total_edges}",
            f"- Aktuell gültige Fakten: {self.active_count}",
            f"- Historische/abgelaufene Fakten: {self.historical_count}"
        ]
        
        # Aktuell gültige Fakten (Vollständige Ausgabe, nicht gekürzt)
        if self.active_facts:
            text_parts.append(f"\n### 【Aktuell gültige Fakten】(Original-Simulationsergebnisse)")
            for i, fact in enumerate(self.active_facts, 1):
                text_parts.append(f"{i}. \"{fact}\"")
        
        # Historische/abgelaufene Fakten (Vollständige Ausgabe, nicht gekürzt)
        if self.historical_facts:
            text_parts.append(f"\n### 【Historische/abgelaufene Fakten】(Evolutionsprozessaufzeichnungen)")
            for i, fact in enumerate(self.historical_facts, 1):
                text_parts.append(f"{i}. \"{fact}\"")
        
        # Schlüsselentitäten (Vollständige Ausgabe, nicht gekürzt)
        if self.all_nodes:
            text_parts.append(f"\n### 【Beteiligte Entitäten】")
            for node in self.all_nodes:
                entity_type = next((l for l in node.labels if l not in ["Entity", "Node"]), "Entität")
                text_parts.append(f"- **{node.name}** ({entity_type})")
        
        return "\n".join(text_parts)


@dataclass
class AgentInterview:
    """Interviewergebnis eines einzelnen Agents"""
    agent_name: str
    agent_role: str  # Rollentyp (z.B.: Student, Lehrer, Medien usw.)
    agent_bio: str  # Kurzbiographie
    question: str  # Interviewfrage
    response: str  # Interviewantwort
    key_quotes: List[str] = field(default_factory=list)  # Schlüsselzitate
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "agent_role": self.agent_role,
            "agent_bio": self.agent_bio,
            "question": self.question,
            "response": self.response,
            "key_quotes": self.key_quotes
        }
    
    def to_text(self) -> str:
        text = f"**{self.agent_name}** ({self.agent_role})\n"
        # Agent-Bio vollständig anzeigen, nicht kürzen
        text += f"_Biografie: {self.agent_bio}_\n\n"
        text += f"**Q:** {self.question}\n\n"
        text += f"**A:** {self.response}\n"
        if self.key_quotes:
            text += "\n**Schlüsselzitate:**\n"
            for quote in self.key_quotes:
                # Verschiedene Anführungszeichen bereinigen
                clean_quote = quote.replace('\u201c', '').replace('\u201d', '').replace('"', '')
                clean_quote = clean_quote.replace('\u300c', '').replace('\u300d', '')
                clean_quote = clean_quote.strip()
                # Führende Satzzeichen entfernen
                while clean_quote and clean_quote[0] in '，,；;：:、。！？\n\r\t ':
                    clean_quote = clean_quote[1:]
                # Inhalt mit Nummern herausfiltern (Frage1-9)
                skip = False
                for d in '123456789':
                    if f'frage{d}' in clean_quote.lower():
                        skip = True
                        break
                if skip:
                    continue
                # Zu langen Inhalt kürzen (nach Satzzeichen, nicht hart kürzen)
                if len(clean_quote) > 150:
                    dot_pos = clean_quote.find('\u3002', 80)
                    if dot_pos > 0:
                        clean_quote = clean_quote[:dot_pos + 1]
                    else:
                        clean_quote = clean_quote[:147] + "..."
                if clean_quote and len(clean_quote) >= 10:
                    text += f'> "{clean_quote}"\n'
        return text


@dataclass
class InterviewResult:
    """
    Interviewergebnis (Interview)
    Enthält Interviewantworten mehrerer Simulations-Agents
    """
    interview_topic: str  # Interviewthema
    interview_questions: List[str]  # Interviewfrageliste
    
    # Für Interview ausgewählte Agents
    selected_agents: List[Dict[str, Any]] = field(default_factory=list)
    # Interviewantworten der jeweiligen Agents
    interviews: List[AgentInterview] = field(default_factory=list)
    
    # Begründung für Agent-Auswahl
    selection_reasoning: str = ""
    # Integrierte Interview-Zusammenfassung
    summary: str = ""
    
    # Statistiken
    total_agents: int = 0
    interviewed_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "interview_topic": self.interview_topic,
            "interview_questions": self.interview_questions,
            "selected_agents": self.selected_agents,
            "interviews": [i.to_dict() for i in self.interviews],
            "selection_reasoning": self.selection_reasoning,
            "summary": self.summary,
            "total_agents": self.total_agents,
            "interviewed_count": self.interviewed_count
        }
    
    def to_text(self) -> str:
        """Konvertiert zu detailliertem Textformat für LLM-Verständnis und Berichtszitate"""
        text_parts = [
            "## Tiefeninterview-Bericht",
            f"**Interviewthema:** {self.interview_topic}",
            f"**Interviewanzahl:** {self.interviewed_count} / {self.total_agents} simulierte Agents",
            "\n### Begründung für Interviewauswahl",
            self.selection_reasoning or "（Automatische Auswahl）",
            "\n---",
            "\n### Interviewaufzeichnungen",
        ]

        if self.interviews:
            for i, interview in enumerate(self.interviews, 1):
                text_parts.append(f"\n#### Interview #{i}: {interview.agent_name}")
                text_parts.append(interview.to_text())
                text_parts.append("\n---")
        else:
            text_parts.append("（Keine Interviewaufzeichnungen）\n\n---")

        text_parts.append("\n### Interview-Zusammenfassung und Kernpunkte")
        text_parts.append(self.summary or "（Keine Zusammenfassung）")

        return "\n".join(text_parts)


class ZepToolsService:
    """
    Zep-Abfrage-Tool-Service
    
    【Kernabfrage-Tools - optimierte Version】
    1. insight_forge - Tiefenblick-Suche (am leistungsstärksten, generiert automatisch Unterfragen, multidimensionale Suche)
    2. panorama_search - Breitensuche (vollständige Übersicht, einschließlich abgelaufener Inhalte)
    3. quick_search - Einfache Suche (schnelle Suche)
    4. interview_agents - Tiefeninterview (interviewt simulierte Agents, erhält mehrperspektivische Ansichten)
    
    【Basis-Tools】
    - search_graph - Graph-semantische Suche
    - get_all_nodes - Alle Knoten des Graphen abrufen
    - get_all_edges - Alle Kanten des Graphen abrufen (mit Zeitinformationen)
    - get_node_detail - Knotendetails abrufen
    - get_node_edges - Kanten des Knotens abrufen
    - get_entities_by_type - Entitäten nach Typ abrufen
    - get_entity_summary - Beziehungszusammenfassung der Entität abrufen
    """
    
    # Retry-Konfiguration
    MAX_RETRIES = 3
    RETRY_DELAY = 2.0
    
    def __init__(self, api_key: Optional[str] = None, llm_client: Optional[LLMClient] = None):
        from app.tenant.settings_override import TenantConfig
        cfg = TenantConfig()
        self.api_key = api_key or cfg.ZEP_API_KEY
        if not self.api_key:
            raise ValueError("ZEP_API_KEY nicht konfiguriert")
        
        self.client = Zep(api_key=self.api_key)
        # LLM-Client für InsightForge-Unterfragegenerierung
        self._llm_client = llm_client
        logger.info("ZepToolsService-Initialisierung abgeschlossen")
    
    @property
    def llm(self) -> LLMClient:
        """Verzögerte Initialisierung des LLM-Clients"""
        if self._llm_client is None:
            self._llm_client = LLMClient()
        return self._llm_client
    
    def _call_with_retry(self, func, operation_name: str, max_retries: int = None):
        """API-Aufruf mit Retry-Mechanismus"""
        max_retries = max_retries or self.MAX_RETRIES
        last_exception = None
        delay = self.RETRY_DELAY
        
        for attempt in range(max_retries):
            try:
                return func()
            except Exception as e:
                last_exception = e
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Zep {operation_name} Versuch {attempt + 1} fehlgeschlagen: {str(e)[:100]}, "
                        f"Retry in {delay:.1f}s..."
                    )
                    time.sleep(delay)
                    delay *= 2
                else:
                    logger.error(f"Zep {operation_name} nach {max_retries} Versuchen weiterhin fehlgeschlagen: {str(e)}")
        
        raise last_exception
    
    def search_graph(
        self, 
        graph_id: str, 
        query: str, 
        limit: int = 10,
        scope: str = "edges"
    ) -> SearchResult:
        """
        Graph-semantische Suche
        
        Verwendet Hybridsuche (semantisch + BM25) um relevante Informationen im Graphen zu suchen.
        Wenn die Zep Cloud Search API nicht verfügbar ist, wird ein Fallback auf lokale Stichwortsuche verwendet.
        
        Args:
            graph_id: Graph-ID (Standalone Graph)
            query: Suchanfrage
            limit: Anzahl der zurückgegebenen Ergebnisse
            scope: Suchbereich, "edges" oder "nodes"
            
        Returns:
            SearchResult: Suchergebnis
        """
        logger.info(f"Graph-Suche: graph_id={graph_id}, query={query[:50]}...")
        
        try:
            search_results = self._call_with_retry(
                func=lambda: self.client.graph.search(
                    graph_id=graph_id,
                    query=query,
                    limit=limit,
                    scope=scope,
                    reranker="cross_encoder"
                ),
                operation_name=f"Graph-Suche(graph={graph_id})"
            )
            
            facts = []
            edges = []
            nodes = []
            
            if hasattr(search_results, 'edges') and search_results.edges:
                for edge in search_results.edges:
                    if hasattr(edge, 'fact') and edge.fact:
                        facts.append(edge.fact)
                    edges.append({
                        "uuid": getattr(edge, 'uuid_', None) or getattr(edge, 'uuid', ''),
                        "name": getattr(edge, 'name', ''),
                        "fact": getattr(edge, 'fact', ''),
                        "source_node_uuid": getattr(edge, 'source_node_uuid', ''),
                        "target_node_uuid": getattr(edge, 'target_node_uuid', ''),
                    })
            
            if hasattr(search_results, 'nodes') and search_results.nodes:
                for node in search_results.nodes:
                    nodes.append({
                        "uuid": getattr(node, 'uuid_', None) or getattr(node, 'uuid', ''),
                        "name": getattr(node, 'name', ''),
                        "labels": getattr(node, 'labels', []),
                        "summary": getattr(node, 'summary', ''),
                    })
                    if hasattr(node, 'summary') and node.summary:
                        facts.append(f"[{node.name}]: {node.summary}")
            
            logger.info(f"Suche abgeschlossen: {len(facts)} relevante Fakten gefunden")
            
            return SearchResult(
                facts=facts,
                edges=edges,
                nodes=nodes,
                query=query,
                total_count=len(facts)
            )
            
        except Exception as e:
            logger.warning(f"Zep Search API fehlgeschlagen, Fallback auf lokale Suche: {str(e)}")
            return self._local_search(graph_id, query, limit, scope)
    
    def _local_search(
        self, 
        graph_id: str, 
        query: str, 
        limit: int = 10,
        scope: str = "edges"
    ) -> SearchResult:
        """
        Lokale Stichwort-Matching-Suche (als Fallback für Zep Search API)

        Ruft alle Kanten/Knoten ab und führt dann lokales Stichwort-Matching durch
        
        Args:
            graph_id: Graph-ID
            query: Suchanfrage
            limit: Anzahl der Ergebnisse
            scope: Suchbereich
            
        Returns:
            SearchResult: Suchergebnisse
        """
        logger.info(f"Verwende lokale Suche: query={query[:30]}...")
        
        facts = []
        edges_result = []
        nodes_result = []
        
        # Abfrage-Stichwörter extrahieren (einfache Segmentierung)
        query_lower = query.lower()
        keywords = [w.strip() for w in query_lower.replace(',', ' ').replace('，', ' ').split() if len(w.strip()) > 1]
        
        def match_score(text: str) -> int:
            """Text-zu-Abfrage-Übereinstimmungspunktzahl berechnen"""
            if not text:
                return 0
            text_lower = text.lower()
            if query_lower in text_lower:
                return 100
            score = 0
            for keyword in keywords:
                if keyword in text_lower:
                    score += 10
            return score
        
        try:
            if scope in ["edges", "both"]:
                all_edges = self.get_all_edges(graph_id)
                scored_edges = []
                for edge in all_edges:
                    score = match_score(edge.fact) + match_score(edge.name)
                    if score > 0:
                        scored_edges.append((score, edge))
                
                scored_edges.sort(key=lambda x: x[0], reverse=True)
                
                for score, edge in scored_edges[:limit]:
                    if edge.fact:
                        facts.append(edge.fact)
                    edges_result.append({
                        "uuid": edge.uuid,
                        "name": edge.name,
                        "fact": edge.fact,
                        "source_node_uuid": edge.source_node_uuid,
                        "target_node_uuid": edge.target_node_uuid,
                    })
            
            if scope in ["nodes", "both"]:
                all_nodes = self.get_all_nodes(graph_id)
                scored_nodes = []
                for node in all_nodes:
                    score = match_score(node.name) + match_score(node.summary)
                    if score > 0:
                        scored_nodes.append((score, node))
                
                scored_nodes.sort(key=lambda x: x[0], reverse=True)
                
                for score, node in scored_nodes[:limit]:
                    nodes_result.append({
                        "uuid": node.uuid,
                        "name": node.name,
                        "labels": node.labels,
                        "summary": node.summary,
                    })
                    if node.summary:
                        facts.append(f"[{node.name}]: {node.summary}")
            
            logger.info(f"Lokale Suche abgeschlossen: {len(facts)} relevante Fakten gefunden")
            
        except Exception as e:
            logger.error(f"Lokale Suche fehlgeschlagen: {str(e)}")
        
        return SearchResult(
            facts=facts,
            edges=edges_result,
            nodes=nodes_result,
            query=query,
            total_count=len(facts)
        )
    
    def get_all_nodes(self, graph_id: str) -> List[NodeInfo]:
        """
        Alle Knoten des Graphen abrufen (mit Seitenumeration)

        Args:
            graph_id: Graph-ID

        Returns:
            Knotenliste
        """
        logger.info(f"Alle Knoten des Graphen {graph_id} abrufen...")

        nodes = fetch_all_nodes(self.client, graph_id)

        result = []
        for node in nodes:
            node_uuid = getattr(node, 'uuid_', None) or getattr(node, 'uuid', None) or ""
            result.append(NodeInfo(
                uuid=str(node_uuid) if node_uuid else "",
                name=node.name or "",
                labels=node.labels or [],
                summary=node.summary or "",
                attributes=node.attributes or {}
            ))

        logger.info(f"{len(result)} Knoten abgerufen")
        return result

    def get_all_edges(self, graph_id: str, include_temporal: bool = True) -> List[EdgeInfo]:
        """
        Alle Kanten des Graphen abrufen (mit Seitenumeration, einschließlich Zeitinformationen)

        Args:
            graph_id: Graph-ID
            include_temporal: Ob Zeitinformationen eingeschlossen werden (Standard True)

        Returns:
            Kantenliste (enthält created_at, valid_at, invalid_at, expired_at)
        """
        logger.info(f"Alle Kanten des Graphen {graph_id} abrufen...")

        edges = fetch_all_edges(self.client, graph_id)

        result = []
        for edge in edges:
            edge_uuid = getattr(edge, 'uuid_', None) or getattr(edge, 'uuid', None) or ""
            edge_info = EdgeInfo(
                uuid=str(edge_uuid) if edge_uuid else "",
                name=edge.name or "",
                fact=edge.fact or "",
                source_node_uuid=edge.source_node_uuid or "",
                target_node_uuid=edge.target_node_uuid or ""
            )
            
            if include_temporal:
                edge_info.created_at = getattr(edge, 'created_at', None)
                edge_info.valid_at = getattr(edge, 'valid_at', None)
                edge_info.invalid_at = getattr(edge, 'invalid_at', None)
                edge_info.expired_at = getattr(edge, 'expired_at', None)

            result.append(edge_info)

        logger.info(f"{len(result)} Kanten abgerufen")
        return result
    
    def get_node_detail(self, node_uuid: str) -> Optional[NodeInfo]:
        """
        Detaillierte Informationen eines einzelnen Knotens abrufen
        
        Args:
            node_uuid: Knoten-UUID
            
        Returns:
            Knoteninformation oder None
        """
        logger.info(f"Knotendetails abrufen: {node_uuid[:8]}...")
        
        try:
            node = self._call_with_retry(
                func=lambda: self.client.graph.node.get(uuid_=node_uuid),
                operation_name=f"Knotendetails abrufen(uuid={node_uuid[:8]}...)"
            )
            
            if not node:
                return None
            
            return NodeInfo(
                uuid=getattr(node, 'uuid_', None) or getattr(node, 'uuid', ''),
                name=node.name or "",
                labels=node.labels or [],
                summary=node.summary or "",
                attributes=node.attributes or {}
            )
        except Exception as e:
            logger.error(f"Knotendetails-Abruf fehlgeschlagen: {str(e)}")
            return None
    
    def get_node_edges(self, graph_id: str, node_uuid: str) -> List[EdgeInfo]:
        """
        Alle Kanten eines Knotens abrufen
        
        Ruft alle Kanten des Graphen ab und filtert dann die mit dem angegebenen Knoten verbundenen Kanten heraus
        
        Args:
            graph_id: Graph-ID
            node_uuid: Knoten-UUID
            
        Returns:
            Kantenliste
        """
        logger.info(f"Knotenbezogene Kanten abrufen für Knoten {node_uuid[:8]}...")
        
        try:
            all_edges = self.get_all_edges(graph_id)
            
            result = []
            for edge in all_edges:
                if edge.source_node_uuid == node_uuid or edge.target_node_uuid == node_uuid:
                    result.append(edge)
            
            logger.info(f"{len(result)} knotenbezogene Kanten gefunden")
            return result
            
        except Exception as e:
            logger.warning(f"Knotenkanten-Abruf fehlgeschlagen: {str(e)}")
            return []
    
    def get_entities_by_type(
        self, 
        graph_id: str, 
        entity_type: str
    ) -> List[NodeInfo]:
        """
        Entitäten nach Typ abrufen
        
        Args:
            graph_id: Graph-ID
            entity_type: Entitätstyp (z.B. Student, PublicFigure etc.)
            
        Returns:
            Liste der Entitäten des entsprechenden Typs
        """
        logger.info(f"Entitäten vom Typ {entity_type} abrufen...")
        
        all_nodes = self.get_all_nodes(graph_id)
        
        filtered = []
        for node in all_nodes:
            if entity_type in node.labels:
                filtered.append(node)
        
        logger.info(f"{len(filtered)} Entitäten vom Typ {entity_type} gefunden")
        return filtered
    
    def get_entity_summary(
        self, 
        graph_id: str, 
        entity_name: str
    ) -> Dict[str, Any]:
        """
        Beziehungszusammenfassung der angegebenen Entität abrufen
        
        Sucht alle mit der Entität verbundenen Informationen und generiert eine Zusammenfassung
        
        Args:
            graph_id: Graph-ID
            entity_name: Entitätsname
            
        Returns:
            Entitätszusammenfassungsinformationen
        """
        logger.info(f"Beziehungszusammenfassung für Entität {entity_name} abrufen...")
        
        search_result = self.search_graph(
            graph_id=graph_id,
            query=entity_name,
            limit=20
        )
        
        all_nodes = self.get_all_nodes(graph_id)
        entity_node = None
        for node in all_nodes:
            if node.name.lower() == entity_name.lower():
                entity_node = node
                break
        
        related_edges = []
        if entity_node:
            related_edges = self.get_node_edges(graph_id, entity_node.uuid)
        
        return {
            "entity_name": entity_name,
            "entity_info": entity_node.to_dict() if entity_node else None,
            "related_facts": search_result.facts,
            "related_edges": [e.to_dict() for e in related_edges],
            "total_relations": len(related_edges)
        }
    
    def get_graph_statistics(self, graph_id: str) -> Dict[str, Any]:
        """
        Statistikinformationen des Graphen abrufen
        
        Args:
            graph_id: Graph-ID
            
        Returns:
            Statistikinformationen
        """
        logger.info(f"Statistiken für Graph {graph_id} abrufen...")
        
        nodes = self.get_all_nodes(graph_id)
        edges = self.get_all_edges(graph_id)
        
        entity_types = {}
        for node in nodes:
            for label in node.labels:
                if label not in ["Entity", "Node"]:
                    entity_types[label] = entity_types.get(label, 0) + 1
        
        relation_types = {}
        for edge in edges:
            relation_types[edge.name] = relation_types.get(edge.name, 0) + 1
        
        return {
            "graph_id": graph_id,
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "entity_types": entity_types,
            "relation_types": relation_types
        }
    
    def get_simulation_context(
        self, 
        graph_id: str,
        simulation_requirement: str,
        limit: int = 30
    ) -> Dict[str, Any]:
        """
        Simulationsbezogene Kontextinformationen abrufen
        
        Synthetische Suche aller mit den Simulationsanforderungen verbundenen Informationen
        
        Args:
            graph_id: Graph-ID
            simulation_requirement: Simulationsanforderungsbeschreibung
            limit: Mengenbeschränkung für jede Art von Information
            
        Returns:
            Simulationskontextinformationen
        """
        logger.info(f"Simulationskontext abrufen: {simulation_requirement[:50]}...")
        
        search_result = self.search_graph(
            graph_id=graph_id,
            query=simulation_requirement,
            limit=limit
        )
        
        stats = self.get_graph_statistics(graph_id)
        
        all_nodes = self.get_all_nodes(graph_id)
        
        entities = []
        for node in all_nodes:
            custom_labels = [l for l in node.labels if l not in ["Entity", "Node"]]
            if custom_labels:
                entities.append({
                    "name": node.name,
                    "type": custom_labels[0],
                    "summary": node.summary
                })
        
        return {
            "simulation_requirement": simulation_requirement,
            "related_facts": search_result.facts,
            "graph_statistics": stats,
            "entities": entities[:limit],  # Begrenzung der Anzahl
            "total_entities": len(entities)
        }
    
    # ========== Kernabfrage-Tools (optimierte Version) ==========
    
    def insight_forge(
        self,
        graph_id: str,
        query: str,
        simulation_requirement: str,
        report_context: str = "",
        max_sub_queries: int = 5
    ) -> InsightForgeResult:
        """
        【InsightForge - Tiefenblick-Suche】
        
        Leistungsstärkste Hybridsuchfunktion, zerlegt Probleme automatisch und sucht multidimensional:
        1. LLM verwendet um Problem in mehrere Unterfragen zu zerlegen
        2. Semantische Suche für jede Unterfrage
        3. Relevante Entitäten extrahieren und deren Details abrufen
        4. Beziehungsketten verfolgen
        5. Alle Ergebnisse integrieren und Tiefenblick generieren
        
        Args:
            graph_id: Graph-ID
            query: Benutzerfrage
            simulation_requirement: Simulationsanforderungsbeschreibung
            report_context: Berichtskontext (optional, für präzisere Unterfragen-Generierung)
            max_sub_queries: Maximale Anzahl der Unterfragen
            
        Returns:
            InsightForgeResult: Tiefenblick-Suchergebnis
        """
        logger.info(f"InsightForge Tiefenblick-Suche: {query[:50]}...")
        
        result = InsightForgeResult(
            query=query,
            simulation_requirement=simulation_requirement,
            sub_queries=[]
        )
        
        sub_queries = self._generate_sub_queries(
            query=query,
            simulation_requirement=simulation_requirement,
            report_context=report_context,
            max_queries=max_sub_queries
        )
        result.sub_queries = sub_queries
        logger.info(f"{len(sub_queries)} Unterfragen generiert")
        
        all_facts = []
        all_edges = []
        seen_facts = set()
        
        for sub_query in sub_queries:
            search_result = self.search_graph(
                graph_id=graph_id,
                query=sub_query,
                limit=15,
                scope="edges"
            )
            
            for fact in search_result.facts:
                if fact not in seen_facts:
                    all_facts.append(fact)
                    seen_facts.add(fact)
            
            all_edges.extend(search_result.edges)
        
        main_search = self.search_graph(
            graph_id=graph_id,
            query=query,
            limit=20,
            scope="edges"
        )
        for fact in main_search.facts:
            if fact not in seen_facts:
                all_facts.append(fact)
                seen_facts.add(fact)
        
        result.semantic_facts = all_facts
        result.total_facts = len(all_facts)
        
        entity_uuids = set()
        for edge_data in all_edges:
            if isinstance(edge_data, dict):
                source_uuid = edge_data.get('source_node_uuid', '')
                target_uuid = edge_data.get('target_node_uuid', '')
                if source_uuid:
                    entity_uuids.add(source_uuid)
                if target_uuid:
                    entity_uuids.add(target_uuid)
        
        entity_insights = []
        node_map = {}
        
        for uuid in list(entity_uuids):
            if not uuid:
                continue
            try:
                node = self.get_node_detail(uuid)
                if node:
                    node_map[uuid] = node
                    entity_type = next((l for l in node.labels if l not in ["Entity", "Node"]), "Entität")
                    
                    related_facts = [
                        f for f in all_facts 
                        if node.name.lower() in f.lower()
                    ]
                    
                    entity_insights.append({
                        "uuid": node.uuid,
                        "name": node.name,
                        "type": entity_type,
                        "summary": node.summary,
                        "related_facts": related_facts
                    })
            except Exception as e:
                logger.debug(f"Knoten {uuid} abrufen fehlgeschlagen: {e}")
                continue
        
        result.entity_insights = entity_insights
        result.total_entities = len(entity_insights)
        
        relationship_chains = []
        for edge_data in all_edges:
            if isinstance(edge_data, dict):
                source_uuid = edge_data.get('source_node_uuid', '')
                target_uuid = edge_data.get('target_node_uuid', '')
                relation_name = edge_data.get('name', '')
                
                source_name = node_map.get(source_uuid, NodeInfo('', '', [], '', {})).name or source_uuid[:8]
                target_name = node_map.get(target_uuid, NodeInfo('', '', [], '', {})).name or target_uuid[:8]
                
                chain = f"{source_name} --[{relation_name}]--> {target_name}"
                if chain not in relationship_chains:
                    relationship_chains.append(chain)
        
        result.relationship_chains = relationship_chains
        result.total_relationships = len(relationship_chains)
        
        logger.info(f"InsightForge完成: {result.total_facts} Fakten, {result.total_entities} Entitäten, {result.total_relationships} Beziehungen")
        return result
    
    def _generate_sub_queries(
        self,
        query: str,
        simulation_requirement: str,
        report_context: str = "",
        max_queries: int = 5
    ) -> List[str]:
        """
        Unterfragen mit LLM generieren
        
        Zerlegt komplexe Probleme in mehrere unabhängig abrufbare Unterfragen
        """
        system_prompt = """Sie sind ein professioneller Problemanalyse-Experte. Ihre Aufgabe ist es, ein komplexes Problem in mehrere Unterfragen zu zerlegen, die in der Simulationswelt unabhängig beobachtet werden können.

Anforderungen:
1. Jede Unterfrage sollte spezifisch genug sein, um relevante Agenten-Verhaltensweisen oder Ereignisse in der Simulationswelt zu finden
2. Unterfragen sollten verschiedene Dimensionen des Originalproblems abdecken (wie: Wer, Was, Warum, Wie, Wann, Wo)
3. Unterfragen sollten mit dem Simulationsszenario zusammenhängen
4. Geben Sie JSON-Format zurück: {"sub_queries": ["Unterfrage1", "Unterfrage2", ...]}"""

        user_prompt = f"""Simulationsanforderungs-Hintergrund:
{simulation_requirement}

{f"Berichtskontext: {report_context[:500]}" if report_context else ""}

Bitte zerlegen Sie das folgende Problem in {max_queries} Unterfragen:
{query}

Geben Sie die Unterfragenliste im JSON-Format zurück."""

        try:
            response = self.llm.chat_json(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3
            )
            
            sub_queries = response.get("sub_queries", [])
            # Sicherstellen, dass es eine Zeichenkettenliste ist
            return [str(sq) for sq in sub_queries[:max_queries]]
            
        except Exception as e:
            logger.warning(f"Unterfragen-Generierung fehlgeschlagen: {str(e)}, verwende Standard-Unterfragen")
            # Fallback: basierend auf der Originalfrage Varianten zurückgeben
            return [
                query,
                f"Hauptbeteiligte an {query}",
                f"Ursachen und Auswirkungen von {query}",
                f"Entwicklungsprozess von {query}"
            ][:max_queries]
    
    def panorama_search(
        self,
        graph_id: str,
        query: str,
        include_expired: bool = True,
        limit: int = 50
    ) -> PanoramaResult:
        """
        【PanoramaSearch - Breitensuche】
        
        Erhalt einer vollständigen Übersicht, einschließlich aller verwandten Inhalte und historischer/abgelaufener Informationen:
        1. Alle verwandten Knoten abrufen
        2. Alle Kanten abrufen (einschließlich abgelaufener/ungültiger)
        3. Aktuell gültige und historische Informationen klassifizieren und organisieren
        
        Dieses Tool eignet sich für Szenarien, die ein vollständiges Bild des Ereignisses benötigen und denEvolutionsprozess verfolgen.
        
        Args:
            graph_id: Graph-ID
            query: Suchanfrage (zur Relevanzsortierung)
            include_expired: Ob abgelaufene Inhalte eingeschlossen werden (Standard True)
            limit: Beschränkung der zurückgegebenen Ergebnismenge
            
        Returns:
            PanoramaResult: Breitensuchergebnis
        """
        logger.info(f"PanoramaSearch Breitensuche: {query[:50]}...")
        
        result = PanoramaResult(query=query)
        
        all_nodes = self.get_all_nodes(graph_id)
        node_map = {n.uuid: n for n in all_nodes}
        result.all_nodes = all_nodes
        result.total_nodes = len(all_nodes)
        
        all_edges = self.get_all_edges(graph_id, include_temporal=True)
        result.all_edges = all_edges
        result.total_edges = len(all_edges)
        
        active_facts = []
        historical_facts = []
        
        for edge in all_edges:
            if not edge.fact:
                continue
            
            source_name = node_map.get(edge.source_node_uuid, NodeInfo('', '', [], '', {})).name or edge.source_node_uuid[:8]
            target_name = node_map.get(edge.target_node_uuid, NodeInfo('', '', [], '', {})).name or edge.target_node_uuid[:8]
            
            is_historical = edge.is_expired or edge.is_invalid
            
            if is_historical:
                valid_at = edge.valid_at or "Unbekannt"
                invalid_at = edge.invalid_at or edge.expired_at or "Unbekannt"
                fact_with_time = f"[{valid_at} - {invalid_at}] {edge.fact}"
                historical_facts.append(fact_with_time)
            else:
                active_facts.append(edge.fact)
        
        query_lower = query.lower()
        keywords = [w.strip() for w in query_lower.replace(',', ' ').replace('，', ' ').split() if len(w.strip()) > 1]
        
        def relevance_score(fact: str) -> int:
            fact_lower = fact.lower()
            score = 0
            if query_lower in fact_lower:
                score += 100
            for kw in keywords:
                if kw in fact_lower:
                    score += 10
            return score
        
        active_facts.sort(key=relevance_score, reverse=True)
        historical_facts.sort(key=relevance_score, reverse=True)
        
        result.active_facts = active_facts[:limit]
        result.historical_facts = historical_facts[:limit] if include_expired else []
        result.active_count = len(active_facts)
        result.historical_count = len(historical_facts)
        
        logger.info(f"PanoramaSearch abgeschlossen: {result.active_count} aktiv, {result.historical_count} historisch")
        return result
    
    def quick_search(
        self,
        graph_id: str,
        query: str,
        limit: int = 10
    ) -> SearchResult:
        """
        【QuickSearch - Einfache Suche】
        
        Schnelles, leichtgewichtiges Suchwerkzeug:
        1. Direkt Zep-semantische Suche aufrufen
        2. Die relevantesten Ergebnisse zurückgeben
        3. Geeignet für einfache, direkte Suchbedürfnisse
        
        Args:
            graph_id: Graph-ID
            query: Suchanfrage
            limit: Anzahl der zurückgegebenen Ergebnisse
            
        Returns:
            SearchResult: Suchergebnis
        """
        logger.info(f"QuickSearch einfache Suche: {query[:50]}...")
        
        result = self.search_graph(
            graph_id=graph_id,
            query=query,
            limit=limit,
            scope="edges"
        )
        
        logger.info(f"QuickSearch abgeschlossen: {result.total_count} Ergebnisse")
        return result
    
    def interview_agents(
        self,
        simulation_id: str,
        interview_requirement: str,
        simulation_requirement: str = "",
        max_agents: int = 5,
        custom_questions: List[str] = None
    ) -> InterviewResult:
        """
        【InterviewAgents - Tiefeninterview】
        
        Ruft die echte OASIS-Interview-API auf, interviewt die in der Simulation laufenden Agents:
        1. Liest automatisch die Persönlichkeitsdatei, um alle simulierten Agents zu verstehen
        2. Verwendet LLM um Interview-Anforderungen zu analysieren und die relevantesten Agents intelligent auszuwählen
        3. Verwendet LLM um Interview-Fragen zu generieren
        4. Ruft die /api/simulation/interview/batch Schnittstelle für echte Interviews auf (Dual-Plattform gleichzeitiges Interview)
        5. Integriert alle Interview-Ergebnisse und generiert Interviewberichte
        
        【Wichtig】Diese Funktion erfordert, dass die Simulationsumgebung in Betrieb ist (OASIS-Umgebung nicht geschlossen)
        
        【Verwendungsszenarien】
        - Erfordert Perspektiven verschiedener Rollen zum Ereignisverständnis
        - Erfordert das Sammeln von Meinungen und Standpunkten verschiedener Parteien
        - Erfordert echte Antworten von simulierten Agents (nicht LLM-simuliert)
        
        Args:
            simulation_id: Simulations-ID (zur Lokalisierung der Persönlichkeitsdatei und zum Aufruf der Interview-API)
            interview_requirement: Interview-Anforderungsbeschreibung (unstrukturiert, z.B. "Schüler-Meinungen zum Ereignis verstehen")
            simulation_requirement: Simulationsanforderungs-Hintergrund (optional)
            max_agents: Maximale Anzahl der zu interviewenden Agents
            custom_questions: Benutzerdefinierte Interview-Fragen (optional, falls nicht angegeben, automatisch generiert)
            
        Returns:
            InterviewResult: Interview-Ergebnis
        """
        from .simulation_runner import SimulationRunner
        
        logger.info(f"InterviewAgents Tiefeninterview (Echt-API): {interview_requirement[:50]}...")
        
        result = InterviewResult(
            interview_topic=interview_requirement,
            interview_questions=custom_questions or []
        )
        
        profiles = self._load_agent_profiles(simulation_id)
        
        if not profiles:
            logger.warning(f"Persönlichkeitsdatei für Simulation {simulation_id} nicht gefunden")
            result.summary = "Keine interviewbaren Agent-Persönlichkeitsdateien gefunden"
            return result
        
        result.total_agents = len(profiles)
        logger.info(f"{len(profiles)} Agent-Persönlichkeiten geladen")
        
        selected_agents, selected_indices, selection_reasoning = self._select_agents_for_interview(
            profiles=profiles,
            interview_requirement=interview_requirement,
            simulation_requirement=simulation_requirement,
            max_agents=max_agents
        )
        
        result.selected_agents = selected_agents
        result.selection_reasoning = selection_reasoning
        logger.info(f"{len(selected_agents)} Agents für Interview ausgewählt: {selected_indices}")
        
        if not result.interview_questions:
            result.interview_questions = self._generate_interview_questions(
                interview_requirement=interview_requirement,
                simulation_requirement=simulation_requirement,
                selected_agents=selected_agents
            )
            logger.info(f"{len(result.interview_questions)} Interview-Fragen generiert")
        
        combined_prompt = "\n".join([f"{i+1}. {q}" for i, q in enumerate(result.interview_questions)])
        
        INTERVIEW_PROMPT_PREFIX = (
            "Du nimmst gerade an einem Interview teil. Bitte beantworte die folgenden Fragen direkt in reinem Textformat, "
            "basierend auf deiner Persönlichkeit, all deinen vergangenen Erinnerungen und Handlungen.\n"
            "Antwortanforderungen:\n"
            "1. Antworte direkt in natürlicher Sprache, rufe keine Werkzeuge auf\n"
            "2. Kein JSON-Format oder Werkzeugaufruf-Format zurückgeben\n"
            "3. Keine Markdown-Überschriften verwenden (wie #, ##, ###)\n"
            "4. Beantworte die Fragen der Reihe nach, jede Antwort beginnt mit「Frage X:」(X ist die Fragennummer)\n"
            "5. Trenne verschiedene Antworten mit Leerzeilen\n"
            "6. Die Antworten sollten substanziell sein, jede Frage sollte mit mindestens 2-3 Sätzen beantwortet werden\n\n"
        )
        optimized_prompt = f"{INTERVIEW_PROMPT_PREFIX}{combined_prompt}"
        
        try:
            interviews_request = []
            for agent_idx in selected_indices:
                interviews_request.append({
                    "agent_id": agent_idx,
                    "prompt": optimized_prompt
                })
            
            logger.info(f"Batch-Interview-API aufrufen (Dual-Plattform): {len(interviews_request)} Agents")
            
            api_result = SimulationRunner.interview_agents_batch(
                simulation_id=simulation_id,
                interviews=interviews_request,
                platform=None,
                timeout=180.0
            )
            
            logger.info(f"Interview-API zurück: {api_result.get('interviews_count', 0)} Ergebnisse, success={api_result.get('success')}")
            
            if not api_result.get("success", False):
                error_msg = api_result.get("error", "Unbekannt")
                logger.warning(f"Interview-API-Rückgabe fehlgeschlagen: {error_msg}")
                result.summary = f"Interview-API-Aufruf fehlgeschlagen: {error_msg}. Bitte überprüfen Sie den Status der OASIS-Simulationsumgebung."
                return result
            
            api_data = api_result.get("result", {})
            results_dict = api_data.get("results", {}) if isinstance(api_data, dict) else {}
            
            for i, agent_idx in enumerate(selected_indices):
                agent = selected_agents[i]
                agent_name = agent.get("realname", agent.get("username", f"Agent_{agent_idx}"))
                agent_role = agent.get("profession", "Unbekannt")
                agent_bio = agent.get("bio", "")
                
                twitter_result = results_dict.get(f"twitter_{agent_idx}", {})
                reddit_result = results_dict.get(f"reddit_{agent_idx}", {})
                
                twitter_response = twitter_result.get("response", "")
                reddit_response = reddit_result.get("response", "")

                twitter_response = self._clean_tool_call_response(twitter_response)
                reddit_response = self._clean_tool_call_response(reddit_response)

                twitter_text = twitter_response if twitter_response else "（Keine Antwort von dieser Plattform erhalten）"
                reddit_text = reddit_response if reddit_response else "（Keine Antwort von dieser Plattform erhalten）"
                response_text = f"【Twitter-Plattform-Antwort】\n{twitter_text}\n\n【Reddit-Plattform-Antwort】\n{reddit_text}"

                import re
                combined_responses = f"{twitter_response} {reddit_response}"

                clean_text = re.sub(r'#{1,6}\s+', '', combined_responses)
                clean_text = re.sub(r'\{[^}]*tool_name[^}]*\}', '', clean_text)
                clean_text = re.sub(r'[*_`|>~\-]{2,}', '', clean_text)
                clean_text = re.sub(r'Frage\s*\d+[：:]\s*', '', clean_text)
                clean_text = re.sub(r'【[^】]+】', '', clean_text)

                sentences = re.split(r'[。！？]', clean_text)
                meaningful = [
                    s.strip() for s in sentences
                    if 20 <= len(s.strip()) <= 150
                    and not re.match(r'^[\s\W，,；;：:、]+', s.strip())
                    and not s.strip().startswith(('{', 'Frage'))
                ]
                meaningful.sort(key=len, reverse=True)
                key_quotes = [s + "。" for s in meaningful[:3]]

                if not key_quotes:
                    paired = re.findall(r'\u201c([^\u201c\u201d]{15,100})\u201d', clean_text)
                    paired += re.findall(r'\u300c([^\u300c\u300d]{15,100})\u300d', clean_text)
                    key_quotes = [q for q in paired if not re.match(r'^[，,；;：:、]', q)][:3]
                
                interview = AgentInterview(
                    agent_name=agent_name,
                    agent_role=agent_role,
                    agent_bio=agent_bio[:1000],
                    question=combined_prompt,
                    response=response_text,
                    key_quotes=key_quotes[:5]
                )
                result.interviews.append(interview)
            
            result.interviewed_count = len(result.interviews)
            
        except ValueError as e:
            logger.warning(f"Interview-API-Aufruf fehlgeschlagen (Umgebung nicht aktiv?): {e}")
            result.summary = f"Interview fehlgeschlagen: {str(e)}. Simulationsumgebung wurde möglicherweise geschlossen, bitte stellen Sie sicher, dass die OASIS-Umgebung läuft."
            return result
        except Exception as e:
            logger.error(f"Interview-API-Aufruf-Ausnahme: {e}")
            import traceback
            logger.error(traceback.format_exc())
            result.summary = f"Fehler im Interview-Prozess: {str(e)}"
            return result
        
        if result.interviews:
            result.summary = self._generate_interview_summary(
                interviews=result.interviews,
                interview_requirement=interview_requirement
            )
        
        logger.info(f"InterviewAgents abgeschlossen: {result.interviewed_count} Agents interviewt (Dual-Plattform)")
        return result
    
    @staticmethod
    def _clean_tool_call_response(response: str) -> str:
        """Agent-Antworten von JSON-Werkzeugaufruf-Umschlägen bereinigen, tatsächlichen Inhalt extrahieren"""
        if not response or not response.strip().startswith('{'):
            return response
        text = response.strip()
        if 'tool_name' not in text[:80]:
            return response
        import re as _re
        try:
            data = json.loads(text)
            if isinstance(data, dict) and 'arguments' in data:
                for key in ('content', 'text', 'body', 'message', 'reply'):
                    if key in data['arguments']:
                        return str(data['arguments'][key])
        except (json.JSONDecodeError, KeyError, TypeError):
            match = _re.search(r'"content"\s*:\s*"((?:[^"\\]|\\.)*)"', text)
            if match:
                return match.group(1).replace('\\n', '\n').replace('\\"', '"')
        return response

    def _load_agent_profiles(self, simulation_id: str) -> List[Dict[str, Any]]:
        """Simulations-Agent-Persönlichkeitsdateien laden"""
        import os
        import csv
        
        sim_dir = os.path.join(
            os.path.dirname(__file__), 
            f'../../uploads/simulations/{simulation_id}'
        )
        
        profiles = []
        
        reddit_profile_path = os.path.join(sim_dir, "reddit_profiles.json")
        if os.path.exists(reddit_profile_path):
            try:
                with open(reddit_profile_path, 'r', encoding='utf-8') as f:
                    profiles = json.load(f)
                logger.info(f"{len(profiles)} Persönlichkeiten aus reddit_profiles.json geladen")
                return profiles
            except Exception as e:
                logger.warning(f"reddit_profiles.json lesen fehlgeschlagen: {e}")
        
        twitter_profile_path = os.path.join(sim_dir, "twitter_profiles.csv")
        if os.path.exists(twitter_profile_path):
            try:
                with open(twitter_profile_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        profiles.append({
                            "realname": row.get("name", ""),
                            "username": row.get("username", ""),
                            "bio": row.get("description", ""),
                            "persona": row.get("user_char", ""),
                            "profession": "Unbekannt"
                        })
                logger.info(f"{len(profiles)} Persönlichkeiten aus twitter_profiles.csv geladen")
                return profiles
            except Exception as e:
                logger.warning(f"twitter_profiles.csv lesen fehlgeschlagen: {e}")
        
        return profiles
    
    def _select_agents_for_interview(
        self,
        profiles: List[Dict[str, Any]],
        interview_requirement: str,
        simulation_requirement: str,
        max_agents: int
    ) -> tuple:
        """
        LLM verwenden um Agents für Interview auszuwählen
        
        Returns:
            tuple: (selected_agents, selected_indices, reasoning)
                - selected_agents: Vollständige Informationsliste der ausgewählten Agents
                - selected_indices: Indexliste der ausgewählten Agents (für API-Aufruf)
                - reasoning: Auswahlgrund
        """
        
        agent_summaries = []
        for i, profile in enumerate(profiles):
            summary = {
                "index": i,
                "name": profile.get("realname", profile.get("username", f"Agent_{i}")),
                "profession": profile.get("profession", "Unbekannt"),
                "bio": profile.get("bio", "")[:200],
                "interested_topics": profile.get("interested_topics", [])
            }
            agent_summaries.append(summary)
        
        system_prompt = """你是一个专业的采访策划专家。你的任务是根据采访需求，从模拟Agent列表中选择最适合采访的对象。

选择标准：
1. Agent的身份/职业与采访主题相关
2. Agent可能持有独特或有价值的观点
3. 选择多样化的视角（如：支持方、反对方、中立方、专业人士等）
4. 优先选择与事件直接相关的角色

返回JSON格式：
{
    "selected_indices": [选中Agent的索引列表],
    "reasoning": "选择理由说明"
}"""

        user_prompt = f"""采访需求：
{interview_requirement}

模拟背景：
{simulation_requirement if simulation_requirement else "未提供"}

可选择的Agent列表（共{len(agent_summaries)}个）：
{json.dumps(agent_summaries, ensure_ascii=False, indent=2)}

请选择最多{max_agents}个最适合采访的Agent，并说明选择理由。"""

        try:
            response = self.llm.chat_json(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3
            )
            
            selected_indices = response.get("selected_indices", [])[:max_agents]
            reasoning = response.get("reasoning", "Automatische Auswahl basierend auf Relevanz")
            
            selected_agents = []
            valid_indices = []
            for idx in selected_indices:
                if 0 <= idx < len(profiles):
                    selected_agents.append(profiles[idx])
                    valid_indices.append(idx)
            
            return selected_agents, valid_indices, reasoning
            
        except Exception as e:
            logger.warning(f"LLM-Agent-Auswahl fehlgeschlagen, verwende Standardauswahl: {e}")
            selected = profiles[:max_agents]
            indices = list(range(min(max_agents, len(profiles))))
            return selected, indices, "Standardauswahlstrategie verwendet"
    
    def _generate_interview_questions(
        self,
        interview_requirement: str,
        simulation_requirement: str,
        selected_agents: List[Dict[str, Any]]
    ) -> List[str]:
        """LLM verwenden um Interview-Fragen zu generieren"""
        
        agent_roles = [a.get("profession", "Unbekannt") for a in selected_agents]
        
        system_prompt = """你是一个专业的记者/采访者。根据采访需求，生成3-5个深度采访问题。

问题要求：
1. 开放性问题，鼓励详细回答
2. 针对不同角色可能有不同答案
3. 涵盖事实、观点、感受等多个维度
4. 语言自然，像真实采访一样
5. 每个问题控制在50字以内，简洁明了
6. 直接提问，不要包含背景说明或前缀

返回JSON格式：{"questions": ["问题1", "问题2", ...]}"""

        user_prompt = f"""采访需求：{interview_requirement}

模拟背景：{simulation_requirement if simulation_requirement else "未提供"}

采访对象角色：{', '.join(agent_roles)}

请生成3-5个采访问题。"""

        try:
            response = self.llm.chat_json(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.5
            )
            
            return response.get("questions", [f"Was meinen Sie zu {interview_requirement}?"])
            
        except Exception as e:
            logger.warning(f"Interview-Fragen-Generierung fehlgeschlagen: {e}")
            return [
                f"Was ist Ihre Meinung zu {interview_requirement}?",
                "Welche Auswirkungen hat dies auf Sie oder Ihre vertretene Gruppe?",
                "Wie sollte dieses Problem Ihrer Meinung nach gelöst oder verbessert werden?"
            ]
    
    def _generate_interview_summary(
        self,
        interviews: List[AgentInterview],
        interview_requirement: str
    ) -> str:
        """Interview-Zusammenfassung generieren"""
        
        if not interviews:
            return "Keine Interviews durchgeführt"
        
        # 收集所有采访内容
        interview_texts = []
        for interview in interviews:
            interview_texts.append(f"【{interview.agent_name}（{interview.agent_role}）】\n{interview.response[:500]}")
        
        system_prompt = """你是一个专业的新闻编辑。请根据多位受访者的回答，生成一份采访摘要。

摘要要求：
1. 提炼各方主要观点
2. 指出观点的共识和分歧
3. 突出有价值的引言
4. 客观中立，不偏袒任何一方
5. 控制在1000字内

格式约束（必须遵守）：
- 使用纯文本段落，用空行分隔不同部分
- 不要使用Markdown标题（如#、##、###）
- 不要使用分割线（如---、***）
- 引用受访者原话时使用中文引号「」
- 可以使用**加粗**标记关键词，但不要使用其他Markdown语法"""

        user_prompt = f"""采访主题：{interview_requirement}

采访内容：
{"".join(interview_texts)}

请生成采访摘要。"""

        try:
            summary = self.llm.chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=800
            )
            return summary
            
        except Exception as e:
            logger.warning(f"Interview-Zusammenfassungs-Generierung fehlgeschlagen: {e}")
            return f"Es wurden {len(interviews)} Interviewte befragt, darunter: " + "、".join([i.agent_name for i in interviews])
