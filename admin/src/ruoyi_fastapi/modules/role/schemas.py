"""角色模块接口契约（对应若依 SysRole 实体与 SysRoleController 契约）。"""

from datetime import datetime

from pydantic import Field

from ruoyi_fastapi.core.schemas import CamelModel


# ---- 响应模型 ----
class RoleResp(CamelModel):
    """角色信息响应（列表/详情/下拉共用，对应若依 SysRole VO）。

    menu_check_strictly / dept_check_strictly 在 DB 为 tinyint(1)，
    声明为 bool 由 Pydantic 自动强转，对齐前端父子联动开关的布尔语义。
    """

    role_id: int = Field(description="角色ID")
    role_name: str = Field(description="角色名称")
    role_key: str = Field(description="角色权限字符串")
    role_sort: int = Field(description="显示顺序")
    data_scope: str | None = Field(default="1", description="数据范围（1全部 2自定 3本部门 4本部门及以下 5仅本人）")
    menu_check_strictly: bool | None = Field(default=True, description="菜单树选择项是否关联显示")
    dept_check_strictly: bool | None = Field(default=True, description="部门树选择项是否关联显示")
    status: str = Field(description="角色状态（0正常 1停用）")
    remark: str | None = Field(default=None, description="备注")
    create_by: str | None = Field(default=None, description="创建者")
    create_time: datetime | None = Field(default=None, description="创建时间")
    update_by: str | None = Field(default=None, description="更新者")
    update_time: datetime | None = Field(default=None, description="更新时间")


# ---- 请求模型 ----
class RoleCreate(CamelModel):
    """新增角色请求（含授权菜单，对应若依 SysRole.menuIds）。"""

    role_name: str = Field(max_length=30, description="角色名称")
    role_key: str = Field(max_length=100, description="角色权限字符串")
    role_sort: int = Field(ge=0, description="显示顺序")
    status: str = Field(default="0", pattern="^[01]$", description="角色状态（0正常 1停用）")
    menu_ids: list[int] = Field(default_factory=list, description="关联菜单ID")
    menu_check_strictly: bool = Field(default=True, description="菜单树选择项是否关联显示")
    dept_check_strictly: bool = Field(default=True, description="部门树选择项是否关联显示")
    remark: str | None = Field(default=None, max_length=500, description="备注")


class RoleUpdate(RoleCreate):
    """修改角色请求（多主键，修改后同步重建角色-菜单关联）。"""

    role_id: int = Field(ge=1, description="角色ID")


class RoleChangeStatusReq(CamelModel):
    """角色启停请求（对应若依 changeStatus 的 JSON 体）。"""

    role_id: int = Field(ge=1, description="角色ID")
    status: str = Field(pattern="^[01]$", description="角色状态（0正常 1停用）")


class RoleDataScopeReq(CamelModel):
    """数据权限修改请求（对应若依 dataScope 接口的 JSON 体）。"""

    role_id: int = Field(ge=1, description="角色ID")
    data_scope: str = Field(pattern="^[1-5]$", description="数据范围（1全部 2自定 3本部门 4本部门及以下 5仅本人）")
    dept_ids: list[int] = Field(default_factory=list, description="自定数据权限绑定的部门ID")


# ---- 分页查询 ----
class RolePageQuery(CamelModel):
    """角色列表分页查询参数（对应若依 selectRoleList 的 where 条件）。"""

    page_num: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=10, ge=1, le=100, description="每页条数")
    role_name: str | None = Field(default=None, description="角色名称（模糊查询）")
    role_key: str | None = Field(default=None, description="角色权限字符串（模糊查询）")
    status: str | None = Field(default=None, pattern="^[01]$", description="角色状态")


# ---- 角色关联用户（authUser 系列） ----
class RoleAuthUserPageQuery(CamelModel):
    """已分配/未分配用户分页查询参数。"""

    page_num: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=10, ge=1, le=100, description="每页条数")
    role_id: int = Field(description="角色ID")
    user_name: str | None = Field(default=None, description="用户账号（模糊查询）")
    phonenumber: str | None = Field(default=None, description="手机号（模糊查询）")
