"""``python -m mini_deerflow`` 的离线 smoke test 入口。"""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence

from mini_deerflow.app import build_application


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="运行 Mini DeerFlow 的确定性离线最小对话"
    )
    parser.add_argument(
        "--message",
        default="create_agent 和 LangGraph 是什么关系？",
        help="传给离线 Lead Agent 的用户消息",
    )
    args = parser.parse_args(argv)

    application = build_application()
    state = application.invoke(args.message)
    print(
        json.dumps(
            {
                "profile": application.settings.model.profile.value,
                "tools": application.tool_names,
                "final_text": str(state["messages"][-1].content),
                "middleware_events": len(state.get("middleware_trace", [])),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
