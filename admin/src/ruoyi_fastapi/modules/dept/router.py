"""部门管理路由（对应若依 SysDeptController）。

查询类接口按若依惯例不落操作日志（不加 @log）；
写操作加 @log 落 sys_oper_log，request 参数供装饰器提取 URL/IP。
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ruoyi_fastapi.core.dependencies import get_db
from ruoyi_fastapi.core.enums import BusinessType
from ruoyi_fastapi.core.permissions import has_perms
from ruoyi_fastapi.core.response import R

from ..log.service import log
from . import service
from .schemas import DeptAddReq, DeptResp, DeptUpdateReq, RoleDeptTreeResp, TreeSelectResp

router = APIRouter(prefix="/system/dept")


# ---------- 查询类（静态路由必须先于 /{deptId} 动态路由注册） ----------


@router.get(
    "/list",
    response_model=R[list[DeptResp]],
    response_model_by_alias=True,
    summary="获取部门列表",
)
def get_dept_list(
    deptName: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
    _perms: None = Depends(has_perms("system:dept:list")),
) -> R[list[DeptResp]]:
    return R.ok(service.get_dept_list(db, dept_name=deptName, status=status))


@router.get(
    "/list/exclude/{deptId}",
    response_model=R[list[DeptResp]],
    response_model_by_alias=True,
    summary="获取部门列表（排除指定部门及其子树）",
)
def get_dept_list_exclude(
    deptId: int,
    db: Session = Depends(get_db),
    _perms: None = Depends(has_perms("system:dept:list")),
) -> R[list[DeptResp]]:
    return R.ok(service.get_dept_list(db, exclude_dept_id=deptId))


@router.get(
    "/treeselect",
    response_model=R[list[TreeSelectResp]],
    response_model_by_alias=True,
    summary="获取部门下拉树（仅正常状态）",
)
def get_dept_tree(
    db: Session = Depends(get_db),
    _perms: None = Depends(has_perms("system:dept:list")),
) -> R[list[TreeSelectResp]]:
    return R.ok(service.get_tree_select(db))


@router.get(
    "/roleDeptTreeselect/{roleId}",
    response_model=RoleDeptTreeResp,
    response_model_by_alias=True,
    summary="获取角色部门树（含勾选回显）",
)
def get_role_dept_tree(
    roleId: int,
    db: Session = Depends(get_db),
    _perms: None = Depends(has_perms("system:role:query")),
) -> RoleDeptTreeResp:
    return service.get_role_dept_tree(db, roleId)


@router.get(
    "/{deptId}",
    response_model=R[DeptResp],
    response_model_by_alias=True,
    summary="获取部门详情",
)
def get_dept_detail(
    deptId: int,
    db: Session = Depends(get_db),
    _perms: None = Depends(has_perms("system:dept:query")),
) -> R[DeptResp]:
    return R.ok(service.get_dept_detail(db, deptId))


# ---------- 写操作（对齐若依：写操作落 sys_oper_log） ----------


@router.post(
    "",
    response_model=R[None],
    response_model_by_alias=True,
    summary="新增部门",
)
@log(title="部门管理", business_type=BusinessType.INSERT)
def add_dept(
    request: Request,
    req: DeptAddReq,
    db: Session = Depends(get_db),
    _perms: None = Depends(has_perms("system:dept:add")),
) -> R[None]:
    service.add_dept(db, req)
    return R.ok()


@router.put(
    "",
    response_model=R[None],
    response_model_by_alias=True,
    summary="修改部门",
)
@log(title="部门管理", business_type=BusinessType.UPDATE)
def update_dept(
    request: Request,
    req: DeptUpdateReq,
    db: Session = Depends(get_db),
    _perms: None = Depends(has_perms("system:dept:edit")),
) -> R[None]:
    service.update_dept(db, req)
    return R.ok()


@router.delete(
    "/{deptId}",
    response_model=R[None],
    response_model_by_alias=True,
    summary="删除部门",
)
@log(title="部门管理", business_type=BusinessType.DELETE)
def delete_dept(
    request: Request,
    deptId: int,
    db: Session = Depends(get_db),
    _perms: None = Depends(has_perms("system:dept:remove")),
) -> R[None]:
    service.delete_dept(db, deptId)
    return R.ok()
