"""v1 路由聚合。

预留接口规划（路线图对应）：
    P2  POST /research        发起研究任务，SSE 流式返回进度与结果
    P2  POST /research/{id}/feedback  人工反馈（interrupt 恢复）
    P4  GET  /research/{id}   任务详情 / 报告读取
骨架期仅注册探活接口，业务路由随各阶段补充。
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def v1_health():
    """v1 探活。"""
    return {"status": "ok", "version": "v1"}
