"""岗位模块的 Pydantic 请求/响应模型。"""

from datetime import datetime
from pydantic import Field
from ruoyi_fastapi.core.schemas import CamelModel


# ---- 响应模型 ----
class PostResp(CamelModel):
    """岗位信息响应（对应若依 SysPost 实体，列表/详情/下拉共用，扁平字段）。"""

    post_id: int = Field(description="岗位ID")
    post_code: str = Field(description="岗位编码")
    post_name: str = Field(description="岗位名称")
    post_sort: int = Field(description="显示顺序")
    status: str = Field(description="状态（0正常 1停用）")
    remark: str | None = Field(default=None, description="备注")
    create_by: str | None = Field(default=None, description="创建者")
    create_time: datetime | None = Field(default=None, description="创建时间")
    update_by: str | None = Field(default=None, description="更新者")
    update_time: datetime | None = Field(default=None, description="更新时间")


# ---- 请求模型 ----
class PostCreate(CamelModel):
    """新增岗位请求。"""

    post_code: str = Field(max_length=64, description="岗位编码")
    post_name: str = Field(max_length=50, description="岗位名称")
    post_sort: int = Field(ge=0, description="显示顺序")
    status: str = Field(default="0", pattern="^[01]$", description="状态（0正常 1停用）")
    remark: str | None = Field(default=None, max_length=500, description="备注")


class PostUpdate(CamelModel):
    """修改岗位请求。"""

    post_id: int = Field(ge=1, description="岗位ID")
    post_code: str = Field(max_length=64, description="岗位编码")
    post_name: str = Field(max_length=50, description="岗位名称")
    post_sort: int = Field(ge=0, description="显示顺序")
    status: str = Field(default="0", pattern="^[01]$", description="状态（0正常 1停用）")
    remark: str | None = Field(default=None, max_length=500, description="备注")


# ---- 分页查询 ----
class PostPageQuery(CamelModel):
    """岗位列表分页查询参数（对应若依 SysPostMapper.selectPostList 的 where 条件）。"""

    page_num: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=10, ge=1, le=100, description="每页条数")
    post_code: str | None = Field(default=None, description="岗位编码（精确匹配）")
    post_name: str | None = Field(default=None, description="岗位名称（模糊查询）")
    status: str | None = Field(default=None, pattern="^[01]$", description="状态")
