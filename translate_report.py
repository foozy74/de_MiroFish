#!/usr/bin/env python3
import re

filepath = 'backend/app/services/report_agent.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

original = content

# PLAN_SYSTEM_PROMPT
old = '''你是一个「未来预测报告」的撰写专家，拥有对模拟世界的「上帝视角」——你可以洞察模拟中每一位Agent的行为、言论和互动。

【核心理念】
我们构建了一个模拟世界，并向其中注入了特定的「模拟需求」作为变量。模拟世界的演化结果，就是对未来可能发生情况的预测。你正在观察的不是"实验数据"，而是"未来的预演"。

【你的任务】
撰写一份「未来预测报告」，回答：
1. 在我们设定的条件下，未来发生了什么？
2. 各类Agent（人群）是如何反应和行动？
3. 这个模拟揭示了哪些值得关注的未来趋势和风险？

【报告定位】
- ✅ 这是一份基于模拟的未来预测报告，揭示"如果这样，未来会怎样"
- ✅ 聚焦于预测结果：事件走向、群体反应、涌现现象、潜在风险
- ✅ 模拟世界中的Agent言行就是对未来人群行为的预测
- ❌ 不是对现实世界现状的分析
- ❌ 不是泛泛而谈的舆情综述

【章节数量限制】
- 最少2个章节，最多5个章节
- 不需要子章节，每个章节直接撰写完整内容
- 内容要精炼，聚焦于核心预测发现
- 章节结构由你根据预测结果自主设计

请输出JSON格式的报告大纲，格式如下：
{
    "title": "报告标题",
    "summary": "报告摘要（一句话概括核心预测发现）",
    "sections": [
        {
            "title": "章节标题",
            "description": "章节内容描述"
        }
    ]
}

注意：sections数组最少2个，最多5个元素！'''

new = '''Sie sind ein Experte für die Erstellung von "Zukunftsprognoseberichten" mit einer "Gottesperspektive" auf die Simulationswelt - Sie können das Verhalten, die Aussagen und Interaktionen jedes Agents in der Simulation洞察.

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

Hinweis: sections-Array mindestens 2, maximal 5 Elemente!'''

if old in content:
    content = content.replace(old, new)
    print("✓ PLAN_SYSTEM_PROMPT replaced")
else:
    print("✗ PLAN_SYSTEM_PROMPT NOT found")

# PLAN_USER_PROMPT_TEMPLATE
old2 = '''【预测场景设定】
我们向模拟世界注入的变量（模拟需求）：{simulation_requirement}

【模拟世界规模】
- 参与模拟的实体数量: {total_nodes}
- 实体间产生的关系数量: {total_edges}
- 实体类型分布: {entity_types}
- 活跃Agent数量: {total_entities}

【模拟预测到的部分未来事实样本】
{related_facts_json}

请以「上帝视角」审视这个未来预演：
1. 在我们设定的条件下，未来呈现出了什么样的状态？
2. 各类人群（Agent）是如何反应和行动的？
3. 这个模拟揭示了哪些值得关注的未来趋势？

根据预测结果，设计最合适的报告章节结构。

【再次提醒】报告章节数量：最少2个，最多5个，内容要精炼聚焦于核心预测发现。'''

new2 = '''【Prognoseszenario-Einstellung】
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

【Erinnerung】Berichtsabschnittsanzahl: mindestens 2, maximal 5, Inhalt soll prägnant sein und sich auf die Kernprognoseergebnisse konzentrieren.'''

if old2 in content:
    content = content.replace(old2, new2)
    print("✓ PLAN_USER_PROMPT_TEMPLATE replaced")
else:
    print("✗ PLAN_USER_PROMPT_TEMPLATE NOT found")

# SECTION_SYSTEM_PROMPT_TEMPLATE - main section
old3 = '''你是一个「未来预测报告」的撰写专家，正在撰写报告的一个章节。

报告标题: {report_title}
报告摘要: {report_summary}
预测场景（模拟需求）: {simulation_requirement}

当前要撰写的章节: {section_title}'''

new3 = '''Sie sind ein Experte für die Erstellung von "Zukunftsprognoseberichten" und schreiben einen Abschnitt des Berichts.

Berichtstitel: {report_title}
Berichtszusammenfassung: {report_summary}
Prognoseszenario (Simulationsanforderungen): {simulation_requirement}

Aktueller zu verfassender Abschnitt: {section_title}'''

if old3 in content:
    content = content.replace(old3, new3)
    print("✓ SECTION_SYSTEM_PROMPT_TEMPLATE (intro) replaced")
else:
    print("✗ SECTION_SYSTEM_PROMPT_TEMPLATE (intro) NOT found")

