"""菜单路由（对齐若依 SysLoginController.getRouters + SysMenuController）。

路由器无统一前缀：getRouters 挂根路径，菜单管理接口显式声明 /system/menu 前缀。
静态路由（/list、/treeselect 等）必须注册在 /{menuId} 动态路由之前。
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ruoyi_fastapi.core.dependencies import get_db
from ruoyi_fastapi.core.enums import BusinessType
from ruoyi_fastapi.core.permissions import get_current_login_user, has_perms
from ruoyi_fastapi.core.response import R
from ruoyi_fastapi.modules.login.schemas import LoginUser

from ..log.service import log
from . import service as menu_service
from .schemas import (
    MenuCreate,
    MenuPageQuery,
    MenuResp,
    MenuTreeSelectResp,
    MenuUpdate,
    RoleMenuTreeResp,
    RouterResp,
)

router = APIRouter(tags=["菜单信息"])


@router.get(
    "/getRouters",
    response_model=R[list[RouterResp]],
    summary="获取路由信息",
)
def get_routers(
    login_user: LoginUser = Depends(get_current_login_user),
    db: Session = Depends(get_db),
) -> R[list[RouterResp]]:
    """根据登录用户角色返回前端路由配置（对应若依 SysLoginController.getRouters）。"""
    return R.ok(menu_service.get_routers(login_user.user_id, db))


# ---------- 菜单管理（/system/menu，对齐若依 SysMenuController） ----------


@router.get(
    "/system/menu/list",
    response_model=R[list[MenuResp]],
    response_model_by_alias=True,
    summary="查询菜单列表",
)
def get_menu_list(
    query: MenuPageQuery = Depends(),  # GET 查询模型必须经 Depends 解析为查询参数
    db: Session = Depends(get_db),
    login_user: LoginUser = Depends(has_perms("system:menu:list")),
) -> R[list[MenuResp]]:
    """菜单列表（平铺不分页；非 admin 用户仅见角色绑定菜单）。"""
    return R.ok(menu_service.select_menu_list(query.menu_name, query.status, login_user.user_id, db))


@router.get(
    "/system/menu/list/exclude/{menuId}",
    response_model=R[list[MenuResp]],
    response_model_by_alias=True,
    summary="查询菜单列表（排除指定菜单及其子树）",
)
def get_menu_list_exclude(
    menuId: int,
    db: Session = Depends(get_db),
    login_user: LoginUser = Depends(has_perms("system:menu:list")),
) -> R[list[MenuResp]]:
    """修改页选择上级菜单时排除自身子树（前端组树后剔除，后端查全量平铺）。"""
    return R.ok(menu_service.select_menu_list(None, None, login_user.user_id, db))


@router.get(
    "/system/menu/treeselect",
    response_model=R[list[MenuTreeSelectResp]],
    response_model_by_alias=True,
    summary="获取菜单下拉树（仅正常状态）",
)
def get_menu_tree(
    db: Session = Depends(get_db),
    login_user: LoginUser = Depends(has_perms("system:menu:list")),
) -> R[list[MenuTreeSelectResp]]:
    return R.ok(menu_service.get_tree_select(login_user.user_id, db))


@router.get(
    "/system/menu/roleMenuTreeselect/{roleId}",
    response_model=RoleMenuTreeResp,
    response_model_by_alias=True,
    summary="获取角色菜单树（含勾选回显）",
)
def get_role_menu_tree(
    roleId: int,
    db: Session = Depends(get_db),
    login_user: LoginUser = Depends(has_perms("system:menu:list")),
) -> RoleMenuTreeResp:
    """角色授权页菜单树 + 已勾选菜单（顶层平铺 checkedKeys/menus，对齐若依 AjaxResult）。"""
    return menu_service.role_menu_tree_select(roleId, login_user.user_id, db)


@router.get(
    "/system/menu/{menuId}",
    response_model=R[MenuResp],
    response_model_by_alias=True,
    summary="菜单详情",
)
def get_menu_detail(
    menuId: int,
    db: Session = Depends(get_db),
    _perms: None = Depends(has_perms("system:menu:query")),
) -> R[MenuResp]:
    return R.ok(menu_service.get_menu_detail(menuId, db))


@router.post(
    "/system/menu",
    response_model=R[bool],
    response_model_by_alias=True,
    summary="新增菜单",
)
@log(title="菜单管理", business_type=BusinessType.INSERT)
def add_menu(
    request: Request,
    req: MenuCreate,
    db: Session = Depends(get_db),
    _perms: None = Depends(has_perms("system:menu:add")),
) -> R[bool]:
    return R.ok(menu_service.add_menu(req, db))


@router.put(
    "/system/menu",
    response_model=R[bool],
    response_model_by_alias=True,
    summary="修改菜单",
)
@log(title="菜单管理", business_type=BusinessType.UPDATE)
def update_menu(
    request: Request,
    req: MenuUpdate,
    db: Session = Depends(get_db),
    _perms: None = Depends(has_perms("system:menu:edit")),
) -> R[bool]:
    return R.ok(menu_service.update_menu(req, db))


@router.delete(
    "/system/menu/{menuId}",
    response_model=R[bool],
    response_model_by_alias=True,
    summary="删除菜单",
)
@log(title="菜单管理", business_type=BusinessType.DELETE)
def delete_menu(
    request: Request,
    menuId: int,
    db: Session = Depends(get_db),
    _perms: None = Depends(has_perms("system:menu:remove")),
) -> R[bool]:
    return R.ok(menu_service.delete_menu(menuId, db))
