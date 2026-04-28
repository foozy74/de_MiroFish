"""
Ontologie-Generierungsdienst
Schnittstelle 1: Analysiert Textinhalt und generiert Entitäts- und Beziehungstypdefinitionen für soziale Simulationen
"""

import json
from typing import Dict, Any, List, Optional
from ..utils.llm_client import LLMClient


# Systemprompts für Ontology-Generierung
ONTOLOGY_SYSTEM_PROMPT = """Sie sind ein professioneller Experte für Wissensgraph-Ontologiedesign. Ihre Aufgabe ist es, den gegebenen Textinhalt und die Simulationsanforderungen zu analysieren und Entitäts- und Beziehungstypen für Social-Media-Meinungssimulationen zu entwerfen.

**Wichtig: Sie müssen gültige JSON-Formatdaten ausgeben, keinen anderen Inhalt.**

## Kernaufgaben-Hintergrund

Wir bauen ein Social-Media-Meinungssimulationssystem auf. In diesem System:
- Jede Entität ist ein "Konto" oder "Subjekt", das in sozialen Medien sprechen, interagieren und Informationen verbreiten kann
- Entitäten beeinflussen sich gegenseitig, teilen, kommentieren und reagieren aufeinander
- Wir müssen die Reaktionen verschiedener Parteien und die Informationsverbreitungspfade in Meinungsereignissen simulieren

Daher müssen Entitäten tatsächlich existierende Subjekte sein, die in sozialen Medien sprechen und interagieren können:

**Können sein**:
- Konkrete Einzelpersonen (öffentliche Personen, Betroffene, Meinungsführer, Experten, gewöhnliche Menschen)
- Unternehmen und Firmen (einschließlich ihrer offiziellen Konten)
- Organisationen und Institutionen (Universitäten, Verbände, NGOs, Gewerkschaften usw.)
- Regierungsabteilungen und Aufsichtsbehörden
- Medienorganisationen (Zeitungen, Fernsehsender, Self-Media, Websites)
- Social-Media-Plattformen selbst
- Vertreter bestimmter Gruppen (z.B. Alumni-Verbände, Fan-Gruppen, Rechtsschutzgruppen usw.)

**Können nicht sein**:
- Abstrakte Konzepte (wie "Meinung", "Emotion", "Trend")
- Themen/Topics (wie "akademische Integrität", "Bildungsreform")
- Meinungen/Einstellungen (wie "Unterstützer", "Gegner")

## Ausgabeformat

Bitte geben Sie das JSON-Format aus, das die folgende Struktur enthält:

```json
{
    "entity_types": [
        {
            "name": "Entitätstyp-Name (Englisch, PascalCase)",
            "description": "Kurze Beschreibung (Englisch, nicht mehr als 100 Zeichen)",
            "attributes": [
                {
                    "name": "Attributname (Englisch, snake_case)",
                    "type": "text",
                    "description": "Attributbeschreibung"
                }
            ],
            "examples": ["Beispielentität 1", "Beispielentität 2"]
        }
    ],
    "edge_types": [
        {
            "name": "Beziehungstyp-Name (Englisch, UPPER_SNAKE_CASE)",
            "description": "Kurze Beschreibung (Englisch, nicht mehr als 100 Zeichen)",
            "source_targets": [
                {"source": "Quell-Entitätstyp", "target": "Ziel-Entitätstyp"}
            ],
            "attributes": []
        }
    ],
    "analysis_summary": "Kurze Analyse und Erklärung des Textinhalts (Deutsch)"
}
```

## Designrichtlinien (äußerst wichtig!)

### 1. Entitätstyp-Design - Muss strikt eingehalten werden

**Mengenanforderung: Genau 10 Entitätstypen**

**Hierarchiestrukturanforderungen (müssen sowohl konkrete als auch Fallback-Typen enthalten)**:

Ihre 10 Entitätstypen müssen die folgende Hierarchie enthalten:

A. **Fallback-Typen (müssen enthalten sein, an den letzten 2 Positionen der Liste)**:
   - `Person`: Fallback-Typ für alle natürlichen Personen. Wenn eine Person nicht unter andere spezifischere Personentypen fällt, wird sie dieser Kategorie zugeordnet.
   - `Organization`: Fallback-Typ für alle Organisationen. Wenn eine Organisation nicht unter andere spezifischere Organisationstypen fällt, wird sie dieser Kategorie zugeordnet.

B. **Konkrete Typen (8, basierend auf dem Textinhalt entworfen)**:
   - Entwerfen Sie spezifischere Typen für die im Text erscheindenden Hauptrollen
   - Zum Beispiel: Wenn der Text akademische Ereignisse betrifft, können Sie `Student`, `Professor`, `University` haben
   - Zum Beispiel: Wenn der Text Geschäftsereignisse betrifft, können Sie `Company`, `CEO`, `Employee` haben

**Warum werden Fallback-Typen benötigt**:
- Im Text erscheinen verschiedene Personen, wie "Lehrer an Grund- und Mittelschulen", "Passant", "bestimmter Netzbürger"
- Wenn kein spezieller Typ übereinstimmt, sollten sie in `Person` eingeordnet werden
- Ebenso sollten kleine Organisationen, temporäre Gruppen usw. in `Organization` eingeordnet werden

**Designprinzipien für konkrete Typen**:
- Identifizieren Sie hochfrequent erscheinende oder Schlüsselrollentypen aus dem Text
- Jeder konkrete Typ sollte klare Grenzen haben, ohne Überschneidungen
- Die Beschreibung muss klar erklären, wie sich dieser Typ vom Fallback-Typ unterscheidet

### 2. Beziehungstyp-Design

- Anzahl: 6-10
- Beziehungen sollten reale Verbindungen in Social-Media-Interaktionen widerspiegeln
- Stellen Sie sicher, dass die source_targets Ihrer definierten Entitätstypen abgedeckt sind

### 3. Attributdesign

- 1-3 Schlüsselattribute für jeden Entitätstyp
- **Hinweis**: Attributnamen dürfen nicht `name`, `uuid`, `group_id`, `created_at`, `summary` verwenden (dies sind System-reservierte Wörter)
- Empfohlen: `full_name`, `title`, `role`, `position`, `location`, `description` usw.

## Entitätstyp-Referenz

**Persönliche Typen (konkret)**:
- Student: Student
- Professor: Professor/Wissenschaftler
- Journalist: Journalist
- Celebrity: Prominente/Influencer
- Executive: Führungskraft
- Official: Regierungsbeamter
- Lawyer: Anwalt
- Doctor: Arzt

**Persönliche Typen (Fallback)**:
- Person: Jede natürliche Person (wird verwendet, wenn nicht in die oben genannten konkreten Typen fällt)

**Organisationstypen (konkret)**:
- University: Hochschule
- Company: Unternehmen
- GovernmentAgency: Regierungsbehörde
- MediaOutlet: Medienorganisation
- Hospital: Krankenhaus
- School: Grund- und Mittelschule
- NGO: Nichtregierungsorganisation

**Organisationstypen (Fallback)**:
- Organization: Jede Organisation (wird verwendet, wenn nicht in die oben genannten konkreten Typen fällt)

## Beziehungstyp-Referenz

- WORKS_FOR: Arbeitet bei
- STUDIES_AT: Studiert an
- AFFILIATED_WITH: Affiliiert mit
- REPRESENTS: Vertritt
- REGULATES: Reglementiert
- REPORTS_ON: Berichtet über
- COMMENTS_ON: Kommentiert
- RESPONDS_TO: Reagiert auf
- SUPPORTS: Unterstützt
- OPPOSES: Lent gegensätzlich
- COLLABORATES_WITH: Kollaboriert mit
- COMPETES_WITH: Konkurriert mit
"""


