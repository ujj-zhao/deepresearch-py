import json

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from ruoyi_fastapi.core.constant import LOGIN_TOKEN_KEY
from ruoyi_fastapi.core.exception import ServiceException
from ruoyi_fastapi.core.redis import redis_client
from ruoyi_fastapi.modules.login.schemas import LoginUser
from .schemas import (
    SysLogininfoQuery,
    SysLogininfoResp,
    SysOnlineUser,
    SysOperLogQuery,
    SysOperLogVO,
)

# 列表查询基础 SQL（对应 selectLogininforList）
_SYS_LOGIN_INFO_LIST_SQL = """
    SELECT info_id, user_name, ipaddr, login_location, browser, os,
           status, msg, login_time
    FROM sys_logininfor
    WHERE 1=1
"""
_SYS_LOGIN_INFO_COUNT_SQL = "SELECT COUNT(*) FROM sys_logininfor WHERE 1=1"

_SYS_OPER_LOG_LIST_SQL = """
    SELECT *
    FROM sys_oper_log
    WHERE 1=1
"""
_SYS_OPER_LOG_COUNT_SQL = "SELECT COUNT(*) FROM sys_oper_log WHERE 1=1"

def _build_logininfo_conditions(query: SysLogininfoQuery) -> tuple[str, dict]:
    """根据查询参数拼接动态条件，返回 (条件 SQL 片段, 参数字典)。"""
    sql = ""
    params: dict = {}

    if query.user_name:
        sql += " AND user_name LIKE :user_name"
        params["user_name"] = f"%{query.user_name}%"
    if query.ipaddr:
        sql += " AND ipaddr LIKE :ipaddr"
        params["ipaddr"] = f"%{query.ipaddr}%"
    if query.status:
        sql += " AND status = :status"
        params["status"] = query.status
    if query.begin_time:
        sql += " AND login_time >= :begin_time"
        params["begin_time"] = query.begin_time
    if query.end_time:
        sql += " AND login_time <= :end_time"
        params["end_time"] = query.end_time

    return sql, params


def _build_oper_log_conditions(query: SysOperLogQuery) -> tuple[str, dict]:
    """根据查询参数拼接动态条件，返回 (条件 SQL 片段, 参数字典)。"""
    sql = ""
    params: dict = {}

    if query.title:
        sql += " AND title LIKE :title"
        params["title"] = f"%{query.title}%"
    if query.business_type:
        sql += " AND business_type = :business_type"
        params["business_type"] = query.business_type
    if query.status:
        sql += " AND status = :status"
        params["status"] = query.status
    if query.oper_name:
        sql += " AND oper_name LIKE :oper_name"
        params["oper_name"] = f"%{query.oper_name}%"
    if query.oper_ip:
        sql += " AND oper_ip LIKE :oper_ip"
        params["oper_ip"] = f"%{query.oper_ip}%"
    if query.begin_time:
        sql += " AND oper_time >= :begin_time"
        params["begin_time"] = query.begin_time
    if query.end_time:
        sql += " AND oper_time <= :end_time"
        params["end_time"] = query.end_time

    return sql, params



def list_logininfo(
    query: SysLogininfoQuery, db: Session
) -> tuple[list[SysLogininfoResp], int]:
    """分页查询登录日志列表。"""
    cond_sql, params = _build_logininfo_conditions(query)

    total = db.execute(text(_SYS_LOGIN_INFO_COUNT_SQL + cond_sql), params).scalar_one()

    page_sql = (
        _SYS_LOGIN_INFO_LIST_SQL
        + cond_sql
        + " ORDER BY info_id DESC LIMIT :limit OFFSET :offset"
    )
    params["limit"] = query.page_size
    params["offset"] = (query.page_num - 1) * query.page_size

    rows = db.execute(text(page_sql), params).mappings().all()
    return [SysLogininfoResp.model_validate(dict(r)) for r in rows], total