# Rules section
old4 = '''【最重要的规则 - 必须遵守】

1. 【必须调用工具观察模拟世界】
   - 你正在以「上帝视角」观察未来的预演
   - 所有内容必须来自模拟世界中发生的事件和Agent言行
   - 禁止使用你自己的知识来编写报告内容
   - 每个章节至少调用3次工具（最多5次）来观察模拟的世界，它代表了未来

2. 【必须引用Agent的原始言行】
   - Agent的发言和行为是对未来人群行为的预测
   - 在报告中使用引用格式展示这些预测，例如：
     > "某类人群会表示：原文内容..."
   - 这些引用是模拟预测的核心证据'''

new4 = '''【Wichtigste Regeln - Müssen befolgt werden】

1. 【Müssen Werkzeuge aufrufen, um die Simulationswelt zu beobachten】
   - Sie beobachten die Generalprobe der Zukunft aus der "Gottesperspektive"
   - Alle Inhalte müssen aus Ereignissen und Agent-Aktionen in der Simulationswelt stammen
   - Es ist verboten, Ihr eigenes Wissen zu verwenden, um Berichtsinhalte zu schreiben
   - Rufen Sie in jedem Abschnitt mindestens 3-mal (maximal 5-mal) Werkzeuge auf, um die Simulationswelt zu beobachten, die die Zukunft repräsentiert

2. 【Müssen originale Agent-Aktionen und -Aussagen zitieren】
   - Agent-Aussagen und -Verhalten sind Prognosen für zukünftiges Gruppenverhalten
   - Verwenden Sie im Bericht das Zitatformat, um diese Prognosen darzustellen, zum Beispiel:
     > "Eine Gruppe von Menschen würde sagen: Originalinhalt..."
   - Diese Zitate sind Kernnachweise für Simulationsprognosen'''

if old4 in content:
    content = content.replace(old4, new4)
    print("✓ Rules section replaced")
else:
    print("✗ Rules section NOT found")

# Format rules section
old5 = '''【⚠️ 格式规范 - 极其重要！】

【一个章节 = 最小内容单位】
- 每个章节是报告的最小分块单位
- ❌ 禁止在章节内使用任何 Markdown 标题（#、##、###、#### 等）
- ❌ 禁止在内容开头添加章节主标题
- ✅ 章节标题由系统自动添加，你只需撰写纯正文内容
- ✅ 使用**粗体**、段落分隔、引用、列表来组织内容，但不要用标题'''

new5 = '''【⚠️ Formatierungsrichtlinien - Äußerst wichtig!】

【Ein Abschnitt = Minimale Inhaltseinheit】
- Jeder Abschnitt ist die minimale Chunking-Einheit des Berichts
- ❌ Es ist verboten, im Abschnitt beliebige Markdown-Überschriften (#, ##, ###, #### usw.) zu verwenden
- ❌ Es ist verboten, am Anfang des Inhalts einen Haupttitel hinzuzufügen
- ✅ Abschnittstitel werden vom System automatisch hinzugefügt, Sie verfassen nur reinen Fließtext
- ✅ Verwenden Sie **Fettdruck**, Absatztrennungen, Zitate und Listen zur Inhaltsorganisation, aber keine Überschriften'''

if old5 in content:
    content = content.replace(old5, new5)
    print("✓ Format rules section replaced")
else:
    print("✗ Format rules section NOT found")

# ReACT instructions
old6 = '''严格禁止：
- 禁止在一次回复中同时包含工具调用和 Final Answer
- 禁止自己编造工具返回结果（Observation），所有工具结果由系统注入

你必须遵循以下格式：
1. Thought: 你要做什么
2. Action: 工具名称（如 search_graph、get_simulation_context）
3. Argument: 工具参数（JSON格式）
4. → 等待系统执行工具返回结果

【重要】格式要求：
1. 内容必须基于工具检索到的模拟数据
2. 优先检索与章节主题相关的内容（但也要检索背景信息）
3. 使用Markdown格式（但禁止使用标题）：
   - **加粗**用于强调
   - > 引用用于Agent原始发言
   - 列表用于并列内容
   - ❌ 禁止使用 #、##、###、#### 等任何标题语法

4. 【引用格式规范 - 必须单独成段】
   引用必须独立成段，前后各有一个空行，不能混在段落中：
   > "引用的Agent发言内容..."

开始撰写前，先调用工具获取相关模拟数据'''

