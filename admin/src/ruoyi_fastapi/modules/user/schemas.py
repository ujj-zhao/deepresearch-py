"""用户模块的 Pydantic 请求/响应模型。"""

from datetime import datetime

from pydantic import Field

from ruoyi_fastapi.core.schemas import CamelModel
from ruoyi_fastapi.modules.post.schemas import PostResp
from ruoyi_fastapi.modules.role.schemas import RoleResp


# ---- 响应模型 ----
class UserListResp(CamelModel):
    """用户列表行（对应若依 SysUserMapper.selectUserList 的关联查询结果，含部门名）。"""

    user_id: int = Field(description="用户ID")
    dept_id: int | None = Field(default=None, description="部门ID")
    user_name: str = Field(description="用户账号")
    nick_name: str | None = Field(default=None, description="用户昵称")
    email: str | None = Field(default=None, description="邮箱")
    phonenumber: str | None = Field(default=None, description="手机号")
    sex: str | None = Field(default=None, description="性别")
    status: str | None = Field(default=None, description="状态")
    login_ip: str | None = Field(default=None, description="最后登录IP")
    login_date: datetime | None = Field(default=None, description="最后登录时间")
    create_time: datetime | None = Field(default=None, description="创建时间")
    dept_name: str | None = Field(default=None, description="部门名称（来自 sys_dept 联查）")


class UserDTO(CamelModel):
    """用户信息响应模型(对外脱敏,不含 password)。"""

    user_id: int = Field(description="用户ID")
    dept_id: int | None = Field(default=None, description="部门ID")
    user_name: str = Field(description="用户账号")
    nick_name: str = Field(description="用户昵称")
    user_type: str | None = Field(default="00", description="用户类型（00系统用户）")
    email: str | None = Field(default="", description="用户邮箱")
    phonenumber: str | None = Field(default="", description="手机号码")
    sex: str | None = Field(default="0", description="用户性别（0男 1女 2未知）")
    avatar: str | None = Field(default="", description="头像地址")
    status: str | None = Field(default="0", description="账号状态（0正常 1停用）")
    del_flag: str | None = Field(default="0", description="删除标志（0代表存在 2代表删除）")
    login_ip: str | None = Field(default="", description="最后登录IP")
    login_date: datetime | None = Field(default=None, description="最后登录时间")
    pwd_update_date: datetime | None = Field(default=None, description="密码最后更新时间")
    remark: str | None = Field(default=None, description="备注")


class UserInfoResp(CamelModel):
    """用户新增/修改页初始化与详情响应（对应若依 getInfo 的 AjaxResult 平铺结构）。

    GET /system/user/（新增页）：仅 roles + posts；
    GET /system/user/{userId}（修改页）：额外带 user + roleIds + postIds 回显。
    """

    code: int = Field(default=200, description="状态码")
    msg: str = Field(default="操作成功", description="状态描述")
    roles: list[RoleResp] = Field(default_factory=list, description="全部角色（非 admin 目标用户已过滤 admin 角色）")
    posts: list[PostResp] = Field(default_factory=list, description="全部岗位")
    user: UserDTO | None = Field(default=None, description="用户详情（仅详情接口返回）")
    role_ids: list[int] = Field(default_factory=list, description="已绑定角色ID")
    post_ids: list[int] = Field(default_factory=list, description="已绑定岗位ID")


class UserAuthRoleResp(CamelModel):
    """用户分配角色页回显（对应若依 authRole 接口的 AjaxResult 平铺结构）。"""

    code: int = Field(default=200, description="状态码")
    msg: str = Field(default="操作成功", description="状态描述")
    user: UserDTO = Field(description="用户信息")
    roles: list[RoleResp] = Field(default_factory=list, description="用户已绑定角色")


# ---- 请求模型 ----
class UserCreate(CamelModel):
    """新增用户请求（含角色/岗位绑定，对应若依 SysUser.roleIds/postIds）。"""

    user_name: str = Field(max_length=30, description="用户账号")
    nick_name: str = Field(max_length=30, description="用户昵称")
    password: str = Field(min_length=6, max_length=100, description="密码")
    dept_id: int | None = Field(default=None, description="部门ID")
    phonenumber: str | None = Field(default=None, max_length=11, description="手机号码")
    email: str | None = Field(default=None, max_length=50, description="用户邮箱")
    sex: str | None = Field(default="0", pattern="^[012]$", description="用户性别")
    status: str = Field(default="0", pattern="^[01]$", description="账号状态（0正常 1停用）")
    remark: str | None = Field(default=None, max_length=500, description="备注")
    role_ids: list[int] = Field(default_factory=list, description="关联角色ID")
    post_ids: list[int] = Field(default_factory=list, description="关联岗位ID")


class UserUpdate(CamelModel):
    """更新用户请求（不允许修改 user_name / password，工作单元模式更新）。"""

    user_id: int = Field(ge=1, description="用户ID")
    nick_name: str = Field(max_length=30, description="用户昵称")
    dept_id: int | None = Field(default=None, description="部门ID")
    phonenumber: str | None = Field(default=None, max_length=11, description="手机号码")
    email: str | None = Field(default=None, max_length=50, description="用户邮箱")
    sex: str | None = Field(default="0", pattern="^[012]$", description="用户性别")
    status: str = Field(default="0", pattern="^[01]$", description="账号状态")
    remark: str | None = Field(default=None, max_length=500, description="备注")
    role_ids: list[int] = Field(default_factory=list, description="关联角色ID")
    post_ids: list[int] = Field(default_factory=list, description="关联岗位ID")


class UserChangeStatusReq(CamelModel):
    """用户启停请求（对应若依 changeStatus 的 JSON 体）。"""

    user_id: int = Field(ge=1, description="用户ID")
    status: str = Field(pattern="^[01]$", description="账号状态（0正常 1停用）")


class ResetPwdReq(CamelModel):
    """重置密码请求（对应若依 resetPwd 的 JSON 体）。"""

    user_id: int = Field(ge=1, description="用户ID")
    password: str = Field(min_length=6, max_length=100, description="新密码")


# ---- 分页查询 ----
class UserPageQuery(CamelModel):
    """用户列表分页查询参数（对应若依 selectUserList 的 where 条件）。"""

    page_num: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=10, ge=1, le=100, description="每页条数")
    user_name: str | None = Field(default=None, description="用户账号(模糊查询)")
    phonenumber: str | None = Field(default=None, description="手机号(模糊查询)")
    status: str | None = Field(default=None, pattern="^[01]$", description="账号状态")
    dept_id: int | None = Field(default=None, description="部门ID（含其子树）")
