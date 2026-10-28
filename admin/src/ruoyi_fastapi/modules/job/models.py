"""定时任务调度表与日志表模型。"""

from datetime import datetime

from sqlalchemy import CHAR, String
from sqlalchemy.orm import Mapped, mapped_column

from ruoyi_fastapi.core.db import AuditMixin, Base


class Job(AuditMixin, Base):
    """定时任务调度表。

    DDL 中主键为复合主键 (job_id, job_name, job_group)。
    """

    __tablename__ = "sys_job"

    job_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="任务ID")
    job_name: Mapped[str] = mapped_column(String(64), primary_key=True, default="", comment="任务名称")
    job_group: Mapped[str] = mapped_column(String(64), primary_key=True, default="DEFAULT", comment="任务组名")
    invoke_target: Mapped[str] = mapped_column(String(500), comment="调用目标字符串")
    cron_expression: Mapped[str | None] = mapped_column(String(255), default="", comment="cron执行表达式")
    misfire_policy: Mapped[str | None] = mapped_column(String(20), default="3", comment="计划执行错误策略（1立即执行 2执行一次 3放弃执行）")
    concurrent: Mapped[str | None] = mapped_column(CHAR(1), default="1", comment="是否并发执行（0允许 1禁止）")
    status: Mapped[str | None] = mapped_column(CHAR(1), default="0", comment="状态（0正常 1暂停）")


class JobLog(Base):
    """定时任务调度日志表。

    DDL 中仅有 create_time 一个审计字段，不混入 AuditMixin。
    """

    __tablename__ = "sys_job_log"

    job_log_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="任务日志ID")
    job_name: Mapped[str] = mapped_column(String(64), comment="任务名称")
    job_group: Mapped[str] = mapped_column(String(64), comment="任务组名")
    invoke_target: Mapped[str] = mapped_column(String(500), comment="调用目标字符串")
    job_message: Mapped[str | None] = mapped_column(String(500), comment="日志信息")
    status: Mapped[str | None] = mapped_column(CHAR(1), default="0", comment="执行状态（0正常 1失败）")
    exception_info: Mapped[str | None] = mapped_column(String(2000), default="", comment="异常信息")
    start_time: Mapped[datetime | None] = mapped_column(comment="执行开始时间")
    end_time: Mapped[datetime | None] = mapped_column(comment="执行结束时间")
    create_time: Mapped[datetime | None] = mapped_column(default=datetime.now, comment="创建时间")
