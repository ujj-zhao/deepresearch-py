"""用户信息表模型。"""

from datetime import datetime

from sqlalchemy import CHAR, String
from sqlalchemy.orm import Mapped, mapped_column

from ruoyi_fastapi.core.db import AuditMixin, Base


class SysUser(AuditMixin, Base):
    """用户信息表。"""

    __tablename__ = "sys_user"

    user_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="用户ID")
    dept_id: Mapped[int | None] = mapped_column(comment="部门ID")
    user_name: Mapped[str] = mapped_column(String(30), comment="用户账号")
    nick_name: Mapped[str] = mapped_column(String(30), comment="用户昵称")
    user_type: Mapped[str | None] = mapped_column(String(2), default="00", comment="用户类型（00系统用户）")
    email: Mapped[str] = mapped_column(String(50), default="", comment="用户邮箱")
    phonenumber: Mapped[str | None] = mapped_column(String(11), default="", comment="手机号码")
    sex: Mapped[str | None] = mapped_column(CHAR(1), default="0", comment="用户性别（0男 1女 2未知）")
    avatar: Mapped[str | None] = mapped_column(String(100), default="", comment="头像地址")
    password: Mapped[str | None] = mapped_column(String(100), default="", comment="密码")
    status: Mapped[str | None] = mapped_column(CHAR(1), default="0", comment="账号状态（0正常 1停用）")
    del_flag: Mapped[str | None] = mapped_column(CHAR(1), default="0", comment="删除标志（0代表存在 2代表删除）")
    login_ip: Mapped[str | None] = mapped_column(String(128), default="", comment="最后登录IP")
    login_date: Mapped[datetime | None] = mapped_column(comment="最后登录时间")
    pwd_update_date: Mapped[datetime | None] = mapped_column(comment="密码最后更新时间")

    # create_by / create_time / update_by / update_time / remark 由 AuditMixin 提供


class UserPost(Base):
    """用户与岗位关联表。"""

    __tablename__ = "sys_user_post"

    user_id: Mapped[int] = mapped_column(primary_key=True, comment="用户ID")
    post_id: Mapped[int] = mapped_column(primary_key=True, comment="岗位ID")


class UserRole(Base):
    """用户和角色关联表。"""

    __tablename__ = "sys_user_role"

    user_id: Mapped[int] = mapped_column(primary_key=True, comment="用户ID")
    role_id: Mapped[int] = mapped_column(primary_key=True, comment="角色ID")
