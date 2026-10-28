from pydantic import Field, BaseModel
from ruoyi_fastapi.core.schemas import CamelModel

"""系统配置查询请求。"""
class BaseConfig(CamelModel):
    
    config_id: int | None = Field(default=None, description="配置 ID")
    config_name: str | None = Field(default=None, description="配置名称")
    config_key: str | None = Field(default=None, description="配置键")
    config_value: str | None = Field(default=None, description="配置值")
    config_type: str | None = Field(default=None, description="配置类型")

class ConfigPage(BaseConfig):
    page_num: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=10, ge=10, le=100, description="每页数量")