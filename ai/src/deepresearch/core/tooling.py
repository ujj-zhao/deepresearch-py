"""检索工具：M1 为确定性 mock，由 researcher 节点程序化直调（非 LLM tool-calling）。

对照 Java 原版：ResearcherNode 的「程序化预搜索」（理解报告 3.2.3 节第 4 点）——
SearchInfoService.searchInfo() 拿回结构化结果后，一路拼 UserMessage 注入 LLM，
一路追加进 site_information。本模块只移植调用点与返回契约；
原版的多引擎工厂（tavily/aliyun/baidu/serpapi）、权重过滤（queryAndFilter）、
3 次重试间隔 500ms 均留到接真实引擎时在函数体内替换，签名不变。
"""

import zlib

from langchain_core.tools import tool

# 与消费方（researcher/reporter）约定死的结果键；接真引擎后追加 weight（信任权重 [-1.0, 1.0]）
RESULT_KEYS = ("title", "url", "content")


@tool
def web_search(query: str) -> list[dict]:
    """Search the web for a query and return structured results for research.

    每条结果含 title / url / content 三个键（接真实引擎后追加 weight：
    [-1.0, 1.0] 的信任权重，越接近 1 越可信）。无结果时返回空列表，不抛异常。

    M1 实现为确定性 mock：同一 query 恒返回同样结果，用于验证
    researcher 的预搜索注入与 site_information 记账链路。
    """
    # 真引擎在此处替换：网络请求 + 重试 3 次、间隔 500ms（对应原版 SearchInfoService L47-49）。
    # 用 crc32 而非内置 hash()：后者受 PYTHONHASHSEED 随机化，跨进程不稳定，会破坏确定性。
    seed = zlib.crc32(query.encode("utf-8"))
    return [
        {
            "title": f"[mock] 关于「{query}」的资料 {i}",
            "url": f"https://example.com/mock/{seed:08x}-{i}",
            "content": f"这是针对「{query}」的模拟搜索结果 {i}，用于验证预搜索注入链路。",
        }
        for i in range(1, 4)
    ]
