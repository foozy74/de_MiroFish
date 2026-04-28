#!/usr/bin/env python3
import re

filepath = 'backend/app/services/oasis_profile_generator.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Replace _get_system_prompt
old_system = '''    def _get_system_prompt(self, is_individual: bool) -> str:
        """获取系统提示词"""
        base_prompt = "你是社交媒体用户画像生成专家。生成详细、真实的人设用于舆论模拟,最大程度还原已有现实情况。必须返回有效的JSON格式，所有字符串值不能包含未转义的换行符。使用中文。"
        return base_prompt'''

new_system = '''    def _get_system_prompt(self, is_individual: bool) -> str:
        """Systemprompt abrufen"""
        base_prompt = "Sie sind ein Experte für die Generierung von Social-Media-Nutzerprofilen. Erstellen Sie detaillierte, realistische Persönlichkeiten für Meinungssimulationen, die die vorhandene Realität maximieren. Geben Sie unbedingt ein gültiges JSON-Format zurück, wobei alle Zeichenkettenwerte keine nicht maskierten Zeilenumbrüche enthalten dürfen. Verwenden Sie Deutsch."
        return base_prompt'''

if old_system in content:
    content = content.replace(old_system, new_system)
    print("✓ _get_system_prompt replaced")
else:
    print("✗ _get_system_prompt NOT found")

# 2. Replace _build_individual_persona_prompt
# Using exact bytes to avoid quote issues
old_individual_raw = (
    '    def _build_individual_persona_prompt(\n'
    '        self,\n'
    '        entity_name: str,\n'
    '        entity_type: str,\n'
    '        entity_summary: str,\n'
    '        entity_attributes: Dict[str, Any],\n'
    '        context: str\n'
    '    ) -> str:\n'
    '        """构建个人实体的详细人设提示词"""\n'
    '        \n'
    '        attrs_str = json.dumps(entity_attributes, ensure_ascii=False) if entity_attributes else "无"\n'
    '        context_str = context[:3000] if context else "无额外上下文"\n'
    '        \n'
    '        return f"""为实体生成详细的社交媒体用户人设,最大程度还原已有现实情况。\n'
    '\n'
    '实体名称: {entity_name}\n'
    '实体类型: {entity_type}\n'
    '实体摘要: {entity_summary}\n'
    '实体属性: {attrs_str}\n'
    '\n'
    '上下文信息:\n'
    '{context_str}\n'
    '\n'
    '请生成JSON，包含以下字段:\n'
    '\n'
    '1. bio: 社交媒体简介，200字\n'
    '2. persona: 详细人设描述（2000字的纯文本），需包含:\n'
    '   - 基本信息（年龄、职业、教育背景、所在地）\n'
    '   - 人物背景（重要经历、与事件的关联、社会关系）\n'
    '   - 性格特征（MBTI类型、核心性格、情绪表达方式）\n'
    '   - 社交媒体行为（发帖频率、内容偏好、互动风格、语言特点）\n'
    '   - 立场观点（对话题的态度、可能被激怒/感动的内容）\n'
    '   - 独特特征（口头禅、特殊经历、个人爱好）\n'
    '   - 个人记忆（人设的重要部分，要介绍这个个体与事件的关联，以及这个个体在事件中的已有动作与反应）\n'
    '3. age: 年龄数字（必须是整数）\n'
    '4. gender: 性别，必须是英文: "male" 或 "female"\n'
    '5. mbti: MBTI类型（如INTJ、ENFP等）\n'
    '6. country: 国家（使用中文，如"中国"）\n'
    '7. profession: 职业\n'
    '8. interested_topics: 感兴趣话题数组\n'
    '\n'
    '重要:\n'
    '- 所有字段值必须是字符串或数字，不要使用换行符\n'
    '- persona必须是一段连贯的文字描述\n'
    '- 使用中文（除了gender字段必须用英文male/female）\n'
    '- 内容要与实体信息保持一致\n'
    '- age必须是有效的整数，gender必须是"male"或"female"\n'
    '"""'
)

