"""researcher 节点：认领并执行计划中的一个研究步骤（PRD FR-4/FR-7）。

对照 Java 版 ResearcherNode.apply()（理解报告 §3.2.3）：
- 认领：原版 4 个 researcher 并行，靠精确匹配 assigned_<自己节点名> 防重复认领；
  M1 单节点串行，改为认领**第一个 pending 步骤**，多次调用靠条件边自循环（架构文档 §6.2）。
- 检索：原版是「程序化预搜索」——节点内直调 SearchInfoService 拿结构化结果注入消息，
  **不是** LLM 自主 tool-calling（researcher.md 里宣传的 searchFilterTool 原版从未绑定，
  照抄此机制：直调 @tool web_search）。
- 消息拼装顺序照抄原版：system 模板 → 任务卡 → 引用格式硬约束 → 预搜索结果。
- PROCESSING 步骤：原版分发给 coder 且要求所有 research 先终态；
  M1 无 coder，降级为无检索的 LLM 分析（真代码执行延到 P3）。
- 值语义（本课最隐蔽的坑）：state["current_plan"] 是活对象，必须**先深拷贝再修改**，
  返回完整新对象；原地改会污染 state、违反"节点只返回增量"的契约。
- 错误处理：LLM 失败 → 步骤标 failed + "ERROR: " 前缀写回，**不抛异常**（PRD FR-7，
  对应原版 StateUtil.handleStepError：闸门把 error 当终态放行，图不中断）。
"""

from copy import deepcopy
from datetime import date
from functools import lru_cache
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from deepresearch.core.llm import get_model
from deepresearch.core.tooling import web_search
from deepresearch.domain.plan import ResearchStep
from deepresearch.domain.state import ResearchState

# prompts/ 在 ai/ 根下：nodes -> graph -> deepresearch -> src -> ai（与 planner 一致）
PROMPTS_DIR = Path(__file__).resolve().parents[4] / "prompts"

# 原版从未替换 {{ locale }}（报告第 6 节指出的 bug），移植时显式定为中文（与 planner 一致）
_LOCALE = "zh-CN"

# 原版 ResearcherNode L128-130 的引用格式硬约束，原文照抄
_CITATION_RULE = (
    "IMPORTANT: DO NOT include inline citations in the text. Instead, track all sources "
    "and include a References section at the end using link reference format. "
    "Include an empty line between each citation for better readability. "
    "Use this format for each reference:\n- [Source Title](URL)\n- [Source Title](URL)"
)


@lru_cache
def _build_system_prompt() -> str:
    """渲染 researcher.md 模板：替换 CURRENT_TIME 与 locale 两类占位符。"""
    template = (PROMPTS_DIR / "researcher.md").read_text(encoding="utf-8")
    return (
        template.replace("{{ CURRENT_TIME }}", date.today().isoformat())
        .replace("{{ locale }}", _LOCALE)
    )


def _build_task_message(step: ResearchStep) -> str:
    """任务卡（原版 buildTaskPrompt L225-238 的格式）。"""
    return f"# Current Task\n\n## Title\n\n{step.title}\n\n## Description\n\n{step.description}"


def _build_search_message(results: list[dict]) -> str:
    """预搜索结果注入（原版格式含"权重"行；M1 mock 无 weight 字段，暂缺该行）。"""
    blocks = [f"标题: {r['title']}\n内容: {r['content']}\nurl: {r['url']}" for r in results]
    return "以下是搜索结果：\n\n" + "\n\n".join(blocks)


def _extract_text(response) -> str:
    """把 LLM 回复压成纯文本。DeepSeek 恒返回 str；内容块列表是防御性兜底。"""
    content = response.content
    if isinstance(content, str):
        return content
    parts = [b.get("text", "") if isinstance(b, dict) else str(b) for b in content]
    return "\n".join(p for p in parts if p)


def researcher(state: ResearchState) -> dict:
    """研究节点：单次认领一个 pending 步骤，执行后返回增量更新。

    返回值契约（LangGraph 按 reducer 合并进全局 state）：
    - current_plan: 深拷贝后写回步骤终态的**完整**计划对象（覆盖通道）
    - research_results: 本次步骤的结果（累加通道）
    - site_information: 本次预搜索的检索来源（累加通道；无检索时为空列表）
    - messages: 研究全文的 AIMessage（累加通道，供 reporter/调试消费）
    无 pending 步骤（或无计划）→ 返回 {}，条件边据此路由到 reporter。
    """
    plan = state.get("current_plan")
    if plan is None:
        return {}

    step_index = next(
        (i for i, s in enumerate(plan.steps) if s.execution_status == "pending"),
        None,
    )
    if step_index is None:
        return {}  # 全部步骤已终态：本轮无事可做，交给条件边离开自循环

    # 先拷贝再修改：state 里的 plan 对象绝不能原地动
    plan = deepcopy(plan)
    step = plan.steps[step_index]

    messages: list = [
        SystemMessage(content=_build_system_prompt()),
        HumanMessage(content=_build_task_message(step)),
        HumanMessage(content=_CITATION_RULE),
    ]

    # 程序化预搜索：仅 research 且需要联网时（processing / 免搜步骤走纯 LLM 分析）
    site_information: list[dict] = []
    if step.step_type == "research" and step.need_web_search:
        site_information = web_search.invoke({"query": f"{step.title} {step.description}"})
        if site_information:
            messages.append(HumanMessage(content=_build_search_message(site_information)))

    try:
        text = _extract_text(get_model("researcher").invoke(messages))
        step.execution_status = "completed"
    except Exception as e:  # 单步失败不中断整图（FR-7），对应原版 handleStepError
        step.execution_status = "failed"
        text = f"ERROR: {e}"

    step.execution_result = text
    return {
        "current_plan": plan,
        "research_results": [
            {"title": step.title, "status": step.execution_status, "content": text}
        ],
        "site_information": site_information,
        "messages": [AIMessage(content=text)],
    }
