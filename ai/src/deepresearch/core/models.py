"""读取模型文件映射"""
import json
from pathlib import Path

from pydantic import BaseModel, Field, TypeAdapter

# models.json 在项目根 ai/ 下（与 prompts/ 同级）：core -> deepresearch -> src -> ai
MODEL_DIR = Path(__file__).resolve().parents[3]


class ModelSpec(BaseModel):
    """模型规格"""
    name: str = Field(description="模型名称")
    model_name: str = Field(description="模型 API 名称")
    temperature: float = Field(description="模型温度")

def load_model_registry() -> dict[str, ModelSpec]:
    """加载模型注册表。

    :return: 模型规格映射，键为模型名称，值为模型规格
    """
    data = json.loads((MODEL_DIR / "models.json").read_text(encoding="utf-8"))
    models = TypeAdapter(list[ModelSpec]).validate_python(data["models"])
    return {model.name: model for model in models}
