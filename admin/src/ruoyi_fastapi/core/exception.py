"""全局异常处理。

对应若依 Java 版 GlobalExceptionHandler + ServiceException。
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from ruoyi_fastapi.core.response import R


class ServiceException(Exception):
    """业务异常，对应若依 ServiceException。

    用法：
        raise ServiceException("用户不存在", code=404)
        raise ServiceException("密码错误次数过多，请 10 分钟后再试")

    handler 会捕获并以 R.fail 结构返回。
    HTTP 状态码统一返回 200（与若依一致），靠响应体里的 code 字段区分业务结果。
    """

    def __init__(self, msg: str = "操作失败", code: int = 500) -> None:
        self.msg = msg
        self.code = code
        super().__init__(msg)


def register_exception_handlers(app: FastAPI) -> None:
    """注册全局异常处理器。"""

    @app.exception_handler(ServiceException)
    async def _service_handler(_: Request, exc: ServiceException) -> JSONResponse:
        return JSONResponse(
            content=R.fail(msg=exc.msg, code=exc.code).model_dump(by_alias=True),
            status_code=200,
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            content=R.fail(msg="请求参数错误", code=400).model_dump(by_alias=True),
            status_code=400,
        )

    @app.exception_handler(Exception)
    async def _global_handler(_: Request, exc: Exception) -> JSONResponse:
        # 生产环境应在此记录完整 traceback 到日志
        return JSONResponse(
            content=R.fail(msg=f"服务器错误: {exc}", code=500).model_dump(by_alias=True),
            status_code=500,
        )
