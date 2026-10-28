"""通知公告契约模型（对应若依 SysNotice + 项目扩展的已读标记）。"""

from datetime import datetime

from pydantic import Field

from ruoyi_fastapi.core.schemas import CamelModel


class NoticeResp(CamelModel):
    """通知公告响应（对应 sys_notice 表；content 由 longblob 解码为文本）。"""

    notice_id: int = Field(description="公告ID")
    notice_title: str = Field(description="公告标题")
    notice_type: str = Field(description="公告类型（1通知 2公告）")
    notice_content: str | None = Field(default=None, description="公告内容（富文本）")
    status: str | None = Field(default=None, description="公告状态（0正常 1关闭）")
    create_by: str | None = Field(default=None, description="创建者")
    create_time: datetime | None = Field(default=None, description="创建时间")
    remark: str | None = Field(default=None, description="备注")


class NoticeDetailResp(NoticeResp):
    """公告详情响应：扩展当前用户已读标记（项目自有功能）。"""

    is_read: bool = Field(default=False, description="当前用户是否已读")


class NoticePageQuery(CamelModel):
    """公告列表查询参数（对应若依 SysNotice 查询条件 + 分页）。"""

    notice_title: str | None = Field(default=None, max_length=50, description="公告标题（模糊）")
    notice_type: str | None = Field(default=None, max_length=1, description="公告类型（1通知 2公告）")
    create_by: str | None = Field(default=None, max_length=50, description="创建者（模糊）")
    page_num: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=10, ge=1, le=100, description="每页条数")


class NoticeCreate(CamelModel):
    """新增公告请求体（对应 insertNotice）。"""

    notice_title: str = Field(min_length=1, max_length=50, description="公告标题")
    notice_type: str = Field(pattern="^[12]$", description="公告类型（1通知 2公告）")
    notice_content: str | None = Field(default=None, description="公告内容（富文本）")
    status: str = Field(default="0", pattern="^[01]$", description="公告状态（0正常 1关闭）")
    remark: str | None = Field(default=None, max_length=255, description="备注")


class NoticeUpdate(NoticeCreate):
    """修改公告请求体：多主键（对应 updateNotice）。"""

    notice_id: int = Field(description="公告ID")
