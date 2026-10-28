# log/router.py
from fastapi import APIRouter
from .routers import cache, logininfor, online, operlog, server

router = APIRouter(prefix="/monitor", tags=["监控-日志"])
router.include_router(logininfor.router)
router.include_router(operlog.router)
router.include_router(online.router)
router.include_router(server.router)
router.include_router(cache.router)
