from fastapi import APIRouter, Depends
from ruoyi_fastapi.core.dependencies import get_db
from ruoyi_fastapi.core.response import PageResult, R
from .. import service as monitor_service


router = APIRouter(prefix="/cache", tags=["监控-缓存"])



@router.get(
    "",
    response_model=R[dict],
    response_model_by_alias=True,
    summary="查询缓存信息",
)
def get_cache_info():
    return R.ok(monitor_service.get_cache_info())

@router.get(
    "/get_names",
    response_model=R[list[str]],
    response_model_by_alias=True,
    summary="查询缓存键列表",
)
def get_cache_names():
    return R.ok(monitor_service.get_cache_names())

@router.get(
    "/{cache_name}",
    response_model=R[list[str]],
    response_model_by_alias=True,
    summary="查询缓存键列表",
)
def get_cache_keys(cache_name: str):
    return R.ok(monitor_service.get_cache_keys(cache_name))

@router.get(
    "/{cache_name}/{cache_key}",
    response_model=R[list[str]],
    response_model_by_alias=True,
    summary="查询缓存值列表",
)
def get_cache_values(cache_name: str, cache_key: str):
    return R.ok(monitor_service.get_cache_values(cache_name, cache_key))


@router.delete(
    "/clear_cache_name/{cache_name}",
    response_model=R[bool],
    response_model_by_alias=True,
    summary="清理缓存键",
)
def clear_cache_name(cache_name: str):
    return R.ok(monitor_service.clear_cache_name(cache_name))

@router.delete(
    "/clear_cache_key/{cache_key}",
    response_model=R[bool],
    response_model_by_alias=True,
    summary="清理缓存值",
)
def clear_cache_key(cache_key: str):
    return R.ok(monitor_service.clear_cache_key(cache_key))

@router.delete(
    "/clear_cache_all",
    response_model=R[bool],
    response_model_by_alias=True,
    summary="清理所有缓存",
)
def clear_cache_all(cache_name: str):
    return R.ok(monitor_service.clear_cache())