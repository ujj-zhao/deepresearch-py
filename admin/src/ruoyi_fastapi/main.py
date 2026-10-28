"""FastAPI 应用入口。"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from ruoyi_fastapi.api.v1.router import router as v1_router
from ruoyi_fastapi.core.db import Base, engine
from ruoyi_fastapi.core.exception import register_exception_handlers
from ruoyi_fastapi.core.middleware import register_middlewares
from ruoyi_fastapi.core.redis import redis_client, redis_pool


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """应用启动时自动建表（仅开发期用，生产环境走 Alembic 迁移）。"""
    Base.metadata.create_all(bind=engine)
    redis_client.ping()  # 确保连接池已初始化
    yield
    redis_client.close()   # 释放客户端连接（redis-py 5+ 已移除 close_connection_pool 参数）
    redis_pool.disconnect()  # 显式传入的连接池不会随 close() 自动关闭，必须显式断开


app = FastAPI(
    title="RuoYi-FastAPI",
    description="基于 FastAPI 的后台管理系统（若依 Python 版）",
    version="0.1.0",
    lifespan=lifespan,
)

# 中间件注册（LIFO：后 add 的先执行）
register_middlewares(app)

# 全局异常处理
register_exception_handlers(app)

# 路由聚合：所有业务接口挂在 /api/v1 前缀下
app.include_router(v1_router, prefix="/api/v1")


@app.get("/")
def health_check():
    """健康检查。"""
    return {"status": "ok", "service": "ruoyi-fastapi"}
