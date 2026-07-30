from pathlib import Path
import subprocess
import sys

from scripts.check_writing_contract import prose_paragraphs, visible_length


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WRITING_CHECKER = PROJECT_ROOT / "scripts" / "check_writing_contract.py"


def test_prose_paragraphs_skip_non_prose_blocks(tmp_path: Path) -> None:
    document = tmp_path / "chapter.md"
    document.write_text(
        "# 标题\n\n"
        "第一行\n第二行\n\n"
        "- 列表不计\n\n"
        "```python\nprint('代码不计')\n```\n\n"
        "| 表格 | 不计 |\n",
        encoding="utf-8",
    )

    assert prose_paragraphs(document) == [(3, "第一行 第二行")]


def test_visible_length_ignores_link_target_but_keeps_label() -> None:
    paragraph = "阅读[官方文档](https://example.com/a/very/long/path)。"

    assert visible_length(paragraph) == len("阅读[官方文档]。")


def test_beginner_contract_rejects_missing_navigation_fields(tmp_path: Path) -> None:
    document = tmp_path / "chapter.md"
    document.write_text(
        "# 第 02 章：示例\n\n"
        "> [!NOTE]\n"
        "> **本章只解决一个问题**：把输出变成对象。\n\n"
        "正文。\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(WRITING_CHECKER),
            "--root",
            str(tmp_path),
            "--require-beginner-contracts",
            "chapter.md",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "missing beginner navigation field: 当前系统" in result.stdout


def test_beginner_contract_rejects_unexplained_fake_model(tmp_path: Path) -> None:
    document = tmp_path / "chapter.md"
    document.write_text(
        "# 第 02 章：示例\n\n"
        "> [!NOTE]\n"
        "> **本章只解决一个问题**：把输出变成对象。\n"
        ">\n"
        "> **当前系统**：模型可以调用。\n"
        ">\n"
        "> **遇到的问题**：输出不稳定。\n"
        ">\n"
        "> **本章目标**：建立对象。\n"
        ">\n"
        "> **暂时不讲**：Graph。\n"
        ">\n"
        "> **学完以后**：可以校验对象。\n"
        ">\n"
        "> **预计时间**：20 分钟。\n\n"
        "下面使用 GenericFakeChatModel。\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(WRITING_CHECKER),
            "--root",
            str(tmp_path),
            "--require-beginner-contracts",
            "chapter.md",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "first Fake Model mention must explain" in result.stdout
