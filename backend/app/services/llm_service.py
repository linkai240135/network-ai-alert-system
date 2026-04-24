from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any

from .rag_service import retrieve_knowledge
from .settings_service import get_setting_map


DEEPSEEK_ENDPOINT = "https://api.deepseek.com/chat/completions"
DEFAULT_CHAT_MODEL = "deepseek-chat"
DEFAULT_REASONER_MODEL = "deepseek-reasoner"


def _compact(value: Any, limit: int = 1800) -> str:
    text = json.dumps(value, ensure_ascii=False, default=str)
    return text if len(text) <= limit else text[:limit] + "..."


def _deepseek_enabled() -> bool:
    return bool(os.getenv("DEEPSEEK_API_KEY"))


def _style_guide() -> str:
    return (
        "输出风格要求："
        "不要写成正式报告，不要使用 Markdown 大标题、分章节标题、表格或加粗。"
        "请像系统里的智能助手直接回复用户一样表达。"
        "先用 1 句话给出总体判断，再用 4 到 6 条扁平要点展开。"
        "每条尽量简洁，优先说明问题、依据、风险和可执行建议。"
    )


def _polish_content(content: str) -> str:
    text = (content or "").strip()
    if not text:
        return text
    text = re.sub(r"^\s{0,3}#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = text.replace("**", "").replace("__", "")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def generate_strategy_plan(payload: dict, knowledge_hits: list[dict]) -> list[dict]:
    service = payload.get("service_profile") or {}
    summary = payload.get("summary") or {}
    attack_name = payload.get("label") or payload.get("attack_type") or "异常流量"
    service_name = service.get("name", "未知服务")
    protocol = service.get("protocol", "--")
    port = service.get("port", "--")
    classifier = summary.get("classifier_name", payload.get("classifier_name", "FT-Transformer"))
    detector = summary.get("detector_name", payload.get("detector_name", "DeepSVDD"))
    importance_hint = "高优先级通信业务" if service_name in {"DNS", "HTTP", "HTTPS"} else "一般业务资产"

    return [
        {
            "step": "立即压制",
            "owner": "安全运营中心",
            "action": f"围绕 {attack_name} 相关源地址执行限流、访问控制或临时封禁，优先降低异常扩散速度。",
        },
        {
            "step": "资产复核",
            "owner": "运维值守团队",
            "action": f"复核目标服务 {service_name} 与端口 {protocol}/{port} 的暴露合理性，并结合 {importance_hint} 评估业务影响面。",
        },
        {
            "step": "研判确认",
            "owner": "二线分析人员",
            "action": f"结合 {classifier} 的分类结果、{detector} 的异常得分以及知识库命中结果完成复核。",
        },
        {
            "step": "闭环回流",
            "owner": "模型训练模块",
            "action": "将误报、漏报或标签修正结果回写反馈样本，触发下一轮阈值校准和模型重训。",
        },
    ]


def _knowledge_digest(knowledge_hits: list[dict]) -> str:
    if not knowledge_hits:
        return "未检索到高相关知识条目，请结合模型结果与人工经验继续研判。"
    return "\n".join(
        [
            f"{index + 1}. [{item['category']}] {item['title']}：{item['content']}"
            for index, item in enumerate(knowledge_hits)
        ]
    )


def _resolve_model(preferred_model: str | None = None) -> str:
    setting_map = get_setting_map()
    configured_model = setting_map.get("deepseek_model") or os.getenv("DEEPSEEK_MODEL", DEFAULT_CHAT_MODEL)
    return preferred_model or configured_model


def _call_deepseek(system_prompt: str, user_prompt: str, preferred_model: str | None = None) -> dict:
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is not configured")

    payload = {
        "model": _resolve_model(preferred_model),
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": float(os.getenv("DEEPSEEK_TEMPERATURE", "0.2")),
        "max_tokens": int(os.getenv("DEEPSEEK_MAX_TOKENS", "1200")),
    }
    request = urllib.request.Request(
        os.getenv("DEEPSEEK_API_BASE", DEEPSEEK_ENDPOINT),
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=int(os.getenv("DEEPSEEK_TIMEOUT", "20"))) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"DeepSeek request failed: {exc.code} {detail}") from exc

    content = body.get("choices", [{}])[0].get("message", {}).get("content", "")
    return {
        "provider": "DeepSeek",
        "model": payload["model"],
        "mode": "online",
        "content": _polish_content(content),
    }


