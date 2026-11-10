"""CLI 入口：uv run deepresearch "研究问题"（P1 里程碑 M1 使用）。

图组装（graph/build.py）完成前，本文件只保证参数解析与调用约定可用；
`build_graph` 采用延迟导入，避免骨架期 import 即崩。
"""

import argparse
from pathlib import Path

from deepresearch.core.config import settings


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="deepresearch",
        description="DeepResearch CLI：planner → researcher → reporter 最小闭环",
    )
    parser.add_argument("query", help="研究问题")
    parser.add_argument("--max-steps", type=int, default=settings.MAX_STEP_NUM,
                        help="单计划最大步骤数")
    parser.add_argument("--out", type=Path, default=None,
                        help="将报告写入指定 markdown 文件（缺省打印到终端）")
    args = parser.parse_args()

    from deepresearch.graph.build import build_graph  # 延迟导入：Session 4 落地

    graph = build_graph()
    result = graph.invoke(
        {"query": args.query, "max_step_num": args.max_steps, "messages": []},
        config={"recursion_limit": settings.MAX_ITERATIONS},
    )

    report = result.get("final_report", "")
    if not report:
        raise SystemExit("图执行完成但没有产出 final_report，检查节点实现")
    if args.out:
        args.out.write_text(report, encoding="utf-8")
        print(f"报告已写入 {args.out}")
    else:
        print(report)


if __name__ == "__main__":
    main()
