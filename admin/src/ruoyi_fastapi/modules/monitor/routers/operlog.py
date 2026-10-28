from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ruoyi_fastapi.core.dependencies import get_db
from ruoyi_fastapi.core.response import PageResult, R
from .. import service as monitor_service
from ..schemas import SysOperLogQuery, SysOperLogVO

router = APIRouter(prefix="/operlog", tags=["监控-操作日志"])


# 静态路由（/list、/export、/clean）必须注册在 /{operLogIds} 动态路由之前
@router.get(
    "/list",
    response_model=PageResult[SysOperLogVO],
    response_model_by_alias=True,
    summary="分页查询操作日志列表",
)
def oper_log_list(
    query: SysOperLogQuery = Depends(),
    db: Session = Depends(get_db),
):
    """分页查询操作日志列表。"""
    rows, total = monitor_service.list_oper_log(query, db)
    return PageResult.of(rows, total)


@router.post(
    "/export",
    response_model=R[bool],
    response_model_by_alias=True,
    summary="导出操作日志列表",
)
def export_oper_log(query: SysOperLogQuery = Depends()):
    """导出操作日志（Excel 生成待接入，当前占位）。"""
    raise NotImplementedError("TODO: 实现导出")


@router.delete(
    "/clean",
    response_model=R[bool],
    response_model_by_alias=True,
    summary="清理操作日志列表",
)
def clean_oper_log(db: Session = Depends(get_db)):
    return R.ok(monitor_service.clean_oper_log(db))


@router.delete(
    "/{operLogIds}",
    response_model=R[bool],
    response_model_by_alias=True,
    summary="移除操作日志列表",
)
def remove_oper_log(operLogIds: str, db: Session = Depends(get_db)):
    """逗号分隔 ID（对齐若依 Long[] 路径参数绑定）。"""
    oper_log_ids = [int(x) for x in operLogIds.split(",") if x.strip()]
    return R.ok(monitor_service.remove_oper_log(oper_log_ids, db))
