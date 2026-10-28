"""中间件注册。

对应若依 Java 版：
- XssFilter（XSS 清洗，第 23 章实现）
- RefererFilter（防盗链）
- Spring CORS 配置
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ruoyi_fastapi.core.config import settings
from ruoyi_fastapi.core.response import R


class RefererCheckMiddleware(BaseHTTPMiddleware):
    """防盗链中间件，对应 Java RefererFilter。

    开关由 settings.REFERER_ENABLED 控制。
    """

    async def dispatch(self, request: Request, call_next):
        if not settings.REFERER_ENABLED:
            return await call_next(request)
        referer = request.headers.get("referer", "")
        if referer:
            allowed = any(d in referer for d in settings.REFERER_ALLOWED_DOMAINS)
            if not allowed:
                return JSONResponse(
                    content=R.fail(msg="非法来源访问", code=403).model_dump(by_alias=True),
                    status_code=403,
                )
        return await call_next(request)


def register_middlewares(app: FastAPI) -> None:
    """注册中间件。

    FastAPI middleware 是 LIFO（后注册的先执行）。
    顺序：CORS（最外层）-> 防盗链
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RefererCheckMiddleware)
