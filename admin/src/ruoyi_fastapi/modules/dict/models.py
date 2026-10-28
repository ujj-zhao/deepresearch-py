"""字典类型与字典数据表模型。"""

from sqlalchemy import CHAR, String
from sqlalchemy.orm import Mapped, mapped_column

from ruoyi_fastapi.core.db import AuditMixin, Base


class DictType(AuditMixin, Base):
    """字典类型表。"""

    __tablename__ = "sys_dict_type"

    dict_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="字典主键")
    dict_name: Mapped[str] = mapped_column(String(100), default="", comment="字典名称")
    dict_type: Mapped[str] = mapped_column(String(100), default="", comment="字典类型")
    status: Mapped[str | None] = mapped_column(CHAR(1), default="0", comment="状态（0正常 1停用）")


class DictData(AuditMixin, Base):
    """字典数据表。"""

    __tablename__ = "sys_dict_data"

    dict_code: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="字典编码")
    dict_sort: Mapped[int | None] = mapped_column(default=0, comment="字典排序")
    dict_label: Mapped[str] = mapped_column(String(100), default="", comment="字典标签")
    dict_value: Mapped[str] = mapped_column(String(100), default="", comment="字典键值")
    dict_type: Mapped[str] = mapped_column(String(100), default="", comment="字典类型")
    css_class: Mapped[str | None] = mapped_column(String(100), comment="样式属性（其他样式扩展）")
    list_class: Mapped[str | None] = mapped_column(String(100), comment="表格回显样式")
    is_default: Mapped[str | None] = mapped_column(CHAR(1), default="N", comment="是否默认（Y是 N否）")
    status: Mapped[str | None] = mapped_column(CHAR(1), default="0", comment="状态（0正常 1停用）")
