"""部门模块接口契约（对齐若依前端字段命名，对外 DTO 统一继承 CamelModel）。"""

from pydantic import Field

from ruoyi_fastapi.core.schemas import CamelModel


class DeptAddReq(CamelModel):
    """新增部门请求体。"""

    parent_id: int = 0
    dept_name: str
    order_num: int = 0
    leader: str | None = None
    phone: str | None = None
    email: str | None = None
    status: str = "0"


class DeptUpdateReq(DeptAddReq):
    """修改部门请求体（多主键）。"""

    dept_id: int


class DeptResp(CamelModel):
    """部门信息响应。"""

    dept_id: int
    parent_id: int
    ancestors: str
    dept_name: str
    order_num: int
    leader: str | None = None
    phone: str | None = None
    email: str | None = None
    status: str
    parent_name: str | None = None  # 详情接口按父链补全


class TreeSelectResp(CamelModel):
    """下拉树节点（对应若依 TreeSelect，children 按项目规范放 Pydantic 侧）。"""

    id: int
    label: str
    children: list["TreeSelectResp"] = Field(default_factory=list)


class RoleDeptTreeResp(CamelModel):
    """角色部门树响应。

    对齐若依前端非标准壳：不套 R，而是顶层平铺 checkedKeys 与 depts 两个键。
    """

    checked_keys: list[int] = Field(default_factory=list)  # alias 自动转 checkedKeys
    depts: list[TreeSelectResp] = Field(default_factory=list)
