"""参数配置表模型。"""

from sqlalchemy import CHAR, String
from sqlalchemy.orm import Mapped, mapped_column

from ruoyi_fastapi.core.db import AuditMixin, Base


class Config(AuditMixin, Base):
    """参数配置表。"""

    __tablename__ = "sys_config"

    config_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="参数主键")
    config_name: Mapped[str] = mapped_column(String(100), default="", comment="参数名称")
    config_key: Mapped[str] = mapped_column(String(100), default="", comment="参数键名")
    config_value: Mapped[str] = mapped_column(String(500), default="", comment="参数键值")
    config_type: Mapped[str | None] = mapped_column(CHAR(1), default="N", comment="系统内置（Y是 N否）")
