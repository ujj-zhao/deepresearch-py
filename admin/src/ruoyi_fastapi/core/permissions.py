"""接口鉴权依赖（对应若依 @PreAuthorize + SecurityUtils.getLoginUser + DataScopeAspect）。"""

from fastapi import Depends, Request
from sqlalchemy import or_, select, text
from sqlalchemy.orm import Session

from ruoyi_fastapi.core.data_scope import DataScope
from ruoyi_fastapi.core.dependencies import get_db
from ruoyi_fastapi.core.exception import ServiceException
from ruoyi_fastapi.modules.dept.models import Dept
from ruoyi_fastapi.modules.login import service as login_service
from ruoyi_fastapi.modules.login.schemas import LoginUser
from ruoyi_fastapi.modules.role.models import RoleDept


def get_current_login_user(request: Request) -> LoginUser:
    """解析当前登录会话。

    模块级依赖：同一请求内多处 Depends 引用时 FastAPI 缓存结果，只解析一次。
    """
    return login_service.get_login_user(request)


def has_perms(*perms: str):
    """校验当前用户拥有任一权限标识（对应若依 ss.hasPermi 语义）。

    admin 的 permissions 含 *:*:* 恒通过。
    """
    def checker(login_user: LoginUser = Depends(get_current_login_user)) -> LoginUser:
        user_perms = login_user.permissions or set()
        if "*:*:*" in user_perms or any(p in user_perms for p in perms):
            return login_user
        raise ServiceException("没有操作权限", code=403)

    return checker

def has_role(*roles: str):
    """校验当前用户拥有任一角色标识（对应若依 ss.hasRole 语义）。

    admin 角色恒通过（角色列表由登录装配写入会话快照）。
    """
    def checker(login_user: LoginUser = Depends(get_current_login_user)) -> LoginUser:
        user_roles = login_user.roles or []
        if any(r.role_key == "admin" or r.role_key in roles for r in user_roles):
            return login_user
        raise ServiceException("没有操作权限", code=403)

    return checker


def get_data_scope(
    login_user: LoginUser = Depends(get_current_login_user),
    db: Session = Depends(get_db),
) -> DataScope:
    """按当前用户的角色计算数据范围（对应若依 DataScopeAspect.doBefore）。

    依赖在请求期读会话快照并查部门集合，返回结构化范围供 service 的
    apply_scope 使用；admin 跳过过滤（对应若依 isAdmin 判断）。
    """
    if login_user.user_id == 1:  # 超级管理员跳过
        return DataScope(all=True)
    scope = DataScope()
    for role in login_user.roles or []:
        match role.data_scope:
            case "1":  # 全部数据权限：短路
                return DataScope(all=True)
            case "2":  # 自定数据权限：sys_role_dept 绑定的部门
                scope.dept_ids |= _select_dept_ids_by_role(role.role_id, db)
            case "3":  # 本部门数据权限
                if login_user.dept_id is not None:
                    scope.dept_ids.add(login_user.dept_id)
            case "4":  # 本部门及以下数据权限：展开子孙部门
                scope.dept_ids |= _select_dept_ids_with_children(login_user.dept_id, db)
            case "5":  # 仅本人数据权限
                scope.user_ids.add(login_user.user_id)
    return scope


def _select_dept_ids_by_role(role_id: int, db: Session) -> set[int]:
    """自定义范围：查 sys_role_dept 绑定的部门（对应若依 OR d.dept_id IN (SELECT ...)）。"""
    stmt = select(RoleDept.dept_id).where(RoleDept.role_id == role_id)
    return set(db.scalars(stmt).all())


def _select_dept_ids_with_children(dept_id: int | None, db: Session) -> set[int]:
    """本部门及以下：ancestors 祖链匹配（对应若依 find_in_set(deptId, ancestors)）。

    dept_id 为 None（用户未挂部门）时返回空集合，交由调用方兜底。
    """
    if dept_id is None:
        return set()
    stmt = select(Dept.dept_id).where(
        or_(
            Dept.dept_id == dept_id,
            text("find_in_set(:did, ancestors)").bindparams(did=dept_id),
        ),
        Dept.status == "0",
        Dept.del_flag == "0",
    )
    return set(db.scalars(stmt).all())
