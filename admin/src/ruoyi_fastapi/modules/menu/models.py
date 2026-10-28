"""菜单权限表模型。"""

from sqlalchemy import CHAR, String
from sqlalchemy.orm import Mapped, mapped_column

from ruoyi_fastapi.core.db import AuditMixin, Base


class Menu(AuditMixin, Base):
    """菜单权限表。"""

    __tablename__ = "sys_menu"

    menu_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="菜单ID")
    menu_name: Mapped[str] = mapped_column(String(50), comment="菜单名称")
    parent_id: Mapped[int | None] = mapped_column(default=0, comment="父菜单ID")
    order_num: Mapped[int | None] = mapped_column(default=0, comment="显示顺序")
    path: Mapped[str | None] = mapped_column(String(200), default="", comment="路由地址")
    component: Mapped[str | None] = mapped_column(String(255), comment="组件路径")
    query: Mapped[str | None] = mapped_column(String(255), comment="路由参数")
    route_name: Mapped[str | None] = mapped_column(String(50), default="", comment="路由名称")
    is_frame: Mapped[int | None] = mapped_column(default=1, comment="是否为外链（0是 1否）")
    is_cache: Mapped[int | None] = mapped_column(default=0, comment="是否缓存（0缓存 1不缓存）")
    menu_type: Mapped[str | None] = mapped_column(CHAR(1), default="", comment="菜单类型（M目录 C菜单 F按钮）")
    visible: Mapped[str | None] = mapped_column(CHAR(1), default="0", comment="菜单状态（0显示 1隐藏）")
    status: Mapped[str | None] = mapped_column(CHAR(1), default="0", comment="菜单状态（0正常 1停用）")
    perms: Mapped[str | None] = mapped_column(String(100), comment="权限标识")
    icon: Mapped[str | None] = mapped_column(String(100), default="#", comment="菜单图标")
    
