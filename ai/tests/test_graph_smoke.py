"""图级冒烟测试：假模型 + mock 检索跑通全图，验证的是"管道"而非模型输出质量。

覆盖三件事：
1. 拓扑与自循环：planner→researcher 循环 N 圈（N=步骤数）→reporter→END；
2. reducer 合并：累加通道（research_results/site_information/messages）与
   覆盖通道（current_plan/final_report）在真实图执行下的行为；
3. 失败降级贯穿全图（FR-7）：LLM 抛错 → 步骤 failed → 图继续 → 报告标注 FAILED。

真 LLM 的输出质量不在本测试职责内（那是真模型验收的事）。
"""

from langchain_core.messages import AIMessage

from deepresearch.domain.plan import ResearchPlan, ResearchStep
from deepresearch.graph.build import build_graph
from deepresearch.graph.nodes import planner as planner_mod
from deepresearch.graph.nodes import researcher as researcher_mod


class FakePlanner:
    """顶替 with_structured_output(ResearchPlan) 链：invoke 直接返回给定计划。"""

    def __init__(self, plan: ResearchPlan) -> None:
        self._plan = plan

    def with_structured_output(self, schema, **kwargs):
        return self

    def invoke(self, messages):
        return self._plan.model_copy(deep=True)


class FakeResearcher:
    """计数 spy：每圈返回不同文本，可断言自循环恰好转了 N 圈。"""

    def __init__(self) -> None:
        self.calls = 0

    def invoke(self, messages):
        self.calls += 1
        return AIMessage(content=f"研究结果{self.calls}")


class BoomResearcher:
    """模拟 LLM 调用抛错的 researcher。"""

    def invoke(self, messages):
        raise RuntimeError("LLM 挂了")


def _make_plan(enough: bool = False) -> ResearchPlan:
    return ResearchPlan(
        title="LangGraph 调研",
        thought="t",
        has_enough_context=enough,
        steps=[
            ResearchStep(title="技术背景", description="d1", need_web_search=True),
            ResearchStep(
                title="汇总结论", description="d2",
                step_type="processing", need_web_search=False,
            ),
        ],
    )


def _run(monkeypatch, plan: ResearchPlan, researcher=None):
    """把假模型装进两个节点模块的命名空间（节点在调用时才查模块全局名）。"""
    researcher = researcher or FakeResearcher()
    monkeypatch.setattr(planner_mod, "get_model", lambda name: FakePlanner(plan))
    monkeypatch.setattr(researcher_mod, "get_model", lambda name: researcher)
    out = build_graph().invoke({"query": "LangGraph 怎么样", "max_step_num": 3})
    return out, researcher


def test_full_loop_completes_all_steps(monkeypatch):
    out, researcher = _run(monkeypatch, _make_plan())
    # 自循环圈数 = 步骤数：第 3 圈不该再进 researcher 节点（路由函数会跑，但节点不调）
    assert researcher.calls == 2
    assert [s.execution_status for s in out["current_plan"].steps] == ["completed", "completed"]
    # 累加通道：两步各贡献一条结果；只有步骤 1 检索，mock 恒返 3 条来源
    assert len(out["research_results"]) == 2
    assert len(out["site_information"]) == 3
    assert len(out["messages"]) == 2  # planner/reporter 不写 messages
    # 覆盖通道：reporter 的成品
    assert "技术背景" in out["final_report"]
    assert "汇总结论" in out["final_report"]
    assert "参考来源" in out["final_report"]


def test_enough_context_skips_research(monkeypatch):
    """planner 出口捷径：has_enough_context=True 直接去 reporter，一圈都不转。"""
    out, researcher = _run(monkeypatch, _make_plan(enough=True))
    assert researcher.calls == 0
    assert "无研究结果" in out["final_report"]


def test_step_failure_does_not_break_graph(monkeypatch):
    """FR-7 端到端：LLM 抛错不中断图，两步都 failed，报告仍产出并标注。"""
    out, _ = _run(monkeypatch, _make_plan(), researcher=BoomResearcher())
    assert [s.execution_status for s in out["current_plan"].steps] == ["failed", "failed"]
    assert out["final_report"].startswith("# LangGraph 调研")
    assert "FAILED" in out["final_report"]
    assert "ERROR:" in out["final_report"]
