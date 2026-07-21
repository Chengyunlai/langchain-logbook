#!/usr/bin/env python3
"""Generate executable lesson notebooks from Markdown ``sync=...`` code fences."""

from __future__ import annotations

import argparse
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
import hashlib
import io
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import textwrap
from types import ModuleType
from unittest.mock import patch

import nbformat


SYNC_FENCE = re.compile(r"^```(?:python|py)\s+sync=([a-zA-Z0-9_.:-]+)\s*$")
OUTPUT_FENCE = re.compile(r"^```text\s+output=([a-z0-9-]+)\s*$")
LESSON_LAB_START = re.compile(
    r"^<!-- lesson-lab:id=(?P<id>[a-z0-9-]+) "
    r"layer=(?P<layer>concept|migration) "
    r"kind=(?P<kind>baseline|failure|repair|contrast|exercise) "
    r"concept=(?P<concept>[a-z0-9-]+)"
    r"(?: pair=(?P<pair>[a-z0-9-]+))? -->$"
)
LESSON_LAB_END = "<!-- /lesson-lab -->"
LESSON_CONTRACT_V2 = "<!-- lesson-contract:v2 -->"


@dataclass(frozen=True, slots=True)
class LessonLab:
    """一个可同步到 Notebook 的完整教学实验。"""

    lab_id: str
    layer: str
    kind: str
    concept: str
    pair: str | None
    title: str
    prediction: str
    code: str
    expected_output: str
    explanation: str
    modification: str
    line: int


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


def _fenced_block(
    lines: list[str], pattern: re.Pattern[str], *, lab_id: str, label: str
) -> tuple[str, str]:
    matches: list[tuple[int, re.Match[str]]] = []
    for index, line in enumerate(lines):
        if match := pattern.match(line):
            matches.append((index, match))
    if len(matches) != 1:
        raise ValueError(f"lesson lab {lab_id} 必须恰好包含一个 {label} fence")
    start, match = matches[0]
    block: list[str] = []
    index = start + 1
    while index < len(lines) and lines[index].strip() != "```":
        block.append(lines[index])
        index += 1
    if index >= len(lines):
        raise ValueError(f"lesson lab {lab_id} 的 {label} fence 未闭合")
    value = textwrap.dedent("\n".join(block)).rstrip()
    return match.group(1), f"{value}\n" if value else ""


def _labeled_prose(lines: list[str], label: str) -> str:
    prefix = f"**{label}**："
    for start, line in enumerate(lines):
        if not line.startswith(prefix):
            continue
        prose = [line.removeprefix(prefix).strip()]
        for following in lines[start + 1 :]:
            if (
                following.startswith("**")
                or following.startswith("```")
                or following.startswith("### ")
            ):
                break
            prose.append(following.strip())
        return "\n".join(item for item in prose if item).strip()
    return ""


def extract_lesson_labs(markdown: str) -> list[LessonLab]:
    """按 Markdown 原始顺序解析 v2 lesson lab。"""

    lines = markdown.splitlines()
    labs: list[LessonLab] = []
    seen: set[str] = set()
    index = 0
    while index < len(lines):
        match = LESSON_LAB_START.match(lines[index])
        if not match:
            if lines[index] == LESSON_LAB_END:
                raise ValueError(f"第 {index + 1} 行存在没有开始 marker 的 lesson lab")
            index += 1
            continue
        lab_id = match.group("id")
        if lab_id in seen:
            raise ValueError(f"重复的 lesson lab id: {lab_id}")
        seen.add(lab_id)
        line = index + 1
        body: list[str] = []
        index += 1
        while index < len(lines) and lines[index] != LESSON_LAB_END:
            if LESSON_LAB_START.match(lines[index]):
                raise ValueError(f"lesson lab {lab_id} 内不允许嵌套 marker")
            body.append(lines[index])
            index += 1
        if index >= len(lines):
            raise ValueError(f"lesson lab {lab_id} 缺少结束 marker")

        sync_id, code = _fenced_block(body, SYNC_FENCE, lab_id=lab_id, label="sync")
        output_id, expected_output = _fenced_block(
            body, OUTPUT_FENCE, lab_id=lab_id, label="output"
        )
        if sync_id != lab_id or output_id != lab_id:
            raise ValueError(
                f"lesson lab {lab_id} 的 marker、sync 与 output id 必须一致"
            )
        title = next(
            (item.removeprefix("### ").strip() for item in body if item.startswith("### ")),
            "",
        )
        labs.append(
            LessonLab(
                lab_id=lab_id,
                layer=match.group("layer"),
                kind=match.group("kind"),
                concept=match.group("concept"),
                pair=match.group("pair"),
                title=title,
                prediction=_labeled_prose(body, "运行前先预测"),
                code=code,
                expected_output=expected_output,
                explanation=_labeled_prose(body, "发生了什么"),
                modification=_labeled_prose(body, "动手修改"),
                line=line,
            )
        )
        index += 1
    return labs