def remove(info_id_list: list[int], db: Session) -> bool:
    """移除登录日志列表。"""
    stmt = text(
        "DELETE FROM sys_logininfor WHERE info_id IN :info_id_list"
    ).bindparams(bindparam("info_id_list", expanding = True))
    db.execute(stmt, {"info_id_list": info_id_list})
    db.commit()
    return True

def clean(db: Session) -> bool:
    """清空登录日志列表（对应若依 cleanLogininfor：truncate table）。"""
    db.execute(text("TRUNCATE TABLE sys_logininfor"))
    db.commit()
    return True

def clearLoginRecordCache(userName: str) -> bool:
    """清除登录记录缓存。"""
    answer = redis_client.getdel(userName)
    if answer is None:
        raise ServiceException("login cache not found", code=400)
    if answer.lower() != code.lower():
        raise ServiceException("login code error", code=400)
    return True


def list_oper_log(
    query: SysOperLogQuery, db: Session
) -> tuple[list[SysOperLogVO], int]:
    """分页查询操作日志列表。"""
    cond_sql, params = _build_oper_log_conditions(query)
    total = db.execute(text(_SYS_OPER_LOG_COUNT_SQL + cond_sql), params).scalar_one()
    page_sql = (
        _SYS_OPER_LOG_LIST_SQL
        + cond_sql
        + " ORDER BY oper_id DESC LIMIT :limit OFFSET :offset"
    )
    params["limit"] = query.page_size
    params["offset"] = (query.page_num - 1) * query.page_size
    
    rows = db.execute(text(page_sql), params).mappings().all()
    return [SysOperLogVO.model_validate(dict(r)) for r in rows], total


def remove_oper_log(operLogIds: list[int], db: Session) -> bool:
    """移除操作日志列表。"""
    if not operLogIds:
        raise ServiceException("operLogIds is empty", code=400)
    stmt = text(
        "DELETE FROM sys_oper_log WHERE oper_id IN :operLogIds"
    ).bindparams(bindparam("operLogIds", expanding = True))
    db.execute(stmt, {"operLogIds": operLogIds})
    db.commit()
    return True

def clean_oper_log(db: Session) -> bool:
    """清空操作日志列表（对应若依 cleanOperLog：truncate table）。"""
    db.execute(text("TRUNCATE TABLE sys_oper_log"))
    db.commit()
    return True

def online_user_list(ipaddr: str | None, user_name: str | None) -> list[SysOnlineUser]:
    """查询在线用户列表（从 Redis 扫描登录会话，对应若依 SysUserOnlineController.list）。"""
    result: list[SysOnlineUser] = []
    for token_key in redis_client.scan_iter(match=LOGIN_TOKEN_KEY + "*"):
        raw = redis_client.get(token_key)
        if not raw:
            continue
        login_user = LoginUser.model_validate(json.loads(raw))

        # 按条件过滤（对应若依 selectOnlineList 的 WHERE 条件）
        if ipaddr and login_user.ipaddr != ipaddr:
            continue
        if user_name and (login_user.user is None or login_user.user.user_name != user_name):
            continue

        result.append(_to_online(login_user, token_key))
    return result


def force_logout(token_id: str) -> bool:
    return redis_client.delete(LOGIN_TOKEN_KEY + token_id) > 0


def _to_online(login_user: LoginUser, token_key: str) -> SysOnlineUser:
    """把登录会话（LoginUser）转成在线用户展示模型（SysOnlineUser）。"""
    return SysOnlineUser(
        token_id=token_key.removeprefix(LOGIN_TOKEN_KEY),
        dept_name=None,  # user 模块补充部门信息后从 login_user.user 取
        user_name=login_user.user.user_name if login_user.user else None,
        ipaddr=login_user.ipaddr,
        login_location=login_user.login_location,
        browser=login_user.browser,
        os=login_user.os,
        login_time=login_user.login_time,
    )



    
