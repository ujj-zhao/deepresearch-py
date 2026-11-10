import operator
from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage

from .plan import ResearchPlan


class ResearchState(TypedDict, total=False):
    """研究状态模型：节点间共享的「黑板」，M1 只保留最小字段集。"""

    # ── 输入（请求时写入）──
    query: str                          # 用户问题（FR-1 的问题）
    session_id: str                     # 会话标识
    max_step_num: int                   # 最大步骤数
    auto_accept_plan: bool              # 是否自动通过计划（FR-6，M2 启用）
    enable_deepresearch: bool           # 是否深度研究（FR-2，M3 启用）

    # ── 中间产物 ──
    messages: Annotated[list[AnyMessage], operator.add]  # 消息历史（累加）
    current_plan: ResearchPlan | None   # 当前研究计划（覆盖：每次写回完整最新值）
    plan_iterations: int                # 计划迭代计数（FR 6.1 反死循环）
    research_results: Annotated[list[dict], operator.add]  # 各步骤研究结果（累加）
    site_information: Annotated[list[dict], operator.add]  # 检索来源（累加）

    # ── 输出 ──
    final_report: str                   # 最终报告（覆盖）



