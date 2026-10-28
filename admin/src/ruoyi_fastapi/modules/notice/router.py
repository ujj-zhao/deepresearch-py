"""通知公告路由（对应若依 SysNoticeController）。"""

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
    NoticeCreate,
    NoticeDetailResp,
    NoticePageQuery,
    NoticeResp,
    NoticeUpdate,
)

router = APIRouter(prefix="/system/notice", tags=["系统-通知公告"])


# 静态路由必须注册在 /{noticeId} 动态路由之前


@router.get(
    "/list",
    response_model=PageResult[NoticeResp],
    response_model_by_alias=True,
    summary="分页查询通知公告列表",
)
def list_notices(
    query: NoticePageQuery = Depends(),
    _: LoginUser = Depends(get_current_login_user),
    _perms: None = Depends(has_perms("system:notice:list")),
    db: Session = Depends(get_db),
):
    rows, total = service.select_notice_list(query, db)
    return PageResult.of(rows, total)


@router.get(
    "/unreadCount",
    response_model=R[int],
    response_model_by_alias=True,
    summary="当前用户未读公告数（项目扩展）",
)
def get_unread_count(
    login_user: LoginUser = Depends(get_current_login_user),
    db: Session = Depends(get_db),
):
    return R.ok(service.select_unread_count(login_user.user_id, db))


@router.get(
    "/listTop",
    response_model=R[list[NoticeResp]],
    response_model_by_alias=True,
    summary="首页公告面板：最新正常状态公告",
    description="静态字面量路由，必须注册在 /{notice_id} 动态路由之前；"
    "首页所有登录用户可见，不挂权限标识（对齐 dict type/{dictType} 策略）",
)
def list_top_notices(
    _: LoginUser = Depends(get_current_login_user),
    db: Session = Depends(get_db),
):
    return R.ok(service.select_notice_top(db))


@router.get(
    "/{notice_id}",
    response_model=R[NoticeDetailResp],
    response_model_by_alias=True,
    summary="公告详情（查看即记已读）",
)
def get_notice_detail(
    notice_id: int,
    login_user: LoginUser = Depends(get_current_login_user),
    _perms: None = Depends(has_perms("system:notice:query")),
    db: Session = Depends(get_db),
):
    return R.ok(service.select_notice_detail(notice_id, login_user.user_id, db))


@router.post(
    "",
    response_model=R[bool],
    response_model_by_alias=True,
    summary="新增通知公告",
)
@log(title="通知公告", business_type=BusinessType.INSERT)
def add_notice(
    request: Request,
    req: NoticeCreate,
    _perms: None = Depends(has_perms("system:notice:add")),
    db: Session = Depends(get_db),
):
    return R.ok(service.insert_notice(req, db))


@router.put(
    "",
    response_model=R[bool],
    response_model_by_alias=True,
    summary="修改通知公告",
)
@log(title="通知公告", business_type=BusinessType.UPDATE)
def update_notice(
    request: Request,
    req: NoticeUpdate,
    _perms: None = Depends(has_perms("system:notice:edit")),
    db: Session = Depends(get_db),
):
    return R.ok(service.update_notice(req, db))


@router.delete(
    "/{notice_ids}",
    response_model=R[bool],
    response_model_by_alias=True,
    summary="删除通知公告",
)
@log(title="通知公告", business_type=BusinessType.DELETE)
def delete_notices(
    notice_ids: str,
    request: Request,
    _perms: None = Depends(has_perms("system:notice:remove")),
    db: Session = Depends(get_db),
):
    ids = [int(x) for x in notice_ids.split(",") if x.strip()]
    return R.ok(service.delete_notice_by_ids(ids, db))
