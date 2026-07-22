"""检查全书正文是否遵守中文技术书写契约。"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


DEFAULT_FILES = (
    "README.md",
    *(f"tutorials/{name}.md" for name in (
        "01_Getting_Started",
        "02_Structured_Output",
        "03_RAG_2.0",
        "04_Smart_Tooling",
        "05_Agent_Middleware",
        "06_Observability_Persistence",
        "07_StateGraph",
        "08_Engineering_Defense",
        "09_Multi_Agent_Eval",
        "10_Human_In_The_Loop",
        "11_Multi_Agent_Patterns",
    )),
    "mini_deerflow/ARCHITECTURE.md",
    "mini_deerflow/LEAD_AGENT_CORE.md",
    "mini_deerflow/SANDBOX_EXTENSIONS.md",
    "mini_deerflow/RUNTIME_GATEWAY.md",
    "mini_deerflow/EVALUATION_OBSERVABILITY.md",
    "mini_deerflow/CAPSTONE.md",
    "mini_deerflow/DEERFLOW_GUIDE.md",
)

CALIBRATION_PATTERNS = (
    re.compile(r"不是.{0,40}而是"),
    re.compile(r"不等于"),
    re.compile(r"这意味着"),
    re.compile(r"换句话说"),
)
LINK_TARGET = re.compile(r"\]\((?:[^()]|\([^)]*\))*\)")
LIST_ITEM = re.compile(r"^\s*(?:[-*+] |\d+[.)] )")


def prose_paragraphs(path: Path) -> list[tuple[int, str]]:
    """返回正文段落；代码、表格、标题、列表、注释和元信息不计入。"""

    paragraphs: list[tuple[int, str]] = []
    buffer: list[str] = []
    start_line = 0
    in_fence = False
    in_comment = False

    def flush() -> None:
        nonlocal buffer, start_line
        if buffer:
            paragraphs.append((start_line, " ".join(part.strip() for part in buffer)))
        buffer = []
        start_line = 0

    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if line.startswith("```"):
            flush()
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if in_comment:
            if "-->" in line:
                in_comment = False
            continue
        if line.startswith("<!--"):
            flush()
            in_comment = "-->" not in line
            continue
        if not line:
            flush()
            continue
        if (
            line.startswith(("#", "|", ">"))
            or LIST_ITEM.match(raw_line)
            or line in {"---", "***"}
        ):
            flush()
            continue
        if not buffer:
            start_line = line_number
        buffer.append(raw_line)

    flush()
    return paragraphs


def visible_length(paragraph: str) -> int:
    """链接目标不属于正文长度；链接文字仍参与计数。"""

    without_targets = LINK_TARGET.sub("]", paragraph)
    return len(without_targets)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--max-paragraph-chars", type=int, default=240)
    parser.add_argument("files", nargs="*")
    args = parser.parse_args()

    root = args.root.resolve()
    relative_files = tuple(args.files) or DEFAULT_FILES
    failures: list[str] = []
    calibration_count = 0
    paragraph_count = 0

    for relative in relative_files:
        path = root / relative
        if not path.is_file():
            failures.append(f"missing: {relative}")
            continue
        text = path.read_text(encoding="utf-8")
        calibration_count += sum(len(pattern.findall(text)) for pattern in CALIBRATION_PATTERNS)
        for line_number, paragraph in prose_paragraphs(path):
            paragraph_count += 1
            length = visible_length(paragraph)
            if length > args.max_paragraph_chars:
                failures.append(
                    f"{relative}:{line_number}: paragraph has {length} characters "
                    f"(maximum {args.max_paragraph_chars})"
                )

    print(
        "Writing contract: "
        f"{paragraph_count} prose paragraph(s), "
        f"{calibration_count} calibration phrase(s), "
        f"{len(failures)} failure(s)"
    )
    for failure in failures:
        print(f"- {failure}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
