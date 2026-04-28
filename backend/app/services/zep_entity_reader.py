"""
Zep-Entität-Lese- und Filterdienst
Liest Knoten aus dem Zep-Graph und filtert Knoten heraus, die vordefinierten Entitätstypen entsprechen
"""

import time
from typing import Dict, Any, List, Optional, Set, Callable, TypeVar
from dataclasses import dataclass, field

from zep_cloud.client import Zep


from ..utils.logger import get_logger
from ..utils.zep_paging import fetch_all_nodes, fetch_all_edges

logger = get_logger('mirofish.zep_entity_reader')

# Für generische Rückgabetypen
T = TypeVar('T')


@dataclass
class EntityNode:
    """Entitätsknoten-Datenstruktur"""
    uuid: str
    name: str
    labels: List[str]
    summary: str
    attributes: Dict[str, Any]
    # Zugehörige Kanteninformationen
    related_edges: List[Dict[str, Any]] = field(default_factory=list)
    # Informationen zu anderen zugehörigen Knoten
    related_nodes: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "uuid": self.uuid,
            "name": self.name,
            "labels": self.labels,
            "summary": self.summary,
            "attributes": self.attributes,
            "related_edges": self.related_edges,
            "related_nodes": self.related_nodes,
        }
    
    def get_entity_type(self) -> Optional[str]:
        """Ruft den Entitätstyp ab (schließt das Standard-Entity-Label aus)"""
        for label in self.labels:
            if label not in ["Entity", "Node"]:
                return label
        return None


@dataclass
class FilteredEntities:
    """Sammlung gefilterter Entitäten"""
    entities: List[EntityNode]
    entity_types: Set[str]
    total_count: int
    filtered_count: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "entities": [e.to_dict() for e in self.entities],
            "entity_types": list(self.entity_types),
            "total_count": self.total_count,
            "filtered_count": self.filtered_count,
        }


