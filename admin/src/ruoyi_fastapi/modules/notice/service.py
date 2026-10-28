"""通知公告业务逻辑（对应若依 SysNoticeServiceImpl + 项目扩展的已读记录）。

notice_content 在库中是 longblob（若依历史遗留），ORM 侧为 bytes：
写入前 encode('utf-8')，读出后 decode('utf-8') 转 Pydantic str。
"""

from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from ruoyi_fastapi.core.exception import ServiceException

from .models import Notice, NoticeRead
from .schemas import (
    NoticeCreate,
    NoticeDetailResp,
    NoticePageQuery,
    NoticeResp,
    NoticeUpdate,
)

# 首页公告面板展示条数
TOP_NOTICE_LIMIT = 8


def _decode_content(raw: bytes | str | None) -> str | None:
    """longblob → 文本（pymysql 读 longblob 返回 bytes）。"""
    if raw is None:
        return None
    if isinstance(raw, bytes):
        return raw.decode("utf-8", errors="replace")
    return raw


def _encode_content(text: str | None) -> bytes | None:
    """文本 → longblob。"""
    return None if text is None else text.encode("utf-8")


def select_notice_list(query: NoticePageQuery, db: Session) -> tuple[list[NoticeResp], int]:
    """分页查询公告列表（对应 selectNoticeList）。"""
    stmt = select(Notice)
    if query.notice_title:
        stmt = stmt.where(Notice.notice_title.like(f"%{query.notice_title}%"))
    if query.notice_type:
        stmt = stmt.where(Notice.notice_type == query.notice_type)
    if query.create_by:
        stmt = stmt.where(Notice.create_by.like(f"%{query.create_by}%"))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(Notice.notice_id.desc())
        .limit(query.page_size)
        .offset((query.page_num - 1) * query.page_size)
    ).all()

    result = []
    for r in rows:
        resp = NoticeResp.model_validate(r)
        resp.notice_content = _decode_content(r.notice_content)
        result.append(resp)
    return result, total


def select_notice_top(db: Session) -> list[NoticeResp]:
    """首页公告面板：正常状态公告按创建时间倒序取前 N 条（对应若依 listTop）。

    二级排序按主键倒序，保证 create_time 相同（如内置数据批量插入）时顺序稳定。
    """
    rows = db.scalars(
        select(Notice)
        .where(Notice.status == "0")
        .order_by(Notice.create_time.desc(), Notice.notice_id.desc())
        .limit(TOP_NOTICE_LIMIT)
    ).all()
    result = []
    for r in rows:
        resp = NoticeResp.model_validate(r)
        resp.notice_content = _decode_content(r.notice_content)
        result.append(resp)
    return result


def select_notice_detail(notice_id: int, user_id: int, db: Session) -> NoticeDetailResp:
    """公告详情（对应 selectNoticeByNoticeIds），并记录当前用户已读。

    已读语义：查看即已读；同一用户同一公告只记一条（幂等）。
    """
    notice = db.get(Notice, notice_id)
    if notice is None:
        raise ServiceException("公告不存在", code=404)

    is_read = db.scalar(
        select(func.count())
        .select_from(NoticeRead)
        .where(NoticeRead.notice_id == notice_id, NoticeRead.user_id == user_id)
    ) > 0
    if not is_read:
        db.add(NoticeRead(notice_id=notice_id, user_id=user_id, read_time=datetime.now()))
        db.commit()

    resp = NoticeDetailResp.model_validate(notice)
    resp.notice_content = _decode_content(notice.notice_content)
    resp.is_read = True
    return resp


def insert_notice(req: NoticeCreate, db: Session) -> bool:
    """新增公告（对应 insertNotice）。"""
    notice = Notice(
        notice_title=req.notice_title,
        notice_type=req.notice_type,
        notice_content=_encode_content(req.notice_content),
        status=req.status,
        remark=req.remark,
    )
    db.add(notice)
    db.commit()
    return True


def update_notice(req: NoticeUpdate, db: Session) -> bool:
    """修改公告（对应 updateNotice）。"""
    notice = db.get(Notice, req.notice_id)
    if notice is None:
        raise ServiceException("公告不存在", code=404)

    notice.notice_title = req.notice_title
    notice.notice_type = req.notice_type
    notice.notice_content = _encode_content(req.notice_content)
    notice.status = req.status
    notice.remark = req.remark
    db.commit()
    return True


def delete_notice_by_ids(notice_ids: list[int], db: Session) -> bool:
    """批量删除公告（对应 deleteNoticeByNoticeIds），并清理已读记录。"""
    if not notice_ids:
        return True

    # 已读记录属于公告的从属数据，随公告一起删除
    db.execute(delete(NoticeRead).where(NoticeRead.notice_id.in_(notice_ids)))
    db.execute(delete(Notice).where(Notice.notice_id.in_(notice_ids)))
    db.commit()
    return True


def select_unread_count(user_id: int, db: Session) -> int:
    """当前用户未读公告数（项目扩展：正常状态公告 - 已读数）。"""
    total = db.scalar(
        select(func.count())
        .select_from(Notice)
        .where(Notice.status == "0")
    ) or 0
    read = db.scalar(
        select(func.count())
        .select_from(NoticeRead)
        .where(NoticeRead.user_id == user_id)
    ) or 0
    return max(total - read, 0)
