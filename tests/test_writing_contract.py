from pathlib import Path

from scripts.check_writing_contract import prose_paragraphs, visible_length


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
