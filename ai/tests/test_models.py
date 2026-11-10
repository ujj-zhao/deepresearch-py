"""models.json 注册表测试：真读文件，不 mock。

为什么必须有：M1 真模型验收时踩过 models.json 路径 bug（parents 数错层级），
而当时 28 个测试全绿——所有节点单测都 mock 了 get_model，**接缝之后的代码
不被任何单测覆盖**。本文件直接调 load_model_registry()，把路径与节点名契约锁死。
"""

from deepresearch.core.models import MODEL_DIR, load_model_registry


def test_models_json_exists_at_expected_path():
    """锁 MODEL_DIR 的 parents 层级：改目录结构导致路径漂移，这里立刻红。"""
    assert (MODEL_DIR / "models.json").is_file()


def test_registry_covers_node_names():
    """节点名契约：节点代码里 get_model("<名字>") 用到的名字必须在注册表里。"""
    registry = load_model_registry()
    assert {"planner", "researcher", "reporter"} <= set(registry)
    for spec in registry.values():
        assert spec.model_name  # API 模型名非空
        assert isinstance(spec.temperature, float)
