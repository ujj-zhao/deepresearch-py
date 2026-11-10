"""条件边路由：纯函数，读 state → 返回下一跳节点名。

契约（对照 Java 原版 dispatcher/*）：
- 只读 state，绝不修改、不调 LLM/工具、不抛业务异常；
- 原版是"节点算好写进 *_next_node 键，dispatcher 只读键"；
  M1 采用 Python 惯例——路由函数现场从 state 计算，少一个状态键。
"""

from deepresearch.domain.state import ResearchState


def after_planner(state: ResearchState) -> str:
    """planner 出口：上下文已足够 → reporter 直接成稿（跳过研究，原版同款捷径）；
    否则 → researcher。plan 缺失时交给 reporter 兜底，不 raise（对照原版闸门：error 也放行）。
    """
    plan = state.get("current_plan")
    if plan is None:
        return "reporter"
    return "reporter" if plan.has_enough_context else "researcher"


def after_researcher(state: ResearchState) -> str:
    """researcher 出口：还有 pending 步骤 → 自循环再认领一个；全部终态 → reporter。

    判据只有"有无 pending"一条：空 steps / 全 completed / 全 failed / plan 缺失
    统统视为完成——这正是绕开 Java 原版 research_team"空 steps 判未完成"死循环的关键。
    """
    plan = state.get("current_plan")
    if plan is None:
        return "reporter"
    has_pending = any(s.execution_status == "pending" for s in plan.steps)
    return "researcher" if has_pending else "reporter"