def _build_v2_notebook(markdown_path: Path, markdown: str) -> nbformat.NotebookNode:
    labs = extract_lesson_labs(markdown)
    if not labs:
        raise ValueError(f"{markdown_path} 声明 v2 契约却没有 lesson lab")
    title = markdown.splitlines()[0].removeprefix("# ")
    cells = [
        nbformat.v4.new_markdown_cell(
            f"# {title}（概念实验与工程迁移）\n\n"
            "按正文顺序完成每个实验：先写预测，再运行代码，阅读输出，最后修改一个变量。\n\n"
            "概念实验不会预先导入 Mini DeerFlow；进入“工程迁移”标签后，才把同一机制放回项目。",
            id=stable_cell_id(f"{markdown_path.name}:v2:intro"),
        )
    ]
    for number, lab in enumerate(labs, start=1):
        lab_metadata = {
            "id": lab.lab_id,
            "layer": lab.layer,
            "kind": lab.kind,
            "concept": lab.concept,
            "pair": lab.pair,
        }
        cells.append(
            nbformat.v4.new_markdown_cell(
                f"## 实验 {number}：{lab.title}\n\n"
                f"`{lab.layer}` · `{lab.kind}` · `{lab.concept}`",
                metadata={
                    "langchain_logbook_lab": lab_metadata,
                    "langchain_logbook_role": "heading",
                },
                id=stable_cell_id(f"{markdown_path.name}:{lab.lab_id}:heading"),
            )
        )
        cells.append(
            nbformat.v4.new_markdown_cell(
                f"**运行前先预测**：{lab.prediction}\n\n"
                "> 先在这里写下你的判断，再执行下一个代码单元。",
                metadata={
                    "langchain_logbook_lab_id": lab.lab_id,
                    "langchain_logbook_role": "prediction",
                },
                id=stable_cell_id(f"{markdown_path.name}:{lab.lab_id}:prediction"),
            )
        )
        cells.append(
            nbformat.v4.new_code_cell(
                lab.code,
                metadata={
                    "langchain_logbook_sync": lab.lab_id,
                    "langchain_logbook_lab": lab_metadata,
                    "langchain_logbook_expected_output": lab.expected_output,
                },
                id=stable_cell_id(f"{markdown_path.name}:{lab.lab_id}:code"),
            )
        )
        cells.append(
            nbformat.v4.new_markdown_cell(
                f"**发生了什么**：{lab.explanation}",
                metadata={
                    "langchain_logbook_lab_id": lab.lab_id,
                    "langchain_logbook_role": "explanation",
                },
                id=stable_cell_id(f"{markdown_path.name}:{lab.lab_id}:explanation"),
            )
        )
        if lab.modification:
            cells.append(
                nbformat.v4.new_markdown_cell(
                    f"**动手修改**：{lab.modification}",
                    metadata={
                        "langchain_logbook_lab_id": lab.lab_id,
                        "langchain_logbook_role": "modification",
                    },
                    id=stable_cell_id(f"{markdown_path.name}:{lab.lab_id}:modification"),
                )
            )
    notebook = nbformat.v4.new_notebook(cells=cells)
    notebook.metadata["langchain_logbook"] = {
        "source": markdown_path.name,
        "generated": True,
        "lesson_contract": "v2",
    }
    return notebook


def build_notebook(markdown_path: Path) -> nbformat.NotebookNode:
    markdown = markdown_path.read_text(encoding="utf-8")
    if LESSON_CONTRACT_V2 in markdown:
        notebook = _build_v2_notebook(markdown_path, markdown)
        notebook.metadata["kernelspec"] = {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        }
        notebook.metadata["language_info"] = {"name": "python", "version": "3.12"}
        return notebook

    synced = extract_synced_cells(markdown)
    if not synced:
        raise ValueError(f"{markdown_path} 没有 sync 代码块")
    title = markdown.splitlines()[0].removeprefix("# ")
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

    module_name = f"_langchain_logbook_{stable_cell_id(source_name)}"
    notebook_module = ModuleType(module_name)
    namespace = notebook_module.__dict__
    sys.modules[module_name] = notebook_module
    execution_count = 0
    try:
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
                exec(
                    compile(cell.source, f"{source_name}:{execution_count}", "exec"),
                    namespace,
                )
            cell.execution_count = execution_count
            rendered = output.getvalue()
            cell.outputs = (
                [nbformat.v4.new_output("stream", name="stdout", text=rendered)]
                if rendered
                else []
            )
    finally:
        sys.modules.pop(module_name, None)


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
