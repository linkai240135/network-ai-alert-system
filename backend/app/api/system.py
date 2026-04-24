import os

from flask import current_app

from . import api_bp
from ..services.llm_service import get_available_models
from ..utils.constants import FEATURE_COLUMNS
from ..services.settings_service import get_setting_map
from ..utils.response import success


@api_bp.get("/system/overview")
def system_overview():
    database_uri = current_app.config["SQLALCHEMY_DATABASE_URI"]
    settings = get_setting_map()
    return success(
        {
            "featureColumns": FEATURE_COLUMNS,
            "databaseMode": "MySQL" if "mysql" in database_uri.lower() else "SQLite",
            "projectStyle": "Enterprise Engineering Edition",
            "llmLayer": {
                "provider": "DeepSeek",
                "enabled": settings.get("deepseek_enabled", "false"),
                "keyConfigured": bool(os.getenv("DEEPSEEK_API_KEY")),
                "model": settings.get("deepseek_model", "deepseek-chat"),
                "availableModels": get_available_models(),
                "capabilities": ["告警研判", "事件报告", "安全问答", "RAG知识检索", "关键词+向量混合召回", "命中分数可视化", "处置建议生成"],
            },
            "innovationTags": [
                "FT-Transformer 已知攻击分类",
                "Deep SVDD 未知异常检测",
                "Conformal 可信校准",
                "Attention 可解释分析",
                "DeepSeek 智能研判",
                "安全知识库 RAG",
                "双路混合检索",
                "处置策略生成",
                "误报反馈反哺训练",
                "真实数据训练链路",
                "事件闭环处置",
                "企业级安全运营大屏",
            ],
        }
    )
