#!/usr/bin/env python3
"""Validate tutorial Markdown and notebooks without calling external services."""

from __future__ import annotations

import argparse
import ast
from dataclasses import asdict, dataclass
import hashlib
import importlib
import json
from pathlib import Path
import re
import sys
import textwrap
from typing import Iterable


PYTHON_FENCE = re.compile(
    r"^(?P<indent>\s*)```(?:python|py)(?:\s+sync=(?P<sync>[a-zA-Z0-9_.:-]+))?\s*$"
)
CHAPTER_NUMBER = re.compile(r"第\s*(\d{2})\s*章")
LEGACY_MODULES = {
    "langchain.smith": "旧 LangSmith evaluation 入口已退出当前课程主线",
    "langserve": "LangServe 已归档，只能出现在 legacy 迁移说明中",
}
LEGACY_NAMES = {
    "LangChainStringEvaluator": "旧 evaluator 不再作为当前评测入口",
    "RunEvalConfig": "旧 langchain.smith 评测配置不再作为当前入口",
    "run_on_dataset": "旧 dataset runner 不再作为当前入口",
}


@dataclass(frozen=True, slots=True)
class Issue:
    code: str
    path: str
    location: str
    message: str
    anchor: str

    @property
    def id(self) -> str:
        payload = f"{self.path}|{self.code}|{self.anchor}".encode()
        return hashlib.sha256(payload).hexdigest()[:16]

    def baseline_record(self) -> dict[str, str]:
        record = asdict(self)
        record["id"] = self.id
        return record


def _normalize_anchor(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())[:160]