def _fallback_alert_analysis(alert: dict, knowledge_hits: list[dict], strategy_plan: list[dict]) -> dict:
    label = alert.get("label") or alert.get("title") or "未知告警"
    risk = alert.get("risk_level", "中")
    service = alert.get("service_profile") or {}
    top_features = alert.get("top_features") or []
    feature_text = "、".join([item.get("label", item.get("feature", "")) for item in top_features[:3] if item])
    suggestions = alert.get("recommendations") or [
        "复核源地址与目标资产的近期访问行为。",
        "结合服务端口画像判断是否存在异常暴露面。",
        "将研判结论沉淀为事件处置记录，并在误报时回流训练样本。",
    ]

    content = "\n".join(
        [
            f"这条告警可以先按 {label} 高风险事件处理，当前风险等级为{risk}，建议直接进入处置闭环。",
            f"- 关键信号主要来自 {alert.get('classifier_name', 'FT-Transformer')} 的分类结果，以及 {alert.get('detector_name', 'DeepSVDD')} 的异常判断。",
            f"- 当前最值得关注的异常特征集中在 {feature_text or '流量速率、连接时长、端口分布等指标'}，说明这不是单一偶发波动。",
            f"- 目标服务是 {service.get('name', '未知服务')}，端口为 {service.get('protocol', '--')}/{service.get('port', '--')}，需要重点评估对通信业务连续性的影响。",
            f"- 建议优先执行：{suggestions[0]}",
            f"- 后续复核可以继续围绕：{'；'.join(suggestions[1:3])}",
        ]
    )
    return {
        "provider": "Local-Rulebook",
        "model": "security-playbook",
        "mode": "fallback",
        "content": _polish_content(content),
        "knowledge_hits": knowledge_hits,
        "strategy_plan": strategy_plan,
        "rag_enabled": True,
    }


def _fallback_incident_analysis(incident: dict, knowledge_hits: list[dict], strategy_plan: list[dict]) -> dict:
    recommendations = incident.get("recommendations") or []
    summary = incident.get("summary") or {}
    content = "\n".join(
        [
            f"这个事件已经具备继续升级处置的条件，事件编号 {incident.get('incident_no', '--')}，类型为 {incident.get('attack_type', '未知类型')}，当前状态是 {incident.get('status', '--')}。",
            f"- 攻击链路上，源地址 {incident.get('source_ip', '--')} 指向目标 {incident.get('destination_ip', '--')}，目前已经聚合 {incident.get('event_count', 1)} 条同源或同类信号。",
            f"- 模型依据主要来自 {summary.get('classifier_name', 'FT-Transformer')} 的分类结果、{summary.get('detector_name', 'DeepSVDD')} 的异常判断，以及 p-value {summary.get('conformal_p_value', '--')} 的可信参考。",
            f"- 从阶段判断看，该事件处于 {incident.get('attack_stage', '未知阶段')}，说明它不是单一告警，而是具备连续攻击特征。",
            f"- 建议优先执行：{(recommendations or ['隔离高风险访问源'])[0]}",
            f"- 后续复盘可继续围绕：{'；'.join((recommendations or ['复核目标资产暴露服务', '提交误报反馈'])[:3])}",
        ]
    )
    return {
        "provider": "Local-Rulebook",
        "model": "security-playbook",
        "mode": "fallback",
        "content": _polish_content(content),
        "knowledge_hits": knowledge_hits,
        "strategy_plan": strategy_plan,
        "rag_enabled": True,
    }


def _attach_rag_context(base_response: dict, knowledge_hits: list[dict], strategy_plan: list[dict]) -> dict:
    response = dict(base_response)
    response["knowledge_hits"] = knowledge_hits
    response["strategy_plan"] = strategy_plan
    response["rag_enabled"] = True
    return response


def analyze_alert(alert: dict, preferred_model: str | None = None) -> dict:
    knowledge_hits = retrieve_knowledge(alert)
    strategy_plan = generate_strategy_plan(alert, knowledge_hits)
    system_prompt = (
        "你是通信网络安全运营专家。请基于模型检测结果、服务画像和可解释特征，"
        "结合检索到的安全知识库内容，输出适合系统内直接展示给用户的告警研判结果。"
        "需要覆盖总体判断、关键依据、业务影响和处置建议。"
        + _style_guide()
    )
    user_prompt = (
        "请分析以下告警，并给出自然、直接、可执行的回复。\n"
        f"告警数据：{_compact(alert)}\n"
        f"知识库检索结果：\n{_knowledge_digest(knowledge_hits)}\n"
        f"建议策略框架：{_compact(strategy_plan, limit=1000)}"
    )
    if _deepseek_enabled():
        try:
            return _attach_rag_context(
                _call_deepseek(system_prompt, user_prompt, preferred_model=preferred_model or DEFAULT_CHAT_MODEL),
                knowledge_hits,
                strategy_plan,
            )
        except Exception as exc:
            fallback = _fallback_alert_analysis(alert, knowledge_hits, strategy_plan)
            fallback["error"] = str(exc)
            return fallback
    return _fallback_alert_analysis(alert, knowledge_hits, strategy_plan)


