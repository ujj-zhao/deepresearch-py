"""角色路由（对齐若依 SysRoleController，前缀 /system/role）。

静态路由（/list、/optionselect、authUser/*）必须注册在 /{roleId} 动态路由之前，
否则会被路径参数提前匹配吞掉。
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ruoyi_fastapi.core.data_scope import DataScope
from ruoyi_fastapi.core.dependencies import get_db
from ruoyi_fastapi.core.enums import BusinessType
from ruoyi_fastapi.core.permissions import get_current_login_user, get_data_scope, has_perms
from ruoyi_fastapi.core.response import PageResult, R
from ruoyi_fastapi.modules.user.schemas import UserListResp

from ..log.service import log
from . import service
from .schemas import (
    RoleAuthUserPageQuery,
    RoleChangeStatusReq,
    RoleCreate,
    RoleDataScopeReq,
    RolePageQuery,
    RoleResp,
    RoleUpdate,
)

router = APIRouter(prefix="/system/role", tags=["角色管理"])


# ---------- 查询类（静态路由先于 /{roleId} 注册） ----------


@router.get(
    "/list",
    response_model=PageResult[RoleResp],
    response_model_by_alias=True,
    summary="查询角色列表",
)
def get_role_list(
    query: RolePageQuery = Depends(),  # GET 查询模型必须经 Depends 解析为查询参数
    db: Session = Depends(get_db),
    _perms: None = Depends(has_perms("system:role:list")),
) -> PageResult[RoleResp]:
    """分页查询角色列表（名称/权限字符模糊、状态精确）。"""
    rows, total = service.get_role_list(query, db)
    return PageResult.of(rows=rows, total=total)


@router.get(
    "/optionselect",
    response_model=R[list[RoleResp]],
    response_model_by_alias=True,
    summary="角色下拉框列表",
)
def get_role_options(
    db: Session = Depends(get_db),
    _perms: None = Depends(get_current_login_user),
) -> R[list[RoleResp]]:
    """全部未删角色（登录即可，无独立权限点）。"""
    return R.ok(service.get_role_options(db))


@router.get(
    "/authUser/allocatedList",
    response_model=PageResult[UserListResp],
    response_model_by_alias=True,
    summary="已分配用户列表",
)
def get_allocated_users(
    query: RoleAuthUserPageQuery = Depends(),
    scope: DataScope = Depends(get_data_scope),
    db: Session = Depends(get_db),
    _perms: None = Depends(has_perms("system:role:list")),
) -> PageResult[UserListResp]:
    """查询已分配该角色的用户（带数据权限过滤）。"""
    rows, total = service.select_allocated_users(query, scope, db)
    return PageResult.of(rows=rows, total=total)


@router.get(
    "/authUser/unallocatedList",
    response_model=PageResult[UserListResp],
    response_model_by_alias=True,
    summary="未分配用户列表",
)
def get_unallocated_users(
    query: RoleAuthUserPageQuery = Depends(),
    scope: DataScope = Depends(get_data_scope),
    db: Session = Depends(get_db),
    _perms: None = Depends(has_perms("system:role:list")),
) -> PageResult[UserListResp]:
    """查询未分配该角色的用户（带数据权限过滤）。"""
    rows, total = service.select_unallocated_users(query, scope, db)
    return PageResult.of(rows=rows, total=total)


@router.get(
    "/{roleId}",
    response_model=R[RoleResp],
    response_model_by_alias=True,
    summary="角色详情",
)
def get_role_detail(
    roleId: int,
    db: Session = Depends(get_db),
    _perms: None = Depends(has_perms("system:role:query")),
) -> R[RoleResp]:
    return R.ok(service.get_role_detail(roleId, db))


# ---------- 写操作（对齐若依：写操作落 sys_oper_log） ----------


@router.post(
    "",
    response_model=R[bool],
    response_model_by_alias=True,
    summary="新增角色",
)
@log(title="角色管理", business_type=BusinessType.INSERT)
def add_role(
    request: Request,
    req: RoleCreate,
    db: Session = Depends(get_db),
    _perms: None = Depends(has_perms("system:role:add")),
) -> R[bool]:
    return R.ok(service.add_role(req, db))


@router.put(
    "",
    response_model=R[bool],
    response_model_by_alias=True,
    summary="修改角色",
)
@log(title="角色管理", business_type=BusinessType.UPDATE)
def update_role(
    request: Request,
    req: RoleUpdate,
    db: Session = Depends(get_db),
    _perms: None = Depends(has_perms("system:role:edit")),
) -> R[bool]:
    return R.ok(service.update_role(req, db))


@router.put(
    "/dataScope",
    response_model=R[bool],
    response_model_by_alias=True,
    summary="修改角色数据权限",
)
@log(title="角色管理", business_type=BusinessType.UPDATE)
def update_role_data_scope(
    request: Request,
    req: RoleDataScopeReq,
    db: Session = Depends(get_db),
    _perms: None = Depends(has_perms("system:role:edit")),
) -> R[bool]:
    return R.ok(service.update_role_data_scope(req, db))


@router.put(
    "/changeStatus",
    response_model=R[bool],
    response_model_by_alias=True,
    summary="角色状态修改",
)
@log(title="角色管理", business_type=BusinessType.UPDATE)
def update_role_status(
    request: Request,
    req: RoleChangeStatusReq,
    db: Session = Depends(get_db),
    _perms: None = Depends(has_perms("system:role:edit")),
) -> R[bool]:
    return R.ok(service.update_role_status(req, db))


@router.put(
    "/authUser/cancel",
    response_model=R[bool],
    response_model_by_alias=True,
    summary="取消用户角色授权",
)
@log(title="角色管理", business_type=BusinessType.GRANT)
def cancel_auth_user(
    request: Request,
    roleId: int,
    userId: int,
    db: Session = Depends(get_db),
    _perms: None = Depends(has_perms("system:role:edit")),
) -> R[bool]:
    return R.ok(service.cancel_auth_user(roleId, userId, db))


@router.put(
    "/authUser/cancelAll",
    response_model=R[bool],
    response_model_by_alias=True,
    summary="批量取消用户角色授权",
)
@log(title="角色管理", business_type=BusinessType.GRANT)
def cancel_auth_users(
    request: Request,
    roleId: int,
    userIds: str,
    db: Session = Depends(get_db),
    _perms: None = Depends(has_perms("system:role:edit")),
) -> R[bool]:
    """userIds 逗号分隔（对齐若依 Long[] 查询参数绑定）。"""
    user_ids = [int(x) for x in userIds.split(",") if x.strip()]
    return R.ok(service.cancel_auth_users(roleId, user_ids, db))


@router.put(
    "/authUser/insertAll",
    response_model=R[bool],
    response_model_by_alias=True,
    summary="批量授权用户角色",
)
@log(title="角色管理", business_type=BusinessType.GRANT)
def insert_auth_users(
    request: Request,
    roleId: int,
    userIds: str,
    db: Session = Depends(get_db),
    _perms: None = Depends(has_perms("system:role:edit")),
) -> R[bool]:
    user_ids = [int(x) for x in userIds.split(",") if x.strip()]
    return R.ok(service.insert_auth_users(roleId, user_ids, db))


@router.delete(
    "/{roleIds}",
    response_model=R[bool],
    response_model_by_alias=True,
    summary="删除角色",
)
@log(title="角色管理", business_type=BusinessType.DELETE)
def delete_role(
    request: Request,
    roleIds: str,
    db: Session = Depends(get_db),
    _perms: None = Depends(has_perms("system:role:remove")),
) -> R[bool]:
    """批量删除角色（逗号分隔 ID，逻辑删除）。"""
    role_ids = [int(x) for x in roleIds.split(",") if x.strip()]
    return R.ok(service.delete_role_by_ids(role_ids, db))
