"""字典模块路由（对应若依 SysDictTypeController / SysDictDataController）。

权限说明：若依原版字典 Controller 均无 @PreAuthorize（type/{dictType} 被全部
业务页面的下拉框调用，不能按管理权限拦截），此处查询接口仅要求登录；
写操作按前端按钮权限标识补挂 has_perms，比原版更严谨。
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ruoyi_fastapi.core.dependencies import get_db
from ruoyi_fastapi.core.enums import BusinessType
from ruoyi_fastapi.core.permissions import get_current_login_user, has_perms
from ruoyi_fastapi.core.response import PageResult, R
from ruoyi_fastapi.modules.log.service import log
from ruoyi_fastapi.modules.login.schemas import LoginUser

from . import service
from .schemas import (
    DictDataCreate,
    DictDataPageQuery,
    DictDataResp,
    DictDataUpdate,
    DictTypeCreate,
    DictTypePageQuery,
    DictTypeResp,
    DictTypeUpdate,
)

dict_type_router = APIRouter(prefix="/system/dict/type", tags=["系统-字典类型"])
dict_data_router = APIRouter(prefix="/system/dict/data", tags=["系统-字典数据"])


# ==================== 字典类型 /system/dict/type ====================

# 静态路由必须注册在动态路径参数路由之前


@dict_type_router.get(
    "/list",
    response_model=PageResult[DictTypeResp],
    response_model_by_alias=True,
    summary="分页查询字典类型列表",
)
def list_dict_types(
    query: DictTypePageQuery = Depends(),
    _: LoginUser = Depends(get_current_login_user),
    db: Session = Depends(get_db),
):
    rows, total = service.select_dict_type_list(query, db)
    return PageResult.of(rows, total)


@dict_type_router.post(
    "/export",
    response_model=R[bool],
    response_model_by_alias=True,
    summary="导出字典类型列表",
)
def export_dict_types(query: DictTypePageQuery = Depends()):
    """导出（Excel 生成待接入，当前占位）。"""
    raise NotImplementedError("TODO: 实现导出")


@dict_type_router.delete(
    "/refreshCache",
    response_model=R[bool],
    response_model_by_alias=True,
    summary="刷新字典缓存",
)
@log(title="字典类型", business_type=BusinessType.CLEAN)
def refresh_cache(request: Request, db: Session = Depends(get_db)):
    return R.ok(service.refresh_dict_cache(db))


@dict_type_router.get(
    "/optionselect",
    response_model=R[list[DictTypeResp]],
    response_model_by_alias=True,
    summary="全部字典类型下拉框",
)
def optionselect(_: LoginUser = Depends(get_current_login_user), db: Session = Depends(get_db)):
    return R.ok(service.select_dict_type_options(db))


@dict_type_router.get(
    "/{dict_id}",
    response_model=R[DictTypeResp],
    response_model_by_alias=True,
    summary="字典类型详情",
)
def get_dict_type(
    dict_id: int,
    _: LoginUser = Depends(get_current_login_user),
    db: Session = Depends(get_db),
):
    return R.ok(service.select_dict_type_detail(dict_id, db))


@dict_type_router.post(
    "",
    response_model=R[bool],
    response_model_by_alias=True,
    summary="新增字典类型",
)
@log(title="字典类型", business_type=BusinessType.INSERT)
def add_dict_type(
    req: DictTypeCreate,
    request: Request,
    _: LoginUser = Depends(get_current_login_user),
    permissions: None = Depends(has_perms("system:dict:add")),
    db: Session = Depends(get_db),
):
    if not service.check_dict_type_unique(req.dict_type, None, db):
        return R.fail(f"新增字典'{req.dict_name}'失败，字典类型已存在")
    return R.ok(service.insert_dict_type(req, db))


@dict_type_router.put(
    "",
    response_model=R[bool],
    response_model_by_alias=True,
    summary="修改字典类型",
)
@log(title="字典类型", business_type=BusinessType.UPDATE)
def update_dict_type(
    req: DictTypeUpdate,
    request: Request,
    _: LoginUser = Depends(get_current_login_user),
    permissions: None = Depends(has_perms("system:dict:edit")),
    db: Session = Depends(get_db),
):
    if not service.check_dict_type_unique(req.dict_type, req.dict_id, db):
        return R.fail(f"修改字典'{req.dict_name}'失败，字典类型已存在")
    return R.ok(service.update_dict_type(req, db))


@dict_type_router.delete(
    "/{dict_ids}",
    response_model=R[bool],
    response_model_by_alias=True,
    summary="删除字典类型",
)
@log(title="字典类型", business_type=BusinessType.DELETE)
def delete_dict_types(
    dict_ids: str,
    request: Request,
    _: LoginUser = Depends(get_current_login_user),
    permissions: None = Depends(has_perms("system:dict:remove")),
    db: Session = Depends(get_db),
):
    ids = [int(x) for x in dict_ids.split(",") if x.strip()]
    return R.ok(service.delete_dict_type_by_ids(ids, db))


# ==================== 字典数据 /system/dict/data ====================

# GET /type/{dictType} 是全部业务页面下拉框的依赖，必须注册在 /{dictCode} 之前


@dict_data_router.get(
    "/list",
    response_model=PageResult[DictDataResp],
    response_model_by_alias=True,
    summary="分页查询字典数据列表",
)
def list_dict_data(
    query: DictDataPageQuery = Depends(),
    _: LoginUser = Depends(get_current_login_user),
    db: Session = Depends(get_db),
):
    rows, total = service.select_dict_data_list(query, db)
    return PageResult.of(rows, total)


@dict_data_router.post(
    "/export",
    response_model=R[bool],
    response_model_by_alias=True,
    summary="导出字典数据列表",
)
def export_dict_data(query: DictDataPageQuery = Depends()):
    """导出（Excel 生成待接入，当前占位）。"""
    raise NotImplementedError("TODO: 实现导出")


@dict_data_router.get(
    "/type/{dict_type}",
    response_model=R[list[DictDataResp]],
    response_model_by_alias=True,
    summary="按字典类型查询字典数据（前端下拉框/标签回显）",
)
def dict_data_by_type(
    dict_type: str,
    _: LoginUser = Depends(get_current_login_user),
    db: Session = Depends(get_db),
):
    return R.ok(service.select_dict_data_by_type(dict_type, db))


@dict_data_router.get(
    "/{dict_code}",
    response_model=R[DictDataResp],
    response_model_by_alias=True,
    summary="字典数据详情",
)
def get_dict_data(
    dict_code: int,
    _: LoginUser = Depends(get_current_login_user),
    db: Session = Depends(get_db),
):
    return R.ok(service.select_dict_data_detail(dict_code, db))


@dict_data_router.post(
    "",
    response_model=R[bool],
    response_model_by_alias=True,
    summary="新增字典数据",
)
@log(title="字典数据", business_type=BusinessType.INSERT)
def add_dict_data(
    req: DictDataCreate,
    request: Request,
    _: LoginUser = Depends(get_current_login_user),
    permissions: None = Depends(has_perms("system:dict:add")),
    db: Session = Depends(get_db),
):
    return R.ok(service.insert_dict_data(req, db))


@dict_data_router.put(
    "",
    response_model=R[bool],
    response_model_by_alias=True,
    summary="修改字典数据",
)
@log(title="字典数据", business_type=BusinessType.UPDATE)
def update_dict_data(
    req: DictDataUpdate,
    request: Request,
    _: LoginUser = Depends(get_current_login_user),
    permissions: None = Depends(has_perms("system:dict:edit")),
    db: Session = Depends(get_db),
):
    return R.ok(service.update_dict_data(req, db))


@dict_data_router.delete(
    "/{dict_codes}",
    response_model=R[bool],
    response_model_by_alias=True,
    summary="删除字典数据",
)
@log(title="字典数据", business_type=BusinessType.DELETE)
def delete_dict_data(
    dict_codes: str,
    request: Request,
    _: LoginUser = Depends(get_current_login_user),
    permissions: None = Depends(has_perms("system:dict:remove")),
    db: Session = Depends(get_db),
):
    ids = [int(x) for x in dict_codes.split(",") if x.strip()]
    return R.ok(service.delete_dict_data_by_ids(ids, db))
