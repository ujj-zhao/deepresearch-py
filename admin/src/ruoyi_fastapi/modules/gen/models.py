"""代码生成业务表与字段表模型。"""

from datetime import datetime

from sqlalchemy import CHAR, String
from sqlalchemy.orm import Mapped, mapped_column

from ruoyi_fastapi.core.db import Base


class GenTable(Base):
    """代码生成业务表。

    DDL 中有 create_by/create_time/update_by/update_time，但无 remark，
    且 remark 字段不可空默认 ''，此处直接声明全部审计字段以精确对齐 DDL。
    """

    __tablename__ = "gen_table"

    table_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="编号")
    table_name: Mapped[str | None] = mapped_column(String(200), default="", comment="表名称")
    table_comment: Mapped[str | None] = mapped_column(String(500), default="", comment="表描述")
    sub_table_name: Mapped[str | None] = mapped_column(String(64), comment="关联子表的表名")
    sub_table_fk_name: Mapped[str | None] = mapped_column(String(64), comment="子表关联的外键名")
    class_name: Mapped[str | None] = mapped_column(String(100), default="", comment="实体类名称")
    tpl_category: Mapped[str | None] = mapped_column(String(200), default="crud", comment="使用的模板（crud单表操作 tree树表操作）")
    tpl_web_type: Mapped[str | None] = mapped_column(String(30), default="", comment="前端模板类型")
    package_name: Mapped[str | None] = mapped_column(String(100), comment="生成包路径")
    module_name: Mapped[str | None] = mapped_column(String(30), comment="生成模块名")
    business_name: Mapped[str | None] = mapped_column(String(30), comment="生成业务名")
    function_name: Mapped[str | None] = mapped_column(String(50), comment="生成功能名")
    function_author: Mapped[str | None] = mapped_column(String(50), comment="生成功能作者")
    form_col_num: Mapped[int | None] = mapped_column(default=1, comment="表单布局（单列 双列 三列）")
    gen_type: Mapped[str | None] = mapped_column(CHAR(1), default="0", comment="生成代码方式（0zip压缩包 1自定义路径）")
    gen_path: Mapped[str | None] = mapped_column(String(200), default="/", comment="生成路径")
    options: Mapped[str | None] = mapped_column(String(1000), comment="其它生成选项")

    # 审计字段（gen_table 无 create_dept，且 remark 默认 ''）
    create_by: Mapped[str | None] = mapped_column(String(64), default="", comment="创建者")
    create_time: Mapped[datetime | None] = mapped_column(default=datetime.now, comment="创建时间")
    update_by: Mapped[str | None] = mapped_column(String(64), default="", comment="更新者")
    update_time: Mapped[datetime | None] = mapped_column(default=datetime.now, onupdate=datetime.now, comment="更新时间")
    remark: Mapped[str | None] = mapped_column(String(500), comment="备注")


class GenTableColumn(Base):
    """代码生成业务表字段。

    DDL 中有 create_by/create_time/update_by/update_time，但无 remark，
    此处直接声明以精确对齐 DDL。
    """

    __tablename__ = "gen_table_column"

    column_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="编号")
    table_id: Mapped[int | None] = mapped_column(comment="归属表编号")
    column_name: Mapped[str | None] = mapped_column(String(200), comment="列名称")
    column_comment: Mapped[str | None] = mapped_column(String(500), comment="列描述")
    column_type: Mapped[str | None] = mapped_column(String(100), comment="列类型")
    java_type: Mapped[str | None] = mapped_column(String(500), comment="JAVA类型")
    java_field: Mapped[str | None] = mapped_column(String(200), comment="JAVA字段名")
    is_pk: Mapped[str | None] = mapped_column(CHAR(1), comment="是否主键（1是）")
    is_increment: Mapped[str | None] = mapped_column(CHAR(1), comment="是否自增（1是）")
    is_required: Mapped[str | None] = mapped_column(CHAR(1), comment="是否必填（1是）")
    is_insert: Mapped[str | None] = mapped_column(CHAR(1), comment="是否为插入字段（1是）")
    is_edit: Mapped[str | None] = mapped_column(CHAR(1), comment="是否编辑字段（1是）")
    is_list: Mapped[str | None] = mapped_column(CHAR(1), comment="是否列表字段（1是）")
    is_query: Mapped[str | None] = mapped_column(CHAR(1), comment="是否查询字段（1是）")
    query_type: Mapped[str | None] = mapped_column(String(200), default="EQ", comment="查询方式")
    html_type: Mapped[str | None] = mapped_column(String(200), comment="显示类型")
    dict_type: Mapped[str | None] = mapped_column(String(200), default="", comment="字典类型")
    sort: Mapped[int | None] = mapped_column(comment="排序")

    # 审计字段（gen_table_column 无 remark）
    create_by: Mapped[str | None] = mapped_column(String(64), default="", comment="创建者")
    create_time: Mapped[datetime | None] = mapped_column(default=datetime.now, comment="创建时间")
    update_by: Mapped[str | None] = mapped_column(String(64), default="", comment="更新者")
    update_time: Mapped[datetime | None] = mapped_column(default=datetime.now, onupdate=datetime.now, comment="更新时间")
