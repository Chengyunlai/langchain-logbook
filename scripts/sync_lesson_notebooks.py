#!/usr/bin/env python3
"""Generate executable lesson notebooks from Markdown ``sync=...`` code fences."""

from __future__ import annotations

import argparse
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import io
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import textwrap
from unittest.mock import patch

import nbformat


SYNC_FENCE = re.compile(r"^```(?:python|py)\s+sync=([a-zA-Z0-9_.:-]+)\s*$")


def stable_cell_id(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:16]


def extract_synced_cells(markdown: str) -> list[tuple[str, str]]:
    lines = markdown.splitlines()
    cells: list[tuple[str, str]] = []
    seen: set[str] = set()
    index = 0
    while index < len(lines):
        match = SYNC_FENCE.match(lines[index])
        if not match:
            index += 1
            continue
        sync_id = match.group(1)
        if sync_id in seen:
            raise ValueError(f"重复的 sync marker: {sync_id}")
        seen.add(sync_id)
        index += 1
        code: list[str] = []
        while index < len(lines) and lines[index].strip() != "```":
            code.append(lines[index])
            index += 1
        if index >= len(lines):
            raise ValueError(f"未闭合的 sync marker: {sync_id}")
        cells.append((sync_id, textwrap.dedent("\n".join(code)).rstrip() + "\n"))
        index += 1
    return cells


def build_notebook(markdown_path: Path) -> nbformat.NotebookNode:
    synced = extract_synced_cells(markdown_path.read_text(encoding="utf-8"))
    if not synced:
        raise ValueError(f"{markdown_path} 没有 sync 代码块")
    title = markdown_path.read_text(encoding="utf-8").splitlines()[0].removeprefix("# ")
    success_cells: list[tuple[str, str]] = []
    event_cells: list[tuple[str, str]] = []
    failure_cells: list[tuple[str, str]] = []
    for item in synced:
        sync_id = item[0]
        if any(key in sync_id for key in ("failure", "boundary", "error")):
            failure_cells.append(item)
        elif any(key in sync_id for key in ("stream", "event")):
            event_cells.append(item)
        else:
            success_cells.append(item)

    cells = [
        nbformat.v4.new_markdown_cell(
            f"# {title}（离线工程实验）\n\n"
            "**目标**：执行本章稳定公共契约并观察失败护栏。  \n"
            "**环境与预计用时**：Python 3.12、offline profile，约 15–25 分钟。  \n"
            "本 Notebook 由同名 Markdown 中带 `sync` 标识的实验代码生成；"
            "可复用业务逻辑始终从 `mini_deerflow` package 导入。",
            id=stable_cell_id(f"{markdown_path.name}:intro"),
        ),
        nbformat.v4.new_markdown_cell(
            "## 1. offline profile 初始化\n\n"
            "显式选择离线模型档位，基础实验不得读取供应商 Key。",
            id=stable_cell_id(f"{markdown_path.name}:offline-heading"),
        ),
        nbformat.v4.new_code_cell(
            "from mini_deerflow.config import ModelProfile, ModelSettings\n\n"
            "lesson_settings = ModelSettings(profile=ModelProfile.OFFLINE)\n"
            "assert lesson_settings.profile is ModelProfile.OFFLINE\n",
            id=stable_cell_id(f"{markdown_path.name}:offline-code"),
        ),
        nbformat.v4.new_markdown_cell(
            "## 2. 前置能力探针\n\n"
            "验证当前 kernel 使用课程锁定的主版本，并能导入 Mini DeerFlow。",
            id=stable_cell_id(f"{markdown_path.name}:probe-heading"),
        ),
        nbformat.v4.new_code_cell(
            "from importlib.metadata import version\n"
            "import mini_deerflow\n\n"
            "assert version('langchain').startswith('1.3.')\n"
            "assert version('langgraph').startswith('1.2.')\n"
            "assert mini_deerflow.__file__\n",
            id=stable_cell_id(f"{markdown_path.name}:probe-code"),
        ),
        nbformat.v4.new_markdown_cell(
            "## 3. 最小成功实验\n\n"
            "以下单元来自 Markdown 的稳定 sync marker。",
            id=stable_cell_id(f"{markdown_path.name}:success-heading"),
        ),
    ]

    def append_experiments(experiments: list[tuple[str, str]]) -> None:
        for sync_id, code in experiments:
            cells.append(
                nbformat.v4.new_markdown_cell(
                    f"### 实验 `{sync_id}`",
                    id=stable_cell_id(f"{markdown_path.name}:{sync_id}:heading"),
                )
            )
            cells.append(
                nbformat.v4.new_code_cell(
                    code,
                    metadata={"langchain_logbook_sync": sync_id},
                    id=stable_cell_id(f"{markdown_path.name}:{sync_id}:code"),
                )
            )

    append_experiments(success_cells)
    cells.append(
        nbformat.v4.new_markdown_cell(
            "## 4. 状态/事件观察\n\n"
            "观察消息、结构化对象、检索命中或 v2 event；不要只看最终自然语言。",
            id=stable_cell_id(f"{markdown_path.name}:event-heading"),
        )
    )
    append_experiments(event_cells)
    cells.append(
        nbformat.v4.new_markdown_cell(
            "## 5. 失败实验\n\n"
            "失败必须被捕获并断言，证明护栏真的阻止了错误路径。",
            id=stable_cell_id(f"{markdown_path.name}:failure-heading"),
        )
    )
    append_experiments(failure_cells)
    cells.extend(
        [
            nbformat.v4.new_markdown_cell(
                "## 6. Mini DeerFlow 工程调用\n\n"
                "以上实验只从 `mini_deerflow` 导入公共接口；Notebook 不复制 Agent、Tool 或 Schema 实现。",
                id=stable_cell_id(f"{markdown_path.name}:project-heading"),
            ),
            nbformat.v4.new_markdown_cell(
                "## 7. 分层练习\n\n"
                "完成同名 Markdown 的练习 A（单点修改）、B（边界判断）、C（项目扩展）和延迟回忆题。"
                "先自行作答，再运行对应 pytest 获取即时反馈。",
                id=stable_cell_id(f"{markdown_path.name}:exercise-heading"),
            ),
            nbformat.v4.new_markdown_cell(
                "## 8. 自动验收摘要\n\n"
                "在项目根目录运行 `make test`。本 Notebook 的所有代码单元必须有执行计数、"
                "不得保存 error output，教程验证结果不得出现本章 drift。",
                id=stable_cell_id(f"{markdown_path.name}:acceptance-heading"),
            ),
            nbformat.v4.new_markdown_cell(
                "## 9. 清理临时资源\n\n"
                "当前实验使用内存对象与 `TemporaryDirectory`，退出上下文后自动清理；"
                "不要把 API Key、向量库或临时产物写回仓库。",
                id=stable_cell_id(f"{markdown_path.name}:cleanup-heading"),
            ),
        ]
    )
    notebook = nbformat.v4.new_notebook(cells=cells)
    notebook.metadata["kernelspec"] = {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3",
    }
    notebook.metadata["language_info"] = {"name": "python", "version": "3.12"}
    notebook.metadata["langchain_logbook"] = {"source": markdown_path.name, "generated": True}
    return notebook


