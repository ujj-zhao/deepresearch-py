from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ruoyi_fastapi.core.dependencies import get_db
from ruoyi_fastapi.core.response import PageResult, R
from .. import service as monitor_service
from ..schemas import SysLogininfoResp, SysLogininfoQuery

router = APIRouter(prefix="/logininfor", tags=["监控-登录日志"])


@router.get(
    "/list",
    response_model=PageResult[SysLogininfoResp],
    response_model_by_alias=True,
    summary="分页查询登录日志列表",
)
def list_logininfo(
    query: SysLogininfoQuery = Depends(),
    db: Session = Depends(get_db),
):
    """分页查询登录日志列表。"""
    rows, total = monitor_service.list_logininfo(query, db)
    return PageResult.of(rows, total)


"""导出监控列表"""
# @router.post(
#     "/export",
#     response_model=R[bool],
#     response_model_by_alias=True,
#     summary="导出登录日志列表",
# )
# def export(request: SysLogininfoReq):
#     return R.ok(monitor_service.export(request))

"""清理监控列表"""
@router.delete(
    "/clean",
    response_model=R[bool],
    response_model_by_alias=True,
    summary="清理登录日志列表",
)
def clean(db: Session = Depends(get_db)):
    return R.ok(monitor_service.clean(db))


"""移除监控列表"""
@router.delete(
    "/{infoIds}",
    response_model=R[bool],
    response_model_by_alias=True,
    summary="移除登录日志列表",
)
def remove(infoIds: str, db: Session = Depends(get_db)):
    try :
        parts = [ p.strip() for p in infoIds.split( "," ) if p.strip()]
        info_id_list = [ int(p) for p in parts if p.isdigit()]
    except ValueError:
        raise ServiceException( "infoIds 格式错误" , code= 400 )
    if not info_id_list:
        return R.ok(False)
    return R.ok(monitor_service.remove(info_id_list, db))


"""解锁监控列表"""
@router.get(
    "/unlock/{user_name}",
    response_model=R[bool],
    response_model_by_alias=True,
    summary="解锁登录日志列表",
)
def unlock(user_name: str):
    return R.ok(monitor_service.clearLoginRecordCache(user_name))