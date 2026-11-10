"""human_feedback 节点：计划人工审批（PRD FR-6），interrupt 暂停点，本身不调 LLM。

对照 Java 版 HumanFeedbackNode（理解报告 §4.2）：
- 原版：编译期 interruptBefore("human_feedback") 停在节点前，恢复时手工
  getState → withResume → withHumanFeedback(对象) 把决定塞进 state，节点再读键；
  驳回时还要 withoutResume() 让下一次路过能再暂停。
- 我们：节点内 interrupt(payload)——恢复值直接是 interrupt() 的返回值；
  节点被整体重新执行（interrupt 前必须无副作用！），再次路过天然会再暂停，
  withoutResume 的等价物是免费的。
- 迭代上限（PRD 6.1）：超限不再给驳回机会，直接强放行（原版同款）。

依赖：走到本节点要求编译时挂 checkpointer（架构文档 §14.4）。
"""

from langgraph.types import interrupt

from deepresearch.core.config import settings
from deepresearch.domain.state import ResearchState


def human_feedback(state: ResearchState) -> dict:
    """审批节点：暂停展示计划，按人工决定返回路由相关增量。

    resume 值契约（CLI 用 Command(resume=decision) 传入）：
        {"accept": bool, "feedback": str}
    - 通过 / 超限强放行 → feedback_content 清空 → 条件边去 researcher
    - 驳回并给意见     → feedback_content 写意见 → 条件边回 planner
    「驳回但意见为空」按通过处理——CLI 保证驳回必带非空意见，不发明第三分支。
    """
    plan = state["current_plan"]
    iterations = state.get("plan_iterations", 0)
    max_iterations = state.get("max_plan_iterations", settings.MAX_PLAN_ITERATIONS)

    if iterations >= max_iterations:
        # 强放行必须清掉上轮驳回残留的意见：after_human_feedback 看意见路由，
        # 不清就是 planner ⇄ human_feedback 死循环（路由从 state 现算的代价）
        return {"feedback_content": ""}

    decision = interrupt(
        {
            "title": plan.title,
            "thought": plan.thought,
            "steps": [
                {
                    "title": step.title,
                    "description": step.description,
                    "step_type": step.step_type,
                    "need_web_search": step.need_web_search,
                }
                for step in plan.steps
            ],
        }
    )

    accepted = bool(decision.get("accept"))
    return {
        "plan_iterations": iterations + 1,
        "feedback_content": "" if accepted else decision.get("feedback", ""),
    }
