"""CLI 入口：uv run deepresearch "研究问题"（P2 里程碑 M2：计划人工审批）。

M2 相对 M1 的三件事：
- checkpointer 接线：interrupt 的暂停快照存进 SqliteSaver（settings.CHECKPOINT_DB）；
- 驱动循环：一次 invoke 返回 ≠ 跑完，可能停在审批点，要"问人 → resume"循环到真终点；
- --resume THREAD_ID：跨进程续跑被终止的审批（持久化检查点的意义所在）。

`build_graph` 延迟导入：--help / 参数解析不依赖图组装链路。
"""

import argparse
from pathlib import Path
from uuid import uuid4
from deepresearch.core.config import settings
from langgraph.types import Command

from deepresearch.core.checkpoint import get_checkpoint_saver
from deepresearch.graph.build import build_graph


def ask_human(plan_view: dict) -> dict | None:
    """渲染待审批计划，收集人的决定，返回 resume 值；选 q 终止返回 None。

    resume 值契约（与 nodes/human_feedback.py 的 decision 解析对齐）：
        {"accept": bool, "feedback": str}
    驳回必须带非空意见：节点侧把"空意见"当通过，这里不拦，人的驳回会被
    静默变成通过——最难查的一类 bug，收口放在输入端。
    """
    print(f"\n研究计划：{plan_view['title']}")
    if plan_view.get("thought"):
        print(f"思路：{plan_view['thought']}")
    for i, step in enumerate(plan_view["steps"], 1):
        search = "需联网" if step["need_web_search"] else "免搜"
        print(f"{i}. [{step['step_type']}|{search}] {step['title']}：{step['description']}")

    while True:
        choice = input("\n[y]通过 [n]驳回 [q]终止: ").strip().lower()
        if choice == "y":
            return {"accept": True, "feedback": ""}
        if choice == "n":
            feedback = input("修改意见: ").strip()
            if feedback:
                return {"accept": False, "feedback": feedback}
            print("驳回必须附意见。")
        elif choice == "q":
            return None


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="deepresearch",
        description="DeepResearch CLI：planner →（人工审批）→ researcher → reporter",
    )
    parser.add_argument("query", nargs="?", default=None, help="研究问题（与 --resume 二选一）")
    parser.add_argument("--max-steps", type=int, default=settings.MAX_STEP_NUM,
                        help="单计划最大步骤数")
    parser.add_argument("--out", type=Path, default=None,
                        help="将报告写入指定 markdown 文件（缺省打印到终端）")
    parser.add_argument("--review", action="store_true",
                        help="计划生成后暂停等待人工审批（缺省自动通过，保持 M1 行为）")
    parser.add_argument("--resume", metavar="THREAD_ID", default=None,
                        help="续跑指定 thread 中被终止的审批")
    args = parser.parse_args()

    # query 与 --resume 恰好给一个：都给/都不给都是用法错误
    if bool(args.query) == bool(args.resume):
        raise SystemExit(
            '用法：deepresearch "研究问题" [--review]，或 deepresearch --resume THREAD_ID'
        )


    graph = build_graph(checkpointer=get_checkpoint_saver(settings.CHECKPOINT_DB))
    thread_id = args.resume or uuid4().hex
    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": settings.MAX_ITERATIONS,
    }
    print(f"thread_id: {thread_id}")

    step_input: dict | Command = (
        {
            "query": args.query,
            "max_step_num": args.max_steps,
            "auto_accept_plan": not args.review,
            "messages": [],
        }
        if args.query
        else None  # None 仅作哨兵：--resume 首轮不 invoke，从检查点读暂停 payload
    )
    result: dict = {}

    while True:
        if step_input is None:
            # --resume 入口：payload 从检查点读（新进程里没有 invoke 返回值可查）
            snapshot = graph.get_state(config)
            interrupts = snapshot.tasks[0].interrupts if snapshot.next else []
            if not interrupts:
                raise SystemExit(f"thread {thread_id} 没有可恢复的暂停任务")
            plan_view = interrupts[0].value
        else:
            result = graph.invoke(step_input, config)
            if "__interrupt__" not in result:
                break  # 没暂停 = 真跑完，result 即最终状态
            plan_view = result["__interrupt__"][0].value

        decision = ask_human(plan_view)
        if decision is None:
            # 终止 = 什么都不做：检查点原样留着，--resume 才能续
            print(f"已终止。续跑：uv run deepresearch --resume {thread_id}")
            return
        step_input = Command(resume=decision)

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
