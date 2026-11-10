"""检查点工厂：checkpointer 选型的唯一出口（P2 起步 → P4 换 Postgres 只改本文件）。

interrupt() 必须配 checkpointer（架构文档 §14.4）：暂停时的黑板快照要有地方存，
恢复才有的读。调用方约定：
- path 为空 → MemorySaver：进程内字典，测试用，进程退出即丢；
- path 给定 → SqliteSaver：单文件持久化，CLI 跨进程 --resume 靠它。
"""

import sqlite3

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver


def get_checkpoint_saver(path: str | None = None) -> BaseCheckpointSaver:
    """根据配置返回检查点保存器。

    SqliteSaver 首次读写自动建表，无需预迁移；不用 from_conn_string
    （那是 context manager，退出即关连接，CLI 需要活到进程结束的对象）。
    """
    if not path:
        return MemorySaver()

    conn = sqlite3.connect(path, check_same_thread=False)
    return SqliteSaver(conn)