class OntologyGenerator:
    """
    Ontology-Generator
    Analysiert Textinhalt und generiert Entitäts- und Beziehungstypdefinitionen
    """
    
    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm_client = llm_client or LLMClient()
    
    def generate(
        self,
        document_texts: List[str],
        simulation_requirement: str,
        additional_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Ontology-Definition generieren
        
        Args:
            document_texts: Dokumenttextliste
            simulation_requirement: Simulationsanforderungsbeschreibung
            additional_context: Zusätzlicher Kontext
            
        Returns:
            Ontology-Definition (entity_types, edge_types usw.)
        """
        # Benutzernachricht erstellen
        user_message = self._build_user_message(
            document_texts, 
            simulation_requirement,
            additional_context
        )
        
        messages = [
            {"role": "system", "content": ONTOLOGY_SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ]
        
        # LLM aufrufen
        result = self.llm_client.chat_json(
            messages=messages,
            temperature=0.3,
            max_tokens=4096
        )
        
        # Validierung und Nachbearbeitung
        result = self._validate_and_process(result)
        
        return result
    
    # Maximale Textlänge für LLM (50.000 Zeichen)
    MAX_TEXT_LENGTH_FOR_LLM = 50000
    
    def _build_user_message(
        self,
        document_texts: List[str],
        simulation_requirement: str,
        additional_context: Optional[str]
    ) -> str:
        """Benutzernachricht erstellen"""
        
        # Texte zusammenführen
        combined_text = "\n\n---\n\n".join(document_texts)
        original_length = len(combined_text)
        
        # Text auf 50.000 Zeichen kürzen, falls überschritten
        if len(combined_text) > self.MAX_TEXT_LENGTH_FOR_LLM:
            combined_text = combined_text[:self.MAX_TEXT_LENGTH_FOR_LLM]
            combined_text += f"\n\n...(Originaltext insgesamt {original_length} Zeichen, erste {self.MAX_TEXT_LENGTH_FOR_LLM} Zeichen für Ontology-Analyse gekürzt)..."
        
        message = f"""## Simulationsanforderungen

{simulation_requirement}

## Dokumentinhalt

{combined_text}
"""
        
        if additional_context:
            message += f"""
## Zusätzliche Hinweise

{additional_context}
"""
        
        message += """
Bitte entwerfen Sie auf Grundlage des oben Genannten Entitäts- und Beziehungstypen für Social-Media-Meinungssimulationen.

**Muss befolgte Regeln**:
1. Genau 10 Entitätstypen müssen ausgegeben werden
2. Die letzten 2 müssen Fallback-Typen sein: Person (persönlicher Fallback) und Organization (Organisations-Fallback)
3. Die ersten 8 sind konkrete, auf Textinhalt basierende Typen
4. Alle Entitätstypen müssen tatsächlich existierende Subjekte sein, die in sozialen Medien sprechen können, keine abstrakten Konzepte
5. Attributnamen dürfen keine reservierten Wörter wie name, uuid, group_id verwenden, verwenden Sie stattdessen full_name, org_name usw.
"""
        
        return message
    
    def _validate_and_process(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Ergebnisse validieren und nachbearbeiten"""
        
        # Sicherstellen, dass erforderliche Felder vorhanden sind
        if "entity_types" not in result:
            result["entity_types"] = []
        if "edge_types" not in result:
            result["edge_types"] = []
        if "analysis_summary" not in result:
            result["analysis_summary"] = ""
        
        # Entitätstypen validieren
        for entity in result["entity_types"]:
            if "attributes" not in entity:
                entity["attributes"] = []
            if "examples" not in entity:
                entity["examples"] = []
            # Sicherstellen, dass description 100 Zeichen nicht überschreitet
            if len(entity.get("description", "")) > 100:
                entity["description"] = entity["description"][:97] + "..."
        
        # Beziehungstypen validieren
        for edge in result["edge_types"]:
            if "source_targets" not in edge:
                edge["source_targets"] = []
            if "attributes" not in edge:
                edge["attributes"] = []
            if len(edge.get("description", "")) > 100:
                edge["description"] = edge["description"][:97] + "..."
        
        # Zep API-Limit: Maximal 10 benutzerdefinierte Entitätstypen, maximal 10 benutzerdefinierte Kantentypen
        MAX_ENTITY_TYPES = 10
        MAX_EDGE_TYPES = 10
        
        # Fallback-Typ-Definitionen
        person_fallback = {
            "name": "Person",
            "description": "Any individual person not fitting other specific person types.",
            "attributes": [
                {"name": "full_name", "type": "text", "description": "Full name of the person"},
                {"name": "role", "type": "text", "description": "Role or occupation"}
            ],
            "examples": ["ordinary citizen", "anonymous netizen"]
        }
        
        organization_fallback = {
            "name": "Organization",
            "description": "Any organization not fitting other specific organization types.",
            "attributes": [
                {"name": "org_name", "type": "text", "description": "Name of the organization"},
                {"name": "org_type", "type": "text", "description": "Type of organization"}
            ],
            "examples": ["small business", "community group"]
        }
        
        # Prüfen, ob Fallback-Typen bereits vorhanden sind
        entity_names = {e["name"] for e in result["entity_types"]}
        has_person = "Person" in entity_names
        has_organization = "Organization" in entity_names
        
        # Fallback-Typen, die hinzugefügt werden müssen
        fallbacks_to_add = []
        if not has_person:
            fallbacks_to_add.append(person_fallback)
        if not has_organization:
            fallbacks_to_add.append(organization_fallback)
        
        if fallbacks_to_add:
            current_count = len(result["entity_types"])
            needed_slots = len(fallbacks_to_add)
            
            # Wenn Hinzufügen 10 überschreiten würde, müssen einige bestehende Typen entfernt werden
            if current_count + needed_slots > MAX_ENTITY_TYPES:
                # Berechnen, wie viele entfernt werden müssen
                to_remove = current_count + needed_slots - MAX_ENTITY_TYPES
                # Vom Ende entfernen (wichtigere konkrete Typen am Anfang beibehalten)
                result["entity_types"] = result["entity_types"][:-to_remove]
            
            # Fallback-Typen hinzufügen
            result["entity_types"].extend(fallbacks_to_add)
        
        # Abschließend sicherstellen, dass Limits nicht überschritten werden (Defensive Programmierung)
        if len(result["entity_types"]) > MAX_ENTITY_TYPES:
            result["entity_types"] = result["entity_types"][:MAX_ENTITY_TYPES]
        
        if len(result["edge_types"]) > MAX_EDGE_TYPES:
            result["edge_types"] = result["edge_types"][:MAX_EDGE_TYPES]
        
        return result
    
    def generate_python_code(self, ontology: Dict[str, Any]) -> str:
        """
        Ontology-Definition in Python-Code konvertieren (ähnlich ontology.py)
        
        Args:
            ontology: Ontology-Definition
            
        Returns:
            Python-Code-Zeichenkette
        """
        code_lines = [
            '"""',
            'Benutzerdefinierte Entitätstyp-Definition',
            'Automatisch generiert von MiroFish für Social-Media-Meinungssimulationen',
            '"""',
            '',
            'from pydantic import Field',
            'from zep_cloud.external_clients.ontology import EntityModel, EntityText, EdgeModel',
            '',
            '',
            '# ============== Entitätstyp-Definition ==============',
            '',
        ]
        
        # Entitätstypen generieren
        for entity in ontology.get("entity_types", []):
            name = entity["name"]
            desc = entity.get("description", f"A {name} entity.")
            
            code_lines.append(f'class {name}(EntityModel):')
            code_lines.append(f'    """{desc}"""')
            
            attrs = entity.get("attributes", [])
            if attrs:
                for attr in attrs:
                    attr_name = attr["name"]
                    attr_desc = attr.get("description", attr_name)
                    code_lines.append(f'    {attr_name}: EntityText = Field(')
                    code_lines.append(f'        description="{attr_desc}",')
                    code_lines.append(f'        default=None')
                    code_lines.append(f'    )')
            else:
                code_lines.append('    pass')
            
            code_lines.append('')
            code_lines.append('')
        
        code_lines.append('        # ============== Beziehungstyp-Definition ==============')
        code_lines.append('')
        
        # Beziehungstypen generieren
        for edge in ontology.get("edge_types", []):
            name = edge["name"]
            # In PascalCase-Klassennamen umwandeln
            class_name = ''.join(word.capitalize() for word in name.split('_'))
            desc = edge.get("description", f"A {name} relationship.")
            
            code_lines.append(f'class {class_name}(EdgeModel):')
            code_lines.append(f'    """{desc}"""')
            
            attrs = edge.get("attributes", [])
            if attrs:
                for attr in attrs:
                    attr_name = attr["name"]
                    attr_desc = attr.get("description", attr_name)
                    code_lines.append(f'    {attr_name}: EntityText = Field(')
                    code_lines.append(f'        description="{attr_desc}",')
                    code_lines.append(f'        default=None')
                    code_lines.append(f'    )')
            else:
                code_lines.append('    pass')
            
            code_lines.append('')
            code_lines.append('')
        
        # Typkonfigurations-Wörterbuch generieren
        code_lines.append('# ============== Typkonfiguration ==============')
        code_lines.append('')
        
        code_lines.append('# ============== Beziehungstyp-Definition ==============')
        code_lines.append('')
        code_lines.append('EDGE_TYPES = {')
        for edge in ontology.get("edge_types", []):
            name = edge["name"]
            class_name = ''.join(word.capitalize() for word in name.split('_'))
            code_lines.append(f'    "{name}": {class_name},')
        code_lines.append('}')
        code_lines.append('')
        
        # source_targets-Zuordnung für Kanten generieren
        code_lines.append('EDGE_SOURCE_TARGETS = {')
        for edge in ontology.get("edge_types", []):
            name = edge["name"]
            source_targets = edge.get("source_targets", [])
            if source_targets:
                st_list = ', '.join([
                    f'{{"source": "{st.get("source", "Entity")}", "target": "{st.get("target", "Entity")}"}}'
                    for st in source_targets
                ])
                code_lines.append(f'    "{name}": [{st_list}],')
        code_lines.append('}')
        
        return '\n'.join(code_lines)

