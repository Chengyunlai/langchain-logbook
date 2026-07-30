"""检查全书正文是否遵守中文技术书写契约。"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


DEFAULT_FILES = (
    "ORIENTATION.md",
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

BEGINNER_CONTRACT_FILES = frozenset(
    relative
    for relative in DEFAULT_FILES
    if relative not in {"README.md"}
)
BEGINNER_NAVIGATION_FIELDS = (
    ("本章只解决一个问题", "本篇只解决一个问题"),
    ("当前系统",),
    ("遇到的问题",),
    ("本章目标", "本篇目标"),
    ("暂时不讲",),
    ("学完以后", "读完以后"),
    ("预计时间",),
)
FAKE_MODEL_PATTERN = re.compile(
    r"GenericFakeChatModel|fake[ _](?:chat[ _])?model|离线模型",
    re.IGNORECASE,
)
FAKE_MODEL_NON_PROVIDER_CUES = ("不调用", "不会调用", "不访问", "不会访问")
FAKE_MODEL_DETERMINISM_CUES = (
    "只按脚本",
    "只返回预设",
    "可重复",
    "稳定复现",
    "稳定验证",
    "确定性",
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


def line_containing(text: str, position: int) -> str:
    """返回指定位置所在的整行。"""

    start = text.rfind("\n", 0, position) + 1
    end = text.find("\n", position)
    return text[start : end if end >= 0 else len(text)].strip()


def beginner_contract_failures(path: Path) -> list[str]:
    """检查章节导航卡与 Fake Model 首次说明。"""

    text = path.read_text(encoding="utf-8")
    failures: list[str] = []
    for aliases in BEGINNER_NAVIGATION_FIELDS:
        if not any(f"**{alias}**" in text for alias in aliases):
            failures.append(f"missing beginner navigation field: {aliases[0]}")

    fake_match = FAKE_MODEL_PATTERN.search(text)
    if fake_match is not None:
        notice_line = line_containing(text, fake_match.start())
        notice_is_complete = (
            any(cue in notice_line for cue in FAKE_MODEL_NON_PROVIDER_CUES)
            and any(cue in notice_line for cue in FAKE_MODEL_DETERMINISM_CUES)
        )
        if not notice_is_complete:
            failures.append(
                "first visible Fake Model mention must explain non-provider "
                "and deterministic behavior"
            )
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--max-paragraph-chars", type=int, default=240)
    parser.add_argument(
        "--require-beginner-contracts",
        action="store_true",
        help="require the beginner navigation card and Fake Model first-use notice",
    )
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
        if args.require_beginner_contracts or relative in BEGINNER_CONTRACT_FILES:
            failures.extend(
                f"{relative}: {failure}"
                for failure in beginner_contract_failures(path)
            )
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
