from fastapi import APIRouter
from ruoyi_fastapi.core.response import R
from .. import service as monitor_service

router = APIRouter(prefix="/server", tags=["监控-服务器"])

@router.get(
    "",
    response_model=R[dict],
    response_model_by_alias=True,
    summary="查询服务器信息",
)
def get_info():
    return R.ok(monitor_service.get_server_info())