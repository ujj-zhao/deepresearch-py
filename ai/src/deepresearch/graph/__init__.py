"""Graph 编排层（P1 核心实现区）。

规划对标 admin 侧参考项目 spring-ai-alibaba-deepresearch：
    state.py   全局研究状态 OverAllState 的 Python 版（TypedDict / Pydantic）
    nodes/     图节点：coordinator、planner、researcher、reporter 等
    edges/     条件边： dispatcher 函数，读状态返回下一节点名
骨架期仅保留目录结构与职责注释，不写任何实现。
"""
