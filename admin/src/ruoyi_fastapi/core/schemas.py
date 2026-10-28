"""核心 Pydantic 基类。"""

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """所有对外 DTO 的基类:snake_case 字段 → camelCase JSON。"""

    model_config = ConfigDict(
        from_attributes=True,        # 允许从 ORM 对象直接转换
        alias_generator=to_camel,    # 自动生成 camelCase 别名(用于 JSON 输出)
        populate_by_name=True,       # 既接受 alias 也接受原字段名
    )
