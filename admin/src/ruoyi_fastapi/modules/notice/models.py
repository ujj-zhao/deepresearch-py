"""通知公告表与已读记录表模型。"""

from datetime import datetime

from sqlalchemy import CHAR, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.mysql import LONGTEXT

from ruoyi_fastapi.core.db import AuditMixin, Base


class Notice(AuditMixin, Base):
    """通知公告表。"""

    __tablename__ = "sys_notice"

    notice_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="公告ID")
    notice_title: Mapped[str] = mapped_column(String(50), comment="公告标题")
    notice_type: Mapped[str] = mapped_column(CHAR(1), comment="公告类型（1通知 2公告）")
    notice_content: Mapped[bytes | None] = mapped_column(LONGTEXT, comment="公告内容")
    status: Mapped[str | None] = mapped_column(CHAR(1), default="0", comment="公告状态（0正常 1关闭）")


class NoticeRead(Base):
    """公告已读记录表。"""

    __tablename__ = "sys_notice_read"

    read_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="已读主键")
    notice_id: Mapped[int] = mapped_column(comment="公告id")
    user_id: Mapped[int] = mapped_column(comment="用户id")
    read_time: Mapped[datetime] = mapped_column(comment="阅读时间")