new_individual_raw = (
    '    def _build_individual_persona_prompt(\n'
    '        self,\n'
    '        entity_name: str,\n'
    '        entity_type: str,\n'
    '        entity_summary: str,\n'
    '        entity_attributes: Dict[str, Any],\n'
    '        context: str\n'
    '    ) -> str:\n'
    '        """Erstellen Sie einen detaillierten Persona-Prompt für einzelne Entitäten"""\n'
    '        \n'
    '        attrs_str = json.dumps(entity_attributes, ensure_ascii=False) if entity_attributes else "Keine"\n'
    '        context_str = context[:3000] if context else "Keine zusätzlichen Kontextinformationen"\n'
    '        \n'
    '        return f"""Generieren Sie ein detailliertes Social-Media-Nutzerprofil für die Entität, das die vorhandene Realität maximiert.\n'
    '\n'
    'Entitätsname: {entity_name}\n'
    'Entitätstyp: {entity_type}\n'
    'Entitätszusammenfassung: {entity_summary}\n'
    'Entitätsattribute: {attrs_str}\n'
    '\n'
    'Kontextinformationen:\n'
    '{context_str}\n'
    '\n'
    'Bitte generieren Sie JSON mit folgenden Feldern:\n'
    '\n'
    '1. bio: Social-Media-Biografie, 200 Zeichen\n'
    '2. persona: Detaillierte Persönlichkeitsbeschreibung (2000 Zeichen Fließtext), muss enthalten:\n'
    '   - Grundlegende Informationen (Alter, Beruf, Bildungs background, Standort)\n'
    '   - Persönlicher Hintergrund (wichtige Erfahrungen, Verbindung zum Ereignis, soziale Beziehungen)\n'
    '   - Persönlichkeitsmerkmale (MBTI-Typ, Kernpersönlichkeit, Artikulationsstil)\n'
    '   - Social-Media-Verhalten (Beitragshäufigkeit, Inhaltspräferenzen, Interaktionsstil, Sprachmerkmale)\n'
    '   - Standpunkte und Meinungen (Einstellung zum Thema, Inhalte die sie aufregen/begeistern könnten)\n'
    '   - Besondere Merkmale (Sprachgewohnheiten, besondere Erfahrungen, persönliche Hobbys)\n'
    '   - Persönliche Erinnerungen (wichtiger Teil der Persona, muss die Verbindung dieser Person zum Ereignis beschreiben, sowie bereits stattgefundene Handlungen und Reaktionen dieser Person während des Ereignisses)\n'
    '3. age: Alterszahl (muss eine Ganzzahl sein)\n'
    '4. gender: Geschlecht, muss auf Englisch sein: "male" oder "female"\n'
    '5. mbti: MBTI-Typ (z.B. INTJ, ENFP usw.)\n'
    '6. country: Land (auf Deutsch, z.B. "Deutschland")\n'
    '7. profession: Beruf\n'
    '8. interested_topics: Array von interessanten Themen\n'
    '\n'
    'Wichtig:\n'
    '- Alle Feldwerte müssen Zeichenketten oder Zahlen sein, keine Zeilenumbrüche verwenden\n'
    '- persona muss eine zusammenhängende Textbeschreibung sein\n'
    '- Deutsch verwenden (außer für das gender-Feld, das Englisch male/female verwenden muss)\n'
    '- Inhalt muss mit den Entitätsinformationen übereinstimmen\n'
    '- age muss eine gültige Ganzzahl sein, gender muss "male" oder "female" sein\n'
    '"""'
)

if old_individual_raw in content:
    content = content.replace(old_individual_raw, new_individual_raw)
    print("✓ _build_individual_persona_prompt replaced")
else:
    print("✗ _build_individual_persona_prompt NOT found")

# 3. Replace _build_group_persona_prompt
old_group_raw = (
    '    def _build_group_persona_prompt(\n'
    '        self,\n'
    '        entity_name: str,\n'
    '        entity_type: str,\n'
    '        entity_summary: str,\n'
    '        entity_attributes: Dict[str, Any],\n'
    '        context: str\n'
    '    ) -> str:\n'
    '        """构建群体/机构实体的详细人设提示词"""\n'
    '        \n'
    '        attrs_str = json.dumps(entity_attributes, ensure_ascii=False) if entity_attributes else "无"\n'
    '        context_str = context[:3000] if context else "无额外上下文"\n'
    '        \n'
    '        return f"""为机构/群体实体生成详细的社交媒体账号设定,最大程度还原已有现实情况。\n'
    '\n'
    '实体名称: {entity_name}\n'
    '实体类型: {entity_type}\n'
    '实体摘要: {entity_summary}\n'
    '实体属性: {attrs_str}\n'
    '\n'
    '上下文信息:\n'
    '{context_str}\n'
    '\n'
    '请生成JSON，包含以下字段:\n'
    '\n'
    '1. bio: 官方账号简介，200字，专业得体\n'
    '2. persona: 详细账号设定描述（2000字的纯文本），需包含:\n'
    '   - 机构基本信息（正式名称、机构性质、成立背景、主要职能）\n'
    '   - 账号定位（账号类型、目标受众、核心功能）\n'
    '   - 发言风格（语言特点、常用表达、禁忌话题）\n'
    '   - 发布内容特点（内容类型、发布频率、活跃时间段）\n'
    '   - 立场态度（对核心话题的官方立场、面对争议的处理方式）\n'
    '   - 特殊说明（代表的群体画像、运营习惯）\n'
    '   - 机构记忆（机构人设的重要部分，要介绍这个机构与事件的关联，以及这个机构在事件中的已有动作与反应）\n'
    '3. age: 固定填30（机构账号的虚拟年龄）\n'
    '4. gender: 固定填"other"（机构账号使用other表示非个人）\n'
    '5. mbti: MBTI类型，用于描述账号风格，如ISTJ代表严谨保守\n'
    '6. country: 国家（使用中文，如"中国"）\n'
    '7. profession: 机构职能描述\n'
    '8. interested_topics: 关注领域数组\n'
    '\n'
    '重要:\n'
    '- 所有字段值必须是字符串或数字，不允许null值\n'
    '- persona必须是一段连贯的文字描述，不要使用换行符\n'
    '- 使用中文（除了gender字段必须用英文"other"）\n'
    '- age必须是整数30，gender必须是字符串"other"\n'
    '- 机构账号发言要符合其身份定位"""'
)