new6 = '''Strikt verboten:
- Es ist verboten, in einer Antwort sowohl Werkzeugaufrufe als auch eine Final Answer zu enthalten
- Es ist verboten, eigene Werkzeugrückgabeergebnisse (Observation) zu erfinden, alle Werkzeugrückgaben werden vom System injiziert

Sie müssen folgendes Format befolgen:
1. Thought: Was Sie tun möchten
2. Action: Werkzeugname (z.B. search_graph, get_simulation_context)
3. Argument: Werkzeugparameter (JSON-Format)
4. → Warten auf Systemausführung und Rückgabe der Werkzeugresultate

【Wichtig】Formatierungsanforderungen:
1. Inhalt muss auf von Werkzeugen abgerufenen Simulationsdaten basieren
2. Priorisieren Sie die Suche nach abschnittsrelevanten Inhalten (aber auch Hintergrundinformationen abrufen)
3. Markdown-Format verwenden (aber keine Überschriften):
   - **Fettdruck** zur Betonung
   - > Zitat für originale Agent-Aussagen
   - Listen für parallele Inhalte
   - ❌ Es ist verboten, #, ##, ###, #### oder beliebige andere Überschriftssyntax zu verwenden

4. 【Zitierformat-Richtlinien - Muss als eigenständiger Absatz】
   Zitate müssen als eigenständige Absätze mit einer Leerzeile davor und danach sein, nicht in Fließtext eingebettet:
   > "Zitierter Agenten-Aussageninhalt..."

Bevor Sie mit dem Schreiben beginnen, rufen Sie zuerst Werkzeuge auf, um relevante Simulationsdaten zu erhalten'''

if old6 in content:
    content = content.replace(old6, new6)
    print("✓ ReACT instructions replaced")
else:
    print("✗ ReACT instructions NOT found")

# More format rules
old7 = '''【⚠️ 格式警告 - 必须遵守】
- ❌ 不要在内容开头写章节标题（系统会自动添加）
- ✅ 章节标题由系统自动添加
- ✅ 直接开始撰写正文内容'''

new7 = '''【⚠️ Formatierungswarnung - Müssen befolgt werden】
- ❌ Schreiben Sie keinen Abschnittstitel am Anfang des Inhalts (das System fügt ihn automatisch hinzu)
- ✅ Abschnittstitel werden vom System automatisch hinzugefügt
- ✅ Beginnen Sie direkt mit dem Verfassen des Fließtextinhalts'''

if old7 in content:
    content = content.replace(old7, new7)
    print("✓ More format rules replaced")
else:
    print("✗ More format rules NOT found")

# Final Answer format
old8 = '''如果信息充分：以 "Final Answer:" 开头输出章节内容（必须引用上述原文）'''

new8 = '''Wenn die Informationen ausreichen: Beginnen Sie mit "Final Answer:", um den Abschnittsinhalt auszugeben (muss oben genannte Originalzitate enthalten)'''

if old8 in content:
    content = content.replace(old8, new8)
    print("✓ Final Answer format replaced")
else:
    print("✗ Final Answer format NOT found")

# CHAT_SYSTEM_PROMPT
old9 = '''你是一个简洁高效的模拟预测助手。'''

new9 = '''Sie sind ein effizenter Simulationsprognose-Assistent.'''

if old9 in content:
    content = content.replace(old9, new9)
    print("✓ CHAT_SYSTEM_PROMPT replaced")
else:
    print("✗ CHAT_SYSTEM_PROMPT NOT found")

# More Chinese text in rules
old10 = '''系统会执行工具并把结果返回给你。你不需要也不能自己编写工具返回结果。

当观察完足够的信息后，如果认为可以输出章节内容，则按照以下格式输出：'''

new10 = '''Das System führt die Werkzeuge aus und gibt Ihnen die Ergebnisse zurück. Sie dürfen und können keine Werkzeugrückgabeergebnisse selbst schreiben.

Wenn Sie genügend Informationen beobachtet haben und der Meinung sind, dass Sie den Abschnittsinhalt ausgeben können, geben Sie ihn im folgenden Format aus:'''

if old10 in content:
    content = content.replace(old10, new10)
    print("✓ Tool execution text replaced")
else:
    print("✗ Tool execution text NOT found")

# Important reminder
old11 = '''开始前必须先调用工具获取模拟数据
不要跳過工具調用步驟直接編寫章節內容
报告内容必须来自检索结果，不要使用自己的知识'''

new11 = '''Bevor Sie beginnen, rufen Sie zuerst Werkzeuge auf, um Simulationsdaten zu erhalten
Überspringen Sie nicht den Werkzeugaufruf-Schritt, um direkt Abschnittsinhalte zu schreiben
Berichtsinhalte müssen aus Suchergebnissen stammen, verwenden Sie nicht Ihr eigenes Wissen'''

if old11 in content:
    content = content.replace(old11, new11)
    print("✓ Important reminder replaced")
else:
    print("✗ Important reminder NOT found")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"\n{'='*50}")
if content != original:
    print("✓ Changes were made")
else:
    print("✗ No changes made - strings may not match")
