"""菜单模块接口契约。"""

from pydantic import Field

from ruoyi_fastapi.core.schemas import CamelModel


class MenuResp(CamelModel):
    """菜单实体（树构建的中间结构，对应若依 SysMenu VO）。"""

    menu_id: int = Field(description="菜单ID")
    menu_name: str = Field(description="菜单名称")
    parent_id: int = Field(default=0, description="父菜单ID")
    order_num: int = Field(default=0, description="显示顺序")
    path: str | None = Field(default="", description="路由地址")
    component: str | None = Field(default=None, description="组件路径")
    query: str | None = Field(default=None, description="路由参数")
    route_name: str | None = Field(default=None, description="路由名称")
    is_frame: int | None = Field(default=1, description="是否为外链（0是 1否）")
    is_cache: int | None = Field(default=0, description="是否缓存（0缓存 1不缓存）")
    menu_type: str | None = Field(default="", description="菜单类型（M目录 C菜单 F按钮）")
    visible: str | None = Field(default="0", description="显示状态（0显示 1隐藏）")
    status: str | None = Field(default="0", description="菜单状态（0正常 1停用）")
    perms: str | None = Field(default=None, description="权限标识")
    icon: str | None = Field(default=None, description="菜单图标")
    # 子节点列表放 Pydantic 模型而非 ORM（项目约定），自引用用前向引用
    children: list["MenuResp"] = Field(default_factory=list, description="子菜单")


class MetaResp(CamelModel):
    """路由元信息（对应若依 MetaVo）。"""

    title: str | None = Field(default=None, description="菜单名称")
    icon: str | None = Field(default=None, description="菜单图标")
    no_cache: bool = Field(default=False, description="是否不缓存页面")
    link: str | None = Field(default=None, description="内链地址")


class RouterResp(CamelModel):
    """前端路由配置（对应若依 RouterVo）。"""

    name: str = Field(default="", description="路由名称")
    path: str = Field(default="", description="路由地址")
    hidden: bool = Field(default=False, description="是否隐藏路由")
    redirect: str | None = Field(default=None, description="重定向地址")
    component: str | None = Field(default=None, description="组件地址")
    query: str | None = Field(default=None, description="路由参数")
    always_show: bool | None = Field(default=None, description="是否始终显示根节点")
    meta: MetaResp | None = Field(default=None, description="路由元信息")
    # 自引用树形结构：前向引用 + default_factory（禁止 =[]）
    children: list["RouterResp"] = Field(default_factory=list, description="子路由")


# ---- 菜单管理 ----
class MenuTreeSelectResp(CamelModel):
    """菜单下拉树节点（对应若依 TreeSelect，新增/修改页上级菜单、角色授权树复用）。"""

    id: int = Field(description="菜单ID")
    label: str = Field(description="菜单名称")
    children: list["MenuTreeSelectResp"] = Field(default_factory=list, description="子节点")


class RoleMenuTreeResp(CamelModel):
    """角色菜单树响应（对应若依 roleMenuTreeselect 的 AjaxResult 平铺结构）。

    对齐若依前端非标准壳：顶层平铺 checkedKeys 与 menus 两个键。
    """

    code: int = Field(default=200, description="状态码")
    msg: str = Field(default="操作成功", description="状态描述")
    checked_keys: list[int] = Field(default_factory=list, description="已勾选菜单ID")
    menus: list[MenuTreeSelectResp] = Field(default_factory=list, description="菜单树")


class MenuPageQuery(CamelModel):
    """菜单列表查询参数（菜单表不分页，按条件全量平铺返回）。"""

    menu_name: str | None = Field(default=None, description="菜单名称（模糊查询）")
    status: str | None = Field(default=None, pattern="^[01]$", description="菜单状态")


class MenuCreate(CamelModel):
    """新增菜单请求（对应若依 SysMenu 实体字段）。"""

    parent_id: int = Field(default=0, ge=0, description="父菜单ID（0 为顶级）")
    menu_type: str = Field(pattern="^[MCF]$", description="菜单类型（M目录 C菜单 F按钮）")
    menu_name: str = Field(max_length=50, description="菜单名称")
    order_num: int = Field(default=0, ge=0, description="显示顺序")
    path: str | None = Field(default=None, max_length=200, description="路由地址")
    component: str | None = Field(default=None, max_length=255, description="组件路径")
    query: str | None = Field(default=None, max_length=255, description="路由参数")
    route_name: str | None = Field(default=None, max_length=50, description="路由名称")
    is_frame: int = Field(default=1, ge=0, le=1, description="是否为外链（0是 1否）")
    is_cache: int = Field(default=0, ge=0, le=1, description="是否缓存（0缓存 1不缓存）")
    visible: str = Field(default="0", pattern="^[01]$", description="显示状态（0显示 1隐藏）")
    status: str = Field(default="0", pattern="^[01]$", description="菜单状态（0正常 1停用）")
    perms: str | None = Field(default=None, max_length=100, description="权限标识")
    icon: str | None = Field(default="#", max_length=100, description="菜单图标")
    remark: str | None = Field(default=None, max_length=500, description="备注")


class MenuUpdate(MenuCreate):
    """修改菜单请求（多主键）。"""

    menu_id: int = Field(ge=1, description="菜单ID")
