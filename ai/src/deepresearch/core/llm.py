"""LLM 工厂：按 models.json 注册表实例化 OpenAI 兼容客户端。

langchain-openai 1.x 的正确用法：`ChatOpenAI(model=..., base_url=..., api_key=...)`。
DeepSeek 走 OpenAI 兼容协议，未显式配置 LLM_API_BASE 时默认用其官方端点。
"""

from functools import lru_cache

from langchain_openai import ChatOpenAI

from .config import settings
from .models import load_model_registry

# DeepSeek OpenAI 兼容端点（LLM_API_BASE 未配置时的兜底）
_DEFAULT_BASE_URL = "https://api.deepseek.com"


@lru_cache
def get_model(name: str) -> ChatOpenAI:
    """按注册表名称获取 LLM 实例。

    :param name: models.json 中的模型名称（如 planner / researcher / reporter）
    :return: 配置好的 ChatOpenAI 实例
    """
    models = load_model_registry()
    spec = models[name]
    return ChatOpenAI(
        model=spec.model_name,
        api_key=settings.LLM_API_KEY or settings.DEEPSEEK_API_KEY,
        base_url=settings.LLM_API_BASE or _DEFAULT_BASE_URL,
        temperature=spec.temperature,
    )
