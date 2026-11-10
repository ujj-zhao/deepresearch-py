"""web_search mock 的纯函数测试（方案第 6 节：不依赖 LLM，直接断言契约）。"""

from deepresearch.core.tooling import RESULT_KEYS, web_search


def test_returns_structured_results():
    """契约一：返回 list[dict]，每条含约定键且值非空。"""
    results = web_search.invoke({"query": "LangGraph 状态机"})
    assert isinstance(results, list) and len(results) == 3
    for r in results:
        assert set(RESULT_KEYS) <= set(r)
        assert all(r[k] for k in RESULT_KEYS)


def test_deterministic_for_same_query():
    """契约二：确定性——同一 query 结果逐字段相等（跨进程稳定，靠 crc32 而非 hash()）。"""
    assert web_search.invoke({"query": "同一查询"}) == web_search.invoke({"query": "同一查询"})


def test_query_echoed_for_pipeline_probe():
    """契约三：query 回显进内容，端到端跑 CLI 时能肉眼确认检索链路被走到。"""
    results = web_search.invoke({"query": "量子计算"})
    assert any("量子计算" in r["content"] for r in results)
