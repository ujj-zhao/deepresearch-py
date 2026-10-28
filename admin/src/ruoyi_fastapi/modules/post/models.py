"""岗位信息表模型。"""

from sqlalchemy import CHAR, String
from sqlalchemy.orm import Mapped, mapped_column

from ruoyi_fastapi.core.db import AuditMixin, Base


class Post(AuditMixin, Base):
    """岗位信息表。"""

    __tablename__ = "sys_post"

    post_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="岗位ID")
    post_code: Mapped[str] = mapped_column(String(64), comment="岗位编码")
    post_name: Mapped[str] = mapped_column(String(50), comment="岗位名称")
    post_sort: Mapped[int] = mapped_column(comment="显示顺序")
    status: Mapped[str] = mapped_column(CHAR(1), comment="状态（0正常 1停用）")
