"""日志模块业务逻辑。

对应若依：
- AsyncFactory.recordLogininfor → record_logininfor
- @Log 注解 + LogAspect 切面 + AsyncFactory.recordOper → @log 装饰器
"""

import functools
import inspect
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from fastapi import BackgroundTasks, Request
from pydantic import BaseModel
from user_agents import parse

from ruoyi_fastapi.core.enums import BusinessType, OperatorType
from ruoyi_fastapi.core.db import SessionLocal
from ruoyi_fastapi.core.ip_utils import get_client_ip, get_real_address_by_ip
from ruoyi_fastapi.modules.login.schemas import LoginUser

from .models import SysLogininfor, SysOperLog

logger = logging.getLogger(__name__)

# 对应若依 AsyncManager：单线程池后台落库，日志失败不影响主流程
_ASYNC_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="async-oper-log")


def record_logininfor(username: str, status: str, msg: str, request: Request) -> None:
    """记录登录日志（对应若依 AsyncManager.me().execute(AsyncFactory.recordLogininfor(...))）。

    请求线程内只提取纯值数据（Request 对象不能跨线程使用），
    落库投递到单线程池异步执行，与登录主流程解耦；
    日志记录失败只落错误日志，绝不影响登录主流程。
    """
    ipaddr = get_client_ip(request)
    user_agent = request.headers.get("user-agent", "")
    _ASYNC_EXECUTOR.submit(
        _save_logininfor, username, ipaddr, user_agent, status, msg or ""
    )


def _save_logininfor(
    username: str, ipaddr: str, user_agent: str, status: str, msg: str
) -> None:
    """后台任务：解析 UA/归属地并用独立会话落库（对应 AsyncFactory.recordLogininfor 任务体）。"""
    try:
        ua = parse(user_agent)
        info = SysLogininfor(
            user_name=username[:50],
            ipaddr=ipaddr[:128],
            login_location=get_real_address_by_ip(ipaddr),
            browser=str(ua.browser.family)[:50],
            os=str(ua.os.family)[:50],
            status=status,
            msg=msg[:255],
            login_time=datetime.now(),
        )
        with SessionLocal() as session:
            session.add(info)
            session.commit()
    except Exception:
        logger.exception("记录登录日志失败")

def log(
    title: str,
    business_type: BusinessType = BusinessType.OTHER,
    operator_type: OperatorType = OperatorType.MANAGE,
    is_save_request_data: bool = True,
    is_save_response_data: bool = True,
):
    """操作日志装饰器（对应若依 @Log 注解 + LogAspect 切面）。

    用法：@log(title="用户管理", business_type=BusinessType.INSERT)
    - 成功/异常都落库 sys_oper_log（异常 status=1），异常原样重新抛出
    - 透传原函数返回值；functools.wraps 保留函数签名（FastAPI 依赖签名生成 OpenAPI）
    - 同步/异步函数分别包装，避免 async 函数被同步 wrapper 破坏
    """
    def decorator(func):
        def _record(args, kwargs, *, result=None, error=None, cost_ms=0):
            _record_oper_log(
                func, title, business_type, operator_type,
                is_save_request_data, is_save_response_data,
                args, kwargs, result=result, error=error, cost_ms=cost_ms,
            )

        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def awrapper(*args, **kwargs):
                start = time.perf_counter()
                result, error = None, None
                try:
                    result = await func(*args, **kwargs)
                    return result
                except Exception as exc:
                    error = exc
                    raise
                finally:
                    _record(args, kwargs, result=result, error=error,
                            cost_ms=int((time.perf_counter() - start) * 1000))
            return awrapper

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result, error = None, None
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as exc:
                error = exc
                raise
            finally:
                _record(args, kwargs, result=result, error=error,
                        cost_ms=int((time.perf_counter() - start) * 1000))
        return wrapper
    return decorator