def execute_in_fresh_namespace(notebook: nbformat.NotebookNode, source_name: str) -> None:
    """顺序执行代码单元，并阻断常见网络与子进程入口。

    这是防止基础实验意外联网的 correctness guard，不是对抗恶意代码的安全
    Sandbox；真正执行不可信代码必须使用后续课程的进程/容器隔离。
    """

    def deny_external_io(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise RuntimeError("课程 Notebook 基础实验禁止网络或子进程访问")

    namespace: dict[str, object] = {"__name__": "__main__"}
    execution_count = 0
    for cell in notebook.cells:
        if cell.cell_type != "code":
            continue
        execution_count += 1
        output = io.StringIO()
        with (
            redirect_stdout(output),
            redirect_stderr(output),
            patch.object(socket, "create_connection", deny_external_io),
            patch.object(socket.socket, "connect", deny_external_io),
            patch.object(socket.socket, "connect_ex", deny_external_io),
            patch.object(subprocess, "Popen", deny_external_io),
            patch.object(os, "system", deny_external_io),
        ):
            exec(compile(cell.source, f"{source_name}:{execution_count}", "exec"), namespace)
        cell.execution_count = execution_count
        rendered = output.getvalue()
        cell.outputs = (
            [nbformat.v4.new_output("stream", name="stdout", text=rendered)] if rendered else []
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("markdown", nargs="+", type=Path)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--backup-dir", type=Path)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    for markdown_path in args.markdown:
        resolved_markdown = markdown_path.resolve()
        notebook_path = resolved_markdown.with_suffix(".ipynb")
        if args.backup_dir and notebook_path.exists():
            backup_dir = args.backup_dir.resolve()
            backup_dir.mkdir(parents=True, exist_ok=True)
            backup_path = backup_dir / notebook_path.name
            if not backup_path.exists():
                shutil.copy2(notebook_path, backup_path)

        notebook = build_notebook(resolved_markdown)
        if args.execute:
            execute_in_fresh_namespace(notebook, resolved_markdown.name)
        nbformat.write(notebook, notebook_path)
        print(f"Synced {notebook_path.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
