from typing import Literal

from pydantic import BaseModel, Field


class ResearchStep(BaseModel):
    """研究步骤模型：计划内最小可执行研究单元（PRD 3.2/3.4）。"""

    title: str = Field(description="步骤标题")
    description: str = Field(description="步骤描述")
    step_type: Literal["research", "processing"] = Field(
        default="research", description="步骤类型：research 需检索研究，processing 为后处理"
    )
    need_web_search: bool = Field(description="是否需要网络搜索", default=True)
    execution_status: Literal["pending", "processing", "completed", "failed"] = Field(
        default="pending", description="执行状态（PRD 3.4 步骤状态机）"
    )
    execution_result: str | None = Field(description="执行结果", default=None)


class ResearchPlan(BaseModel):
    """研究计划模型：系统生成的结构化方案（PRD FR-5）。"""

    title: str = Field(description="研究计划标题")
    thought: str = Field(description="研究思路")
    has_enough_context: bool = Field(description="是否有足够的上下文")
    steps: list[ResearchStep] = Field(description="研究步骤")
