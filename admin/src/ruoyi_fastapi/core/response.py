"""统一响应模型。

对应若依 Java 版：
- R[T] -> AjaxResult（code/msg/data）
- PageResult[T] -> TableDataInfo（code/msg/rows/total）
"""

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class R(BaseModel, Generic[T]):
    """统一响应模型。"""

    code: int = Field(default=200, description="状态码")
    msg: str = Field(default="操作成功", description="状态描述")
    data: T | None = Field(default=None, description="业务数据")

    @classmethod
    def ok(cls, data: T | None = None, msg: str = "操作成功") -> "R[T]":
        """构造成功响应。"""
        return cls(code=200, msg=msg, data=data)

    @classmethod
    def fail(cls, msg: str = "操作失败", code: int = 500) -> "R[T]":
        """构造失败响应。"""
        return cls(code=code, msg=msg, data=None)


class PageResult(BaseModel, Generic[T]):
    """分页查询统一响应。"""

    code: int = Field(default=200, description="状态码")
    msg: str = Field(default="查询成功", description="状态描述")
    rows: list[T] = Field(default_factory=list, description="列表数据")
    total: int = Field(default=0, description="总记录数")

    @classmethod
    def of(cls, rows: list[T], total: int) -> "PageResult[T]":
        """从查询结果构造分页响应。"""
        return cls(rows=rows, total=total)
