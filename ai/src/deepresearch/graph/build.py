"""图组装：M1 拓扑的唯一定义处（对照 Java DeepResearchConfiguration.deepResearch()）。

拓扑：START → planner →(after_planner)→ researcher ⇄(after_researcher 自循环)→ reporter → END
"""

from langgraph.graph import END, START, StateGraph

from deepresearch.domain.state import ResearchState
from deepresearch.graph.edges import after_planner, after_researcher
from deepresearch.graph.nodes.planner import planner
from deepresearch.graph.nodes.reporter import reporter
from deepresearch.graph.nodes.researcher import researcher

# 两条条件边共用的 path_map：路由函数返回值必须落在这些键里
_ROUTE = {"researcher": "researcher", "reporter": "reporter"}


def build_graph():
    """组装并编译最小闭环图，返回可 invoke/astream 的编译产物（供 CLI 与测试用）。"""
    builder = StateGraph(ResearchState)
    builder.add_node("planner", planner)
    builder.add_node("researcher", researcher)
    builder.add_node("reporter", reporter)

    builder.add_edge(START, "planner")
    # 注意：planner/researcher 的出口完全由条件边负责，
    # 绝不能再对同一节点 add_edge 固定边——"固定边+条件边"并存会在 compile 时报多重出边。
    builder.add_conditional_edges("planner", after_planner, _ROUTE)
    builder.add_conditional_edges("researcher", after_researcher, _ROUTE)
    builder.add_edge("reporter", END)

    return builder.compile()