def _relative(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _extract_python_fences(text: str) -> Iterable[tuple[int, str, str | None]]:
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        match = PYTHON_FENCE.match(lines[index])
        if not match:
            index += 1
            continue
        start = index + 2
        index += 1
        code: list[str] = []
        while index < len(lines) and not re.match(r"^\s*```\s*$", lines[index]):
            code.append(lines[index])
            index += 1
        yield start, textwrap.dedent("\n".join(code)), match.group("sync")
        index += 1


def _call_uses_v2(call: ast.Call) -> bool:
    return any(
        keyword.arg == "version"
        and isinstance(keyword.value, ast.Constant)
        and keyword.value.value == "v2"
        for keyword in call.keywords
    )


def _call_name(call: ast.Call) -> str:
    try:
        return ast.unparse(call.func)
    except Exception:
        return ""


def _ast_issues(tree: ast.AST, *, path: str, location_prefix: str, source: str) -> list[Issue]:
    issues: list[Issue] = []
    source_lines = source.splitlines()

    def anchor_for(node: ast.AST) -> str:
        line = getattr(node, "lineno", 1)
        if 1 <= line <= len(source_lines):
            return _normalize_anchor(source_lines[line - 1])
        return f"{location_prefix}:{line}"

    for node in ast.walk(tree):
        import_targets: list[tuple[str, str | None]] = []
        if isinstance(node, ast.Import):
            import_targets.extend((imported.name, None) for imported in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            import_targets.extend(
                (node.module, imported.name)
                for imported in node.names
                if imported.name != "*"
            )
        for module_name, symbol_name in import_targets:
            try:
                module = importlib.import_module(module_name)
                if symbol_name is not None and not hasattr(module, symbol_name):
                    # ``from package import submodule`` may resolve a child module
                    # even when the package does not eagerly expose it.
                    importlib.import_module(f"{module_name}.{symbol_name}")
            except (ImportError, ModuleNotFoundError, AttributeError) as error:
                target = f"{module_name}.{symbol_name}" if symbol_name else module_name
                issues.append(
                    Issue(
                        code="import-unavailable",
                        path=path,
                        location=f"{location_prefix}:{getattr(node, 'lineno', 1)}",
                        message=f"当前锁定环境无法导入 {target}: {error}",
                        anchor=anchor_for(node),
                    )
                )

        if isinstance(node, (ast.For, ast.AsyncFor)):
            if (
                isinstance(node.target, (ast.Tuple, ast.List))
                and len(node.target.elts) == 2
                and isinstance(node.iter, ast.Call)
                and _call_name(node.iter).split(".")[-1] in {"stream", "astream"}
                and _call_uses_v2(node.iter)
            ):
                issues.append(
                    Issue(
                        code="stream-v2-tuple",
                        path=path,
                        location=f"{location_prefix}:{getattr(node, 'lineno', 1)}",
                        message="v2 stream 返回 {type, ns, data} envelope，不能解包成二元组",
                        anchor=anchor_for(node),
                    )
                )

        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for legacy_module, reason in LEGACY_MODULES.items():
                if module == legacy_module or module.startswith(f"{legacy_module}."):
                    issues.append(
                        Issue(
                            code="legacy-import",
                            path=path,
                            location=f"{location_prefix}:{getattr(node, 'lineno', 1)}",
                            message=f"{module}: {reason}",
                            anchor=anchor_for(node),
                        )
                    )
            for imported in node.names:
                if imported.name in LEGACY_NAMES:
                    issues.append(
                        Issue(
                            code="legacy-import",
                            path=path,
                            location=f"{location_prefix}:{getattr(node, 'lineno', 1)}",
                            message=f"{imported.name}: {LEGACY_NAMES[imported.name]}",
                            anchor=anchor_for(node),
                        )
                    )

        if isinstance(node, ast.Call) and _call_name(node).split(".")[-1] in {
            "invoke",
            "ainvoke",
            "stream",
            "astream",
        }:
            receiver = _call_name(node).lower()
            if "agent" not in receiver or not node.args or not isinstance(node.args[0], ast.Dict):
                continue
            keys = {
                key.value
                for key in node.args[0].keys
                if isinstance(key, ast.Constant) and isinstance(key.value, str)
            }
            if "input" in keys and "messages" not in keys:
                issues.append(
                    Issue(
                        code="agent-input-key",
                        path=path,
                        location=f"{location_prefix}:{getattr(node, 'lineno', 1)}",
                        message="默认 AgentState 使用 messages；input 字段可能被静默忽略",
                        anchor=anchor_for(node),
                    )
                )

    return issues


def _parse_code(
    code: str,
    *,
    path: str,
    location_prefix: str,
    syntax_code: str,
) -> tuple[ast.AST | None, list[Issue]]:
    try:
        return ast.parse(code), []
    except SyntaxError as error:
        line = error.lineno or 1
        source_lines = code.splitlines()
        anchor = source_lines[line - 1] if 1 <= line <= len(source_lines) else error.msg
        return None, [
            Issue(
                code=syntax_code,
                path=path,
                location=f"{location_prefix}:{line}",
                message=error.msg,
                anchor=_normalize_anchor(anchor),
            )
        ]


def _validate_markdown(path: Path, root: Path) -> list[Issue]:
    relative = _relative(path, root)
    text = path.read_text(encoding="utf-8")
    issues: list[Issue] = []
    for fence_line, code, _ in _extract_python_fences(text):
        tree, syntax_issues = _parse_code(
            code,
            path=relative,
            location_prefix=f"line {fence_line}",
            syntax_code="markdown-syntax",
        )
        issues.extend(syntax_issues)
        if tree is not None:
            issues.extend(
                _ast_issues(
                    tree,
                    path=relative,
                    location_prefix=f"line {fence_line}",
                    source=code,
                )
            )
    return issues


def _cell_source(cell: dict[str, object]) -> str:
    source = cell.get("source", "")
    return "".join(source) if isinstance(source, list) else str(source)


def _validate_notebook(path: Path, root: Path) -> list[Issue]:
    relative = _relative(path, root)
    try:
        notebook = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return [
            Issue(
                code="notebook-json",
                path=relative,
                location="file",
                message=str(error),
                anchor="invalid-notebook-json",
            )
        ]

    issues: list[Issue] = []
    code_cells = [cell for cell in notebook.get("cells", []) if cell.get("cell_type") == "code"]
    if code_cells and all(cell.get("execution_count") is None for cell in code_cells):
        issues.append(
            Issue(
                code="notebook-unexecuted",
                path=relative,
                location="notebook",
                message="所有代码单元均未执行；核心 Notebook 不能据此标记为已验证",
                anchor="all-code-cells-unexecuted",
            )
        )

    for cell_index, cell in enumerate(notebook.get("cells", []), start=1):
        if cell.get("cell_type") != "code":
            continue
        source = _cell_source(cell)
        for output in cell.get("outputs", []):
            if output.get("output_type") == "error":
                error_name = str(output.get("ename", "Error"))
                error_value = str(output.get("evalue", ""))
                issues.append(
                    Issue(
                        code="notebook-error-output",
                        path=relative,
                        location=f"cell {cell_index}",
                        message=f"{error_name}: {error_value}",
                        anchor=f"cell-{cell_index}:{error_name}:{_normalize_anchor(error_value)}",
                    )
                )
        tree, syntax_issues = _parse_code(
            source,
            path=relative,
            location_prefix=f"cell {cell_index}",
            syntax_code="notebook-syntax",
        )
        issues.extend(syntax_issues)
        if tree is not None:
            issues.extend(
                _ast_issues(
                    tree,
                    path=relative,
                    location_prefix=f"cell {cell_index}",
                    source=source,
                )
            )
    return issues


def _first_chapter_number_from_markdown(path: Path) -> str | None:
    match = CHAPTER_NUMBER.search(path.read_text(encoding="utf-8"))
    return match.group(1) if match else None


def _first_chapter_number_from_notebook(path: Path) -> str | None:
    try:
        notebook = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    for cell in notebook.get("cells", []):
        if cell.get("cell_type") == "markdown":
            match = CHAPTER_NUMBER.search(_cell_source(cell))
            if match:
                return match.group(1)
    return None


def _markdown_code_contract(path: Path) -> tuple[bool, list[str]]:
    contracts: list[tuple[str | None, str]] = []
    for _, code, sync_id in _extract_python_fences(path.read_text(encoding="utf-8")):
        try:
            contracts.append((sync_id, ast.dump(ast.parse(code), include_attributes=False)))
        except SyntaxError:
            # 语法问题由 Markdown 校验器单独、带准确行号报告。
            continue
    uses_markers = any(sync_id is not None for sync_id, _ in contracts)
    if uses_markers:
        return True, sorted(
            f"{sync_id}:{contract}" for sync_id, contract in contracts if sync_id
        )
    return False, [contract for _, contract in contracts]


def _notebook_code_contract(path: Path, *, marked_only: bool) -> list[str]:
    try:
        notebook = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    contracts: list[str] = []
    for cell in notebook.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        sync_id = cell.get("metadata", {}).get("langchain_logbook_sync")
        if marked_only and not sync_id:
            continue
        try:
            contract = ast.dump(ast.parse(_cell_source(cell)), include_attributes=False)
            contracts.append(f"{sync_id}:{contract}" if marked_only else contract)
        except SyntaxError:
            continue
    return sorted(contracts) if marked_only else contracts


def _markdown_sync_ids(path: Path) -> set[str]:
    return {
        sync_id
        for _, _, sync_id in _extract_python_fences(path.read_text(encoding="utf-8"))
        if sync_id is not None
    }


def _notebook_sync_ids(path: Path) -> set[str]:
    try:
        notebook = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    return {
        str(sync_id)
        for cell in notebook.get("cells", [])
        if cell.get("cell_type") == "code"
        if (sync_id := cell.get("metadata", {}).get("langchain_logbook_sync"))
    }


def _contract_digest(contracts: list[str]) -> str:
    return hashlib.sha256("\n".join(contracts).encode()).hexdigest()[:12]


def _validate_pairs(tutorials: Path, root: Path) -> list[Issue]:
    issues: list[Issue] = []
    markdown = {path.stem: path for path in tutorials.glob("[0-9][0-9]_*.md")}
    notebooks = {path.stem: path for path in tutorials.glob("[0-9][0-9]_*.ipynb")}
    for stem in sorted(markdown.keys() | notebooks.keys()):
        if stem not in notebooks:
            path = markdown[stem]
            issues.append(
                Issue(
                    code="missing-notebook",
                    path=_relative(path, root),
                    location="file",
                    message="章节 Markdown 缺少同名 Notebook",
                    anchor=stem,
                )
            )
            continue
        if stem not in markdown:
            path = notebooks[stem]
            issues.append(
                Issue(
                    code="missing-markdown",
                    path=_relative(path, root),
                    location="file",
                    message="章节 Notebook 缺少同名 Markdown",
                    anchor=stem,
                )
            )
            continue
        md_number = _first_chapter_number_from_markdown(markdown[stem])
        nb_number = _first_chapter_number_from_notebook(notebooks[stem])
        if md_number != nb_number:
            issues.append(
                Issue(
                    code="chapter-number-drift",
                    path=_relative(notebooks[stem], root),
                    location="title",
                    message=f"Markdown 章节号 {md_number!r} 与 Notebook 章节号 {nb_number!r} 不一致",
                    anchor=f"{stem}:{md_number}:{nb_number}",
                )
            )
        uses_markers, markdown_contract = _markdown_code_contract(markdown[stem])
        notebook_contract = _notebook_code_contract(notebooks[stem], marked_only=uses_markers)
        if markdown_contract != notebook_contract:
            md_digest = _contract_digest(markdown_contract)
            nb_digest = _contract_digest(notebook_contract)
            issues.append(
                Issue(
                    code="code-content-drift",
                    path=_relative(notebooks[stem], root),
                    location="code cells",
                    message=(
                        "Markdown Python 代码块与 Notebook 代码单元不一致："
                        f"md={len(markdown_contract)}/{md_digest}, "
                        f"ipynb={len(notebook_contract)}/{nb_digest}"
                    ),
                    anchor=f"{stem}:{md_digest}:{nb_digest}",
                )
            )
    return issues


def _validate_required_experiments(tutorials: Path, root: Path) -> list[Issue]:
    """Ensure a pair cannot go green by deleting the same experiment on both sides."""

    manifest_path = root / "quality" / "lesson-contracts.json"
    if not manifest_path.exists():
        return []
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return [
            Issue(
                code="lesson-contract-manifest",
                path=_relative(manifest_path, root),
                location="file",
                message=f"无法读取课程实验清单: {error}",
                anchor="invalid-lesson-contract-manifest",
            )
        ]

    issues: list[Issue] = []
    chapters = manifest.get("chapters", {})
    if not isinstance(chapters, dict):
        chapters = {}
    for stem, chapter_contract in sorted(chapters.items()):
        if not isinstance(chapter_contract, dict):
            continue
        required = chapter_contract.get("required_sync_ids", [])
        if not isinstance(required, list):
            continue
        markdown_path = tutorials / f"{stem}.md"
        notebook_path = tutorials / f"{stem}.ipynb"
        markdown_ids = _markdown_sync_ids(markdown_path) if markdown_path.exists() else set()
        notebook_ids = _notebook_sync_ids(notebook_path) if notebook_path.exists() else set()
        for sync_id in sorted({str(item) for item in required}):
            missing_from = []
            if sync_id not in markdown_ids:
                missing_from.append("Markdown")
            if sync_id not in notebook_ids:
                missing_from.append("Notebook")
            if missing_from:
                issues.append(
                    Issue(
                        code="missing-required-experiment",
                        path=_relative(manifest_path, root),
                        location=stem,
                        message=f"必备实验 {sync_id!r} 缺少于: {', '.join(missing_from)}",
                        anchor=f"{stem}:{sync_id}:{','.join(missing_from)}",
                    )
                )
    return issues


def discover_issues(root: Path) -> list[Issue]:
    tutorials = root / "tutorials"
    if not tutorials.is_dir():
        return [
            Issue(
                code="missing-tutorials-directory",
                path="tutorials",
                location="directory",
                message="找不到 tutorials 目录",
                anchor="tutorials",
            )
        ]
    issues = _validate_pairs(tutorials, root)
    issues.extend(_validate_required_experiments(tutorials, root))
    for path in sorted(tutorials.glob("[0-9][0-9]_*.md")):
        issues.extend(_validate_markdown(path, root))
    for path in sorted(tutorials.glob("[0-9][0-9]_*.ipynb")):
        issues.extend(_validate_notebook(path, root))
    # 同一行导入可能同时命中旧模块和旧符号。公共问题 ID 会把它们合并为
    # 一个可处理项，避免 baseline 保存重复记录。
    unique = {issue.id: issue for issue in issues}
    return sorted(unique.values(), key=lambda issue: (issue.path, issue.location, issue.code, issue.id))


def _load_baseline(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {record["id"]: record for record in data.get("issues", [])}


def _write_baseline(path: Path, issues: list[Issue]) -> None:
    payload = {
        "version": 1,
        "description": "现有教程已知债务；修复后必须更新基线，新增问题会直接失败。",
        "issues": [issue.baseline_record() for issue in issues],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _print_issue(prefix: str, issue: Issue) -> None:
    print(f"[{prefix}] {issue.code} {issue.path} {issue.location}: {issue.message} ({issue.id})")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--baseline",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "quality" / "tutorial-baseline.json",
    )
    parser.add_argument("--write-baseline", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve()
    issues = discover_issues(root)
    if args.write_baseline:
        _write_baseline(args.baseline, issues)
        print(f"Wrote {len(issues)} known issue(s) to {args.baseline}")
        return 0

    baseline = _load_baseline(args.baseline)
    current = {issue.id: issue for issue in issues}
    new_ids = sorted(current.keys() - baseline.keys())
    known_ids = sorted(current.keys() & baseline.keys())
    stale_ids = sorted(baseline.keys() - current.keys())

    for issue_id in new_ids:
        _print_issue("new", current[issue_id])
    for issue_id in known_ids:
        _print_issue("known", current[issue_id])
    for issue_id in stale_ids:
        record = baseline[issue_id]
        print(
            f"[stale] {record.get('code')} {record.get('path')}: "
            "问题已修复或移动，请更新 baseline"
        )

    print(f"Tutorial validation: {len(new_ids)} new, {len(known_ids)} known, {len(stale_ids)} stale")
    return 1 if new_ids or stale_ids else 0


if __name__ == "__main__":
    sys.exit(main())
