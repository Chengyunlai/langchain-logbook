from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from scripts.sync_lesson_notebooks import (
    build_notebook,
    execute_in_fresh_namespace,
    extract_lesson_labs,
    extract_synced_cells,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class NotebookSyncTests(unittest.TestCase):
    def test_chapter_one_notebook_explains_fake_model_before_first_code(self) -> None:
        notebook = build_notebook(PROJECT_ROOT / "tutorials/01_Getting_Started.md")

        intro = notebook.cells[0].source
        first_code = next(cell for cell in notebook.cells if cell.cell_type == "code")

        self.assertIn("真实开发写法", intro)
        self.assertIn("Fake Model", intro)
        self.assertIn("不会调用外部大模型", intro)
        self.assertIn("GenericFakeChatModel", first_code.source)

    def test_v2_labs_are_parsed_with_teaching_prose(self) -> None:
        markdown = (
            "# 第 07 章：Demo\n\n"
            "<!-- lesson-contract:v2 -->\n\n"
            "<!-- lesson-lab:id=demo-failure layer=concept kind=failure "
            "concept=merge pair=merge-results -->\n"
            "### 让并行写入发生冲突\n\n"
            "**运行前先预测**：会覆盖还是报错？\n\n"
            "```python sync=demo-failure\nprint('conflict')\n```\n\n"
            "**观察结果**：\n\n"
            "```text output=demo-failure\nconflict\n```\n\n"
            "**发生了什么**：两个写入没有合并规则。\n\n"
            "**动手修改**：增加 reducer 后再运行。\n"
            "<!-- /lesson-lab -->\n"
        )

        labs = extract_lesson_labs(markdown)

        self.assertEqual([lab.lab_id for lab in labs], ["demo-failure"])
        self.assertEqual(labs[0].title, "让并行写入发生冲突")
        self.assertEqual(labs[0].prediction, "会覆盖还是报错？")
        self.assertEqual(labs[0].expected_output, "conflict\n")
        self.assertIn("没有合并规则", labs[0].explanation)
        self.assertIn("增加 reducer", labs[0].modification)

    def test_v2_notebook_preserves_lab_order_and_does_not_preload_project(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            markdown = Path(directory, "07_Demo.md")
            markdown.write_text(
                "# 第 07 章：Demo\n\n"
                "<!-- lesson-contract:v2 -->\n\n"
                "<!-- notebook-reading-path:start -->\n"
                "第一次先完成实验 1，再进入实验 2。\n"
                "<!-- notebook-reading-path:end -->\n\n"
                "<!-- lesson-lab:id=demo-failure layer=concept kind=failure "
                "concept=merge pair=merge-results -->\n"
                "### 先看失败\n\n"
                "**运行前先预测**：先输出哪一行？\n\n"
                "```python sync=demo-failure\nprint('failure')\n```\n\n"
                "**观察结果**：\n\n"
                "```text output=demo-failure\nfailure\n```\n\n"
                "**发生了什么**：失败证据先出现。\n\n"
                "**动手修改**：修改输出并比较。\n"
                "<!-- /lesson-lab -->\n\n"
                "<!-- lesson-lab:id=demo-repair layer=concept kind=repair "
                "concept=merge pair=merge-results -->\n"
                "### 再做修复\n\n"
                "**运行前先预测**：修复后输出什么？\n\n"
                "```python sync=demo-repair\nprint('repair')\n```\n\n"
                "**观察结果**：\n\n"
                "```text output=demo-repair\nrepair\n```\n\n"
                "**发生了什么**：修复紧邻失败。\n\n"
                "**动手修改**：交换两个值再观察。\n"
                "<!-- /lesson-lab -->\n",
                encoding="utf-8",
            )

            notebook = build_notebook(markdown)
            execute_in_fresh_namespace(notebook, markdown.name)

        synced = [
            cell
            for cell in notebook.cells
            if cell.cell_type == "code" and cell.metadata.get("langchain_logbook_sync")
        ]
        self.assertEqual(
            [cell.metadata["langchain_logbook_sync"] for cell in synced],
            ["demo-failure", "demo-repair"],
        )
        self.assertNotIn(
            "mini_deerflow",
            "\n".join(cell.source for cell in notebook.cells[:3]),
        )
        self.assertIn("第一次先完成实验 1", notebook.cells[0].source)
        prose = "\n".join(
            cell.source for cell in notebook.cells if cell.cell_type == "markdown"
        )
        self.assertLess(prose.index("先输出哪一行"), prose.index("失败证据先出现"))
        self.assertIn("修改输出并比较", prose)
        self.assertEqual(synced[0].outputs[0].text, "failure\n")

    def test_duplicate_and_unclosed_sync_markers_are_rejected(self) -> None:
        duplicate = "```python sync=demo\na = 1\n```\n```python sync=demo\nb = 2\n```"
        unclosed = "```python sync=demo\na = 1"

        with self.assertRaisesRegex(ValueError, "重复"):
            extract_synced_cells(duplicate)
        with self.assertRaisesRegex(ValueError, "未闭合"):
            extract_synced_cells(unclosed)

    def test_generated_notebook_has_the_required_learning_sections_and_executes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            markdown = Path(directory, "01_Demo.md")
            markdown.write_text(
                "# 第 01 章：Demo\n\n"
                "```python sync=demo-success\nvalue = 1\nassert value == 1\n```\n\n"
                "```python sync=demo-failure\ntry:\n    raise ValueError('x')\n"
                "except ValueError:\n    observed = True\n```\n\n"
                "```python sync=demo-stream-failure\nstream_error = 'observed'\n```\n",
                encoding="utf-8",
            )

            notebook = build_notebook(markdown)
            execute_in_fresh_namespace(notebook, markdown.name)

        markdown_text = "\n".join(
            cell.source for cell in notebook.cells if cell.cell_type == "markdown"
        )
        for required in [
            "环境与预计用时",
            "offline profile 初始化",
            "前置能力探针",
            "最小成功实验",
            "失败实验",
            "分层练习",
            "自动验收摘要",
            "清理临时资源",
        ]:
            self.assertIn(required, markdown_text)
        self.assertTrue(
            all(cell.execution_count for cell in notebook.cells if cell.cell_type == "code")
        )
        sync_ids = [
            cell.metadata.get("langchain_logbook_sync")
            for cell in notebook.cells
            if cell.cell_type == "code" and cell.metadata.get("langchain_logbook_sync")
        ]
        self.assertEqual(len(sync_ids), len(set(sync_ids)))

    def test_executor_rejects_subprocess_escape(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            markdown = Path(directory, "01_Demo.md")
            markdown.write_text(
                "# 第 01 章：Demo\n\n"
                "```python sync=demo-success\n"
                "import subprocess\n"
                "subprocess.run(['curl', 'https://example.com'], check=True)\n"
                "```\n",
                encoding="utf-8",
            )
            notebook = build_notebook(markdown)

            with self.assertRaisesRegex(RuntimeError, "禁止网络或子进程"):
                execute_in_fresh_namespace(notebook, markdown.name)

    def test_executor_supports_jupyter_style_top_level_await(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            markdown = Path(directory, "06_Demo.md")
            markdown.write_text(
                "# 第 06 章：Demo\n\n"
                "<!-- lesson-contract:v2 -->\n\n"
                "<!-- lesson-lab:id=demo-await layer=concept kind=repair "
                "concept=async-execution -->\n"
                "### 在 Notebook 中等待异步调用\n\n"
                "**运行前先预测**：顶层 await 会返回什么？\n\n"
                "```python sync=demo-await\n"
                "import asyncio\n\n"
                "async def answer():\n"
                "    await asyncio.sleep(0)\n"
                "    return 42\n\n"
                "result = await answer()\n"
                "print(result)\n"
                "```\n\n"
                "**观察结果**：\n\n"
                "```text output=demo-await\n42\n```\n\n"
                "**发生了什么**：Notebook 内核直接等待协程。\n\n"
                "**动手修改**：修改返回值并重跑。\n"
                "<!-- /lesson-lab -->\n",
                encoding="utf-8",
            )
            notebook = build_notebook(markdown)

            execute_in_fresh_namespace(notebook, markdown.name)

        code_cell = next(
            cell
            for cell in notebook.cells
            if cell.cell_type == "code"
            and cell.metadata.get("langchain_logbook_sync") == "demo-await"
        )
        self.assertEqual(code_cell.outputs[0].text, "42\n")


if __name__ == "__main__":
    unittest.main()
