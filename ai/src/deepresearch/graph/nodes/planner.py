"""planner 节点：根据用户问题生成结构化研究计划（PRD FR-5）。

对照 Java 版 PlannerNode.apply()：
- 模板消息（本文件的 planner.md，渲染占位符后作为 system 消息）
- 用户 query 作为独立的 human 消息追加（原版不是模板占位符！）
- BeanOutputConverter<Plan> ≈ with_structured_output(ResearchPlan)
M1 暂不实现：短用户角色记忆、背景调查消息、反馈消息、RAG 消息（M2/M3 再补）。
"""

from datetime import date
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage

from deepresearch.core.llm import get_model
from deepresearch.domain.plan import ResearchPlan
from deepresearch.domain.state import ResearchState

# prompts/ 在 ai/ 根下：nodes -> graph -> deepresearch -> src -> ai
PROMPTS_DIR = Path(__file__).resolve().parents[4] / "prompts"

# 原版从未替换 {{ locale }}（报告第 6 节指出的 bug），移植时显式定为中文
_LOCALE = "zh-CN"


def planner(state: ResearchState) -> dict:
    """计划节点：读 query/max_step_num，产出 current_plan。"""
    query = state.get("query", "")
    max_step_num = state.get("max_step_num", 3)

    template = (PROMPTS_DIR / "planner.md").read_text(encoding="utf-8")
    system_prompt = (
        template.replace("{{ CURRENT_TIME }}", date.today().isoformat())
        .replace("{{ max_step_num }}", str(max_step_num))
        .replace("{{ locale }}", _LOCALE)
    )

    # DeepSeek 不支持 json_schema 型 response_format，须走 function_calling（工具调用）
    llm = get_model("planner").with_structured_output(ResearchPlan, method="function_calling")
    plan: ResearchPlan | None = None
    for _ in range(3):  # 实测 DeepSeek 偶发返回空 tool_calls → parsed 为 None，重试兜底
        plan = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=query)])
        if plan is not None:
            break
    if plan is None:
        raise RuntimeError(f"planner 连续 3 次未产出合法计划: {query[:50]}")

    # 代码兜底：不赌 prompt 遵守步骤上限（PRD FR-5）
    plan.steps = plan.steps[:max_step_num]
    return {"current_plan": plan}
