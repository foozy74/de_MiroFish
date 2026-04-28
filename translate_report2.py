#!/usr/bin/env python3
"""
Translate report_agent.py Chinese text to German.
Uses exact string matching to avoid breaking f-strings.
"""

FILE_PATH = "/Users/jurgen/dev/thesolution/github/der_fish/de_MiroFish/backend/app/services/report_agent.py"

with open(FILE_PATH, 'r', encoding='utf-8') as f:
    content = f.read()

# Dictionary of Chinese -> German translations
# Organized by section for clarity

translations = {
    # === MODULE DOCSTRING ===
    '"""Report Agent服务\n使用LangChain + Zep实现ReACT模式的模拟报告生成\n\n功能：\n1. 根据模拟需求和Zep图谱信息生成报告\n2. 先规划目录结构，然后分段生成\n3. 每段采用ReACT多轮思考与反思模式\n4. 支持与用户对话，在对话中自主调用检索工具\n"""':
    '"""Report Agent-Dienst\nBerichterstattung mit LangChain + Zep im ReACT-Modus\n\nFunktionen:\n1. Berichte basierend auf Simulationsanforderungen und Zep-Graph-Informationen generieren\n2. Zuerst die Gliederungsstruktur planen, dann abschnittsweise generieren\n3. Jeder Abschnitt verwendet ReACT-Multi-Runden-Denk- und Reflexionsmodus\n4. Dialog mit Benutzern unterstützen, dabei autonom Suchwerkzeuge aufrufen\n"""',

    # === ReportLogger CLASS DOCSTRING ===
    '"""Report Agent 详细日志记录器\n    \n    在报告文件夹中生成 agent_log.jsonl 文件，记录每一步详细动作。\n    每行是一个完整的 JSON 对象，包含时间戳、动作类型、详细内容等。\n    """':
    '"""Detaillierter Protokollierer für den Report Agent\n    \n    Erstellt eine agent_log.jsonl-Datei im Berichtsordner, die jeden Schritt detailliert aufzeichnet.\n    Jede Zeile ist ein vollständiges JSON-Objekt mit Zeitstempel, Aktionstyp, detaillierten Inhalten usw.\n    """',

    # === __init__ docstring ===
    '"""初始化日志记录器\n        \n        Args:\n            report_id: 报告ID，用于确定日志文件路径\n        """':
    '"""Protokollierer initialisieren\n        \n        Args:\n            report_id: Berichts-ID zur Bestimmung des Protokolldateipfads\n        """',

    # === _ensure_log_file ===
    '"""确保日志文件所在目录存在"""':
    '"""Stellt sicher, dass das Protokollverzeichnis existiert"""',

    # === _get_elapsed_time ===
    '"""获取从开始到现在的耗时（秒）"""':
    '"""Gibt die seit dem Start vergangene Zeit in Sekunden zurück"""',

    # === log method docstring ===
    '"""记录一条日志\n        \n        Args:\n            action: 动作类型，如 \'start\', \'tool_call\', \'llm_response\', \'section_complete\' 等\n            stage: 当前阶段，如 \'planning\', \'generating\', \'completed\'\n            details: 详细内容字典，不截断\n            section_title: 当前章节标题（可选）\n            section_index: 当前章节索引（可选）\n        """':
    '"""Einen Protokolleintrag aufzeichnen\n        \n        Args:\n            action: Aktionstyp wie \'start\', \'tool_call\', \'llm_response\', \'section_complete\' usw.\n            stage: Aktuelle Phase wie \'planning\', \'generating\', \'completed\'\n            details: Detailliertes Inhaltswörterbuch, ohne Kürzung\n            section_title: Aktueller Abschnittstitel (optional)\n            section_index: Aktueller Abschnittsindex (optional)\n        """',

    # === comment about appending ===
    '# 追加写入 JSONL 文件':
    '# JSONL-Datei im Append-Modus schreiben',

    # === log_start ===
    '"""记录报告生成开始"""':
    '"""Zeichnet den Berichtsgenerierungsstart auf"""',

    '"message": "报告生成任务开始"':
    '"message": "Berichtsgenerierungsaufgabe gestartet"',

    # === log_planning_start ===
    '"""记录大纲规划开始"""':
    '"""Zeichnet den Start der Gliederungsplanung auf"""',

    '"message": "开始规划报告大纲"':
    '"message": "Beginne mit der Planung der Berichtsgliederung"',

    # === log_planning_context ===
    '"""记录规划时获取的上下文信息"""':
    '"""Zeichnet die bei der Planung erhaltenen Kontextinformationen auf"""',

    '"message": "获取模拟上下文信息"':
    '"message": "Simulationskontextinformationen abrufen"',

    # === log_planning_complete ===
    '"""记录大纲规划完成"""':
    '"""Zeichnet den Abschluss der Gliederungsplanung auf"""',

    '"message": "大纲规划完成"':
    '"message": "Gliederungsplanung abgeschlossen"',

    # === log_section_start ===
    '"""记录章节生成开始"""':
    '"""Zeichnet den Start der Abschnittsgenerierung auf"""',

    # === log_react_thought ===
    '"""记录 ReACT 思考过程"""':
    '"""Zeichnet den ReACT-Denkprozess auf"""',

    # === log_tool_call ===
    '"""记录工具调用"""':
    '"""Zeichnet Werkzeugaufrufe auf"""',

    # === log_tool_result ===
    '"""记录工具调用结果（完整内容，不截断）"""':
    '"""Zeichnet Werkzeugrückgabeergebnisse auf (vollständiger Inhalt, nicht gekürzt)"""',

    # === log_llm_response ===
    '"""记录 LLM 响应（完整内容，不截断）"""':
    '"""Zeichnet LLM-Antworten auf (vollständiger Inhalt, nicht gekürzt)"""',

    # === log_section_content ===
    '"""记录章节内容生成完成（仅记录内容，不代表整个章节完成）"""':
    '"""Zeichnet den Abschluss der Abschnittsinhaltsgenerierung auf (nur Inhalt, nicht den gesamten Abschnitt)"""',

    # === log_section_full_complete ===
    '"""记录章节生成完成\n\n        前端应监听此日志来判断一个章节是否真正完成，并获取完整内容\n        """':
    '"""Zeichnet den Abschluss der Abschnittsgenerierung auf\n\n        Das Frontend sollte dieses Protokoll überwachen, um zu bestimmen, ob ein Abschnitt wirklich abgeschlossen ist, und den vollständigen Inhalt abrufen\n        """',

    # === log_report_complete ===
    '"""记录报告生成完成"""':
    '"""Zeichnet den Abschluss der Berichtsgenerierung auf"""',

    # === log_error ===
    '"""记录错误"""':
    '"""Fehler aufzeichnen"""',

    # === ReportConsoleLogger CLASS ===
    '"""Report Agent 控制台日志记录器\n    \n    将控制台风格的日志（INFO、WARNING等）写入报告文件夹中的 console_log.txt 文件。\n    这些日志与 agent_log.jsonl 不同，是纯文本格式的控制台输出。\n    """':
    '"""Konsolenprotokollierer für den Report Agent\n    \n    Schreibt konsolenähnliche Protokolle (INFO, WARNING usw.) in die Datei console_log.txt im Berichtsordner.\n    Diese Protokolle unterscheiden sich von agent_log.jsonl und sind unformatierte Konsolenausgaben.\n    """',

    '"""初始化控制台日志记录器\n        \n        Args:\n            report_id: 报告ID，用于确定日志文件路径\n        """':
    '"""Konsolenprotokollierer initialisieren\n        \n        Args:\n            report_id: Berichts-ID zur Bestimmung des Protokolldateipfads\n        """',

    # === ReportStatus ===
    '"""报告状态"""':
    '"""Berichtsstatus"""',

    # === ReportSection ===
    '"""报告章节"""':
    '"""Berichtsabschnitt"""',

    '"""转换为Markdown格式"""':
    '"""In Markdown-Format konvertieren"""',

    # === ReportOutline ===
    '"""报告大纲"""':
    '"""Berichtsgliederung"""',

    # === Report ===
    '"""完整报告"""':
    '"""Vollständiger Bericht"""',

    # === SECTION_SYSTEM_PROMPT_TEMPLATE - Core ideas section ===
    '模拟世界是对未来的预演。我们向模拟世界注入了特定条件（模拟需求），\n模拟中Agent的行为和互动，就是对未来人群行为的预测。\n\n你的任务是：\n- 揭示在设定条件下，未来发生了什么\n- 预测各类人群（Agent）是如何反应和行动的\n- 发现值得关注的未来趋势、风险和机会':
    'Die Simulationswelt ist eine Generalprobe der Zukunft. Wir haben spezifische Bedingungen (Simulationsanforderungen) in die Simulationswelt injiziert.\nDas Verhalten und die Interaktionen der Agents in der Simulation sind Vorhersagen für das zukünftige Gruppenverhalten.\n\nIhre Aufgabe:\n- Aufzeigen, was unter den festgelegten Bedingungen in der Zukunft passiert ist\n- Vorhersagen, wie verschiedene Gruppen (Agents) reagiert und gehandelt haben\n- Bemerkenswerte Zukunftstrends, Risiken und Chancen identifizieren',

    '❌ 不要写成对现实世界现状的分析':
    '❌ Dies ist keine Analyse des aktuellen Zustands der realen Welt',

    '✅ 要聚焦于"未来会怎样"——模拟结果就是预测的未来':
    '✅ Fokus auf "wie die Zukunft aussehen wird" - Simulationsergebnisse sind die vorhergesagte Zukunft',

    # === SECTION_SYSTEM_PROMPT_TEMPLATE - Rules section ===
    '【一个章节 = 最小内容单位】\n- 每个章节是报告的最小分块单位\n- ❌ 禁止在章节内使用任何 Markdown 标题（#、##、###、#### 等）\n- ❌ 禁止在内容开头添加章节主标题\n- ✅ 章节标题由系统自动添加，你只需撰写纯正文内容\n- ✅ 使用**粗体**、段落分隔、引用、列表来组织内容，但不要用标题':
    '【Ein Abschnitt = Minimale Inhaltseinheit】\n- Jeder Abschnitt ist die kleinste Chunk-Einheit des Berichts\n- ❌ Es ist verboten, beliebige Markdown-Überschriften (#, ##, ###, #### usw.) im Abschnitt zu verwenden\n- ❌ Es ist verboten, am Anfang des Inhalts den Haupttitel des Abschnitts hinzuzufügen\n- ✅ Abschnittstitel werden vom System automatisch hinzugefügt, Sie schreiben nur reinen Fließtext\n- ✅ Verwenden Sie **Fettdruck**, Absatztrennungen, Zitate und Listen zur Inhaltsorganisation, aber keine Überschriften',

    # === Section content requirements ===
    '1. 内容必须基于工具检索到的模拟数据\n2. 大量引用原文来展示模拟效果\n3. 使用Markdown格式（但禁止使用标题）：\n   - 使用 **粗体文字** 标记重点（代替子标题）\n   - 使用列表（-或1.2.3.）组织要点\n   - 使用空行分隔不同段落\n   - ❌ 禁止使用 #、##、###、#### 等任何标题语法\n4. 【引用格式规范 - 必须单独成段】\n   引用必须独立成段，前后各有一个空行，不能混在段落中：\n\n   ✅ 正确格式：\n   ```\n   校方的回应被认为缺乏实质内容。\n\n   > "校方的应对模式在瞬息万变的社交媒体环境中显得僵化和迟缓。"\n\n   这一评价反映了公众的普遍不满。\n   ```\n\n   ❌ 错误格式：\n   ```\n   校方的回应被认为缺乏实质内容。> "校方的应对模式..." 这一评价反映了...\n   ```\n5. 保持与其他章节的逻辑连贯性\n6. 【避免重复】仔细阅读下方已完成的章节内容，不要重复描述相同的信息\n7. 【再次强调】不要添加任何标题！用**粗体**代替小节标题':
    '1. Inhalt muss auf simulationsdaten basieren, die durch Werkzeugsuche abgerufen wurden\n2. Reichhaltig Originalzitate verwenden, um Simulationseffekte zu demonstrieren\n3. Markdown-Format verwenden (aber keine Überschriften verwenden):\n   - **Fettformatierung** verwenden, um Schwerpunkte zu markieren (ersetzt Unterabschnittstitel)\n   - Listen (- oder 1.2.3.) verwenden, um Punkte zu organisieren\n   - Leerzeilen verwenden, um verschiedene Absätze zu trennen\n   - ❌ Es ist verboten, beliebige Überschriftssyntax wie #, ##, ###, #### usw. zu verwenden\n4. 【Zitatformat-Spezifikation - Muss als eigener Absatz sein】\n   Zitate müssen als eigenständige Absätze verfasst werden, mit einer Leerzeile davor und danach, und dürfen nicht in Absätze eingebettet sein:\n\n   ✅ Korrektes Format:\n   ```\n   Die Antwort der Universitätsleitung wurde als substanzarm eingestuft.\n\n   > "Das Reaktionsmuster der Universitätsleitung wirkte starr und verzögert im schnelllebigen Social-Media-Umfeld."\n\n   Diese Bewertung spiegelt die allgemeine Unzufriedenheit der Öffentlichkeit wider.\n   ```\n\n   ❌ Falsches Format:\n   ```\n   Die Antwort der Universitätsleitung wurde als substanzarm eingestuft.> "Das Reaktionsmuster..." Diese Bewertung spiegelt...\n   ```\n5. Logische Kohärenz mit anderen Abschnitten beibehalten\n6. 【Wiederholung vermeiden】Lesen Sie die unten abgeschlossenen Abschnitte sorgfältig durch und wiederholen Sie nicht dieselben Informationen\n7. 【Erneute Betonung】Keine Überschriften hinzufügen! Verwenden Sie **Fettdruck** anstelle von Unterabschnittstiteln',

    # === REACT Observation template ===
    'Observation（检索结果）:\n\n═══ 工具 {tool_name} 返回 ═══\n{result}\n\n═══════════════════════════════════════════════════════════════\n已调用工具 {tool_calls_count}/{max_tool_calls} 次（已用: {used_tools_str}）{unused_hint}\n- Wenn die Informationen ausreichen: Beginnen Sie mit "Final Answer:", um den Abschnittsinhalt auszugeben (muss oben genannte Originalzitate enthalten)\n- 如果需要更多信息：调用一个工具继续检索\n═══════════════════════════════════════════════════════════════':
    'Observation（Suchergebnisse）:\n\n═══ Werkzeug {tool_name} zurückgegeben ═══\n{result}\n\n═══════════════════════════════════════════════════════════════\nWerkzeuge {tool_calls_count}/{max_tool_calls} mal aufgerufen (verwendet: {used_tools_str}) {unused_hint}\n- Wenn die Informationen ausreichen: Beginnen Sie mit "Final Answer:", um den Abschnittsinhalt auszugeben (muss oben genannte Originalzitate enthalten)\n- Wenn mehr Informationen benötigt werden: Rufen Sie ein Werkzeug auf, um die Suche fortzusetzen\n═══════════════════════════════════════════════════════════════',

    # === REACT_INSUFFICIENT_TOOLS_MSG_ALT ===
    '"当前只调用了 {tool_calls_count} 次工具，至少需要 {min_tool_calls} 次。\n请调用工具获取模拟数据。{unused_hint}"':
    '"Bisher wurden nur {tool_calls_count} Werkzeuge aufgerufen, mindestens {min_tool_calls} sind erforderlich.\nBitte rufen Sie Werkzeuge auf, um Simulationsdaten zu erhalten. {unused_hint}"',

    # === REACT_TOOL_LIMIT_MSG ===
    '"工具调用次数已达上限（{tool_calls_count}/{max_tool_calls}），不能再调用工具。\n\'请立即基于已获取的信息，以 "Final Answer:" 开头输出章节内容。\'"':
    '"Die Anzahl der Werkzeugaufrufe hat das Limit erreicht ({tool_calls_count}/{max_tool_calls}), es können keine weiteren Werkzeuge aufgerufen werden.\n\'Bitte geben Sie sofort basierend auf den erhaltenen Informationen den Abschnittsinhalt aus, beginnend mit "Final Answer:".\'"',

    # === REACT_UNUSED_TOOLS_HINT ===
    '"\\n💡 你还没有使用过: {unused_list}，建议尝试不同工具获取多角度信息"':
    '"\\n💡 Sie haben noch nicht verwendet: {unused_list}, es wird empfohlen, verschiedene Werkzeuge zu verwenden, um Informationen aus mehrPerspektiven zu erhalten"',

    # === REACT_FORCE_FINAL_MSG ===
    '"已达到工具调用限制，请直接输出 Final Answer: 并生成章节内容。"':
    '"Die Werkzeugaufrufbeschränkung wurde erreicht, bitte geben Sie direkt Final Answer: aus und generieren Sie den Abschnittsinhalt."',

    # === CHAT_OBSERVATION_SUFFIX ===
    '"\n\n请简洁回答问题。"':
    '"\n\nBitte beantworten Sie die Frage prägnant."',

    # === ReportAgent CLASS ===
    '"""Report Agent - 模拟报告生成Agent\n\n    采用ReACT（Reasoning + Acting）模式：\n    1. 规划阶段：分析模拟需求，规划报告目录结构\n    2. 生成阶段：逐章节生成内容，每章节可多次调用工具获取信息\n    3. 反思阶段：检查内容完整性和准确性\n    """':
    '"""Report Agent - Simulationsbericht-Generierungs-Agent\n\n    Verwendet den ReACT（Reasoning + Acting）-Modus:\n    1. Planungsphase: Simulationsanforderungen analysieren, Berichtsgliederungsstruktur planen\n    2. Generierungsphase: Inhalt abschnittsweise generieren, jeder Abschnitt kann mehrmals Werkzeuge aufrufen\n    3. Reflexionsphase: Inhaltsvollständigkeit und -genauigkeit überprüfen\n    """',

    '"""初始化Report Agent\n        \n        Args:\n            graph_id: 图谱ID\n            simulation_id: 模拟ID\n            simulation_requirement: 模拟需求描述\n            llm_client: LLM客户端（可选）\n            zep_tools: Zep工具服务（可选）\n        """':
    '"""Report Agent initialisieren\n        \n        Args:\n            graph_id: Graph-ID\n            simulation_id: Simulations-ID\n            simulation_requirement: Simulationsanforderungsbeschreibung\n            llm_client: LLM-Client (optional)\n            zep_tools: Zep-Werkzeugdienst (optional)\n        """',

    # === _execute_tool ===
    '"""执行工具调用\n        \n        Args:\n            tool_name: 工具名称\n            parameters: 工具参数\n            report_context: 报告上下文（用于InsightForge）\n            \n        Returns:\n            工具执行结果（文本格式）\n        """':
    '"""Werkzeugaufruf ausführen\n        \n        Args:\n            tool_name: Werkzeugname\n            parameters: Werkzeugparameter\n            report_context: Berichtskontext (für InsightForge)\n            \n        Returns:\n            Werkzeugausführungsergebnis (Textformat)\n        """',

    # === error messages ===
    '"未知工具: {tool_name}。请使用以下工具之一: insight_forge, panorama_search, quick_search"':
    '"Unbekanntes Werkzeug: {tool_name}. Bitte verwenden Sie eines der folgenden Werkzeuge: insight_forge, panorama_search, quick_search"',

    '"工具执行失败: {str(e)}"':
    '"Werkzeugausführung fehlgeschlagen: {str(e)}"',

    # === fallback titles ===
    '"模拟分析报告"':
    '"Simulationsanalysebericht"',

    '"未来预测报告"':
    '"Zukunftsprognosebericht"',

    '"基于模拟预测的未来趋势与风险分析"':
    '"Zukünftige Trends und Risikoanalyse basierend auf Simulationsvorhersagen"',

    '"预测场景与核心发现"':
    '"Prognoseszenario und Kernerkenntnisse"',

    '"人群行为预测分析"':
    '"Analyse der Gruppenverhaltensvorhersage"',

    '"趋势展望与风险提示"':
    '"Trendprognose und Risikohinweise"',

    # === plan_outline ===
    '"""规划报告大纲\n        \n        使用LLM分析模拟需求，规划报告的目录结构\n        \n        Args:\n            progress_callback: 进度回调函数\n            \n        Returns:\n            ReportOutline: 报告大纲\n        """':
    '"""Berichtsgliederung planen\n        \n        LLM verwenden, um Simulationsanforderungen zu analysieren und die Berichtsverzeichnisstruktur zu planen\n        \n        Args:\n            progress_callback: Fortschrittsrückruffunktion\n            \n        Returns:\n            ReportOutline: Berichtsgliederung\n        """',

    'progress_callback("planning", 0, "正在分析模拟需求...")':
    'progress_callback("planning", 0, "Analysiere Simulationsanforderungen...")',

    'progress_callback("planning", 30, "正在生成报告大纲...")':
    'progress_callback("planning", 30, "Generiere Berichtsgliederung...")',

    'progress_callback("planning", 80, "正在解析大纲结构...")':
    'progress_callback("planning", 80, "Analysiere Gliederungsstruktur...")',

    'progress_callback("planning", 100, "大纲规划完成")':
    'progress_callback("planning", 100, "Gliederungsplanung abgeschlossen")',

    # === _generate_section_react ===
    '"""使用ReACT模式生成单个章节内容\n        \n        ReACT循环：\n        1. Thought（思考）- 分析需要什么信息\n        2. Action（行动）- 调用工具获取信息\n        3. Observation（观察）- 分析工具返回结果\n        4. 重复直到信息足够或达到最大次数\n        5. Final Answer（最终回答）- 生成章节内容\n        \n        Args:\n            section: 要生成的章节\n            outline: 完整大纲\n            previous_sections: 之前章节的内容（用于保持连贯性）\n            progress_callback: 进度回调\n            section_index: 章节索引（用于日志记录）\n            \n        Returns:\n            章节内容（Markdown格式）\n        """':
    '"""Einzelnen Abschnittsinhalt im ReACT-Modus generieren\n        \n        ReACT-Schleife:\n        1. Thought（Denken）- Analysieren, welche Informationen benötigt werden\n        2. Action（Handeln）- Werkzeuge aufrufen, um Informationen zu erhalten\n        3. Observation（Beobachten）- Werkzeugrückgabeergebnisse analysieren\n        4. Wiederholen, bis genügend Informationen vorhanden sind oder das Maximum erreicht wird\n        5. Final Answer（Endgültige Antwort）- Abschnittsinhalt generieren\n        \n        Args:\n            section: Zu generierender Abschnitt\n            outline: Vollständige Gliederung\n            previous_sections: Inhalt der vorherigen Abschnitte (zur Aufrechterhaltung der Kohärenz)\n            progress_callback: Fortschrittsrückruf\n            section_index: Abschnittsindex (für Protokollierung)\n            \n        Returns:\n            Abschnittsinhalt (Markdown-Format)\n        """',

    # === previous_content default ===
    '"（这是第一个章节）"':
    '"（Dies ist der erste Abschnitt）"',

    # === max iterations comment ===
    '# 最大迭代轮数':
    '# Maximale Iterationsrunden',

    # === min tool calls comment ===
    '# 最少工具调用次数':
    '# Minimale Werkzeugaufrufanzahl',

    # === conflict retries comment ===
    '# 工具调用与Final Answer同时出现的连续冲突次数':
    '# Anzahl der aufeinanderfolgenden Konflikte, bei denen Werkzeugaufrufe und Final Answer gleichzeitig auftreten',

    # === report context ===
    '# 报告上下文，用于InsightForge的子问题生成':
    '# Berichtskontext für die Unterfragen-Generierung von InsightForge',

    # === check LLM response ===
    '# 检查 LLM 返回是否为 None（API 异常或内容为空）':
    '# Überprüfen, ob LLM None zurückgibt (API-Ausnahme oder leerer Inhalt)',

    '"（响应为空）"':
    '"（Antwort ist leer）"',

    '"请继续生成内容。"':
    '"Bitte fahren Sie mit der Inhaltsgenerierung fort."',

    # === conflict handling ===
    '# ── 冲突处理：LLM 同时输出了工具调用和 Final Answer ──':
    '# ── Konfliktbehandlung: LLM hat sowohl Werkzeugaufrufe als auch Final Answer ausgegeben ──',

    '"【格式错误】你在一次回复中同时包含了工具调用和 Final Answer，这是不允许的。\n"\n                        "每次回复只能做以下两件事之一：\n"\n                        "- 调用一个工具（输出一个 <tool_call> 块，不要写 Final Answer）\n"\n                        "- 输出最终内容（以 \'Final Answer:\' 开头，不要包含 <tool_call>）\n"\n                        "请重新回复，只做其中一件事。"':
    '"【Formatfehler】Sie haben in einer Antwort sowohl Werkzeugaufrufe als auch Final Answer enthalten, was nicht erlaubt ist.\n"\n                        "In jeder Antwort darf nur eines von zwei Dingen getan werden:\n"\n                        "- Ein Werkzeug aufrufen (ein <tool_call>-Block ausgeben, Final Answer nicht schreiben)\n"\n                        "- Endgültigen Inhalt ausgeben (beginnend mit \'Final Answer:\', kein <tool_call> enthalten)\n"\n                        "Bitte antworten Sie erneut und tun Sie nur eines davon."',

    # === 情况 comments ===
    '# ── 情况1：LLM 输出了 Final Answer ──':
    '# ── Fall 1: LLM hat Final Answer ausgegeben ──',

    '# 工具调用次数不足，拒绝并要求继续调工具':
    '# Unzureichende Werkzeugaufrufe, ablehnen und fortfahren Werkzeuge aufrufen lassen',

    '# 正常结束':
    '# Normaler Abschluss',

    '# ── 情况2：LLM 尝试调用工具 ──':
    '# ── Fall 2: LLM versucht Werkzeuge aufzurufen ──',

    '# 工具额度已耗尽 → 明确告知，要求输出 Final Answer':
    '# Werkzeugkontingent erschöpft → Klar mitteilen, Final Answer ausgeben lassen',

    '# 只执行第一个工具调用':
    '# Nur den ersten Werkzeugaufruf ausführen',

    '# ── 情况3：既没有工具调用，也没有 Final Answer ──':
    '# ── Fall 3: Weder Werkzeugaufrufe noch Final Answer ──',

    '# 工具调用次数不足，推荐未用过的工具':
    '# Unzureichende Werkzeugaufrufe, empfehlen unbenutzte Werkzeuge',

    # === chat method ===
    '"""与Report Agent对话\n        \n        在对话中Agent可以自主调用检索工具来回答问题\n        \n        Args:\n            message: 用户消息\n            chat_history: 对话历史\n            \n        Returns:\n            {\n                "response": "Agent回复",\n                "tool_calls": [调用的工具列表],\n                "sources": [信息来源]\n            }\n        """':
    '"""Mit dem Report Agent sprechen\n        \n        Im Dialog kann der Agent autonom Suchwerkzeuge aufrufen, um Fragen zu beantworten\n        \n        Args:\n            message: Benutzernachricht\n            chat_history: Dialogverlauf\n            \n        Returns:\n            {\n                "response": "Agent-Antwort",\n                "tool_calls": [Liste der aufgerufenen Werkzeuge],\n                "sources": [Informationsquellen]\n            }\n        """',

    # === ReportManager CLASS ===
    '"""报告管理器\n    \n    负责报告的持久化存储和检索\n    \n    文件结构（分章节输出）：\n    reports/\n      {report_id}/\n        meta.json          - 报告元信息和状态\n        outline.json       - 报告大纲\n        progress.json      - 生成进度\n        section_01.md      - 第1章节\n        section_02.md      - 第2章节\n        ...\n        full_report.md     - 完整报告\n    """':
    '"""Berichtsmanager\n    \n    Verantwortlich für die persistente Speicherung und Abfrage von Berichten\n    \n    Dateistruktur (abschnittsweise Ausgabe):\n    reports/\n      {report_id}/\n        meta.json          - Berichtsmetainformationen und Status\n        outline.json       - Berichtsgliederung\n        progress.json      - Generierungsfortschritt\n        section_01.md      - Abschnitt 1\n        section_02.md      - Abschnitt 2\n        ...\n        full_report.md     - Vollständiger Bericht\n    """',

    '"""确保报告根目录存在"""':
    '"""Stellt sicher, dass das Stammverzeichnis für Berichte existiert"""',

    '"""获取报告文件夹路径"""':
    '"""Pfad zum Berichtsordner abrufen"""',

    '"""确保报告文件夹存在并返回路径"""':
    '"""Stellt sicher, dass der Berichtsordner existiert und gibt den Pfad zurück"""',

    '"""获取报告元信息文件路径"""':
    '"""Pfad zur Berichtsmetainformationsdatei abrufen"""',

    '"""获取完整报告Markdown文件路径"""':
    '"""Pfad zur vollständigen Berichts-Markdown-Datei abrufen"""',

    '"""获取大纲文件路径"""':
    '"""Pfad zur Gliederungsdatei abrufen"""',

    '"""获取进度文件路径"""':
    '"""Pfad zur Fortschrittsdatei abrufen"""',

    '"""获取章节Markdown文件路径"""':
    '"""Pfad zur Abschnitts-Markdown-Datei abrufen"""',

    '"""获取 Agent 日志文件路径"""':
    '"""Pfad zur Agent-Protokolldatei abrufen"""',

    '"""获取控制台日志文件路径"""':
    '"""Pfad zur Konsolenprotokolldatei abrufen"""',

    '"""获取控制台日志内容\n        \n        这是报告生成过程中的控制台输出日志（INFO、WARNING等），\n        与 agent_log.jsonl 的结构化日志不同。\n        \n        Args:\n            report_id: 报告ID\n            from_line: 从第几行开始读取（用于增量获取，0 表示从头开始）\n            \n        Returns:\n            {\n                "logs": [日志行列表],\n                "total_lines": 总行数,\n                "from_line": 起始行号,\n                "has_more": 是否还有更多日志\n            }\n        """':
    '"""Konsolenprotokollinhalt abrufen\n        \n        Dies sind Konsolenausgabeprotokolle während der Berichtsgenerierung (INFO, WARNING usw.),\n        die sich von den strukturierten Protokollen in agent_log.jsonl unterscheiden.\n        \n        Args:\n            report_id: Berichts-ID\n            from_line: Ab welcher Zeile mit dem Lesen begonnen werden soll (für inkrementelles Abrufen, 0 bedeutet von Anfang an)\n            \n        Returns:\n            {\n                "logs": [Protokollzeilenliste],\n                "total_lines": Gesamtzahl der Zeilen,\n                "from_line": Startzeilennummer,\n                "has_more": Ob weitere Protokolle vorhanden sind\n            }\n        """',

    '"""获取完整的控制台日志（一次性获取全部）\n        \n        Args:\n            report_id: 报告ID\n            \n        Returns:\n            日志行列表\n        """':
    '"""Vollständige Konsolenprotokolle abrufen (alle auf einmal)\n        \n        Args:\n            report_id: Berichts-ID\n            \n        Returns:\n            Protokollzeilenliste\n        """',

    '"""获取 Agent 日志内容\n        \n        Args:\n            report_id: 报告ID\n            from_line: 从第几行开始读取（用于增量获取，0 表示从头开始）\n            \n        Returns:\n            {\n                "logs": [日志条目列表],\n                "total_lines": 总行数,\n                "from_line": 起始行号,\n                "has_more": 是否还有更多日志\n            }\n        """':
    '"""Agent-Protokollinhalt abrufen\n        \n        Args:\n            report_id: Berichts-ID\n            from_line: Ab welcher Zeile mit dem Lesen begonnen werden soll (für inkrementelles Abrufen, 0 bedeutet von Anfang an)\n            \n        Returns:\n            {\n                "logs": [Protokolleintragsliste],\n                "total_lines": Gesamtzahl der Zeilen,\n                "from_line": Startzeilennummer,\n                "has_more": Ob weitere Protokolle vorhanden sind\n            }\n        """',

    '"""获取完整的 Agent 日志（用于一次性获取全部）\n        \n        Args:\n            report_id: 报告ID\n            \n        Returns:\n            日志条目列表\n        """':
    '"""Vollständige Agent-Protokolle abrufen (für einmaliges Abrufen aller)\n        \n        Args:\n            report_id: Berichts-ID\n            \n        Returns:\n            Protokolleintragsliste\n        """',

    '"""保存报告大纲\n        \n        在规划阶段完成后立即调用\n        """':
    '"""Berichtsgliederung speichern\n        \n        Wird sofort nach Abschluss der Planungsphase aufgerufen\n        """',

    '"""保存单个章节\n\n        在每个章节生成完成后立即调用，实现分章节输出\n\n        Args:\n            report_id: 报告ID\n            section_index: 章节索引（从1开始）\n            section: 章节对象\n\n        Returns:\n            保存的文件路径\n        """':
    '"""Einzelnen Abschnitt speichern\n\n        Wird nach Abschluss der Generierung jedes Abschnitts sofort aufgerufen, um abschnittsweise Ausgabe zu ermöglichen\n\n        Args:\n            report_id: Berichts-ID\n            section_index: Abschnittsindex (beginnt bei 1)\n            section: Abschnittsobjekt\n\n        Returns:\n            Pfad der gespeicherten Datei\n        """',

    '"""清理章节内容\n        \n        1. 移除内容开头与章节标题重复的Markdown标题行\n        2. 将所有 ### 及以下级别的标题转换为粗体文本\n        \n        Args:\n            content: 原始内容\n            section_title: 章节标题\n            \n        Returns:\n            清理后的内容\n        """':
    '"""Abschnittsinhalt bereinigen\n        \n        1. Markdown-Titelzeilen am Anfang des Inhalts entfernen, die mit dem Abschnittstitel übereinstimmen\n        2. Alle Titel der Ebene ### und darunter in Fetttext konvertieren\n        \n        Args:\n            content: Originalinhalt\n            section_title: Abschnittstitel\n            \n        Returns:\n            Bereinigter Inhalt\n        """',

    '"""更新报告生成进度\n        \n        前端可以通过读取progress.json获取实时进度\n        """':
    '"""Fortschritt der Berichtsgenerierung aktualisieren\n        \n        Das Frontend kann den Echtzeitfortschritt durch Lesen von progress.json abrufen\n        """',

    '"""获取报告生成进度"""':
    '"""Fortschritt der Berichtsgenerierung abrufen"""',

    '"""获取已生成的章节列表\n        \n        返回所有已保存的章节文件信息\n        """':
    '"""Liste der generierten Abschnitte abrufen\n        \n        Gibt Informationen zu allen gespeicherten Abschnittsdateien zurück\n        """',

    '"""组装完整报告\n        \n        从已保存的章节文件组装完整报告，并进行标题清理\n        """':
    '"""Vollständigen Bericht zusammenstellen\n        \n        Stellt den vollständigen Bericht aus den gespeicherten Abschnittsdateien zusammen und bereinigt die Titel\n        """',

    '"""后处理报告内容\n        \n        1. 移除重复的标题\n        2. 保留报告主标题(#)和章节标题(##)，移除其他级别的标题(###, ####等)\n        3. 清理多余的空行和分隔线\n        \n        Args:\n            content: 原始报告内容\n            outline: 报告大纲\n            \n        Returns:\n            处理后的内容\n        """':
    '"""Nachbearbeitung des Berichtsinhalts\n        \n        1. Doppelte Titel entfernen\n        2. Berichts-Haupttitel (#) und Abschnittstitel (##) beibehalten, andere Titelebenen (###, #### usw.) entfernen\n        3. Überzählige Leerzeilen und Trennlinien bereinigen\n        \n        Args:\n            content: Originaler Berichtsinhalt\n            outline: Berichtsgliederung\n            \n        Returns:\n            Verarbeiteter Inhalt\n        """',

    '"""保存报告元信息和完整报告"""':
    '"""Berichtsmetainformationen und vollständigen Bericht speichern"""',

    '"""获取报告"""':
    '"""Bericht abrufen"""',

    '"""根据模拟ID获取报告"""':
    '"""Bericht anhand der Simulations-ID abrufen"""',

    '"""列出报告"""':
    '"""Berichte auflisten"""',

    '"""删除报告（整个文件夹）"""':
    '"""Bericht löschen (gesamten Ordner)"""',

    # === Default report titles (backup) ===
    '"模拟分析报告"':
    '"Simulationsanalysebericht"',

    '"未来预测报告"':
    '"Zukunftsprognosebericht"',

    '"基于模拟预测的未来趋势与风险分析"':
    '"Zukünftige Trends und Risikoanalyse basierend auf Simulationsvorhersagen"',

    '"预测场景与核心发现"':
    '"Prognoseszenario und Kernerkenntnisse"',

    '"人群行为预测分析"':
    '"Gruppenverhaltensvorhersageanalyse"',

    '"趋势展望与风险提示"':
    '"Trendprognose und Risikohinweise"',
}

# Apply translations
for chinese, german in translations.items():
    if chinese in content:
        content = content.replace(chinese, german)
        print(f"Translated: {chinese[:60]}...")
    else:
        print(f"NOT FOUND: {chinese[:60]}...")

# Write back
with open(FILE_PATH, 'w', encoding='utf-8') as f:
    f.write(content)

print("\nDone!")
