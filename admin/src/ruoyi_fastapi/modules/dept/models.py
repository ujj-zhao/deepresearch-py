"""部门表模型。"""

from datetime import datetime

from sqlalchemy import CHAR, String
from sqlalchemy.orm import Mapped, mapped_column

from ruoyi_fastapi.core.db import Base


class Dept(Base):
    """部门表。

    DDL 中 sys_dept 仅有 create_by/create_time/update_by/update_time 四个审计字段，
    无 remark，故不混入 AuditMixin（避免引入不存在的 remark 列引发 1054），直接声明。
    """

    __tablename__ = "sys_dept"

    dept_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="部门id")
    parent_id: Mapped[int | None] = mapped_column(default=0, comment="父部门id")
    ancestors: Mapped[str | None] = mapped_column(String(50), default="", comment="祖级列表")
    dept_name: Mapped[str | None] = mapped_column(String(30), default="", comment="部门名称")
    order_num: Mapped[int | None] = mapped_column(default=0, comment="显示顺序")
    leader: Mapped[str | None] = mapped_column(String(20), comment="负责人")
    phone: Mapped[str | None] = mapped_column(String(11), comment="联系电话")
    email: Mapped[str | None] = mapped_column(String(50), comment="邮箱")
    status: Mapped[str | None] = mapped_column(CHAR(1), default="0", comment="部门状态（0正常 1停用）")
    del_flag: Mapped[str | None] = mapped_column(CHAR(1), default="0", comment="删除标志（0代表存在 2代表删除）")
    # 注意：DDL 中 sys_dept 无 parent_name 列，父部门名称由详情接口按父链补全（DeptResp.parent_name）
    create_by: Mapped[str | None] = mapped_column(String(64), default="", comment="创建者")
    create_time: Mapped[datetime | None] = mapped_column(default=datetime.now, comment="创建时间")
    update_by: Mapped[str | None] = mapped_column(String(64), default="", comment="更新者")
    update_time: Mapped[datetime | None] = mapped_column(
        default=datetime.now, onupdate=datetime.now, comment="更新时间"
    )

