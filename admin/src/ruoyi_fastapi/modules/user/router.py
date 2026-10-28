"""用户路由（对齐若依 SysUserController，前缀 /system/user）。

静态路由（/list、/deptTree、/export、authRole、resetPwd 等）必须注册在
/{userId} 动态路由之前，否则会被路径参数提前匹配吞掉。
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ruoyi_fastapi.core.data_scope import DataScope
from ruoyi_fastapi.core.dependencies import get_db
from ruoyi_fastapi.core.enums import BusinessType
from ruoyi_fastapi.core.permissions import get_data_scope, has_perms
from ruoyi_fastapi.core.response import PageResult, R
from ruoyi_fastapi.modules.dept.schemas import TreeSelectResp
from ruoyi_fastapi.modules.dept.service import get_tree_select
from ruoyi_fastapi.modules.login.schemas import LoginUser
from ruoyi_fastapi.modules.user.schemas import (
    ResetPwdReq,
    UserAuthRoleResp,
    UserChangeStatusReq,
    UserCreate,
    UserInfoResp,
    UserListResp,
    UserPageQuery,
    UserUpdate,
)

from ..log.service import log
from . import service

router = APIRouter(prefix="/system/user", tags=["用户管理"])


# ---------- 查询类（静态路由先于 /{userId} 注册） ----------


@router.get(
    "/list",
    response_model=PageResult[UserListResp],
    response_model_by_alias=True,
    summary="查询用户列表",
)
def get_user_list(
    query: UserPageQuery = Depends(),  # GET 查询模型必须经 Depends 解析为查询参数
    scope: DataScope = Depends(get_data_scope),  # 数据权限：按角色的 data_scope 过滤可见范围
    db: Session = Depends(get_db),
    _perms: None = Depends(has_perms("system:user:list")),
) -> PageResult[UserListResp]:
    """分页查询用户列表（对应若依 SysUserController.list，方法上带 @DataScope）。"""
    rows, total = service.select_user_list(query, scope, db)
    return PageResult.of(rows=rows, total=total)


@router.get(
    "/deptTree",
    response_model=R[list[TreeSelectResp]],
    response_model_by_alias=True,
    summary="获取部门树（列表页左侧树）",
)
def get_dept_tree(
    db: Session = Depends(get_db),
    _perms: None = Depends(has_perms("system:user:list")),
) -> R[list[TreeSelectResp]]:
    return R.ok(get_tree_select(db))


@router.post(
    "/export",
    response_model=R[bool],
    response_model_by_alias=True,
    summary="导出用户列表",
)
@log(title="用户管理", business_type=BusinessType.EXPORT)
def export_user(
    request: Request,
    query: UserPageQuery,
    db: Session = Depends(get_db),
    _perms: None = Depends(has_perms("system:user:export")),
) -> R[bool]:
    """导出用户数据（Excel 生成待接入，当前占位）。"""
    raise NotImplementedError("TODO: 实现导出")


@router.get(
    "/authRole/{userId}",
    response_model=UserAuthRoleResp,
    response_model_by_alias=True,
    summary="用户分配角色页回显",
)
def get_user_auth_role(
    userId: int,
    db: Session = Depends(get_db),
    _perms: None = Depends(has_perms("system:user:query")),
) -> UserAuthRoleResp:
    """返回用户与其已绑定角色（顶层平铺 user/roles，对齐若依 AjaxResult）。"""
    return service.get_user_auth_role(userId, db)


@router.put(
    "/authRole",
    response_model=R[bool],
    response_model_by_alias=True,
    summary="执行用户分配角色",
)
@log(title="用户管理", business_type=BusinessType.GRANT)
def insert_user_auth(
    request: Request,
    userId: int,
    roleIds: str,
    db: Session = Depends(get_db),
    _perms: None = Depends(has_perms("system:user:edit")),
) -> R[bool]:
    """roleIds 逗号分隔（对齐若依 Long[] 查询参数绑定）。"""
    role_ids = [int(x) for x in roleIds.split(",") if x.strip()]
    return R.ok(service.insert_user_auth(userId, role_ids, db))


@router.put(
    "/resetPwd",
    response_model=R[bool],
    response_model_by_alias=True,
    summary="重置密码",
)
@log(title="用户管理", business_type=BusinessType.UPDATE)
def reset_pwd(
    request: Request,
    body: ResetPwdReq,
    db: Session = Depends(get_db),
    _perms: None = Depends(has_perms("system:user:resetPwd")),
) -> R[bool]:
    return R.ok(service.reset_pwd(body, db))


@router.put(
    "/changeStatus",
    response_model=R[bool],
    response_model_by_alias=True,
    summary="账号启停",
)
@log(title="用户管理", business_type=BusinessType.UPDATE)
def change_status(
    request: Request,
    body: UserChangeStatusReq,
    db: Session = Depends(get_db),
    _perms: None = Depends(has_perms("system:user:edit")),
) -> R[bool]:
    return R.ok(service.change_status(body, db))


@router.get(
    "/",
    response_model=UserInfoResp,
    response_model_by_alias=True,
    summary="新增用户页初始化",
)
@router.get(
    "/{userId}",
    response_model=UserInfoResp,
    response_model_by_alias=True,
    summary="用户详情（含角色/岗位回显）",
)
def get_user_info(
    userId: int | None = None,
    db: Session = Depends(get_db),
    _perms: None = Depends(has_perms("system:user:query")),
) -> UserInfoResp:
    """对应若依 getInfo（@GetMapping({"/", "/{userId}"}) 双路径共用一个方法）。

    无 userId：仅返回角色/岗位全量（新增页）；有 userId：额外回显用户与已绑定 ID。
    """
    if userId is None:
        return service.get_user_form_init(db)
    return service.get_user_detail(userId, db)


# ---------- 写操作（对齐若依：写操作落 sys_oper_log） ----------


@router.post(
    "",
    response_model=R[bool],
    response_model_by_alias=True,
    summary="新增用户",
)
@log(title="用户管理", business_type=BusinessType.INSERT)
def add_user(
    request: Request,
    body: UserCreate,
    db: Session = Depends(get_db),
    _perms: None = Depends(has_perms("system:user:add")),
) -> R[bool]:
    """新增用户（账号/手机/邮箱唯一性校验 + BCrypt 哈希 + 角色/岗位绑定）。"""
    return R.ok(service.add_user(body, db))


@router.put(
    "",
    response_model=R[bool],
    response_model_by_alias=True,
    summary="修改用户",
)
@log(title="用户管理", business_type=BusinessType.UPDATE)
def update_user(
    request: Request,
    body: UserUpdate,
    db: Session = Depends(get_db),
    _perms: None = Depends(has_perms("system:user:edit")),
) -> R[bool]:
    return R.ok(service.update_user(body, db))


@router.delete(
    "/{userIds}",
    response_model=R[bool],
    response_model_by_alias=True,
    summary="删除用户",
)
@log(title="用户管理", business_type=BusinessType.DELETE)
def delete_user(
    request: Request,
    userIds: str,
    db: Session = Depends(get_db),
    login_user: LoginUser = Depends(has_perms("system:user:remove")),
) -> R[bool]:
    """批量删除用户（逗号分隔 ID，逻辑删除；不可删 admin 与自己）。"""
    user_ids = [int(x) for x in userIds.split(",") if x.strip()]
    return R.ok(service.delete_user_by_ids(user_ids, login_user.user_id, db))
