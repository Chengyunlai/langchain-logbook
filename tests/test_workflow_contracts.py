from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
from textwrap import dedent
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_CHECKER = PROJECT_ROOT / "scripts" / "check_workflows.py"


VALID_QUALITY = """
name: Quality
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v8.3.2
      - run: make check
"""

VALID_DEPLOY = """
name: Deploy
on:
  workflow_dispatch:
permissions:
  contents: read
  pages: write
  id-token: write
concurrency:
  group: pages
  cancel-in-progress: false
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v8.3.2
      - uses: actions/configure-pages@v6
      - run: make check
      - uses: actions/upload-pages-artifact@v5
        with:
          path: docs-site/dist
  deploy:
    needs: build
    environment:
      name: github-pages
    steps:
      - uses: actions/deploy-pages@v5
"""


class WorkflowContractCliTests(unittest.TestCase):
    def write_workflows(
        self,
        root: Path,
        *,
        quality: str = VALID_QUALITY,
        deploy: str = VALID_DEPLOY,
    ) -> Path:
        workflows = root / ".github" / "workflows"
        workflows.mkdir(parents=True)
        (workflows / "quality.yml").write_text(dedent(quality), encoding="utf-8")
        (workflows / "deploy.yml").write_text(dedent(deploy), encoding="utf-8")
        return root

    def run_checker(self, root: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(WORKFLOW_CHECKER), "--root", str(root)],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_accepts_quality_and_pages_using_same_validated_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.write_workflows(Path(directory))

            result = self.run_checker(root)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_reports_quality_workflow_that_bypasses_make_check(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.write_workflows(
                Path(directory),
                quality="""
                name: Quality
                jobs:
                  test:
                    steps:
                      - run: make test
                """,
            )

            result = self.run_checker(root)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("quality-gate", result.stdout)

    def test_reports_conditional_or_ignored_quality_gate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.write_workflows(
                Path(directory),
                quality="""
                name: Quality
                jobs:
                  check:
                    steps:
                      - run: make check
                        if: false
                        continue-on-error: true
                """,
            )

            result = self.run_checker(root)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("quality-gate", result.stdout)

    def test_reports_quality_gate_inside_a_conditional_job(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.write_workflows(
                Path(directory),
                quality="""
                name: Quality
                jobs:
                  check:
                    if: false
                    steps:
                      - run: make check
                """,
            )

            result = self.run_checker(root)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("quality-gate", result.stdout)

    def test_reports_pages_build_that_rebuilds_without_make_check(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.write_workflows(
                Path(directory),
                deploy="""
                name: Deploy
                jobs:
                  build:
                    steps:
                      - uses: withastro/action@v3
                  deploy:
                    needs: build
                    steps:
                      - uses: actions/deploy-pages@v4
                """,
            )

            result = self.run_checker(root)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("deploy-gate", result.stdout)

    def test_reports_pages_build_that_ignores_make_check_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.write_workflows(
                Path(directory),
                deploy=VALID_DEPLOY.replace(
                    "- run: make check",
                    "- run: make check\n        continue-on-error: true",
                ),
            )

            result = self.run_checker(root)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("deploy-gate", result.stdout)

    def test_reports_gate_inside_a_failure_tolerant_pages_job(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.write_workflows(
                Path(directory),
                deploy=VALID_DEPLOY.replace(
                    "build:\n    runs-on:",
                    "build:\n    continue-on-error: true\n    runs-on:",
                ),
            )

            result = self.run_checker(root)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("deploy-gate", result.stdout)

    def test_reports_pages_upload_that_does_not_use_validated_dist(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.write_workflows(
                Path(directory),
                deploy="""
                name: Deploy
                jobs:
                  build:
                    steps:
                      - run: make check
                      - uses: actions/upload-pages-artifact@v3
                        with:
                          path: docs-site/public
                  deploy:
                    needs: build
                    steps:
                      - uses: actions/deploy-pages@v4
                """,
            )

            result = self.run_checker(root)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("deploy-artifact", result.stdout)

    def test_reports_pages_build_that_mutates_dist_after_the_gate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.write_workflows(
                Path(directory),
                deploy="""
                name: Deploy
                on:
                  workflow_dispatch:
                permissions:
                  contents: read
                  pages: write
                  id-token: write
                concurrency:
                  group: pages
                  cancel-in-progress: false
                jobs:
                  build:
                    steps:
                      - uses: actions/configure-pages@v5
                      - run: make check
                      - run: npm run build
                      - uses: actions/upload-pages-artifact@v4
                        with:
                          path: docs-site/dist
                  deploy:
                    needs: build
                    environment:
                      name: github-pages
                    steps:
                      - uses: actions/deploy-pages@v4
                """,
            )

            result = self.run_checker(root)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("deploy-artifact-flow", result.stdout)

    def test_reports_deploy_job_that_does_not_depend_on_validated_build(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.write_workflows(
                Path(directory),
                deploy="""
                name: Deploy
                concurrency:
                  group: pages
                  cancel-in-progress: false
                jobs:
                  build:
                    steps:
                      - run: make check
                      - uses: actions/upload-pages-artifact@v3
                        with:
                          path: docs-site/dist
                  deploy:
                    environment:
                      name: github-pages
                    steps:
                      - uses: actions/deploy-pages@v4
                """,
            )

            result = self.run_checker(root)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("deploy-wiring", result.stdout)

    def test_reports_pages_workflow_without_manual_safe_release_controls(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.write_workflows(
                Path(directory),
                deploy="""
                name: Deploy
                on:
                  push:
                permissions:
                  contents: write
                  pages: write
                  id-token: write
                jobs:
                  build:
                    steps:
                      - run: make check
                      - uses: actions/upload-pages-artifact@v3
                        with:
                          path: docs-site/dist
                  deploy:
                    needs: build
                    environment:
                      name: github-pages
                    steps:
                      - uses: actions/deploy-pages@v4
                """,
            )

            result = self.run_checker(root)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("deploy-safety", result.stdout)

    def test_reports_stale_pages_action_major(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.write_workflows(
                Path(directory),
                deploy=VALID_DEPLOY.replace(
                    "actions/upload-pages-artifact@v5",
                    "actions/upload-pages-artifact@v4",
                ),
            )

            result = self.run_checker(root)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("pages-action-version", result.stdout)

    def test_reports_nonexistent_setup_uv_major_tag(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.write_workflows(
                Path(directory),
                quality=VALID_QUALITY.replace(
                    "astral-sh/setup-uv@v8.3.2",
                    "astral-sh/setup-uv@v8",
                ),
            )

            result = self.run_checker(root)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("setup-uv-version", result.stdout)

    def test_requires_setup_uv_once_in_each_gate_job(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.write_workflows(
                Path(directory),
                quality=VALID_QUALITY.replace(
                    "- uses: astral-sh/setup-uv@v8.3.2",
                    "- uses: astral-sh/setup-uv@v8.3.2\n"
                    "      - uses: astral-sh/setup-uv@v8.3.2",
                ),
                deploy=VALID_DEPLOY.replace(
                    "      - uses: astral-sh/setup-uv@v8.3.2\n",
                    "",
                ),
            )

            result = self.run_checker(root)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("setup-uv-version", result.stdout)


if __name__ == "__main__":
    unittest.main()
