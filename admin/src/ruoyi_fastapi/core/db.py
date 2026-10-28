"""数据库核心组件。

提供全局共享的 SQLAlchemy 引擎、会话工厂、声明式 Base 与审计字段 Mixin。
所有 ORM 模型统一继承 Base；带 RuoYi 标准审计字段的表混入 AuditMixin。
关联表（如 sys_user_role）直接继承 Base，不带审计字段。
"""

from datetime import datetime

from sqlalchemy import String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from ruoyi_fastapi.core.config import settings

# 全局唯一引擎：进程内共享一个连接池，禁止多处重复创建
engine = create_engine(
    settings.mysql_url,
    echo=settings.DEBUG,        # 调试模式下打印实际执行的 SQL
    pool_pre_ping=True,         # 取连接前做存活探测，自动重连断掉的连接
    pool_recycle=3600,          # 连接超过 1 小时强制回收，规避 MySQL wait_timeout 断连
    pool_size=10,               # 连接池常驻连接数
    max_overflow=20,            # 高峰期允许临时超出的连接数
)

# 会话工厂：调用 SessionLocal() 创建独立会话，用完必须 close
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,      # commit 后对象不过期，请求层仍可读取属性
)


class Base(DeclarativeBase):
    """全局声明式基类，所有 ORM 模型继承它（不含审计字段）。"""


class AuditMixin:
    """RuoYi 标准审计字段 Mixin。

    严格对齐 fastapi_ruoyi 库的 DDL：create_by/update_by 为 varchar(64)，
    create_time/update_time 为 datetime，remark 为 varchar(500)。
    注意：fastapi_ruoyi 的表均无 create_dept 字段，故此处不再声明。
    需要审计字段的业务表混入此类；关联表（如 sys_user_role）无须混入。
    """

    create_by: Mapped[str | None] = mapped_column(String(64), default="", comment="创建者")
    create_time: Mapped[datetime | None] = mapped_column(
        default=datetime.now, comment="创建时间"
    )
    update_by: Mapped[str | None] = mapped_column(String(64), default="", comment="更新者")
    update_time: Mapped[datetime | None] = mapped_column(
        default=datetime.now, onupdate=datetime.now, comment="更新时间"
    )
    remark: Mapped[str | None] = mapped_column(String(500), comment="备注")
