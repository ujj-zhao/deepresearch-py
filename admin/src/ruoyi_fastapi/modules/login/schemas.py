from pydantic import Field

from ruoyi_fastapi.core.schemas import CamelModel
from ..user.schemas import UserDTO

class RoleDTO ( CamelModel ):
    role_id: int 
    role_key: str 
    data_scope: str | None

class LoginUser(CamelModel):
    """登录用户会话信息（对应若依 LoginUser，登录后存入 Redis login_tokens）。"""

    user_id: int | None = Field(default=None, description="用户ID")
    dept_id: int | None = Field(default=None, description="部门ID")
    token: str | None = Field(default=None, description="用户唯一标识")
    login_time: int | None = Field(default=None, description="登录时间（毫秒时间戳）")
    expire_time: int | None = Field(default=None, description="过期时间（毫秒时间戳）")
    ipaddr: str | None = Field(default=None, description="登录IP地址")
    login_location: str | None = Field(default=None, description="登录地点")
    browser: str | None = Field(default=None, description="浏览器类型")
    os: str | None = Field(default=None, description="操作系统")
    permissions: set[str] | None = Field(default=None, description="权限列表")
    # UserDTO
    user: UserDTO | None = Field(default=None, description="用户信息")
    # RoleDTO
    roles: list[RoleDTO] | None = Field(default=None, description="角色权限信息列表")


class LoginRequest(CamelModel):
    """用户登录请求。"""

    username: str = Field(description="用户名")
    password: str = Field(description="密码")
    code: str = Field(description="验证码")
    uuid: str = Field(description="验证码唯一标识")


class LoginResponse(CamelModel):
    """登录响应：返回 token。"""

    token: str = Field(description="登录令牌")


class GetInfoResp(CamelModel):
    """getInfo 响应（对应若依 AjaxResult 中的 user/roles/permissions 三键）。"""

    user: UserDTO = Field(description="当前用户信息")
    roles: list[str] = Field(default_factory=list, description="角色权限字符串列表")
    permissions: set[str] = Field(default_factory=set, description="菜单权限标识集合")
