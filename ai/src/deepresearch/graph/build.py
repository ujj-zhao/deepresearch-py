"""图组装：M2 拓扑的唯一定义处（对照 Java DeepResearchConfiguration.deepResearch()）。

拓扑：START → planner →(after_planner)→ [human_feedback 审批环 | researcher]
      ⇄(after_researcher 自循环)→ reporter → END
checkpointer 由调用方注入（存哪是 CLI/测试的策略，组装不关心）；
不传 = 保持 M1 行为，但走到 human_feedback 的 interrupt 会报错（架构文档 §14.4）。
"""

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from deepresearch.domain.state import ResearchState
from deepresearch.graph.edges import (
    after_human_feedback,
    after_planner,
    after_researcher,
)
from deepresearch.graph.nodes.human_feedback import human_feedback
from deepresearch.graph.nodes.planner import planner
from deepresearch.graph.nodes.reporter import reporter
from deepresearch.graph.nodes.researcher import researcher

# 三条条件边共用的 path_map：路由函数返回值必须落在这些键里
_ROUTE = {
    "researcher": "researcher",
    "reporter": "reporter",
    "human_feedback": "human_feedback",
}


def build_graph(checkpointer: BaseCheckpointSaver | None = None):
    """组装并编译 M2 图，返回可 invoke/astream 的编译产物（供 CLI 与测试用）。"""
    builder = StateGraph(ResearchState)
    builder.add_node("planner", planner)
    builder.add_node("human_feedback", human_feedback)
    builder.add_node("researcher", researcher)
    builder.add_node("reporter", reporter)

    builder.add_edge(START, "planner")
    # 注意：planner/human_feedback/researcher 的出口完全由条件边负责，
    # 绝不能再对同一节点 add_edge 固定边——"固定边+条件边"并存会在 compile 时报多重出边。
    builder.add_conditional_edges("planner", after_planner, _ROUTE)
    builder.add_conditional_edges("human_feedback", after_human_feedback, _ROUTE)
    builder.add_conditional_edges("researcher", after_researcher, _ROUTE)

    builder.add_edge("reporter", END)

    return builder.compile(checkpointer=checkpointer)
