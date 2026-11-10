"""LangGraph 最小冒烟测试。

用一个两节点的玩具图验证 P1 依赖的三个核心机制：
1. StateGraph 的状态流转（节点返回 dict，LangGraph 负责合并进 state）
2. Annotated reducer（列表字段的累加合并，而不是覆盖）
3. 条件边（根据 state 动态决定下一个节点或结束）

这个文件是 P1 的基线：图核心实现的集成测试将复用同样的断言思路。
"""

import operator
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph


# 定义状态模型
class State(TypedDict):
    """玩具图状态。

    steps 标注了 reducer：各节点返回的列表会被"累加"合并；
    result 没有标注：后写的节点直接覆盖前一个节点的值。
    """

    steps: Annotated[list[str], operator.add]
    result: str

# 定义节点
def node_plan(state: State) -> dict:
    """模拟规划节点：追加一步，并写一个中间结果。"""
    return {"steps": ["plan"], "result": "planned"}


# 定义节点
def node_run(state: State) -> dict:
    """模拟执行节点：再追加一步，并写最终结果。"""
    return {"steps": ["run"], "result": "done"}


# 定义条件边路由函数
def route_after_plan(state: State) -> str:
    """条件边路由函数：返回下一个节点的名字或 END。"""
    if state["result"] == "planned":
        return "run"
    return END

# 定义图
def build_graph():
    """组装玩具图：START -> plan -> (条件边) -> run -> END。"""
    builder = StateGraph(State)
    builder.add_node("plan", node_plan)
    builder.add_node("run", node_run)
    builder.add_edge(START, "plan")
    builder.add_conditional_edges("plan", route_after_plan, {"run": "run", END: END})
    builder.add_edge("run", END)
    return builder.compile()


# 测试 reducer 字段累加、普通字段覆盖
def test_reducer_accumulates_and_plain_field_overwrites():
    """reducer 字段累加、普通字段覆盖，是 LangGraph 状态合并的两条基本规则。"""
    graph = build_graph()
    final = graph.invoke({"steps": [], "result": ""})

    # plan 和 run 各自只返回了自己那一步，reducer 把它们累加成完整列表
    assert final["steps"] == ["plan", "run"]
    # result 被 run 节点覆盖为最终值
    assert final["result"] == "done"

# 测试条件边按 state 路由
def test_conditional_edge_routes_to_next_node():
    """条件边按 state 路由：planned 走 run 分支，图完整跑通到 END。"""
    graph = build_graph()
    final = graph.invoke({"steps": [], "result": ""})

    assert final["result"] == "done"

# 测试图结构
def test_graph_structure():
    """编译后的图可以直接检查拓扑，P1 的 build.py 测试会用到同样的手段。"""
    graph = build_graph()
    nodes = set(graph.get_graph().nodes)

    assert {"plan", "run"} <= nodes

if __name__ == "__main__":
    graph = build_graph()

    # 1. 看图拓扑：打印纯文本 mermaid（不要用 draw_mermaid_png，它依赖外网 mermaid.ink 会超时）
    print(graph.get_graph().draw_mermaid())

    # 2. 逐步观察执行：stream_mode="updates" 每个节点跑完立刻吐出它的增量返回值
    for chunk in graph.stream({"steps": [], "result": ""}, stream_mode="updates"):
        for node_name, update in chunk.items():
            print(f"[执行节点] {node_name} -> {update}")

    # 3. 想看更细的内部日志（superstep、channel 读写），用 debug=True
    final = graph.invoke({"steps": [], "result": ""}, debug=True)
    print("最终 state:", final)

    test_reducer_accumulates_and_plain_field_overwrites()
