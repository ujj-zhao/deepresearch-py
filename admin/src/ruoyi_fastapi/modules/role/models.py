"""角色信息表模型。"""

from sqlalchemy import CHAR, String
from sqlalchemy.orm import Mapped, mapped_column

from ruoyi_fastapi.core.db import AuditMixin, Base


class Role(AuditMixin, Base):
    """角色信息表。"""

    __tablename__ = "sys_role"

    role_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="角色ID")
    role_name: Mapped[str] = mapped_column(String(30), comment="角色名称")
    role_key: Mapped[str] = mapped_column(String(100), comment="角色权限字符串")
    role_sort: Mapped[int] = mapped_column(comment="显示顺序")
    data_scope: Mapped[str | None] = mapped_column(CHAR(1), default="1", comment="数据范围（1：全部数据权限 2：自定数据权限 3：本部门数据权限 4：本部门及以下数据权限）")
    menu_check_strictly: Mapped[int | None] = mapped_column(default=1, comment="菜单树选择项是否关联显示")
    dept_check_strictly: Mapped[int | None] = mapped_column(default=1, comment="部门树选择项是否关联显示")
    status: Mapped[str] = mapped_column(CHAR(1), comment="角色状态（0正常 1停用）")
    del_flag: Mapped[str | None] = mapped_column(CHAR(1), default="0", comment="删除标志（0代表存在 2代表删除）")


class RoleDept(Base):
    """角色和部门关联表。"""

    __tablename__ = "sys_role_dept"

    role_id: Mapped[int] = mapped_column(primary_key=True, comment="角色ID")
    dept_id: Mapped[int] = mapped_column(primary_key=True, comment="部门ID")


class RoleMenu(Base):
    """角色和菜单关联表。"""

    __tablename__ = "sys_role_menu"

    role_id: Mapped[int] = mapped_column(primary_key=True, comment="角色ID")
    menu_id: Mapped[int] = mapped_column(primary_key=True, comment="菜单ID")
