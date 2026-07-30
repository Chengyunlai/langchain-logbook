#!/usr/bin/env python3
"""Validate local release contracts in a built documentation site."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
import sys
from urllib.parse import unquote, urlsplit


@dataclass(frozen=True)
class Finding:
    code: str
    source: Path
    detail: str


class ContractParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []
        self.home_urls: list[str] = []
        self.pagefind_bundle_paths: list[str] = []
        self.primary_start_hrefs: list[str] = []
        self.notebook_downloads: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        for name, value in attrs:
            if tag == "a" and name == "href":
                self.hrefs.append(value or "")
            if name == "data-home-url":
                self.home_urls.append(value or "")
            if name == "data-bundle-path":
                self.pagefind_bundle_paths.append(value or "")
        if tag == "a" and "data-primary-start" in attributes:
            self.primary_start_hrefs.append(attributes.get("href") or "")
        if tag == "a" and "data-course-notebook" in attributes:
            self.notebook_downloads.append(
                (attributes.get("href") or "", attributes.get("download") or "")
            )


FRIENDLY_NOTEBOOK_FILENAMES = {
    "05_agent_middleware": "05_Context_State_Store.ipynb",
    "06_observability_persistence": "06_Agent_Middleware.ipynb",
    "09_multi_agent_eval": "09_Checkpoint_Recovery.ipynb",
}


def _normalized_base(base: str) -> str:
    stripped = base.strip("/")
    return f"/{stripped}" if stripped else "/"


def _parse_html(path: Path) -> ContractParser:
    parser = ContractParser()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser


def _repository_source(
    href: str,
    *,
    repository_url: str,
) -> str | None:
    normalized_repository = repository_url.rstrip("/")
    parsed = urlsplit(href)
    parsed_repository = urlsplit(normalized_repository)
    if (parsed.scheme, parsed.netloc) != (
        parsed_repository.scheme,
        parsed_repository.netloc,
    ):
        return None

    repository_path = parsed_repository.path.rstrip("/")
    blob_prefix = f"{repository_path}/blob/"
    if not parsed.path.startswith(blob_prefix):
        return None
    branch_and_source = unquote(parsed.path[len(blob_prefix) :])
    _branch, separator, source = branch_and_source.partition("/")
    return source if separator and source else ""


def _source_exists(repo_root: Path, source: str) -> bool:
    candidate = (repo_root / source).resolve()
    try:
        candidate.relative_to(repo_root.resolve())
    except ValueError:
        return False
    return candidate.is_file()


def check_contracts(
    *,
    site: Path,
    base: str,
    repo_root: Path,
    repository_url: str,
) -> list[Finding]:
    findings: list[Finding] = []
    normalized_base = _normalized_base(base)

    index = site / "index.html"
    search = site / "search" / "index.html"
    if not index.is_file():
        findings.append(Finding("home-base", Path("index.html"), "missing home page"))
    else:
        index_contract = _parse_html(index)
        home_urls = index_contract.home_urls
        if home_urls != [normalized_base]:
            findings.append(
                Finding(
                    "home-base",
                    index.relative_to(site),
                    f"expected data-home-url={normalized_base!r}, got {home_urls!r}",
                )
            )
        expected_start = f"{normalized_base}/posts/orientation/"
        if normalized_base == "/":
            expected_start = "/posts/orientation/"
        if index_contract.primary_start_hrefs != [expected_start]:
            findings.append(
                Finding(
                    "primary-start",
                    index.relative_to(site),
                    "expected one explicit beginner orientation start link, got "
                    f"{index_contract.primary_start_hrefs!r}",
                )
            )

    expected_bundle = (
        "/pagefind/"
        if normalized_base == "/"
        else f"{normalized_base}/pagefind/"
    )
    if not search.is_file():
        findings.append(
            Finding("pagefind-base", Path("search/index.html"), "missing search page")
        )
    else:
        bundle_paths = _parse_html(search).pagefind_bundle_paths
        if bundle_paths != [expected_bundle]:
            findings.append(
                Finding(
                    "pagefind-base",
                    search.relative_to(site),
                    f"expected data-bundle-path={expected_bundle!r}, got {bundle_paths!r}",
                )
            )

    for html in sorted(site.rglob("*.html")):
        html_text = html.read_text(encoding="utf-8")
        if any(
            marker in html_text
            for marker in (
                "<!-- lesson-lab:",
                "<!-- /lesson-lab -->",
            )
        ):
            findings.append(
                Finding(
                    "internal-lesson-marker",
                    html.relative_to(site),
                    "internal lesson-lab metadata must be removed before publication",
                )
            )
        for href in _parse_html(html).hrefs:
            source = _repository_source(href, repository_url=repository_url)
            if source is not None and not _source_exists(repo_root, source):
                findings.append(
                    Finding(
                        "repository-source",
                        html.relative_to(site),
                        f"{href} does not map to a local repository file",
                    )
                )
        if html.parent.parent.name == "posts" and html.parent.name[:2].isdigit():
            notebook_downloads = _parse_html(html).notebook_downloads
            if len(notebook_downloads) != 1:
                findings.append(
                    Finding(
                        "course-notebook",
                        html.relative_to(site),
                        "expected one Notebook download link, got "
                        f"{notebook_downloads!r}",
                    )
                )
            else:
                notebook_href, download_filename = notebook_downloads[0]
                notebook_url = urlsplit(notebook_href).path
                notebook_relative = notebook_url.removeprefix(f"{normalized_base}/")
                if normalized_base == "/":
                    notebook_relative = notebook_url.removeprefix("/")
                if not (site / notebook_relative).is_file():
                    findings.append(
                        Finding(
                            "course-notebook",
                            html.relative_to(site),
                            f"Notebook target does not exist: {notebook_href}",
                        )
                    )
                expected_filename = FRIENDLY_NOTEBOOK_FILENAMES.get(html.parent.name)
                if expected_filename is not None and (
                    Path(notebook_url).name != expected_filename
                    or download_filename != expected_filename
                ):
                    findings.append(
                        Finding(
                            "course-notebook-name",
                            html.relative_to(site),
                            f"expected href and download name {expected_filename!r}, "
                            f"got href={notebook_href!r}, download={download_filename!r}",
                        )
                    )
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, required=True)
    parser.add_argument("--base", default="/")
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--repository-url", required=True)
    args = parser.parse_args()

    site = args.site.resolve()
    repo_root = args.repo_root.resolve()
    if not site.is_dir():
        print(f"[site-contract:build] build directory does not exist: {site}")
        return 1
    if not repo_root.is_dir():
        print(f"[site-contract:repository] repository does not exist: {repo_root}")
        return 1

    findings = check_contracts(
        site=site,
        base=args.base,
        repo_root=repo_root,
        repository_url=args.repository_url,
    )
    for finding in findings:
        print(f"[site-contract:{finding.code}] {finding.source}: {finding.detail}")
    print(f"Site release contracts: {len(findings)} failure(s)")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
