from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TUTORIAL_CHECKER = PROJECT_ROOT / "scripts" / "validate_tutorials.py"
LINK_CHECKER = PROJECT_ROOT / "scripts" / "check_site_links.py"
SITE_CONTRACT_CHECKER = PROJECT_ROOT / "scripts" / "check_site_contracts.py"
SEO_CHECKER = PROJECT_ROOT / "scripts" / "check_site_seo.py"


def _notebook(
    *,
    code: str = "value = 1",
    execution_count: int | None = 1,
    outputs: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "cells": [
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": ["# 第 01 章：Demo"],
            },
            {
                "cell_type": "code",
                "execution_count": execution_count,
                "metadata": {},
                "outputs": outputs or [],
                "source": [code],
            },
        ],
        "metadata": {},
        "nbformat": 4,
        "nbformat_minor": 5,
    }


class TutorialCheckerCliTests(unittest.TestCase):
    def run_checker(self, root: Path, *extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(TUTORIAL_CHECKER),
                "--root",
                str(root),
                "--baseline",
                str(root / "quality-baseline.json"),
                *extra,
            ],
            check=False,
            capture_output=True,
            text=True,
        )

    def write_pair(self, root: Path, *, markdown_code: str, notebook: dict[str, object] | None = None) -> None:
        tutorials = root / "tutorials"
        tutorials.mkdir()
        (tutorials / "01_Demo.md").write_text(
            "# 第 01 章：Demo\n\n```python\n" + markdown_code + "\n```\n",
            encoding="utf-8",
        )
        (tutorials / "01_Demo.ipynb").write_text(
            json.dumps(notebook or _notebook(), ensure_ascii=False),
            encoding="utf-8",
        )
        (root / "quality-baseline.json").write_text('{"issues": []}\n', encoding="utf-8")

    def test_reports_invalid_markdown_python(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_pair(root, markdown_code="value =")

            result = self.run_checker(root)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("markdown-syntax", result.stdout)

    def test_reports_v2_stream_tuple_unpacking(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_pair(
                root,
                markdown_code=(
                    'async for chunk, metadata in agent.astream({}, version="v2"):\n'
                    "    print(chunk, metadata)"
                ),
            )

            result = self.run_checker(root)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("stream-v2-tuple", result.stdout)

    def test_reports_stored_notebook_errors(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_pair(
                root,
                markdown_code="value = 1",
                notebook=_notebook(
                    outputs=[
                        {
                            "output_type": "error",
                            "ename": "RuntimeError",
                            "evalue": "boom",
                            "traceback": [],
                        }
                    ]
                ),
            )

            result = self.run_checker(root)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("notebook-error-output", result.stdout)

    def test_reports_unavailable_markdown_import(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_pair(root, markdown_code="from package_that_cannot_exist import Widget")

            result = self.run_checker(root)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("import-unavailable", result.stdout)

    def test_reports_markdown_notebook_code_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_pair(
                root,
                markdown_code="value = 1",
                notebook=_notebook(code="value = 2"),
            )

            result = self.run_checker(root)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("code-content-drift", result.stdout)

    def test_sync_markers_compare_only_executable_lesson_contracts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            notebook = _notebook(code="value = 1")
            notebook["cells"][1]["metadata"] = {"langchain_logbook_sync": "demo-value"}
            self.write_pair(root, markdown_code="value = 999", notebook=notebook)
            (root / "tutorials" / "01_Demo.md").write_text(
                "# 第 01 章：Demo\n\n"
                "```python\nvalue = 999\n```\n\n"
                "```python sync=demo-value\nvalue = 1\n```\n",
                encoding="utf-8",
            )

            result = self.run_checker(root)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_changed_sync_marker_contract_is_reported_as_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            notebook = _notebook(code="value = 2")
            notebook["cells"][1]["metadata"] = {"langchain_logbook_sync": "demo-value"}
            self.write_pair(root, markdown_code="value = 1", notebook=notebook)
            (root / "tutorials" / "01_Demo.md").write_text(
                "# 第 01 章：Demo\n\n"
                "```python sync=demo-value\nvalue = 1\n```\n",
                encoding="utf-8",
            )

            result = self.run_checker(root)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("code-content-drift", result.stdout)

    def test_reports_missing_required_lesson_experiment(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            notebook = _notebook(code="value = 1")
            notebook["cells"][1]["metadata"] = {"langchain_logbook_sync": "demo-value"}
            self.write_pair(root, markdown_code="value = 1", notebook=notebook)
            (root / "tutorials" / "01_Demo.md").write_text(
                "# 第 01 章：Demo\n\n"
                "```python sync=demo-value\nvalue = 1\n```\n",
                encoding="utf-8",
            )
            quality = root / "quality"
            quality.mkdir()
            (quality / "lesson-contracts.json").write_text(
                json.dumps(
                    {
                        "version": 1,
                        "chapters": {
                            "01_Demo": {
                                "required_sync_ids": ["demo-value", "demo-failure"]
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )

            result = self.run_checker(root)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("missing-required-experiment", result.stdout)
            self.assertIn("demo-failure", result.stdout)

    def test_reports_missing_notebook_pair(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tutorials = root / "tutorials"
            tutorials.mkdir()
            (tutorials / "01_Demo.md").write_text(
                "# 第 01 章：Demo\n\n```python\nvalue = 1\n```\n",
                encoding="utf-8",
            )
            (root / "quality-baseline.json").write_text('{"issues": []}\n', encoding="utf-8")

            result = self.run_checker(root)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("missing-notebook", result.stdout)

    def test_baseline_accepts_known_debt_and_rejects_stale_entries(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_pair(root, markdown_code="value =")

            write_result = self.run_checker(root, "--write-baseline")
            known_result = self.run_checker(root)
            (root / "tutorials" / "01_Demo.md").write_text(
                "# 第 01 章：Demo\n\n```python\nvalue = 1\n```\n",
                encoding="utf-8",
            )
            stale_result = self.run_checker(root)

            self.assertEqual(write_result.returncode, 0, write_result.stdout + write_result.stderr)
            self.assertEqual(known_result.returncode, 0, known_result.stdout + known_result.stderr)
            self.assertIn("known", known_result.stdout.lower())
            self.assertEqual(stale_result.returncode, 1, stale_result.stdout + stale_result.stderr)
            self.assertIn("stale", stale_result.stdout.lower())


class SiteLinkCheckerCliTests(unittest.TestCase):
    def run_checker(self, site: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(LINK_CHECKER),
                "--site",
                str(site),
                "--base",
                "/langchain-logbook",
            ],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_accepts_existing_base_path_page(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory)
            (site / "posts" / "one").mkdir(parents=True)
            (site / "index.html").write_text(
                '<a href="/langchain-logbook/posts/one/">One</a>',
                encoding="utf-8",
            )
            (site / "posts" / "one" / "index.html").write_text("ok", encoding="utf-8")

            result = self.run_checker(site)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_reports_missing_internal_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory)
            (site / "index.html").write_text(
                '<a href="/langchain-logbook/posts/missing/">Missing</a>',
                encoding="utf-8",
            )

            result = self.run_checker(site)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("broken-link", result.stdout)

    def test_reports_absolute_internal_link_outside_configured_base(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory)
            (site / "posts" / "one").mkdir(parents=True)
            (site / "posts" / "one" / "index.html").write_text("ok", encoding="utf-8")
            (site / "index.html").write_text(
                '<a href="/posts/one/">Missing deployment base</a>',
                encoding="utf-8",
            )

            result = self.run_checker(site)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("broken-link", result.stdout)

    def test_reports_relative_link_that_escapes_site_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            site = workspace / "dist"
            site.mkdir()
            (workspace / "outside.html").write_text("exists outside dist", encoding="utf-8")
            (site / "index.html").write_text(
                '<a href="../outside.html">Escape build root</a>',
                encoding="utf-8",
            )

            result = self.run_checker(site)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("broken-link", result.stdout)


class SiteReleaseContractCliTests(unittest.TestCase):
    repository_url = "https://github.com/ExampleOwner/langchain-logbook"

    def write_site(
        self,
        workspace: Path,
        *,
        source_href: str | None = None,
        home_url: str = "/langchain-logbook",
        bundle_path: str = "/langchain-logbook/pagefind/",
    ) -> tuple[Path, Path]:
        repository = workspace / "repository"
        site = workspace / "dist"
        (repository / "mini_deerflow").mkdir(parents=True)
        (repository / "mini_deerflow" / "CAPSTONE.md").write_text(
            "# Capstone\n",
            encoding="utf-8",
        )
        (site / "search").mkdir(parents=True)
        href = source_href or (
            f"{self.repository_url}/blob/main/mini_deerflow/CAPSTONE.md"
        )
        (site / "index.html").write_text(
            f'<main data-home-url="{home_url}"></main>'
            f'<a href="{href}">Edit</a>',
            encoding="utf-8",
        )
        (site / "search" / "index.html").write_text(
            '<div id="pagefind-search" '
            f'data-bundle-path="{bundle_path}"></div>',
            encoding="utf-8",
        )
        return site, repository

    def run_checker(
        self,
        site: Path,
        repository: Path,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SITE_CONTRACT_CHECKER),
                "--site",
                str(site),
                "--base",
                "/langchain-logbook",
                "--repo-root",
                str(repository),
                "--repository-url",
                self.repository_url,
            ],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_accepts_valid_local_release_contracts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            site, repository = self.write_site(Path(directory))

            result = self.run_checker(site, repository)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_reports_repository_blob_link_without_local_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            site, repository = self.write_site(
                Path(directory),
                source_href=(
                    f"{self.repository_url}/blob/main/src/data/blog/CAPSTONE.md"
                ),
            )

            result = self.run_checker(site, repository)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("repository-source", result.stdout)

    def test_reports_home_return_url_outside_deployment_base(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            site, repository = self.write_site(Path(directory), home_url="/")

            result = self.run_checker(site, repository)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("home-base", result.stdout)

    def test_reports_duplicate_home_return_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            site, repository = self.write_site(Path(directory))
            (site / "index.html").write_text(
                '<main data-home-url="/wrong" '
                'data-home-url="/langchain-logbook"></main>'
                f'<a href="{self.repository_url}/blob/main/'
                'mini_deerflow/CAPSTONE.md">Edit</a>',
                encoding="utf-8",
            )

            result = self.run_checker(site, repository)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("home-base", result.stdout)

    def test_reports_pagefind_bundle_outside_deployment_base(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            site, repository = self.write_site(
                Path(directory),
                bundle_path="/pagefind/",
            )

            result = self.run_checker(site, repository)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("pagefind-base", result.stdout)


class SiteSeoCliTests(unittest.TestCase):
    site_url = "https://example.com/langchain-logbook/"

    def run_checker(self, site: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SEO_CHECKER),
                "--site",
                str(site),
                "--site-url",
                self.site_url,
            ],
            check=False,
            capture_output=True,
            text=True,
        )

    def page(
        self,
        *,
        canonical: str,
        page_type: str,
        robots: str = "index, follow",
    ) -> str:
        structured_type = "BlogPosting" if page_type == "article" else "WebPage"
        structured_data = {
            "@context": "https://schema.org",
            "@graph": [
                {
                    "@type": "WebSite",
                    "url": self.site_url,
                    "potentialAction": {
                        "@type": "SearchAction",
                        "target": self.site_url + "search/?q={search_term_string}",
                        "query-input": "required name=search_term_string",
                    },
                },
                {"@type": structured_type, "url": canonical},
            ],
        }
        return (
            "<html><head>"
            f'<link rel="canonical" href="{canonical}">'
            '<meta name="description" content="Agent engineering course">'
            f'<meta name="robots" content="{robots}">'
            '<meta property="og:title" content="LangChain Logbook">'
            '<meta property="og:description" content="Agent engineering course">'
            f'<meta property="og:url" content="{canonical}">'
            f'<meta property="og:type" content="{page_type}">'
            '<meta property="og:image" content="https://example.com/og.png">'
            '<meta name="twitter:card" content="summary_large_image">'
            '<meta name="twitter:title" content="LangChain Logbook">'
            '<meta name="twitter:description" content="Agent engineering course">'
            '<meta name="twitter:image" content="https://example.com/og.png">'
            '<script type="application/ld+json">'
            + json.dumps(structured_data)
            + "</script></head><body></body></html>"
        )

    def write_valid_site(self, root: Path) -> Path:
        site = root / "dist"
        article = site / "posts" / "introduction"
        search = site / "search"
        article.mkdir(parents=True)
        search.mkdir(parents=True)
        (site / "index.html").write_text(
            self.page(canonical=self.site_url, page_type="website"),
            encoding="utf-8",
        )
        (article / "index.html").write_text(
            self.page(
                canonical=self.site_url + "posts/introduction/",
                page_type="article",
            ),
            encoding="utf-8",
        )
        (search / "index.html").write_text(
            self.page(
                canonical=self.site_url + "search/",
                page_type="website",
                robots="noindex, follow",
            ),
            encoding="utf-8",
        )
        (site / "404.html").write_text(
            '<html><head><meta name="robots" content="noindex, follow"></head></html>',
            encoding="utf-8",
        )
        (site / "robots.txt").write_text(
            "User-agent: *\nAllow: /\n\n"
            f"Sitemap: {self.site_url}sitemap-index.xml\n",
            encoding="utf-8",
        )
        (site / "sitemap-index.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            f"<sitemap><loc>{self.site_url}sitemap-0.xml</loc></sitemap>"
            "</sitemapindex>",
            encoding="utf-8",
        )
        (site / "sitemap-0.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            f"<url><loc>{self.site_url}</loc></url>"
            f"<url><loc>{self.site_url}posts/introduction/</loc></url>"
            "</urlset>",
            encoding="utf-8",
        )
        (site / "llms.txt").write_text(
            f"# LangChain Logbook\n\n- {self.site_url}\n"
            f"- {self.site_url}sitemap-index.xml\n",
            encoding="utf-8",
        )
        return site

    def test_accepts_complete_seo_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            site = self.write_valid_site(Path(directory))

            result = self.run_checker(site)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_reports_missing_canonical(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            site = self.write_valid_site(Path(directory))
            index = site / "index.html"
            index.write_text(
                index.read_text(encoding="utf-8").replace(
                    f'<link rel="canonical" href="{self.site_url}">', ""
                ),
                encoding="utf-8",
            )

            result = self.run_checker(site)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("seo:canonical", result.stdout)

    def test_reports_article_without_blogposting_data(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            site = self.write_valid_site(Path(directory))
            article = site / "posts" / "introduction" / "index.html"
            article.write_text(
                article.read_text(encoding="utf-8").replace(
                    '"@type": "BlogPosting"', '"@type": "WebPage"'
                ),
                encoding="utf-8",
            )

            result = self.run_checker(site)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("seo:structured-data", result.stdout)

    def test_reports_indexable_search_and_404_pages(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            site = self.write_valid_site(Path(directory))
            search = site / "search" / "index.html"
            search.write_text(
                search.read_text(encoding="utf-8").replace(
                    "noindex, follow", "index, follow"
                ),
                encoding="utf-8",
            )
            (site / "404.html").write_text(
                '<html><head><meta name="robots" content="index, follow"></head></html>',
                encoding="utf-8",
            )

            result = self.run_checker(site)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("seo:robots", result.stdout)

    def test_reports_wrong_robots_sitemap(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            site = self.write_valid_site(Path(directory))
            (site / "robots.txt").write_text(
                "User-agent: *\nAllow: /\n\nSitemap: https://wrong.example/sitemap.xml\n",
                encoding="utf-8",
            )

            result = self.run_checker(site)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("seo:robots-sitemap", result.stdout)

    def test_reports_noindex_page_in_sitemap(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            site = self.write_valid_site(Path(directory))
            sitemap = site / "sitemap-0.xml"
            sitemap.write_text(
                sitemap.read_text(encoding="utf-8").replace(
                    "</urlset>",
                    f"<url><loc>{self.site_url}search/</loc></url></urlset>",
                ),
                encoding="utf-8",
            )

            result = self.run_checker(site)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("seo:sitemap", result.stdout)

    def test_reports_404_page_in_sitemap(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            site = self.write_valid_site(Path(directory))
            sitemap = site / "sitemap-0.xml"
            sitemap.write_text(
                sitemap.read_text(encoding="utf-8").replace(
                    "</urlset>",
                    f"<url><loc>{self.site_url}404.html</loc></url></urlset>",
                ),
                encoding="utf-8",
            )

            result = self.run_checker(site)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("seo:sitemap", result.stdout)

    def test_reports_missing_llms_discovery_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            site = self.write_valid_site(Path(directory))
            (site / "llms.txt").unlink()

            result = self.run_checker(site)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("seo:llms", result.stdout)

if __name__ == "__main__":
    unittest.main()