def _find_request(args: tuple, kwargs: dict) -> Request | None:
    """从路由函数参数中定位 Request（对应 LogAspect 里取 ServletRequestAttributes）。"""
    if isinstance(kwargs.get("request"), Request):
        return kwargs["request"]
    return next((a for a in args if isinstance(a, Request)), None)


def _resolve_oper_name(kwargs: dict) -> str:
    """从依赖注入的 LoginUser 取操作人（对应 SecurityUtils.getUsername()，取不到留空）。

    按类型扫描而非参数名：权限依赖可能绑定成 _perms 等任意名字，值都是 LoginUser。
    """
    for value in kwargs.values():
        if isinstance(value, LoginUser) and value.user is not None:
            return value.user.user_name
    return ""


def _build_oper_param(kwargs: dict) -> str:
    """序列化路由函数入参（对应 LogAspect 的 paramsJson）。

    跳过 request/response/db 等框架对象、下划线开头的约定忽略参数（_perms 等）、
    LoginUser 会话对象（含 token 与完整用户数据，禁止入日志），
    password 类字段脱敏，不可 JSON 序列化的对象直接跳过，超长截断到列宽 2000。
    """
    params: dict = {}
    for key, value in kwargs.items():
        if key in ("request", "response", "db", "background_tasks"):
            continue
        if key.startswith("_"):
            continue
        if isinstance(value, LoginUser):
            continue
        if "password" in key.lower():
            params[key] = "******"
            continue
        if isinstance(value, BaseModel):
            params[key] = value.model_dump(mode="json", by_alias=True)
            continue
        try:
            json.dumps(value)
            params[key] = value
        except (TypeError, ValueError):
            continue
    return json.dumps(params, ensure_ascii=False, default=str)[:2000]


def _build_json_result(result) -> str:
    """序列化响应结果（对应 LogAspect 的 jsonResult，超长截断到列宽 2000）。"""
    if result is None:
        return ""
    if isinstance(result, BaseModel):
        return result.model_dump_json(by_alias=True)[:2000]
    return str(result)[:2000]


def _save_oper_log(payload: dict) -> None:
    """后台任务：解析操作地点并用独立会话落库（对应 AsyncFactory.recordOper）。

    写库逻辑在后台执行，任何失败只落错误日志，绝不能影响主流程。
    """
    try:
        payload["oper_location"] = get_real_address_by_ip(payload.get("oper_ip", ""))
        info = SysOperLog(**payload)
        with SessionLocal() as session:
            session.add(info)
            session.commit()
    except Exception:
        logger.exception("记录操作日志失败")


def _record_oper_log(
    func,
    title: str,
    business_type: BusinessType,
    operator_type: OperatorType,
    is_save_request_data: bool,
    is_save_response_data: bool,
    args: tuple,
    kwargs: dict,
    result=None,
    error: Exception | None = None,
    cost_ms: int = 0,
) -> None:
    """组装一条操作日志并提交后台落库（对应 LogAspect.recordOper）。"""
    request = _find_request(args, kwargs)
    payload = {
        "title": title,
        "business_type": int(business_type),
        "method": f"{func.__module__}.{func.__qualname__}",
        "request_method": request.method if request else "",
        "operator_type": int(operator_type),
        "oper_name": _resolve_oper_name(kwargs),
        "oper_url": request.url.path if request else "",
        "oper_ip": get_client_ip(request) if request else "",
        "oper_param": _build_oper_param(kwargs) if is_save_request_data else "",
        "json_result": _build_json_result(result) if is_save_response_data else "",
        "status": 0 if error is None else 1,
        "error_msg": str(error)[:2000] if error is not None else "",
        "oper_time": datetime.now(),
        "cost_time": cost_ms,
    }
    # FastAPI 响应返回后在线程池执行，不阻塞响应；路由未声明 BackgroundTasks 时用线程池兜底
    background_tasks = kwargs.get("background_tasks")
    if isinstance(background_tasks, BackgroundTasks):
        background_tasks.add_task(_save_oper_log, payload)
    else:
        _ASYNC_EXECUTOR.submit(_save_oper_log, payload)
