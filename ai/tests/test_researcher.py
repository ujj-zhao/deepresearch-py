"""researcher 节点测试：monkeypatch get_model 用假 LLM，不依赖网络与真实模型。

覆盖五条契约：
1. 无事可做（无计划 / 无 pending 步骤）→ 返回空增量
2. 认领第一个 pending 步骤并写回终态（单次只处理一步）
3. 程序化预搜索注入 + site_information 记账；免搜/processing 步骤不检索
4. 深拷贝坑：state 里的原 plan 对象绝不能被原地修改
5. LLM 异常 → failed + "ERROR: " 前缀，不抛异常（PRD FR-7）
"""

import pytest
from langchain_core.messages import AIMessage

from deepresearch.domain.plan import ResearchPlan, ResearchStep
from deepresearch.graph.nodes import researcher as researcher_mod
from deepresearch.graph.nodes.researcher import researcher


class FakeLLM:
    """假 LLM：记录收到的消息，返回固定文本；boom=True 时抛异常。"""

    def __init__(self, reply: str = "研究结论", boom: bool = False):
        self.reply = reply
        self.boom = boom
        self.received: list = []

    def invoke(self, messages):
        self.received = list(messages)
        if self.boom:
            raise RuntimeError("模型服务不可用")
        return AIMessage(content=self.reply)


def _plan(*steps: ResearchStep) -> ResearchPlan:
    return ResearchPlan(title="测试计划", thought="略", has_enough_context=False, steps=list(steps))


def _step(title: str = "步骤", *, step_type: str = "research", need_search: bool = True,
          status: str = "pending") -> ResearchStep:
    return ResearchStep(
        title=title,
        description=f"{title}的描述",
        step_type=step_type,
        need_web_search=need_search,
        execution_status=status,
    )


@pytest.fixture
def fake_model(monkeypatch):
    """把 researcher 模块的 get_model 换成返回 FakeLLM，并暴露实例供断言。"""
    holder: dict[str, FakeLLM] = {}

    def _install(reply: str = "研究结论", boom: bool = False) -> FakeLLM:
        fake = FakeLLM(reply=reply, boom=boom)
        holder["llm"] = fake
        monkeypatch.setattr(researcher_mod, "get_model", lambda name: fake)
        return fake

    return _install


def test_no_plan_returns_empty():
    assert researcher({"query": "q"}) == {}


def test_all_steps_terminal_returns_empty(fake_model):
    llm = fake_model()
    state = {"current_plan": _plan(_step(status="completed"), _step("p2", status="failed"))}
    assert researcher(state) == {}
    assert llm.received == []  # 一步都不该执行


def test_claims_first_pending_only(fake_model):
    fake_model()
    s1, s2, s3 = _step("A"), _step("B"), _step("C", need_search=False)
    state = {"current_plan": _plan(s1, s2, s3)}
    update = researcher(state)

    new_plan = update["current_plan"]
    assert [s.execution_status for s in new_plan.steps] == ["completed", "pending", "pending"]
    assert new_plan.steps[0].execution_result == "研究结论"
    assert len(update["research_results"]) == 1
    assert update["research_results"][0]["title"] == "A"


def test_deepcopy_contract_state_plan_untouched(fake_model):
    """最隐蔽的坑：返回的是新对象，state 里的原 plan 必须保持 pending 原样。"""
    fake_model()
    original = _plan(_step("A"))
    state = {"current_plan": original}
    update = researcher(state)

    assert update["current_plan"] is not original
    assert original.steps[0].execution_status == "pending"
    assert original.steps[0].execution_result is None


def test_research_step_injects_presearch(fake_model):
    llm = fake_model()
    state = {"current_plan": _plan(_step("LangGraph"))}
    update = researcher(state)

    # 记账：mock 检索 3 条来源进 site_information（累加通道）
    assert len(update["site_information"]) == 3
    assert {"title", "url", "content"} <= set(update["site_information"][0])
    # 消息结构：system 模板 + 任务卡 + 引用约束 + 预搜索结果
    assert isinstance(llm.received[0].content, str)
    assert "{{ locale }}" not in llm.received[0].content  # 占位符已替换
    assert "LangGraph" in llm.received[1].content  # 任务卡
    assert "References section" in llm.received[2].content  # 引用硬约束
    assert "以下是搜索结果" in llm.received[3].content
    assert any("LangGraph" in m.content for m in llm.received[3:])  # query 用了 title+description


def test_no_search_for_processing_or_flag_off(fake_model):
    llm = fake_model()
    update = researcher({"current_plan": _plan(_step("汇总", step_type="processing"))})
    assert update["site_information"] == []
    assert len(llm.received) == 3  # 无预搜索消息
    assert update["research_results"][0]["status"] == "completed"

    llm2 = fake_model()
    update2 = researcher({"current_plan": _plan(_step("推理", need_search=False))})
    assert update2["site_information"] == []
    assert len(llm2.received) == 3


def test_llm_failure_marks_step_failed_not_raise(fake_model):
    fake_model(boom=True)
    state = {"current_plan": _plan(_step("A"))}
    update = researcher(state)  # 不应抛异常

    step = update["current_plan"].steps[0]
    assert step.execution_status == "failed"
    assert step.execution_result.startswith("ERROR: ")
    assert update["research_results"][0]["status"] == "failed"
    # 检索已发生的来源仍记账（事实通道不因后续失败而丢弃）
    assert len(update["site_information"]) == 3


def test_non_string_content_coerced(fake_model):
    """部分 provider 返回内容块列表：统一压成纯文本写回，不留 repr 垃圾。"""
    fake_model(reply=[{"type": "text", "text": "块1"}, {"type": "text", "text": "块2"}])
    update = researcher({"current_plan": _plan(_step("A"))})
    assert update["research_results"][0]["content"] == "块1\n块2"
    assert update["current_plan"].steps[0].execution_status == "completed"