new_group_raw = (
    '    def _build_group_persona_prompt(\n'
    '        self,\n'
    '        entity_name: str,\n'
    '        entity_type: str,\n'
    '        entity_summary: str,\n'
    '        entity_attributes: Dict[str, Any],\n'
    '        context: str\n'
    '    ) -> str:\n'
    '        """Erstellen Sie einen detaillierten Persona-Prompt für Gruppen-/Institutional-Entitäten"""\n'
    '        \n'
    '        attrs_str = json.dumps(entity_attributes, ensure_ascii=False) if entity_attributes else "Keine"\n'
    '        context_str = context[:3000] if context else "Keine zusätzlichen Kontextinformationen"\n'
    '        \n'
    '        return f"""Generieren Sie ein detailliertes Social-Media-Konto für institutionelle Gruppierungen, das die vorhandene Realität maximiert.\n'
    '\n'
    'Entitätsname: {entity_name}\n'
    'Entitätstyp: {entity_type}\n'
    'Entitätszusammenfassung: {entity_summary}\n'
    'Entitätsattribute: {attrs_str}\n'
    '\n'
    'Kontextinformationen:\n'
    '{context_str}\n'
    '\n'
    'Bitte generieren Sie JSON mit folgenden Feldern:\n'
    '\n'
    '1. bio: Offizielle Kontobiografie, 200 Zeichen, professionell und angemessen\n'
    '2. persona: Detaillierte Kontodarstellung (2000 Zeichen Fließtext), muss enthalten:\n'
    '   - Grundlegende Institutsinformationen (offizieller Name, Art der Institution, Gründungshintergrund, Hauptfunktionen)\n'
    '   - Konto-Positionierung (Kontotyp, Zielgruppe, Kernfunktionen)\n'
    '   - Sprechstil (Sprachmerkmale, häufig verwendete Ausdrücke, Tabuthemen)\n'
    '   - Merkmale der veröffentlichten Inhalte (Inhaltstypen, Veröffentlichungshäufigkeit, aktive Zeiträume)\n'
    '   - Standpunkte und Haltungen (offizielle Position zu Kernthemen, Umgang mit Kontroversen)\n'
    '   - Besondere Hinweise (dargestellte Gruppenprofile, Betriebsgewohnheiten)\n'
    '   - Institutionelle Erinnerungen (wichtiger Teil der Persona, muss die Verbindung dieser Institution zum Ereignis beschreiben, sowie bereits stattgefundene Handlungen und Reaktionen dieser Institution während des Ereignisses)\n'
    '3. age: Immer 30 (virtuelles Alter des Institutionenkontos)\n'
    '4. gender: Immer "other" (Institutionenkonten verwenden "other" für Nicht-Personen)\n'
    '5. mbti: MBTI-Typ zur Beschreibung des Kontostils, z.B. ISTJ für seriös und konservativ\n'
    '6. country: Land (auf Deutsch, z.B. "Deutschland")\n'
    '7. profession: Beschreibung der institutionellen Funktion\n'
    '8. interested_topics: Array der interessierten Bereiche\n'
    '\n'
    'Wichtig:\n'
    '- Alle Feldwerte müssen Zeichenketten oder Zahlen sein, keine Nullwerte erlaubt\n'
    '- persona muss eine zusammenhängende Textbeschreibung sein, keine Zeilenumbrüche verwenden\n'
    '- Deutsch verwenden (außer für das gender-Feld, das Englisch "other" verwenden muss)\n'
    '- age muss die Ganzzahl 30 sein, gender muss die Zeichenkette "other" sein\n'
    '- Institutionelle Konten müssen in ihrem Identitätsdesignat sprechen"""'
)

if old_group_raw in content:
    content = content.replace(old_group_raw, new_group_raw)
    print("✓ _build_group_persona_prompt replaced")
else:
    print("✗ _build_group_persona_prompt NOT found")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("\nDone! Checking syntax...")