class ZepEntityReader:
    """
    Zep-Entität-Lese- und Filterdienst
    
    Hauptfunktionen:
    1. Liest alle Knoten aus dem Zep-Graph
    2. Filtert Knoten heraus, die vordefinierten Entitätstypen entsprechen (Labels nicht nur Entity)
    3. Ruft zugehörige Kanten und verknüpfte Knoteninformationen für jede Entität ab
    """
    
    def __init__(self, api_key: Optional[str] = None):
        from app.tenant.settings_override import TenantConfig
        cfg = TenantConfig()
        self.api_key = api_key or cfg.ZEP_API_KEY
        if not self.api_key:
            raise ValueError("ZEP_API_KEY nicht konfiguriert")
        
        self.client = Zep(api_key=self.api_key)
    
    def _call_with_retry(
        self, 
        func: Callable[[], T], 
        operation_name: str,
        max_retries: int = 3,
        initial_delay: float = 2.0
    ) -> T:
        """
        Zep-API-Aufruf mit Wiederholungsmechanismus
        
        Args:
            func: Die auszuführende Funktion (parameterloses Lambda oder Callable)
            operation_name: Operationsname für Protokolle
            max_retries: Maximale Anzahl von Wiederholungen (Standard 3, d.h. max. 3 Versuche)
            initial_delay: Anfängliche Verzögerung in Sekunden
            
        Returns:
            API-Aufrufergebnis
        """
        last_exception = None
        delay = initial_delay
        
        for attempt in range(max_retries):
            try:
                return func()
            except Exception as e:
                last_exception = e
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Zep {operation_name} Versuch {attempt + 1} fehlgeschlagen: {str(e)[:100]}, "
                        f"Wiederholung in {delay:.1f} Sekunden..."
                    )
                    time.sleep(delay)
                    delay *= 2  # Exponential Backoff
                else:
                    logger.error(f"Zep {operation_name} nach {max_retries} Versuchen immer noch fehlgeschlagen: {str(e)}")
        
        raise last_exception
    
    def get_all_nodes(self, graph_id: str) -> List[Dict[str, Any]]:
        """
        Ruft alle Knoten des Graphen ab (paged abgerufen)

        Args:
            graph_id: Graph-ID

        Returns:
            Knotenliste
        """
        logger.info(f"Rufe alle Knoten des Graphen {graph_id} ab...")

        nodes = fetch_all_nodes(self.client, graph_id)

        nodes_data = []
        for node in nodes:
            nodes_data.append({
                "uuid": getattr(node, 'uuid_', None) or getattr(node, 'uuid', ''),
                "name": node.name or "",
                "labels": node.labels or [],
                "summary": node.summary or "",
                "attributes": node.attributes or {},
            })

        logger.info(f"{len(nodes_data)} Knoten abgerufen")
        return nodes_data

    def get_all_edges(self, graph_id: str) -> List[Dict[str, Any]]:
        """
        Ruft alle Kanten des Graphen ab (paged abgerufen)

        Args:
            graph_id: Graph-ID

        Returns:
            Kantenliste
        """
        logger.info(f"Rufe alle Kanten des Graphen {graph_id} ab...")

        edges = fetch_all_edges(self.client, graph_id)

        edges_data = []
        for edge in edges:
            edges_data.append({
                "uuid": getattr(edge, 'uuid_', None) or getattr(edge, 'uuid', ''),
                "name": edge.name or "",
                "fact": edge.fact or "",
                "source_node_uuid": edge.source_node_uuid,
                "target_node_uuid": edge.target_node_uuid,
                "attributes": edge.attributes or {},
            })

        logger.info(f"{len(edges_data)} Kanten abgerufen")
        return edges_data
    
    def get_node_edges(self, node_uuid: str) -> List[Dict[str, Any]]:
        """
        Ruft alle zugehörigen Kanten eines bestimmten Knotens ab (mit Wiederholungsmechanismus)
        
        Args:
            node_uuid: Knoten-UUID
            
        Returns:
            Kantenliste
        """
        try:
            # Zep-API mit Wiederholungsmechanismus aufrufen
            edges = self._call_with_retry(
                func=lambda: self.client.graph.node.get_entity_edges(node_uuid=node_uuid),
                operation_name=f"Knotenkanten abrufen(node={node_uuid[:8]}...)"
            )
            
            edges_data = []
            for edge in edges:
                edges_data.append({
                    "uuid": getattr(edge, 'uuid_', None) or getattr(edge, 'uuid', ''),
                    "name": edge.name or "",
                    "fact": edge.fact or "",
                    "source_node_uuid": edge.source_node_uuid,
                    "target_node_uuid": edge.target_node_uuid,
                    "attributes": edge.attributes or {},
                })
            
            return edges_data
        except Exception as e:
            logger.warning(f"Fehler beim Abrufen der Kanten für Knoten {node_uuid}: {str(e)}")
            return []
    
    def filter_defined_entities(
        self, 
        graph_id: str,
        defined_entity_types: Optional[List[str]] = None,
        enrich_with_edges: bool = True
    ) -> FilteredEntities:
        """
        Filtert Knoten heraus, die vordefinierten Entitätstypen entsprechen
        
        Filterlogik:
        - Wenn die Labels eines Knotens nur "Entity" enthalten, entspricht diese Entität nicht unseren vordefinierten Typen, überspringen
        - Wenn die Labels eines Knotens andere Labels außer "Entity" und "Node" enthalten, entspricht es den vordefinierten Typen, behalten
        
        Args:
            graph_id: Graph-ID
            defined_entity_types: Liste vordefinierter Entitätstypen (optional, wenn angegeben, werden nur diese Typen behalten)
            enrich_with_edges: Ob zugehörige Kanteninformationen für jede Entität abgerufen werden sollen
            
        Returns:
            FilteredEntities: Sammlung gefilterter Entitäten
        """
        logger.info(f"Beginne mit dem Filtern der Entitäten im Graphen {graph_id}...")
        
        # Alle Knoten abrufen
        all_nodes = self.get_all_nodes(graph_id)
        total_count = len(all_nodes)
        
        # Alle Kanten abrufen (für nachfolgende Zuordnungssuche)
        all_edges = self.get_all_edges(graph_id) if enrich_with_edges else []
        
        # Mapping von Knoten-UUID zu Knotendaten erstellen
        node_map = {n["uuid"]: n for n in all_nodes}
        
        # Entitäten filtern, die den Bedingungen entsprechen
        filtered_entities = []
        entity_types_found = set()
        
        for node in all_nodes:
            labels = node.get("labels", [])
            
            # Filterlogik: Labels müssen andere Labels außer "Entity" und "Node" enthalten
            custom_labels = [l for l in labels if l not in ["Entity", "Node"]]
            
            if not custom_labels:
                # Nur Standard-Labels, überspringen
                continue
            
            # Wenn vordefinierte Typen angegeben wurden, prüfen ob sie übereinstimmen
            if defined_entity_types:
                matching_labels = [l for l in custom_labels if l in defined_entity_types]
                if not matching_labels:
                    continue
                entity_type = matching_labels[0]
            else:
                entity_type = custom_labels[0]
            
            entity_types_found.add(entity_type)
            
            # Entitätsknotenobjekt erstellen
            entity = EntityNode(
                uuid=node["uuid"],
                name=node["name"],
                labels=labels,
                summary=node["summary"],
                attributes=node["attributes"],
            )
            
            # Zugehörige Kanten und Knoten abrufen
            if enrich_with_edges:
                related_edges = []
                related_node_uuids = set()
                
                for edge in all_edges:
                    if edge["source_node_uuid"] == node["uuid"]:
                        related_edges.append({
                            "direction": "outgoing",
                            "edge_name": edge["name"],
                            "fact": edge["fact"],
                            "target_node_uuid": edge["target_node_uuid"],
                        })
                        related_node_uuids.add(edge["target_node_uuid"])
                    elif edge["target_node_uuid"] == node["uuid"]:
                        related_edges.append({
                            "direction": "incoming",
                            "edge_name": edge["name"],
                            "fact": edge["fact"],
                            "source_node_uuid": edge["source_node_uuid"],
                        })
                        related_node_uuids.add(edge["source_node_uuid"])
                
                entity.related_edges = related_edges
                
                # Basisinformationen der zugehörigen Knoten abrufen
                related_nodes = []
                for related_uuid in related_node_uuids:
                    if related_uuid in node_map:
                        related_node = node_map[related_uuid]
                        related_nodes.append({
                            "uuid": related_node["uuid"],
                            "name": related_node["name"],
                            "labels": related_node["labels"],
                            "summary": related_node.get("summary", ""),
                        })
                
                entity.related_nodes = related_nodes
            
            filtered_entities.append(entity)
        
        logger.info(f"Filterung abgeschlossen: Gesamtknoten {total_count}, entspricht {len(filtered_entities)}, "
                   f"Entitätstypen: {entity_types_found}")
        
        return FilteredEntities(
            entities=filtered_entities,
            entity_types=entity_types_found,
            total_count=total_count,
            filtered_count=len(filtered_entities),
        )
    
    def get_entity_with_context(
        self, 
        graph_id: str, 
        entity_uuid: str
    ) -> Optional[EntityNode]:
        """
        Ruft eine einzelne Entität mit vollständigem Kontext ab (Kanten und verknüpfte Knoten, mit Wiederholungsmechanismus)
        
        Args:
            graph_id: Graph-ID
            entity_uuid: Entität-UUID
            
        Returns:
            EntityNode oder None
        """
        try:
            # Knoten mit Wiederholungsmechanismus abrufen
            node = self._call_with_retry(
                func=lambda: self.client.graph.node.get(uuid_=entity_uuid),
                operation_name=f"Knotendetails abrufen(uuid={entity_uuid[:8]}...)"
            )
            
            if not node:
                return None
            
            # Die Kanten des Knotens abrufen
            edges = self.get_node_edges(entity_uuid)
            
            # Alle Knoten für Zuordnungsfindung abrufen
            all_nodes = self.get_all_nodes(graph_id)
            node_map = {n["uuid"]: n for n in all_nodes}
            
            # Zugehörige Kanten und Knoten verarbeiten
            related_edges = []
            related_node_uuids = set()
            
            for edge in edges:
                if edge["source_node_uuid"] == entity_uuid:
                    related_edges.append({
                        "direction": "outgoing",
                        "edge_name": edge["name"],
                        "fact": edge["fact"],
                        "target_node_uuid": edge["target_node_uuid"],
                    })
                    related_node_uuids.add(edge["target_node_uuid"])
                else:
                    related_edges.append({
                        "direction": "incoming",
                        "edge_name": edge["name"],
                        "fact": edge["fact"],
                        "source_node_uuid": edge["source_node_uuid"],
                    })
                    related_node_uuids.add(edge["source_node_uuid"])
            
            # Zugehörige Knoteninformationen abrufen
            related_nodes = []
            for related_uuid in related_node_uuids:
                if related_uuid in node_map:
                    related_node = node_map[related_uuid]
                    related_nodes.append({
                        "uuid": related_node["uuid"],
                        "name": related_node["name"],
                        "labels": related_node["labels"],
                        "summary": related_node.get("summary", ""),
                    })
            
            return EntityNode(
                uuid=getattr(node, 'uuid_', None) or getattr(node, 'uuid', ''),
                name=node.name or "",
                labels=node.labels or [],
                summary=node.summary or "",
                attributes=node.attributes or {},
                related_edges=related_edges,
                related_nodes=related_nodes,
            )
            
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Entität {entity_uuid}: {str(e)}")
            return None
    
    def get_entities_by_type(
        self, 
        graph_id: str, 
        entity_type: str,
        enrich_with_edges: bool = True
    ) -> List[EntityNode]:
        """
        Ruft alle Entitäten eines bestimmten Typs ab
        
        Args:
            graph_id: Graph-ID
            entity_type: Entitätstyp (z.B. "Student", "PublicFigure" usw.)
            enrich_with_edges: Ob zugehörige Kanteninformationen abgerufen werden sollen
            
        Returns:
            Entitätenliste
        """
        result = self.filter_defined_entities(
            graph_id=graph_id,
            defined_entity_types=[entity_type],
            enrich_with_edges=enrich_with_edges
        )
        return result.entities


