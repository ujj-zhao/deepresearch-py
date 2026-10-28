"""图节点集合（P1 起逐步实现）。

每个节点是一个函数：读全局状态 -> 执行（可调用 LLM/工具）-> 返回状态更新。
对标 Java 版的 node 包（CoordinatorNode / PlannerNode / ResearcherNode / ReporterNode 等）。
"""
