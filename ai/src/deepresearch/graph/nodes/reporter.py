"""reporter 节点（M1 最小版）：把各步骤研究结果拼成最终报告（PRD FR-8）。

对照 Java 版 ReporterNode（理解报告 §3.3）：原版把 research_results / site_information
汇总后交给 reporterAgent（LLM，system=reporter.md）润色成稿。
M1 先用**纯代码拼接**跑通端到端闭环，LLM 成稿是下一步升级——
届时只替换本函数中间的组装逻辑，读/写 state 的契约不变。

契约：
- 读 research_results（累加通道，元素 {title, status, content}，由 researcher 定义）
- 读 current_plan（仅取报告标题）、site_information（汇总参考来源）
- 返回 {"final_report": markdown 字符串}（覆盖通道）
"""

from deepresearch.domain.state import ResearchState


def reporter(state: ResearchState) -> dict:
    """报告节点：无 LLM 的最小拼接实现，保证 M1 拓扑可端到端 invoke。"""
    plan = state.get("current_plan")
    title = plan.title if plan is not None else "研究报告"
    results = state.get("research_results", [])

    if not results:
        return {"final_report": f"# {title}\n\n（无研究结果：计划为空或全部失败）"}

    sections = [f"# {title}\n"]
    for i, r in enumerate(results, 1):
        mark = "completed" if r["status"] == "completed" else "FAILED"
        sections.append(f"## 步骤 {i}：{r['title']}（{mark}）\n\n{r['content']}\n")

    sources = state.get("site_information", [])
    if sources:
        refs = "\n".join(f"- [{s['title']}]({s['url']})" for s in sources)
        sections.append(f"## 参考来源\n\n{refs}\n")

    return {"final_report": "\n".join(sections)}
