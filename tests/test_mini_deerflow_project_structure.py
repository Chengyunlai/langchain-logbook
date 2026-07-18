from __future__ import annotations

import ast
from contextlib import redirect_stdout
import importlib
import io
import json
from pathlib import Path
import unittest

from pydantic import ValidationError

from mini_deerflow.__main__ import main
from mini_deerflow.api import ConversationRequest
from mini_deerflow.evals import EvaluationCase, evaluate_required_terms
from mini_deerflow.sandbox import SandboxCommand


ROOT = Path(__file__).resolve().parents[1]


class MiniDeerFlowProjectStructureTests(unittest.TestCase):
    def test_module_cli_runs_the_same_offline_composition_root(self) -> None:
        output = io.StringIO()

        with redirect_stdout(output):
            exit_code = main(["--message", "解释 create_agent"])

        payload = json.loads(output.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["profile"], "offline")
        self.assertIn("task", payload["tools"])
        self.assertGreaterEqual(payload["middleware_events"], 3)

    def test_langgraph_manifest_points_to_an_importable_graph_factory(self) -> None:
        manifest = json.loads((ROOT / "langgraph.json").read_text(encoding="utf-8"))

        self.assertEqual(manifest["dependencies"], ["."])
        self.assertEqual(manifest["python_version"], "3.12")
        self.assertEqual(set(manifest["graphs"]), {"mini_deerflow"})

        module_name, attribute_name = manifest["graphs"]["mini_deerflow"].split(":")
        factory = getattr(importlib.import_module(module_name), attribute_name)
        first_graph = factory({})
        second_graph = factory({})

        self.assertIsNot(first_graph, second_graph)
        self.assertTrue(callable(first_graph.invoke))
        self.assertIn("model", first_graph.get_graph().nodes)
        self.assertIsNone(first_graph.checkpointer)
        self.assertIsNone(first_graph.store)

    def test_future_course_modules_are_real_importable_boundaries(self) -> None:
        expected_exports = {
            "mini_deerflow.api": "ConversationRequest",
            "mini_deerflow.capstone": "CapstoneRequest",
            "mini_deerflow.evals": "EvaluationCase",
            "mini_deerflow.runtime": "RunDescriptor",
            "mini_deerflow.sandbox": "SandboxProvider",
        }

        for module_name, public_name in expected_exports.items():
            with self.subTest(module=module_name):
                module = importlib.import_module(module_name)
                self.assertIn(public_name, module.__all__)
                self.assertTrue(hasattr(module, public_name))

    def test_capstone_and_deerflow_reading_guides_are_published_course_sources(self) -> None:
        capstone = (ROOT / "mini_deerflow" / "CAPSTONE.md").read_text(encoding="utf-8")
        guide = (ROOT / "mini_deerflow" / "DEERFLOW_GUIDE.md").read_text(encoding="utf-8")

        self.assertIn("从空目录逐步建立项目", capstone)
        self.assertIn("4af617835805dd7cd78162ebed02fd6b782ea8bf", guide)
        self.assertIn("路线四：Gateway", guide)

    def test_harness_modules_do_not_depend_on_the_api_adapter(self) -> None:
        package_root = ROOT / "mini_deerflow"
        violations: list[str] = []

        for path in package_root.rglob("*.py"):
            if "api" in path.relative_to(package_root).parts:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    imported = [node.module or ""]
                else:
                    continue
                if any(name == "mini_deerflow.api" or name.startswith("mini_deerflow.api.") for name in imported):
                    violations.append(str(path.relative_to(ROOT)))

        self.assertEqual(violations, [])

    def test_future_boundaries_already_enforce_useful_contracts(self) -> None:
        with self.assertRaises(ValidationError):
            ConversationRequest(message="hello", user_id="model-chosen-user")
        with self.assertRaises(ValueError):
            SandboxCommand(argv=())

        result = evaluate_required_terms(
            EvaluationCase(
                case_id="scaffold-smoke",
                prompt="解释 Agent 架构",
                required_terms=("LangGraph", "Middleware"),
            ),
            "LangGraph 提供 runtime。",
        )
        self.assertFalse(result.passed)
        self.assertEqual(result.missing_terms, ("Middleware",))


if __name__ == "__main__":
    unittest.main()
