"""FastAPI 应用入口。"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from deepresearch.api.v1.router import router as v1_router
from deepresearch.core.config import settings


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """应用生命周期。P1 阶段在此初始化图运行时 / 检查点器等资源。"""
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="Graph 编排的多智能体深度研究服务（Python 版）",
    version="0.1.0",
    lifespan=lifespan,
)

# 路由聚合：业务接口挂在 /api/v1 前缀下（与 admin 服务前缀保持一致）
app.include_router(v1_router, prefix="/api/v1")


@app.get("/")
def health_check():
    """健康检查。"""
    return {"status": "ok", "service": settings.APP_NAME}
