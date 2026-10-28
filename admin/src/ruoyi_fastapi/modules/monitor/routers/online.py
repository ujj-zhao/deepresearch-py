from fastapi import APIRouter

from ruoyi_fastapi.core.response import R

from .. import service as monitor_service
from ..schemas import SysOnlineUser

router = APIRouter(prefix="/online", tags=["监控-在线用户"])


@router.get(
    "/list",
    response_model=R[list[SysOnlineUser]],
    response_model_by_alias=True,
    summary="查询在线用户列表",
)
def online_user_list(ipaddr: str | None = None, user_name: str | None = None):
    return R.ok(monitor_service.online_user_list(ipaddr, user_name))


@router.delete(
    "/{token_id}",
    response_model=R[bool],
    response_model_by_alias=True,
    summary="强退用户",
)
def force_logout(token_id: str):
    return R.ok(monitor_service.force_logout(token_id))
