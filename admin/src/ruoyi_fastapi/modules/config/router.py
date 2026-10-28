from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from . import service
from .models import Config
from .schemas import BaseConfig, ConfigPage
from ruoyi_fastapi.core.dependencies import get_db
from ruoyi_fastapi.core.enums import BusinessType
from ruoyi_fastapi.core.response import R, PageResult
from ruoyi_fastapi.core.permissions import has_perms
from ruoyi_fastapi.modules.log.service import log
router = APIRouter(prefix="/system/config", tags=["系统"])
        

"""查询系统配置列表"""
@router.get(
    "/list",
    response_model = PageResult[BaseConfig],
    summary = "查询系统配置列表",
    description = "根据分页参数查询系统配置列表",
    )
def list_configs(config: ConfigPage = Depends(), db: Session = Depends(get_db)) -> PageResult[BaseConfig]:
    rows, total = service.select_config_list(config, db)
    return PageResult.of(rows=rows, total=total)

"""导出参数配置"""
@router.post(
    "/export",
    summary = "参数管理",
    )
def export(config: BaseConfig, db: Session = Depends(get_db)) -> R[bool]:
    return R.ok(service.export(db, config))

"""根据系统配置ID获取系统配置详情"""
@router.get(
    "/{config_id}",
    response_model = R[BaseConfig],
    summary = "获取系统配置详情",
    )
def get_info(
    config_id: int,
    db: Session = Depends(get_db),
    permissions:None = Depends(has_perms("system:config:info")),
) -> R[BaseConfig]:
    return R.ok(db.get(Config, config_id))

"""根据配置键获取系统配置"""
@router.get(
    "/config_key/{config_key}",
    summary = "根据配置键获取系统配置",
)
def get_config(
    config_key: str,
    db: Session = Depends(get_db),
    permissions:None = Depends(has_perms("system:config:config_key")),
) -> R[str]:
    return R.ok(service.select_config_by_key(config_key, db))

"""添加参数配置"""
@router.post(
    "",
    response_model = R[bool],
    summary = "添加系统配置",
    )
def add(
    config: BaseConfig,
    db: Session = Depends(get_db),
    permissions:None = Depends(has_perms("system:config:add")),
) -> R[bool]:
    if not service.check_config_key_unique(config.config_key, config.config_id, db):
        return R.fail("新增参数失败，参数键名已存在")
    return R.ok(service.save_config(config, db))

"""修改参数配置"""
@router.put(
    "",
    response_model = R[bool],
    summary = "修改系统配置",
    )
@log(title="修改系统配置", business_type=BusinessType.UPDATE)
def update(
    config: BaseConfig,
    db: Session = Depends(get_db),
    permissions:None = Depends(has_perms("system:config:update")),
) -> R[None]:
    if not service.check_config_key_unique(config.config_key, config.config_id, db):
        return R.fail("修改参数失败，参数键名已存在")
    if not service.update_config(config, db):
        return R.fail("配置不存在")
    return R.ok()

"""删除参数配置"""
@router.delete(
    "/{configIds}",
    response_model = R[bool],
    summary = "删除系统配置",
    )
def delete(configIds: str, db: Session = Depends(get_db)) -> R[bool]:
    ids = [int(x) for x in configIds.split(",") if x.strip()]
    return R.ok(service.delete_configs(ids, db))

"""刷新参数配置"""
@router.post(
    "/refreshCache",
    response_model = R[bool],
    summary = "刷新系统配置缓存",
    )
def refresh_cache(db: Session = Depends(get_db)) -> R[bool]:
    return R.ok(service.refresh_config_cache(db))

