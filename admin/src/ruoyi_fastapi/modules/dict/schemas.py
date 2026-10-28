"""字典模块契约模型（对应若依 SysDictType / SysDictData 的请求与响应）。"""

from datetime import datetime

from pydantic import Field

from ruoyi_fastapi.core.schemas import CamelModel


# ==================== 字典类型 ====================

class DictTypeResp(CamelModel):
    """字典类型响应（对应 sys_dict_type 表 + 列表页展示字段）。"""

    dict_id: int = Field(description="字典主键")
    dict_name: str = Field(description="字典名称")
    dict_type: str = Field(description="字典类型")
    status: str | None = Field(default=None, description="状态（0正常 1停用）")
    create_time: datetime | None = Field(default=None, description="创建时间")
    remark: str | None = Field(default=None, description="备注")


class DictTypePageQuery(CamelModel):
    """字典类型列表查询参数（对应若依 SysDictType 查询条件 + 分页）。"""

    dict_name: str | None = Field(default=None, max_length=100, description="字典名称（模糊）")
    dict_type: str | None = Field(default=None, max_length=100, description="字典类型（模糊）")
    status: str | None = Field(default=None, max_length=1, description="状态（0正常 1停用）")
    page_num: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=10, ge=1, le=100, description="每页条数")


class DictTypeCreate(CamelModel):
    """新增字典类型请求体（对应 insertDictType）。"""

    dict_name: str = Field(min_length=1, max_length=100, description="字典名称")
    dict_type: str = Field(min_length=1, max_length=100, description="字典类型")
    status: str = Field(default="0", pattern="^[01]$", description="状态（0正常 1停用）")
    remark: str | None = Field(default=None, max_length=500, description="备注")


class DictTypeUpdate(DictTypeCreate):
    """修改字典类型请求体：多主键（对应 updateDictType）。"""

    dict_id: int = Field(description="字典主键")


# ==================== 字典数据 ====================

class DictDataResp(CamelModel):
    """字典数据响应（对应 sys_dict_data 表）。"""

    dict_code: int = Field(description="字典编码")
    dict_sort: int | None = Field(default=0, description="字典排序")
    dict_label: str = Field(description="字典标签")
    dict_value: str = Field(description="字典键值")
    dict_type: str = Field(description="字典类型")
    css_class: str | None = Field(default=None, description="样式属性")
    list_class: str | None = Field(default=None, description="表格回显样式")
    is_default: str | None = Field(default="N", description="是否默认（Y是 N否）")
    status: str | None = Field(default=None, description="状态（0正常 1停用）")
    create_time: datetime | None = Field(default=None, description="创建时间")
    remark: str | None = Field(default=None, description="备注")


class DictDataPageQuery(CamelModel):
    """字典数据列表查询参数（对应若依 SysDictData 查询条件 + 分页）。"""

    dict_type: str | None = Field(default=None, max_length=100, description="字典类型（等值）")
    dict_label: str | None = Field(default=None, max_length=100, description="字典标签（模糊）")
    status: str | None = Field(default=None, max_length=1, description="状态（0正常 1停用）")
    page_num: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=10, ge=1, le=100, description="每页条数")


class DictDataCreate(CamelModel):
    """新增字典数据请求体（对应 insertDictData）。"""

    dict_label: str = Field(min_length=1, max_length=100, description="字典标签")
    dict_value: str = Field(min_length=1, max_length=100, description="字典键值")
    dict_type: str = Field(min_length=1, max_length=100, description="字典类型")
    dict_sort: int = Field(default=0, description="字典排序")
    css_class: str | None = Field(default=None, max_length=100, description="样式属性")
    list_class: str | None = Field(default=None, max_length=100, description="表格回显样式")
    is_default: str = Field(default="N", pattern="^[YN]$", description="是否默认（Y是 N否）")
    status: str = Field(default="0", pattern="^[01]$", description="状态（0正常 1停用）")
    remark: str | None = Field(default=None, max_length=500, description="备注")


class DictDataUpdate(DictDataCreate):
    """修改字典数据请求体：多主键（对应 updateDictData）。"""

    dict_code: int = Field(description="字典编码")
