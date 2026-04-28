"""
OASIS Agent Profile-Generator
Wandelt Entitäten aus dem Zep-Graph in das von der OASIS-Simulationsplattform benötigte Agent Profile-Format um

Optimierungsverbesserungen:
1. Zep-Abruffunktion aufrufen, um Knoteninformationen ein zweites Mal anzureichern
2. Prompt-Generierung optimieren, um sehr detaillierte Persönlichkeiten zu erstellen
3. Unterscheidung zwischen individuellen Entitäten und abstrakten Gruppenentitäten
"""

import json
import random
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

from openai import OpenAI
from zep_cloud.client import Zep


from ..utils.logger import get_logger
from .zep_entity_reader import EntityNode, ZepEntityReader

logger = get_logger('mirofish.oasis_profile')


@dataclass
class OasisAgentProfile:
    """OASIS Agent Profile-Datenstruktur"""
    # Allgemeine Felder
    user_id: int
    user_name: str
    name: str
    bio: str
    persona: str
    
    # Optionale Felder - Reddit-Stil
    karma: int = 1000
    
    # Optionale Felder - Twitter-Stil
    friend_count: int = 100
    follower_count: int = 150
    statuses_count: int = 500
    
    # Zusätzliche Persönlichkeitsinformationen
    age: Optional[int] = None
    gender: Optional[str] = None
    mbti: Optional[str] = None
    country: Optional[str] = None
    profession: Optional[str] = None
    interested_topics: List[str] = field(default_factory=list)
    
    # Quellentitätsinformationen
    source_entity_uuid: Optional[str] = None
    source_entity_type: Optional[str] = None
    
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    
    def to_reddit_format(self) -> Dict[str, Any]:
        """In Reddit-Plattformformat konvertieren"""
        profile = {
            "user_id": self.user_id,
            "username": self.user_name,  # OASIS-Bibliothek erfordert Feldname username (ohne Unterstrich)
            "name": self.name,
            "bio": self.bio,
            "persona": self.persona,
            "karma": self.karma,
            "created_at": self.created_at,
        }
        
        # Zusätzliche Persönlichkeitsinformationen hinzufügen (falls vorhanden)
        if self.age:
            profile["age"] = self.age
        if self.gender:
            profile["gender"] = self.gender
        if self.mbti:
            profile["mbti"] = self.mbti
        if self.country:
            profile["country"] = self.country
        if self.profession:
            profile["profession"] = self.profession
        if self.interested_topics:
            profile["interested_topics"] = self.interested_topics
        
        return profile
    
    def to_twitter_format(self) -> Dict[str, Any]:
        """In Twitter-Plattformformat konvertieren"""
        profile = {
            "user_id": self.user_id,
            "username": self.user_name,  # OASIS-Bibliothek erfordert Feldname username (ohne Unterstrich)
            "name": self.name,
            "bio": self.bio,
            "persona": self.persona,
            "friend_count": self.friend_count,
            "follower_count": self.follower_count,
            "statuses_count": self.statuses_count,
            "created_at": self.created_at,
        }
        
        # Zusätzliche Persönlichkeitsinformationen hinzufügen
        if self.age:
            profile["age"] = self.age
        if self.gender:
            profile["gender"] = self.gender
        if self.mbti:
            profile["mbti"] = self.mbti
        if self.country:
            profile["country"] = self.country
        if self.profession:
            profile["profession"] = self.profession
        if self.interested_topics:
            profile["interested_topics"] = self.interested_topics
        
        return profile
    
    def to_dict(self) -> Dict[str, Any]:
        """In vollständigen Dictionary-Format konvertieren"""
        return {
            "user_id": self.user_id,
            "user_name": self.user_name,
            "name": self.name,
            "bio": self.bio,
            "persona": self.persona,
            "karma": self.karma,
            "friend_count": self.friend_count,
            "follower_count": self.follower_count,
            "statuses_count": self.statuses_count,
            "age": self.age,
            "gender": self.gender,
            "mbti": self.mbti,
            "country": self.country,
            "profession": self.profession,
            "interested_topics": self.interested_topics,
            "source_entity_uuid": self.source_entity_uuid,
            "source_entity_type": self.source_entity_type,
            "created_at": self.created_at,
        }