def analyze_incident(incident: dict, preferred_model: str | None = None) -> dict:
    knowledge_hits = retrieve_knowledge(incident)
    strategy_plan = generate_strategy_plan(incident, knowledge_hits)
    system_prompt = (
        "你是 SOC 二线分析专家。请把安全事件转化为可执行的闭环处置建议，"
        "结合知识库内容覆盖事件判断、攻击链路、模型依据、处置动作和复盘建议。"
        + _style_guide()
    )
    user_prompt = (
        "请分析以下安全事件，并直接给出适合系统展示的自然回复。\n"
        f"事件数据：{_compact(incident)}\n"
        f"知识库检索结果：\n{_knowledge_digest(knowledge_hits)}\n"
        f"建议策略框架：{_compact(strategy_plan, limit=1000)}"
    )
    if _deepseek_enabled():
        try:
            return _attach_rag_context(
                _call_deepseek(system_prompt, user_prompt, preferred_model=preferred_model or DEFAULT_CHAT_MODEL),
                knowledge_hits,
                strategy_plan,
            )
        except Exception as exc:
            fallback = _fallback_incident_analysis(incident, knowledge_hits, strategy_plan)
            fallback["error"] = str(exc)
            return fallback
    return _fallback_incident_analysis(incident, knowledge_hits, strategy_plan)


def chat_with_assistant(question: str, context: dict | None = None, preferred_model: str | None = None) -> dict:
    rag_query = {"title": question, **(context or {})}
    knowledge_hits = retrieve_knowledge(rag_query)
    system_prompt = (
        "你是网络异常检测与智能告警系统里的智能助手。"
        "回答必须围绕数据导入、模型训练、异常检测、告警研判、事件处置和反馈闭环展开，"
        "并优先利用检索到的安全知识库内容。"
        + _style_guide()
    )
    user_prompt = (
        f"问题：{question}\n"
        f"上下文：{_compact(context or {})}\n"
        f"知识库检索结果：\n{_knowledge_digest(knowledge_hits)}"
    )
    if _deepseek_enabled():
        try:
            return _attach_rag_context(
                _call_deepseek(system_prompt, user_prompt, preferred_model=preferred_model or DEFAULT_CHAT_MODEL),
                knowledge_hits,
                [],
            )
        except Exception as exc:
            return {
                "provider": "Local-Rulebook",
                "model": "security-playbook",
                "mode": "fallback",
                "content": _polish_content(
                    "当前智能问答没有成功连接在线模型，我先给你一个可直接使用的结论。\n"
                    "- 展示时建议围绕“数据导入 - 模型训练 - 实时检测 - 告警研判 - 事件处置 - 反馈重训”这条主链路来讲。\n"
                    "- 如果现在需要继续演示，可以先使用系统已有的知识增强结果，不影响主流程展示。\n"
                    f"- 本次在线调用失败原因是：{exc}"
                ),
                "knowledge_hits": knowledge_hits,
                "strategy_plan": [],
                "rag_enabled": True,
            }
    return {
        "provider": "Local-Rulebook",
        "model": "security-playbook",
        "mode": "fallback",
        "content": _polish_content(
            "当前智能问答还没有接入在线模型，所以先使用本地知识增强结果回答你。\n"
            "- 你可以重点展示知识库检索、告警研判、事件报告和反馈闭环这几条主线。\n"
            "- 配置完成在线模型后，系统会进一步提供更自然的解释、问答和处置建议。"
        ),
        "knowledge_hits": knowledge_hits,
        "strategy_plan": [],
        "rag_enabled": True,
    }


def generate_incident_report(incident: dict, preferred_model: str | None = None) -> dict:
    analysis = analyze_incident(incident, preferred_model=preferred_model or DEFAULT_REASONER_MODEL)
    content = "\n\n".join(
        [
            "# DeepSeek 智能事件报告",
            f"事件编号：{incident.get('incident_no', '--')}",
            f"事件类型：{incident.get('attack_type', '--')}",
            f"风险等级：{incident.get('severity', '--')}",
            "",
            analysis["content"],
        ]
    )
    return {**analysis, "report": content}


def get_available_models() -> list[dict]:
    return [
        {
            "code": DEFAULT_CHAT_MODEL,
            "name": "DeepSeek Chat",
            "scene": "在线告警研判、页面交互分析",
            "recommended": True,
        },
        {
            "code": DEFAULT_REASONER_MODEL,
            "name": "DeepSeek Reasoner",
            "scene": "复杂事件复盘、深度推理、长报告生成",
            "recommended": False,
        },
    ]
