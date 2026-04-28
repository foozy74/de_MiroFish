#!/usr/bin/env python3
import re

def translate_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    
    # oasis_profile_generator.py
    if 'oasis_profile_generator' in filepath:
        replacements = [
            ('logger.warning(f"Zep客户端初始化失败: {e}")', 'logger.warning(f"Zep-Client-Initialisierung fehlgeschlagen: {e}")'),
            ('logger.debug(f"跳过Zep检索：未设置graph_id")', 'logger.debug(f"Zep-Abruf übersprungen: graph_id nicht gesetzt")'),
            ('logger.debug(f"Zep边搜索第 {attempt + 1} 次失败: {str(e)[:80]}, 重试中...")', 'logger.debug(f"Zep-Kantensuche Versuch {attempt + 1} fehlgeschlagen: {str(e)[:80]}, Retry...")'),
            ('logger.debug(f"Zep边搜索在 {max_retries} 次尝试后仍失败: {e}")', 'logger.debug(f"Zep-Kantensuche nach {max_retries} Versuchen weiterhin fehlgeschlagen: {e}")'),
            ('logger.debug(f"Zep节点搜索第 {attempt + 1} 次失败: {str(e)[:80]}, 重试中...")', 'logger.debug(f"Zep-Knotensuche Versuch {attempt + 1} fehlgeschlagen: {str(e)[:80]}, Retry...")'),
            ('logger.debug(f"Zep节点搜索在 {max_retries} 次尝试后仍失败: {e}")', 'logger.debug(f"Zep-Knotensuche nach {max_retries} Versuchen weiterhin fehlgeschlagen: {e}")'),
            ('logger.info(f"Zep混合检索完成: {entity_name}, 获取 {len(results[\'facts\'])} 条事实, {len(results[\'node_summaries\'])} 个相关节点")', 'logger.info(f"Zep-Hybridsuche abgeschlossen: {entity_name}, {len(results[\'facts\"])} Fakten, {len(results[\'node_summaries\"])} relevante Knoten abgerufen")'),
            ('logger.warning(f"Zep检索超时 ({entity_name})")', 'logger.warning(f"Zep-Abruf-Timeout ({entity_name})")'),
            ('logger.warning(f"Zep检索失败 ({entity_name}): {e}")', 'logger.warning(f"Zep-Abruf fehlgeschlagen ({entity_name}): {e}")'),
            ('logger.warning(f"LLM输出被截断 (attempt {attempt+1}), 尝试修复...")', 'logger.warning(f"LLM-Ausgabe abgeschnitten (Versuch {attempt+1}), Reparaturg...")'),
            ('logger.warning(f"JSON解析失败 (attempt {attempt+1}): {str(je)[:80]}")', 'logger.warning(f"JSON-Parsing fehlgeschlagen (Versuch {attempt+1}): {str(je)[:80]}")'),
            ('logger.warning(f"LLM调用失败 (attempt {attempt+1}): {str(e)[:80]}")', 'logger.warning(f"LLM-Aufruf fehlgeschlagen (Versuch {attempt+1}): {str(e)[:80]}")'),
            ('logger.warning(f"LLM生成人设失败（{max_attempts}次尝试）: {last_error}, 使用规则生成")', 'logger.warning(f"LLM-Persönlichkeitsgenerierung fehlgeschlagen ({max_attempts} Versuche): {last_error}, verwende Regelgenerierung")'),
            ('logger.info(f"从损坏的JSON中提取了部分信息")', 'logger.info(f"Teilweise Informationen aus beschädigtem JSON extrahiert")'),
            ('logger.warning(f"JSON修复失败，返回基础结构")', 'logger.warning(f"JSON-Reparatur fehlgeschlagen, gebe Basisstruktur zurück")'),
            ('logger.warning(f"实时保存 profiles 失败: {e}")', 'logger.warning(f"Echtzeit-Speicherung der Profiles fehlgeschlagen: {e}")'),
            ('logger.error(f"生成实体 {entity.name} 的人设失败: {str(e)}")', 'logger.error(f"Persönlichkeitsgenerierung für Entität {entity.name} fehlgeschlagen: {str(e)}")'),
            ('logger.info(f"开始并行生成 {total} 个Agent人设（并行数: {parallel_count}）...")', 'logger.info(f"Starte parallele Generierung von {total} Agent-Persönlichkeiten (Parallelität: {parallel_count})...")'),
            ('logger.warning(f"[{current}/{total}] {entity.name} 使用备用人设: {error}")', 'logger.warning(f"[{current}/{total}] {entity.name} verwendet Fallback-Persönlichkeit: {error}")'),
            ('logger.info(f"[{current}/{total}] 成功生成人设: {entity.name} ({entity_type})")', 'logger.info(f"[{current}/{total}] Persönlichkeit erfolgreich generiert: {entity.name} ({entity_type})")'),
            ('logger.error(f"处理实体 {entity.name} 时发生异常: {str(e)}")', 'logger.error(f"Ausnahme bei der Verarbeitung der Entität {entity.name}: {str(e)}")'),
            ('logger.info(f"已保存 {len(profiles)} 个Twitter Profile到 {file_path} (OASIS CSV格式)")', 'logger.info(f"{len(profiles)} Twitter-Profile nach {file_path} gespeichert (OASIS CSV-Format)")'),
            ('logger.info(f"已保存 {len(profiles)} 个Reddit Profile到 {file_path} (JSON格式，包含user_id字段)")', 'logger.info(f"{len(profiles)} Reddit-Profile nach {file_path} gespeichert (JSON-Format, mit user_id-Feld)")'),
            ('logger.warning("save_profiles_to_json已废弃，请使用save_profiles方法")', 'logger.warning("save_profiles_to_json ist veraltet, bitte verwenden Sie die save_profiles-Methode")'),
        ]
        
    # zep_tools.py
    elif 'zep_tools' in filepath:
        replacements = [
            ('logger.info("ZepToolsService 初始化完成")', 'logger.info("ZepToolsService-Initialisierung abgeschlossen")'),
            ('logger.error(f"Zep {operation_name} 在 {max_retries} 次尝试后仍失败: {str(e)}")', 'logger.error(f"Zep {operation_name} nach {max_retries} Versuchen weiterhin fehlgeschlagen: {str(e)}")'),
            ('logger.info(f"图谱搜索: graph_id={graph_id}, query={query[:50]}...")', 'logger.info(f"Graph-Suche: graph_id={graph_id}, query={query[:50]}...")'),
            ('logger.info(f"搜索完成: 找到 {len(facts)} 条相关事实")', 'logger.info(f"Suche abgeschlossen: {len(facts)} relevante Fakten gefunden")'),
            ('logger.warning(f"Zep Search API失败，降级为本地搜索: {str(e)}")', 'logger.warning(f"Zep Search API fehlgeschlagen, Fallback auf lokale Suche: {str(e)}")'),
            ('logger.info(f"使用本地搜索: query={query[:30]}...")', 'logger.info(f"Verwende lokale Suche: query={query[:30]}...")'),
            ('logger.info(f"本地搜索完成: 找到 {len(facts)} 条相关事实")', 'logger.info(f"Lokale Suche abgeschlossen: {len(facts)} relevante Fakten gefunden")'),
            ('logger.error(f"本地搜索失败: {str(e)}")', 'logger.error(f"Lokale Suche fehlgeschlagen: {str(e)}")'),
            ('logger.info(f"获取图谱 {graph_id} 的所有节点...")', 'logger.info(f"Alle Knoten des Graphen {graph_id} abrufen...")'),
            ('logger.info(f"获取到 {len(result)} 个节点")', 'logger.info(f"{len(result)} Knoten abgerufen")'),
            ('logger.info(f"获取图谱 {graph_id} 的所有边...")', 'logger.info(f"Alle Kanten des Graphen {graph_id} abrufen...")'),
            ('logger.info(f"获取到 {len(result)} 条边")', 'logger.info(f"{len(result)} Kanten abgerufen")'),
            ('logger.info(f"获取节点详情: {node_uuid[:8]}...")', 'logger.info(f"Knotendetails abrufen: {node_uuid[:8]}...")'),
            ('logger.error(f"获取节点详情失败: {str(e)}")', 'logger.error(f"Knotendetails-Abruf fehlgeschlagen: {str(e)}")'),
            ('logger.info(f"获取节点 {node_uuid[:8]}... 的相关边")', 'logger.info(f"Knotenbezogene Kanten abrufen für Knoten {node_uuid[:8]}...")'),
            ('logger.info(f"找到 {len(result)} 条与节点相关的边")', 'logger.info(f"{len(result)} knotenbezogene Kanten gefunden")'),
            ('logger.warning(f"获取节点边失败: {str(e)}")', 'logger.warning(f"Knotenkanten-Abruf fehlgeschlagen: {str(e)}")'),
            ('logger.info(f"获取类型为 {entity_type} 的实体...")', 'logger.info(f"Entitäten vom Typ {entity_type} abrufen...")'),
            ('logger.info(f"找到 {len(filtered)} 个 {entity_type} 类型的实体")', 'logger.info(f"{len(filtered)} Entitäten vom Typ {entity_type} gefunden")'),
            ('logger.info(f"获取实体 {entity_name} 的关系摘要...")', 'logger.info(f"Beziehungszusammenfassung für Entität {entity_name} abrufen...")'),
            ('logger.info(f"获取图谱 {graph_id} 的统计信息...")', 'logger.info(f"Statistiken für Graph {graph_id} abrufen...")'),
            ('logger.info(f"获取模拟上下文: {simulation_requirement[:50]}...")', 'logger.info(f"Simulationskontext abrufen: {simulation_requirement[:50]}...")'),
            ('logger.info(f"InsideForge 深度洞察检索: {query[:50]}...")', 'logger.info(f"InsideForge Tiefensuche: {query[:50]}...")'),
            ('logger.info(f"生成 {len(sub_queries)} 个子问题")', 'logger.info(f"{len(sub_queries)} Unterfragen generiert")'),
            ('logger.debug(f"获取节点 {uuid} 失败: {e}")', 'logger.debug(f"Knoten {uuid} abrufen fehlgeschlagen: {e}")'),
            ('logger.info(f"InsideForge完成: {result.total_facts}条事实, {result.total_entities}个实体, {result.total_relationships}条关系")', 'logger.info(f"InsideForge abgeschlossen: {result.total_facts} Fakten, {result.total_entities} Entitäten, {result.total_relationships} Beziehungen")'),
            ('logger.warning(f"生成子问题失败: {str(e)}，使用默认子问题")', 'logger.warning(f"Unterfragen-Generierung fehlgeschlagen: {str(e)}, verwende Standard-Unterfragen")'),
            ('logger.info(f"PanoramaSearch 广度搜索: {query[:50]}...")', 'logger.info(f"PanoramaSearch Breittensuche: {query[:50]}...")'),
            ('logger.info(f"PanoramaSearch完成: {result.active_count}条有效, {result.historical_count}条历史")', 'logger.info(f"PanoramaSearch abgeschlossen: {result.active_count} aktiv, {result.historical_count} historisch")'),
            ('logger.info(f"QuickSearch 简单搜索: {query[:50]}...")', 'logger.info(f"QuickSearch einfache Suche: {query[:50]}...")'),
            ('logger.info(f"QuickSearch完成: {result.total_count}条结果")', 'logger.info(f"QuickSearch abgeschlossen: {result.total_count} Ergebnisse")'),
            ('logger.info(f"InterviewAgents 深度采访（真实API）: {interview_requirement[:50]}...")', 'logger.info(f"InterviewAgents Tiefeninterview (Echt-API): {interview_requirement[:50]}...")'),
            ('logger.warning(f"未找到模拟 {simulation_id} 的人设文件")', 'logger.warning(f"Persönlichkeitsdatei für Simulation {simulation_id} nicht gefunden")'),
            ('logger.info(f"加载到 {len(profiles)} 个Agent人设")', 'logger.info(f"{len(profiles)} Agent-Persönlichkeiten geladen")'),
            ('logger.info(f"选择了 {len(selected_agents)} 个Agent进行采访: {selected_indices}")', 'logger.info(f"{len(selected_agents)} Agents für Interview ausgewählt: {selected_indices}")'),
            ('logger.info(f"生成了 {len(result.interview_questions)} 个采访问题")', 'logger.info(f"{len(result.interview_questions)} Interview-Fragen generiert")'),
            ('logger.info(f"调用批量采访API（双平台）: {len(interviews_request)} 个Agent")', 'logger.info(f"Batch-Interview-API aufrufen (Dual-Plattform): {len(interviews_request)} Agents")'),
            ('logger.info(f"采访API返回: {api_result.get(\'interviews_count\', 0)} 个结果, success={api_result.get(\'success\')}")', 'logger.info(f"Interview-API zurück: {api_result.get(\'interviews_count\', 0)} Ergebnisse, success={api_result.get(\'success\')}")'),
            ('logger.warning(f"采访API返回失败: {error_msg}")', 'logger.warning(f"Interview-API-Rückgabe fehlgeschlagen: {error_msg}")'),
            ('logger.warning(f"采访API调用失败（环境未运行？）: {e}")', 'logger.warning(f"Interview-API-Aufruf fehlgeschlagen (Umgebung nicht aktiv?): {e}")'),
            ('logger.error(f"采访API调用异常: {e}")', 'logger.error(f"Interview-API-Aufruf-Ausnahme: {e}")'),
            ('logger.info(f"InterviewAgents完成: 采访了 {result.interviewed_count} 个Agent（双平台）")', 'logger.info(f"InterviewAgents abgeschlossen: {result.interviewed_count} Agents interviewt (Dual-Plattform)")'),
            ('logger.info(f"从 reddit_profiles.json 加载了 {len(profiles)} 个人设")', 'logger.info(f"{len(profiles)} Persönlichkeiten aus reddit_profiles.json geladen")'),
            ('logger.warning(f"读取 reddit_profiles.json 失败: {e}")', 'logger.warning(f"reddit_profiles.json lesen fehlgeschlagen: {e}")'),
            ('logger.info(f"从 twitter_profiles.csv 加载了 {len(profiles)} 个人设")', 'logger.info(f"{len(profiles)} Persönlichkeiten aus twitter_profiles.csv geladen")'),
            ('logger.warning(f"读取 twitter_profiles.csv 失败: {e}")', 'logger.warning(f"twitter_profiles.csv lesen fehlgeschlagen: {e}")'),
            ('logger.warning(f"LLM选择Agent失败，使用默认选择: {e}")', 'logger.warning(f"LLM-Agent-Auswahl fehlgeschlagen, verwende Standardauswahl: {e}")'),
            ('logger.warning(f"生成采访问题失败: {e}")', 'logger.warning(f"Interview-Fragen-Generierung fehlgeschlagen: {e}")'),
            ('logger.warning(f"生成采访摘要失败: {e}")', 'logger.warning(f"Interview-Zusammenfassungs-Generierung fehlgeschlagen: {e}")'),
        ]
    
    # simulation_config_generator.py
    elif 'simulation_config_generator' in filepath:
        replacements = [
            ('logger.info(f"开始智能生成模拟配置: simulation_id={simulation_id}, 实体数={len(entities)}")', 'logger.info(f"Starte intelligente Simulationskonfigurationsgenerierung: simulation_id={simulation_id}, Entitäten={len(entities)}")'),
            ('logger.info("为初始帖子分配合适的发布者 Agent...")', 'logger.info("分配合适的 Publisher-Agent für Initialbeiträge...")'),
            ('logger.info(f"模拟配置生成完成: {len(params.agent_configs)} 个Agent配置")', 'logger.info(f"Simulationskonfigurationsgenerierung abgeschlossen: {len(params.agent_configs)} Agent-Konfigurationen")'),
            ('logger.warning(f"LLM输出被截断 (attempt {attempt+1})")', 'logger.warning(f"LLM-Ausgabe abgeschnitten (Versuch {attempt+1})")'),
            ('logger.warning(f"JSON解析失败 (attempt {attempt+1}): {str(e)[:80]}")', 'logger.warning(f"JSON-Parsing fehlgeschlagen (Versuch {attempt+1}): {str(e)[:80]}")'),
            ('logger.warning(f"LLM调用失败 (attempt {attempt+1}): {str(e)[:80]}")', 'logger.warning(f"LLM-Aufruf fehlgeschlagen (Versuch {attempt+1}): {str(e)[:80]}")'),
            ('logger.warning(f"时间配置LLM生成失败: {e}, 使用默认配置")', 'logger.warning(f"Zeitkonfigurations-LLM-Generierung fehlgeschlagen: {e}, verwende Standardkonfiguration")'),
            ('logger.warning(f"agents_per_hour_min ({agents_per_hour_min}) 超过总Agent数 ({num_entities})，已修正")', 'logger.warning(f"agents_per_hour_min ({agents_per_hour_min}) überschreitet Gesamt-Agent-Anzahl ({num_entities}), korrigiert")'),
            ('logger.warning(f"agents_per_hour_max ({agents_per_hour_max}) 超过总Agent数 ({num_entities})，已修正")', 'logger.warning(f"agents_per_hour_max ({agents_per_hour_max}) überschreitet Gesamt-Agent-Anzahl ({num_entities}), korrigiert")'),
            ('logger.warning(f"agents_per_hour_min >= max，已修正为 {agents_per_hour_min}")', 'logger.warning(f"agents_per_hour_min >= max, korrigiert auf {agents_per_hour_min}")'),
            ('logger.warning(f"事件配置LLM生成失败: {e}, 使用默认配置")', 'logger.warning(f"Ereigniskonfigurations-LLM-Generierung fehlgeschlagen: {e}, verwende Standardkonfiguration")'),
            ('logger.warning(f"未找到类型 \'{poster_type}\' 的匹配 Agent，使用影响力最高的 Agent")', 'logger.warning(f"Kein passender Agent für Typ \'{poster_type}\' gefunden, verwende Agent mit höchstem Einfluss")'),
            ('logger.info(f"初始帖子分配: poster_type=\'{poster_type}\' -> agent_id={matched_agent_id}")', 'logger.info(f"Initialbeitrags-Zuordnung: poster_type=\'{poster_type}\' -> agent_id={matched_agent_id}")'),
            ('logger.warning(f"Agent配置批次LLM生成失败: {e}, 使用规则生成")', 'logger.warning(f"Agent-Konfigurations-Chargen-LLM-Generierung fehlgeschlagen: {e}, verwende Regelgenerierung")'),
        ]
    
    # report_agent.py
    elif 'report_agent' in filepath:
        replacements = [
            ('logger.info(f"ReportAgent 初始化完成: graph_id={graph_id}, simulation_id={simulation_id}")', 'logger.info(f"ReportAgent-Initialisierung abgeschlossen: graph_id={graph_id}, simulation_id={simulation_id}")'),
            ('logger.info(f"执行工具: {tool_name}, 参数: {parameters}")', 'logger.info(f"Werkzeug ausführen: {tool_name}, Parameter: {parameters}")'),
            ('logger.info("search_graph 已重定向到 quick_search")', 'logger.info("search_graph wurde auf quick_search umgeleitet")'),
            ('logger.info("get_simulation_context 已重定向到 insight_forge")', 'logger.info("get_simulation_context wurde auf insight_forge umgeleitet")'),
            ('logger.error(f"工具执行失败: {tool_name}, 错误: {str(e)}")', 'logger.error(f"Werkzeugausführung fehlgeschlagen: {tool_name}, Fehler: {str(e)}")'),
            ('logger.info("开始规划报告大纲...")', 'logger.info("Beginne mit der Planung des Berichtslayouts...")'),
            ('logger.info(f"大纲规划完成: {len(sections)} 个章节")', 'logger.info(f"Layoutplanung abgeschlossen: {len(sections)} Abschnitte")'),
            ('logger.error(f"大纲规划失败: {str(e)}")', 'logger.error(f"Layoutplanung fehlgeschlagen: {str(e)}")'),
            ('logger.info(f"ReACT生成章节: {section.title}")', 'logger.info(f"ReACT generiert Abschnitt: {section.title}")'),
            ('logger.warning(f"章节 {section.title} 第 {iteration + 1} 次迭代: LLM 返回 None")', 'logger.warning(f"Abschnitt {section.title} Iterationsversuch {iteration + 1}: LLM gab None zurück")'),
            ('logger.debug(f"LLM响应: {response[:200]}...")', 'logger.debug(f"LLM-Antwort: {response[:200]}...")'),
            ('logger.info(f"章节 {section.title} 生成完成（工具调用: {tool_calls_count}次）")', 'logger.info(f"Abschnitt {section.title} Generierung abgeschlossen (Werkzeugaufrufe: {tool_calls_count})")'),
            ('logger.info(f"LLM 尝试调用 {len(tool_calls)} 个工具，只执行第一个: {call[\'name\']}")', 'logger.info(f"LLM versucht {len(tool_calls)} Werkzeuge aufzurufen, nur das erste wird ausgeführt: {call[\'name\']}")'),
        ]
    
    else:
        replacements = []
    
    for old, new in replacements:
        if old in content:
            content = content.replace(old, new)
            print(f"  ✓ {old[:60]}...")
        else:
            print(f"  ✗ NOT FOUND: {old[:60]}...")
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return content != original

files = [
    'backend/app/services/oasis_profile_generator.py',
    'backend/app/services/zep_tools.py',
    'backend/app/services/simulation_config_generator.py',
    'backend/app/services/report_agent.py',
]

for f in files:
    print(f"\n{f}:")
    translate_file(f)

print("\n✓ Logging messages translated")