class OasisProfileGenerator:
    """
    OASIS Profile-Generator
    
    Wandelt Entitäten aus dem Zep-Graph in für die OASIS-Simulation erforderliche Agent Profile um
    
    Optimierungsmerkmale:
    1. Zep-Graph-Abruffunktion aufrufen, um reichhaltigeren Kontext zu erhalten
    2. Sehr detaillierte Persönlichkeiten generieren (einschließlich Grundinformationen, Berufserfahrung, Persönlichkeitsmerkmale, Social-Media-Verhalten usw.)
    3. Unterscheidung zwischen individuellen Entitäten und abstrakten Gruppen-/Institutionsentitäten
    """
    
    # MBTI-Typenliste
    MBTI_TYPES = [
        "INTJ", "INTP", "ENTJ", "ENTP",
        "INFJ", "INFP", "ENFJ", "ENFP",
        "ISTJ", "ISFJ", "ESTJ", "ESFJ",
        "ISTP", "ISFP", "ESTP", "ESFP"
    ]
    
    # Länderliste
    COUNTRIES = [
        "China", "US", "UK", "Japan", "Germany", "France", 
        "Canada", "Australia", "Brazil", "India", "South Korea"
    ]
    
    # Entitätstypen für Einzelpersonen (erfordern Generierung konkreter Persönlichkeiten)
    INDIVIDUAL_ENTITY_TYPES = [
        "student", "alumni", "professor", "person", "publicfigure", 
        "expert", "faculty", "official", "journalist", "activist"
    ]
    
    # Gruppen-/Institutionsentitätstypen (erfordern Generierung von Gruppenvertreter-Persönlichkeiten)
    GROUP_ENTITY_TYPES = [
        "university", "governmentagency", "organization", "ngo", 
        "mediaoutlet", "company", "institution", "group", "community"
    ]
    
    def __init__(
        self, 
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        zep_api_key: Optional[str] = None,
        graph_id: Optional[str] = None
    ):
        from app.tenant.settings_override import TenantConfig
        cfg = TenantConfig()
        self.api_key = api_key or cfg.LLM_API_KEY
        self.base_url = base_url or cfg.LLM_BASE_URL
        self.model_name = model_name or cfg.LLM_MODEL_NAME
        
        if not self.api_key:
            raise ValueError("LLM_API_KEY nicht konfiguriert")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
        
        # Zep-Client für Abruf von reichhaltigem Kontext
        cfg = TenantConfig()
        self.zep_api_key = zep_api_key or cfg.ZEP_API_KEY
        self.zep_client = None
        self.graph_id = graph_id
        
        if self.zep_api_key:
            try:
                self.zep_client = Zep(api_key=self.zep_api_key)
            except Exception as e:
                logger.warning(f"Zep-Client-Initialisierung fehlgeschlagen: {e}")
    
    def generate_profile_from_entity(
        self, 
        entity: EntityNode, 
        user_id: int,
        use_llm: bool = True
    ) -> OasisAgentProfile:
        """
        OASIS Agent Profile aus Zep-Entität generieren
        
        Args:
            entity: Zep-Entitätsknoten
            user_id: Benutzer-ID (für OASIS)
            use_llm: LLM zur Generierung detaillierter Persönlichkeit verwenden
            
        Returns:
            OasisAgentProfile
        """
        entity_type = entity.get_entity_type() or "Entity"
        
        # Grundinformationen
        name = entity.name
        user_name = self._generate_username(name)
        
        # Kontextinformationen aufbauen
        context = self._build_entity_context(entity)
        
        if use_llm:
            # LLM zur Generierung detaillierter Persönlichkeit verwenden
            profile_data = self._generate_profile_with_llm(
                entity_name=name,
                entity_type=entity_type,
                entity_summary=entity.summary,
                entity_attributes=entity.attributes,
                context=context
            )
        else:
            # Regelbasierte Generierung der Grundpersönlichkeit
            profile_data = self._generate_profile_rule_based(
                entity_name=name,
                entity_type=entity_type,
                entity_summary=entity.summary,
                entity_attributes=entity.attributes
            )
        
        return OasisAgentProfile(
            user_id=user_id,
            user_name=user_name,
            name=name,
            bio=profile_data.get("bio", f"{entity_type}: {name}"),
            persona=profile_data.get("persona", entity.summary or f"A {entity_type} named {name}."),
            karma=profile_data.get("karma", random.randint(500, 5000)),
            friend_count=profile_data.get("friend_count", random.randint(50, 500)),
            follower_count=profile_data.get("follower_count", random.randint(100, 1000)),
            statuses_count=profile_data.get("statuses_count", random.randint(100, 2000)),
            age=profile_data.get("age"),
            gender=profile_data.get("gender"),
            mbti=profile_data.get("mbti"),
            country=profile_data.get("country"),
            profession=profile_data.get("profession"),
            interested_topics=profile_data.get("interested_topics", []),
            source_entity_uuid=entity.uuid,
            source_entity_type=entity_type,
        )
    
    def _generate_username(self, name: str) -> str:
        """Benutzernamen generieren"""
        username = name.lower().replace(" ", "_")
        username = ''.join(c for c in username if c.isalnum() or c == '_')
        
        suffix = random.randint(100, 999)
        return f"{username}_{suffix}"
    
    def _search_zep_for_entity(self, entity: EntityNode) -> Dict[str, Any]:
        """
        Zep-Graph-Hybridsuchfunktion verwenden, um reichhaltige Informationen zu verwandten Entitäten zu erhalten
        
        Zep hat keine eingebaute Hybridsuch-Schnittstelle, daher müssen edges und nodes separat durchsucht und die Ergebnisse dann zusammengeführt werden.
        Parallele Anfragen werden verwendet, um die Effizienz zu verbessern.
        
        Args:
            entity: Entitätsknotenobjekt
            
        Returns:
            Dictionary mit Fakten, Knotenzusammenfassungen und Kontext
        """
        import concurrent.futures
        
        if not self.zep_client:
            return {"facts": [], "node_summaries": [], "context": ""}
        
        entity_name = entity.name
        
        results = {
            "facts": [],
            "node_summaries": [],
            "context": ""
        }
        
        if not self.graph_id:
            logger.debug(f"Zep-Abruf übersprungen: graph_id nicht gesetzt")
            return results
        
        comprehensive_query = f"Alle Informationen, Aktivitäten, Ereignisse, Beziehungen und Hintergründe über {entity_name}"
        
        def search_edges():
            """Kantensuche (Fakten/Beziehungen) - mit Retry-Mechanismus"""
            max_retries = 3
            last_exception = None
            delay = 2.0
            
            for attempt in range(max_retries):
                try:
                    return self.zep_client.graph.search(
                        query=comprehensive_query,
                        graph_id=self.graph_id,
                        limit=30,
                        scope="edges",
                        reranker="rrf"
                    )
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.debug(f"Zep-Kantensuche Versuch {attempt + 1} fehlgeschlagen: {str(e)[:80]}, Retry...")
                        time.sleep(delay)
                        delay *= 2
                    else:
                        logger.debug(f"Zep-Kantensuche nach {max_retries} Versuchen weiterhin fehlgeschlagen: {e}")
            return None
        
        def search_nodes():
            """Knotensuche (Entitätszusammenfassungen) - mit Retry-Mechanismus"""
            max_retries = 3
            last_exception = None
            delay = 2.0
            
            for attempt in range(max_retries):
                try:
                    return self.zep_client.graph.search(
                        query=comprehensive_query,
                        graph_id=self.graph_id,
                        limit=20,
                        scope="nodes",
                        reranker="rrf"
                    )
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.debug(f"Zep-Knotensuche Versuch {attempt + 1} fehlgeschlagen: {str(e)[:80]}, Retry...")
                        time.sleep(delay)
                        delay *= 2
                    else:
                        logger.debug(f"Zep-Knotensuche nach {max_retries} Versuchen weiterhin fehlgeschlagen: {e}")
            return None
        
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                edge_future = executor.submit(search_edges)
                node_future = executor.submit(search_nodes)
                
                edge_result = edge_future.result(timeout=30)
                node_result = node_future.result(timeout=30)
            
            all_facts = set()
            if edge_result and hasattr(edge_result, 'edges') and edge_result.edges:
                for edge in edge_result.edges:
                    if hasattr(edge, 'fact') and edge.fact:
                        all_facts.add(edge.fact)
            results["facts"] = list(all_facts)
            
            all_summaries = set()
            if node_result and hasattr(node_result, 'nodes') and node_result.nodes:
                for node in node_result.nodes:
                    if hasattr(node, 'summary') and node.summary:
                        all_summaries.add(node.summary)
                    if hasattr(node, 'name') and node.name and node.name != entity_name:
                        all_summaries.add(f"Verwandte Entität: {node.name}")
            results["node_summaries"] = list(all_summaries)
            
            context_parts = []
            if results["facts"]:
                context_parts.append("Fakteninformationen:\n" + "\n".join(f"- {f}" for f in results["facts"][:20]))
            if results["node_summaries"]:
                context_parts.append("Verwandte Entitäten:\n" + "\n".join(f"- {s}" for s in results["node_summaries"][:10]))
            results["context"] = "\n\n".join(context_parts)
            
            logger.info(f"Zep-Hybridsuche abgeschlossen: {entity_name}, {len(results['facts'])} Fakten, {len(results['node_summaries'])} relevante Knoten abgerufen")
            
        except concurrent.futures.TimeoutError:
            logger.warning(f"Zep-Abruf-Timeout ({entity_name})")
        except Exception as e:
            logger.warning(f"Zep-Abruf fehlgeschlagen ({entity_name}): {e}")
        
        return results
    
    def _build_entity_context(self, entity: EntityNode) -> str:
        """
        Vollständigen Kontext der Entität aufbauen
        
        Einschließlich:
        1. Edge-Informationen der Entität selbst (Fakten)
        2. Detaillierte Informationen der verwandten Knoten
        3. Reichhaltige Informationen von Zep-Hybridsuche
        """
        context_parts = []
        
        if entity.attributes:
            attrs = []
            for key, value in entity.attributes.items():
                if value and str(value).strip():
                    attrs.append(f"- {key}: {value}")
            if attrs:
                context_parts.append("### Entitätsattribute\n" + "\n".join(attrs))
        
        existing_facts = set()
        if entity.related_edges:
            relationships = []
            for edge in entity.related_edges:
                fact = edge.get("fact", "")
                edge_name = edge.get("edge_name", "")
                direction = edge.get("direction", "")
                
                if fact:
                    relationships.append(f"- {fact}")
                    existing_facts.add(fact)
                elif edge_name:
                    if direction == "outgoing":
                        relationships.append(f"- {entity.name} --[{edge_name}]--> (verwandte Entität)")
                    else:
                        relationships.append(f"- (verwandte Entität) --[{edge_name}]--> {entity.name}")
            
            if relationships:
                context_parts.append("### Verwandte Fakten und Beziehungen\n" + "\n".join(relationships))
        
        if entity.related_nodes:
            related_info = []
            for node in entity.related_nodes:
                node_name = node.get("name", "")
                node_labels = node.get("labels", [])
                node_summary = node.get("summary", "")
                
                custom_labels = [l for l in node_labels if l not in ["Entity", "Node"]]
                label_str = f" ({', '.join(custom_labels)})" if custom_labels else ""
                
                if node_summary:
                    related_info.append(f"- **{node_name}**{label_str}: {node_summary}")
                else:
                    related_info.append(f"- **{node_name}**{label_str}")
            
            if related_info:
                context_parts.append("### Verbundene Entitätsinformationen\n" + "\n".join(related_info))
        
        zep_results = self._search_zep_for_entity(entity)
        
        if zep_results.get("facts"):
            new_facts = [f for f in zep_results["facts"] if f not in existing_facts]
            if new_facts:
                context_parts.append("### Zep-abgerufene Fakteninformationen\n" + "\n".join(f"- {f}" for f in new_facts[:15]))
        
        if zep_results.get("node_summaries"):
            context_parts.append("### Zep-abgerufene verwandte Knoten\n" + "\n".join(f"- {s}" for s in zep_results["node_summaries"][:10]))
        
        return "\n\n".join(context_parts)
    
    def _is_individual_entity(self, entity_type: str) -> bool:
        """Prüfen, ob es sich um eine individuelle Entität handelt"""
        return entity_type.lower() in self.INDIVIDUAL_ENTITY_TYPES
    
    def _is_group_entity(self, entity_type: str) -> bool:
        """Prüfen, ob es sich um eine Gruppen-/Institutionsentität handelt"""
        return entity_type.lower() in self.GROUP_ENTITY_TYPES
    
    def _generate_profile_with_llm(
        self,
        entity_name: str,
        entity_type: str,
        entity_summary: str,
        entity_attributes: Dict[str, Any],
        context: str
    ) -> Dict[str, Any]:
        """
        Sehr detaillierte Persönlichkeit mit LLM generieren
        
        Unterscheidung nach Entitätstyp:
        - Individuelle Entität: Konkrete Personenkonfiguration generieren
        - Gruppen-/Institutionsentität: Repräsentatives Konto generieren
        """
        
        is_individual = self._is_individual_entity(entity_type)
        
        if is_individual:
            prompt = self._build_individual_persona_prompt(
                entity_name, entity_type, entity_summary, entity_attributes, context
            )
        else:
            prompt = self._build_group_persona_prompt(
                entity_name, entity_type, entity_summary, entity_attributes, context
            )

        max_attempts = 3
        last_error = None
        
        for attempt in range(max_attempts):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": self._get_system_prompt(is_individual)},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.7 - (attempt * 0.1)
                )
                
                content = response.choices[0].message.content
                
                finish_reason = response.choices[0].finish_reason
                if finish_reason == 'length':
                    logger.warning(f"LLM-Ausgabe abgeschnitten (Versuch {attempt+1}), Reparaturg...")
                    content = self._fix_truncated_json(content)
                
                try:
                    result = json.loads(content)
                    
                    if "bio" not in result or not result["bio"]:
                        result["bio"] = entity_summary[:200] if entity_summary else f"{entity_type}: {entity_name}"
                    if "persona" not in result or not result["persona"]:
                        result["persona"] = entity_summary or f"{entity_name} ist ein {entity_type}."
                    
                    return result
                    
                except json.JSONDecodeError as je:
                    logger.warning(f"JSON-Parsing fehlgeschlagen (Versuch {attempt+1}): {str(je)[:80]}")
                    
                    result = self._try_fix_json(content, entity_name, entity_type, entity_summary)
                    if result.get("_fixed"):
                        del result["_fixed"]
                        return result
                    
                    last_error = je
                    
            except Exception as e:
                logger.warning(f"LLM-Aufruf fehlgeschlagen (Versuch {attempt+1}): {str(e)[:80]}")
                last_error = e
                import time
                time.sleep(1 * (attempt + 1))
        
        logger.warning(f"LLM-Persönlichkeitsgenerierung fehlgeschlagen ({max_attempts} Versuche): {last_error}, verwende Regelgenerierung")
        return self._generate_profile_rule_based(
            entity_name, entity_type, entity_summary, entity_attributes
        )
    
    def _fix_truncated_json(self, content: str) -> str:
        """Beschädigtes JSON reparieren (Ausgabe wurde durch max_tokens-Limit abgeschnitten)"""
        import re
        
        content = content.strip()
        
        open_braces = content.count('{') - content.count('}')
        open_brackets = content.count('[') - content.count(']')
        
        if content and content[-1] not in '",}]':
            content += '"'
        
        content += ']' * open_brackets
        content += '}' * open_braces
        
        return content
    
    def _try_fix_json(self, content: str, entity_name: str, entity_type: str, entity_summary: str = "") -> Dict[str, Any]:
        """Versuchen, beschädigtes JSON zu reparieren"""
        import re
        
        content = self._fix_truncated_json(content)
        
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            json_str = json_match.group()
            
            def fix_string_newlines(match):
                s = match.group(0)
                s = s.replace('\n', ' ').replace('\r', ' ')
                s = re.sub(r'\s+', ' ', s)
                return s
            
            json_str = re.sub(r'"[^"\\]*(?:\\.[^"\\]*)*"', fix_string_newlines, json_str)
            
            try:
                result = json.loads(json_str)
                result["_fixed"] = True
                return result
            except json.JSONDecodeError as e:
                try:
                    json_str = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', json_str)
                    json_str = re.sub(r'\s+', ' ', json_str)
                    result = json.loads(json_str)
                    result["_fixed"] = True
                    return result
                except:
                    pass
        
        bio_match = re.search(r'"bio"\s*:\s*"([^"]*)"', content)
        persona_match = re.search(r'"persona"\s*:\s*"([^"]*)', content)
        
        bio = bio_match.group(1) if bio_match else (entity_summary[:200] if entity_summary else f"{entity_type}: {entity_name}")
        persona = persona_match.group(1) if persona_match else (entity_summary or f"{entity_name} ist ein {entity_type}.")
        
        if bio_match or persona_match:
            logger.info(f"Teilweise Informationen aus beschädigtem JSON extrahiert")
            return {
                "bio": bio,
                "persona": persona,
                "_fixed": True
            }
        
        logger.warning(f"JSON-Reparatur fehlgeschlagen, gebe Basisstruktur zurück")
        return {
            "bio": entity_summary[:200] if entity_summary else f"{entity_type}: {entity_name}",
            "persona": entity_summary or f"{entity_name} ist ein {entity_type}."
        }
    
    def _get_system_prompt(self, is_individual: bool) -> str:
        """Systemprompt abrufen"""
        base_prompt = "Sie sind ein Experte für die Generierung von Social-Media-Nutzerprofilen. Erstellen Sie detaillierte, realistische Persönlichkeiten für Meinungssimulationen, die die vorhandene Realität maximieren. Geben Sie unbedingt ein gültiges JSON-Format zurück, wobei alle Zeichenkettenwerte keine nicht maskierten Zeilenumbrüche enthalten dürfen. Verwenden Sie Deutsch."
        return base_prompt
    
    def _build_individual_persona_prompt(
        self,
        entity_name: str,
        entity_type: str,
        entity_summary: str,
        entity_attributes: Dict[str, Any],
        context: str
    ) -> str:
        """Erstellen Sie einen detaillierten Persona-Prompt für einzelne Entitäten"""
        
        attrs_str = json.dumps(entity_attributes, ensure_ascii=False) if entity_attributes else "Keine"
        context_str = context[:3000] if context else "Keine zusätzlichen Kontextinformationen"
        
        return f"""Generieren Sie ein detailliertes Social-Media-Nutzerprofil für die Entität, das die vorhandene Realität maximiert.

Entitätsname: {entity_name}
Entitätstyp: {entity_type}
Entitätszusammenfassung: {entity_summary}
Entitätsattribute: {attrs_str}

Kontextinformationen:
{context_str}

Bitte generieren Sie JSON mit folgenden Feldern:

1. bio: Social-Media-Biografie, 200 Zeichen
2. persona: Detaillierte Persönlichkeitsbeschreibung (2000 Zeichen Fließtext), muss enthalten:
   - Grundlegende Informationen (Alter, Beruf, Bildungs background, Standort)
   - Persönlicher Hintergrund (wichtige Erfahrungen, Verbindung zum Ereignis, soziale Beziehungen)
   - Persönlichkeitsmerkmale (MBTI-Typ, Kernpersönlichkeit, Artikulationsstil)
   - Social-Media-Verhalten (Beitragshäufigkeit, Inhaltspräferenzen, Interaktionsstil, Sprachmerkmale)
   - Standpunkte und Meinungen (Einstellung zum Thema, Inhalte die sie aufregen/begeistern könnten)
   - Besondere Merkmale (Sprachgewohnheiten, besondere Erfahrungen, persönliche Hobbys)
   - Persönliche Erinnerungen (wichtiger Teil der Persona, muss die Verbindung dieser Person zum Ereignis beschreiben, sowie bereits stattgefundene Handlungen und Reaktionen dieser Person während des Ereignisses)
3. age: Alterszahl (muss eine Ganzzahl sein)
4. gender: Geschlecht, muss auf Englisch sein: "male" oder "female"
5. mbti: MBTI-Typ (z.B. INTJ, ENFP usw.)
6. country: Land (auf Deutsch, z.B. "Deutschland")
7. profession: Beruf
8. interested_topics: Array von interessanten Themen

Wichtig:
- Alle Feldwerte müssen Zeichenketten oder Zahlen sein, keine Zeilenumbrüche verwenden
- persona muss eine zusammenhängende Textbeschreibung sein
- Deutsch verwenden (außer für das gender-Feld, das Englisch male/female verwenden muss)
- Inhalt muss mit den Entitätsinformationen übereinstimmen
- age muss eine gültige Ganzzahl sein, gender muss "male" oder "female" sein
"""

    def _build_group_persona_prompt(
        self,
        entity_name: str,
        entity_type: str,
        entity_summary: str,
        entity_attributes: Dict[str, Any],
        context: str
    ) -> str:
        """Erstellen Sie einen detaillierten Persona-Prompt für Gruppen-/Institutional-Entitäten"""
        
        attrs_str = json.dumps(entity_attributes, ensure_ascii=False) if entity_attributes else "Keine"
        context_str = context[:3000] if context else "Keine zusätzlichen Kontextinformationen"
        
        return f"""Generieren Sie ein detailliertes Social-Media-Konto für institutionelle Gruppierungen, das die vorhandene Realität maximiert.

Entitätsname: {entity_name}
Entitätstyp: {entity_type}
Entitätszusammenfassung: {entity_summary}
Entitätsattribute: {attrs_str}

Kontextinformationen:
{context_str}

Bitte generieren Sie JSON mit folgenden Feldern:

1. bio: Offizielle Kontobiografie, 200 Zeichen, professionell und angemessen
2. persona: Detaillierte Kontodarstellung (2000 Zeichen Fließtext), muss enthalten:
   - Grundlegende Institutsinformationen (offizieller Name, Art der Institution, Gründungshintergrund, Hauptfunktionen)
   - Konto-Positionierung (Kontotyp, Zielgruppe, Kernfunktionen)
   - Sprechstil (Sprachmerkmale, häufig verwendete Ausdrücke, Tabuthemen)
   - Merkmale der veröffentlichten Inhalte (Inhaltstypen, Veröffentlichungshäufigkeit, aktive Zeiträume)
   - Standpunkte und Haltungen (offizielle Position zu Kernthemen, Umgang mit Kontroversen)
   - Besondere Hinweise (dargestellte Gruppenprofile, Betriebsgewohnheiten)
   - Institutionelle Erinnerungen (wichtiger Teil der Persona, muss die Verbindung dieser Institution zum Ereignis beschreiben, sowie bereits stattgefundene Handlungen und Reaktionen dieser Institution während des Ereignisses)
3. age: Immer 30 (virtuelles Alter des Institutionenkontos)
4. gender: Immer "other" (Institutionenkonten verwenden "other" für Nicht-Personen)
5. mbti: MBTI-Typ zur Beschreibung des Kontostils, z.B. ISTJ für seriös und konservativ
6. country: Land (auf Deutsch, z.B. "Deutschland")
7. profession: Beschreibung der institutionellen Funktion
8. interested_topics: Array der interessierten Bereiche

Wichtig:
- Alle Feldwerte müssen Zeichenketten oder Zahlen sein, keine Nullwerte erlaubt
- persona muss eine zusammenhängende Textbeschreibung sein, keine Zeilenumbrüche verwenden
- Deutsch verwenden (außer für das gender-Feld, das Englisch "other" verwenden muss)
- age muss die Ganzzahl 30 sein, gender muss die Zeichenkette "other" sein
- Institutionelle Konten müssen in ihrem Identitätsdesignat sprechen"""
    
    def _generate_profile_rule_based(
        self,
        entity_name: str,
        entity_type: str,
        entity_summary: str,
        entity_attributes: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Regelbasierte Generierung der Grundpersönlichkeit"""
        
        entity_type_lower = entity_type.lower()
        
        if entity_type_lower in ["student", "alumni"]:
            return {
                "bio": f"{entity_type} with interests in academics and social issues.",
                "persona": f"{entity_name} is a {entity_type.lower()} who is actively engaged in academic and social discussions. They enjoy sharing perspectives and connecting with peers.",
                "age": random.randint(18, 30),
                "gender": random.choice(["male", "female"]),
                "mbti": random.choice(self.MBTI_TYPES),
                "country": random.choice(self.COUNTRIES),
                "profession": "Student",
                "interested_topics": ["Education", "Social Issues", "Technology"],
            }
        
        elif entity_type_lower in ["publicfigure", "expert", "faculty"]:
            return {
                "bio": f"Expert and thought leader in their field.",
                "persona": f"{entity_name} is a recognized {entity_type.lower()} who shares insights and opinions on important matters. They are known for their expertise and influence in public discourse.",
                "age": random.randint(35, 60),
                "gender": random.choice(["male", "female"]),
                "mbti": random.choice(["ENTJ", "INTJ", "ENTP", "INTP"]),
                "country": random.choice(self.COUNTRIES),
                "profession": entity_attributes.get("occupation", "Expert"),
                "interested_topics": ["Politics", "Economics", "Culture & Society"],
            }
        
        elif entity_type_lower in ["mediaoutlet", "socialmediaplatform"]:
            return {
                "bio": f"Official account for {entity_name}. News and updates.",
                "persona": f"{entity_name} is a media entity that reports news and facilitates public discourse. The account shares timely updates and engages with the audience on current events.",
                "age": 30,
                "gender": "other",
                "mbti": "ISTJ",
                "country": "Deutschland",
                "profession": "Media",
                "interested_topics": ["General News", "Current Events", "Public Affairs"],
            }
        
        elif entity_type_lower in ["university", "governmentagency", "ngo", "organization"]:
            return {
                "bio": f"Official account of {entity_name}.",
                "persona": f"{entity_name} is an institutional entity that communicates official positions, announcements, and engages with stakeholders on relevant matters.",
                "age": 30,
                "gender": "other",
                "mbti": "ISTJ",
                "country": "Deutschland",
                "profession": entity_type,
                "interested_topics": ["Public Policy", "Community", "Official Announcements"],
            }
        
        else:
            return {
                "bio": entity_summary[:150] if entity_summary else f"{entity_type}: {entity_name}",
                "persona": entity_summary or f"{entity_name} is a {entity_type.lower()} participating in social discussions.",
                "age": random.randint(25, 50),
                "gender": random.choice(["male", "female"]),
                "mbti": random.choice(self.MBTI_TYPES),
                "country": random.choice(self.COUNTRIES),
                "profession": entity_type,
                "interested_topics": ["General", "Social Issues"],
            }
    
    def set_graph_id(self, graph_id: str):
        """Graph-ID für Zep-Abruf setzen"""
        self.graph_id = graph_id
    
    def generate_profiles_from_entities(
        self,
        entities: List[EntityNode],
        use_llm: bool = True,
        progress_callback: Optional[callable] = None,
        graph_id: Optional[str] = None,
        parallel_count: int = 5,
        realtime_output_path: Optional[str] = None,
        output_platform: str = "reddit"
    ) -> List[OasisAgentProfile]:
        """
        Agent Profile stapelweise aus Entitäten generieren (unterstützt parallele Generierung)
        
        Args:
            entities: Entitätsliste
            use_llm: Ob LLM zur detaillierten Persönlichkeitsgenerierung verwendet wird
            progress_callback: Fortschritts-Callback-Funktion (current, total, message)
            graph_id: Graph-ID, für Zep-Abruf zur Erlangung reichhaltigeren Kontextes
            parallel_count: Anzahl paralleler Generierungen, Standard 5
            realtime_output_path: Echtzeit-Schreibdateipfad (falls angegeben, wird bei jeder Generierung einmal geschrieben)
            output_platform: Ausgabeplattform-Format ("reddit" oder "twitter")
            
        Returns:
            Agent Profile-Liste
        """
        import concurrent.futures
        from threading import Lock
        
        if graph_id:
            self.graph_id = graph_id
        
        total = len(entities)
        profiles = [None] * total
        completed_count = [0]
        lock = Lock()
        
        def save_profiles_realtime():
            """Generierte Profiles in Echtzeit in Datei speichern"""
            if not realtime_output_path:
                return
            
            with lock:
                existing_profiles = [p for p in profiles if p is not None]
                if not existing_profiles:
                    return
                
                try:
                    if output_platform == "reddit":
                        profiles_data = [p.to_reddit_format() for p in existing_profiles]
                        with open(realtime_output_path, 'w', encoding='utf-8') as f:
                            json.dump(profiles_data, f, ensure_ascii=False, indent=2)
                    else:
                        import csv
                        profiles_data = [p.to_twitter_format() for p in existing_profiles]
                        if profiles_data:
                            fieldnames = list(profiles_data[0].keys())
                            with open(realtime_output_path, 'w', encoding='utf-8', newline='') as f:
                                writer = csv.DictWriter(f, fieldnames=fieldnames)
                                writer.writeheader()
                                writer.writerows(profiles_data)
                except Exception as e:
                    logger.warning(f"Echtzeit-Speicherung der Profiles fehlgeschlagen: {e}")
        
        def generate_single_profile(idx: int, entity: EntityNode) -> tuple:
            """Funktion zur Generierung eines einzelnen Profiles"""
            entity_type = entity.get_entity_type() or "Entity"
            
            try:
                profile = self.generate_profile_from_entity(
                    entity=entity,
                    user_id=idx,
                    use_llm=use_llm
                )
                
                self._print_generated_profile(entity.name, entity_type, profile)
                
                return idx, profile, None
                
            except Exception as e:
                logger.error(f"Persönlichkeitsgenerierung für Entität {entity.name} fehlgeschlagen: {str(e)}")
                fallback_profile = OasisAgentProfile(
                    user_id=idx,
                    user_name=self._generate_username(entity.name),
                    name=entity.name,
                    bio=f"{entity_type}: {entity.name}",
                    persona=entity.summary or f"A participant in social discussions.",
                    source_entity_uuid=entity.uuid,
                    source_entity_type=entity_type,
                )
                return idx, fallback_profile, str(e)
        
        logger.info(f"Starte parallele Generierung von {total} Agent-Persönlichkeiten (Parallelität: {parallel_count})...")
        print(f"\n{'='*60}")
        print(f"Agent-Persönlichkeiten werden generiert - {total} Entitäten gesamt, Parallelität: {parallel_count}")
        print(f"{'='*60}\n")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=parallel_count) as executor:
            future_to_entity = {
                executor.submit(generate_single_profile, idx, entity): (idx, entity)
                for idx, entity in enumerate(entities)
            }
            
            for future in concurrent.futures.as_completed(future_to_entity):
                idx, entity = future_to_entity[future]
                entity_type = entity.get_entity_type() or "Entity"
                
                try:
                    result_idx, profile, error = future.result()
                    profiles[result_idx] = profile
                    
                    with lock:
                        completed_count[0] += 1
                        current = completed_count[0]
                    
                    save_profiles_realtime()
                    
                    if progress_callback:
                        progress_callback(
                            current, 
                            total, 
                            f"Abgeschlossen {current}/{total}: {entity.name} ({entity_type})"
                        )
                    
                    if error:
                        logger.warning(f"[{current}/{total}] {entity.name} verwendet Fallback-Persönlichkeit: {error}")
                    else:
                        logger.info(f"[{current}/{total}] Persönlichkeit erfolgreich generiert: {entity.name} ({entity_type})")
                        
                except Exception as e:
                    logger.error(f"Ausnahme bei der Verarbeitung der Entität {entity.name}: {str(e)}")
                    with lock:
                        completed_count[0] += 1
                    profiles[idx] = OasisAgentProfile(
                        user_id=idx,
                        user_name=self._generate_username(entity.name),
                        name=entity.name,
                        bio=f"{entity_type}: {entity.name}",
                        persona=entity.summary or "A participant in social discussions.",
                        source_entity_uuid=entity.uuid,
                        source_entity_type=entity_type,
                    )
                    save_profiles_realtime()
        
        print(f"\n{'='*60}")
        print(f"Persönlichkeitsgenerierung abgeschlossen! {len([p for p in profiles if p])} Agents generiert")
        print(f"{'='*60}\n")
        
        return profiles
    
    def _print_generated_profile(self, entity_name: str, entity_type: str, profile: OasisAgentProfile):
        """Generierte Persönlichkeit in Echtzeit auf Konsole ausgeben (Vollständiger Inhalt, nicht gekürzt)"""
        separator = "-" * 70
        
        topics_str = ', '.join(profile.interested_topics) if profile.interested_topics else 'Keine'
        
        output_lines = [
            f"\n{separator}",
            f"[Generiert] {entity_name} ({entity_type})",
            f"{separator}",
            f"Benutzername: {profile.user_name}",
            f"",
            f"【Biografie】",
            f"{profile.bio}",
            f"",
            f"【Detaillierte Persönlichkeit】",
            f"{profile.persona}",
            f"",
            f"【Basisattribute】",
            f"Alter: {profile.age} | Geschlecht: {profile.gender} | MBTI: {profile.mbti}",
            f"Beruf: {profile.profession} | Land: {profile.country}",
            f"Interessante Themen: {topics_str}",
            separator
        ]
        
        output = "\n".join(output_lines)
        
        print(output)
    
    def save_profiles(
        self,
        profiles: List[OasisAgentProfile],
        file_path: str,
        platform: str = "reddit"
    ):
        """
        Profile in Datei speichern (wählt korrektes Format nach Plattform)
        
        OASIS-Plattformformatanforderungen:
        - Twitter: CSV-Format
        - Reddit: JSON-Format
        
        Args:
            profiles: Profile-Liste
            file_path: Dateipfad
            platform: Plattformtyp ("reddit" oder "twitter")
        """
        if platform == "twitter":
            self._save_twitter_csv(profiles, file_path)
        else:
            self._save_reddit_json(profiles, file_path)
    
    def _save_twitter_csv(self, profiles: List[OasisAgentProfile], file_path: str):
        """
        Twitter Profile im CSV-Format speichern (entspricht OASIS-Anforderungen)
        
        OASIS Twitter geforderte CSV-Felder:
        - user_id: Benutzer-ID (beginnt bei 0 gemäß CSV-Reihenfolge)
        - name: Echter Benutzername
        - username: Benutzername im System
        - user_char: Detaillierte Persönlichkeitsbeschreibung (in LLM-Systemprompt injiziert, lenkt Agent-Verhalten)
        - description: Kurze öffentliche Biografie (auf der Profilseite angezeigt)
        
        user_char vs description Unterschied:
        - user_char: Interner Gebrauch, LLM-Systemprompt, bestimmt wie Agent denkt und handelt
        - description: Extern angezeigt, für andere Benutzer sichtbare Biografie
        """
        import csv
        
        if not file_path.endswith('.csv'):
            file_path = file_path.replace('.json', '.csv')
        
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            headers = ['user_id', 'name', 'username', 'user_char', 'description']
            writer.writerow(headers)
            
            for idx, profile in enumerate(profiles):
                user_char = profile.bio
                if profile.persona and profile.persona != profile.bio:
                    user_char = f"{profile.bio} {profile.persona}"
                user_char = user_char.replace('\n', ' ').replace('\r', ' ')
                
                description = profile.bio.replace('\n', ' ').replace('\r', ' ')
                
                row = [
                    idx,
                    profile.name,
                    profile.user_name,
                    user_char,
                    description
                ]
                writer.writerow(row)
        
        logger.info(f"{len(profiles)} Twitter-Profile nach {file_path} gespeichert (OASIS CSV-Format)")
    
    def _normalize_gender(self, gender: Optional[str]) -> str:
        """
        Gender-Feld ins von OASIS geforderte englische Format standardisieren
        
        OASIS-Anforderung: male, female, other
        """
        if not gender:
            return "other"
        
        gender_lower = gender.lower().strip()
        
        gender_map = {
            "男": "male",
            "女": "female",
            "机构": "other",
            "其他": "other",
            "male": "male",
            "female": "female",
            "other": "other",
        }
        
        return gender_map.get(gender_lower, "other")
    
    def _save_reddit_json(self, profiles: List[OasisAgentProfile], file_path: str):
        """
        Reddit Profile im JSON-Format speichern
        
        Verwendet das mit to_reddit_format() konsistente Format, um sicherzustellen, dass OASIS korrekt lesen kann.
        Muss das user_id-Feld enthalten, dies ist der Schlüssel für OASIS agent_graph.get_agent() Matching!
        
        Erforderliche Felder:
        - user_id: Benutzer-ID (Integer, wird verwendet um initial_posts poster_agent_id abzugleichen)
        - username: Benutzername
        - name: Anzeigename
        - bio: Biografie
        - persona: Detaillierte Persönlichkeit
        - age: Alter (Integer)
        - gender: "male", "female", oder "other"
        - mbti: MBTI-Typ
        - country: Land
        """
        data = []
        for idx, profile in enumerate(profiles):
            item = {
                "user_id": profile.user_id if profile.user_id is not None else idx,
                "username": profile.user_name,
                "name": profile.name,
                "bio": profile.bio[:150] if profile.bio else f"{profile.name}",
                "persona": profile.persona or f"{profile.name} is a participant in social discussions.",
                "karma": profile.karma if profile.karma else 1000,
                "created_at": profile.created_at,
                "age": profile.age if profile.age else 30,
                "gender": self._normalize_gender(profile.gender),
                "mbti": profile.mbti if profile.mbti else "ISTJ",
                "country": profile.country if profile.country else "Deutschland",
            }
            
            if profile.profession:
                item["profession"] = profile.profession
            if profile.interested_topics:
                item["interested_topics"] = profile.interested_topics
            
            data.append(item)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"{len(profiles)} Reddit-Profile nach {file_path} gespeichert (JSON-Format, mit user_id-Feld)")
    
    # Alte Methodennamen als Alias behalten, für Rückwärtskompatibilität
    def save_profiles_to_json(
        self,
        profiles: List[OasisAgentProfile],
        file_path: str,
        platform: str = "reddit"
    ):
        """[Veraltet] Bitte verwenden Sie die save_profiles()-Methode"""
        logger.warning("save_profiles_to_json ist veraltet, bitte verwenden Sie die save_profiles-Methode")
        self.save_profiles(profiles, file_path, platform)

