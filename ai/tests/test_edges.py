"""路由纯函数单测：不依赖 LLM，手搓 state dict 断言下一跳与「只读」契约。"""

import pytest

from deepresearch.domain.plan import ResearchPlan, ResearchStep
from deepresearch.graph.build import _ROUTE
from deepresearch.graph.edges import after_planner, after_researcher


def _plan(statuses: list[str], enough: bool = False) -> ResearchPlan:
    """按执行状态列表构造计划：_plan(["pending", "completed"]) 一行造好场景。"""
    steps = [
        ResearchStep(
            title=f"步骤{i}",
            description=f"描述{i}",
            need_web_search=False,
            execution_status=s,
        )
        for i, s in enumerate(statuses, 1)
    ]
    return ResearchPlan(title="t", thought="t", has_enough_context=enough, steps=steps)


def _state(plan: ResearchPlan | None) -> dict:
    return {} if plan is None else {"current_plan": plan}


def test_empty_steps_route_to_reporter():
    """Java 原版死循环 bug 的回归位：空 steps 必须视为完成，而非「还没研究」。"""
    assert after_researcher(_state(_plan([]))) == "reporter"


@pytest.mark.parametrize(("enough", "expected"), [(True, "reporter"), (False, "researcher")])
def test_after_planner(enough, expected):
    assert after_planner(_state(_plan(["pending"], enough=enough))) == expected


@pytest.mark.parametrize(
    ("statuses", "expected"),
    [
        (["pending"], "researcher"),
        (["completed", "pending"], "researcher"),  # pending 夹在中间也要抓到
        (["completed", "completed"], "reporter"),
        (["completed", "failed"], "reporter"),  # failed 是终态，不再循环
    ],
)
def test_after_researcher(statuses, expected):
    assert after_researcher(_state(_plan(statuses))) == expected


@pytest.mark.parametrize("router", [after_planner, after_researcher])
def test_no_plan_falls_back_to_reporter(router):
    """plan 缺失不 raise：交给 reporter 兜底（对照原版闸门：error 也放行）。"""
    assert router(_state(None)) == "reporter"


def test_routers_do_not_mutate_state():
    """路由是纯函数：谁将来改成「顺手标记步骤」，这里会红。"""
    plan = _plan(["pending", "completed"])
    after_planner(_state(plan))
    after_researcher(_state(plan))
    assert [s.execution_status for s in plan.steps] == ["pending", "completed"]
    assert plan.has_enough_context is False


def test_router_returns_are_registered_paths():
    """返回值必须落在 build.py 的 path_map 键里——否则 compile 期才炸，提前锁住。"""
    for router in (after_planner, after_researcher):
        for plan in (_plan([]), _plan(["pending"]), _plan(["completed"], enough=True), None):
            assert router(_state(plan)) in _ROUTE
