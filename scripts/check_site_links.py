#!/usr/bin/env python3
"""Check internal links in a built static site."""

from __future__ import annotations

import argparse
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
import sys


IGNORED_SCHEMES = {"data", "http", "https", "mailto", "tel", "javascript"}


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.targets: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "a" and attributes.get("href"):
            self.targets.append(attributes["href"] or "")
        if tag in {"img", "script", "source", "link"}:
            attribute = "href" if tag == "link" else "src"
            if attributes.get(attribute):
                self.targets.append(attributes[attribute] or "")


def _candidate_paths(site: Path, source: Path, target: str, base: str) -> list[Path]:
    parsed = urlsplit(target)
    if parsed.scheme.lower() in IGNORED_SCHEMES or parsed.netloc or not parsed.path:
        return []
    path = unquote(parsed.path)
    if path.startswith("#"):
        return []

    normalized_base = "/" + base.strip("/") if base.strip("/") else ""
    if path.startswith("/"):
        if normalized_base and path != normalized_base and not path.startswith(f"{normalized_base}/"):
            # 未包含 GitHub Pages base 的根绝对路径即使碰巧存在于 dist，部署后
            # 仍会失效。返回哨兵目标，让公共检查器把它报告为断链。
            return [site / "__base_path_mismatch__" / path.lstrip("/")]
        if normalized_base and path.startswith(normalized_base):
            path = path[len(normalized_base) :]
        relative = Path(path.lstrip("/"))
    else:
        relative = source.parent.relative_to(site) / path

    raw = (site / relative).resolve()
    try:
        raw.relative_to(site.resolve())
    except ValueError:
        return [raw]

    if path.endswith("/") or not raw.suffix:
        return [raw / "index.html", raw.with_suffix(".html")]
    return [raw]


def check_site(site: Path, base: str) -> list[tuple[Path, str]]:
    broken: list[tuple[Path, str]] = []
    resolved_site = site.resolve()
    for html in sorted(site.rglob("*.html")):
        parser = LinkParser()
        parser.feed(html.read_text(encoding="utf-8"))
        for target in parser.targets:
            candidates = _candidate_paths(site, html, target, base)
            if candidates and not any(
                candidate.exists() and candidate.resolve().is_relative_to(resolved_site)
                for candidate in candidates
            ):
                broken.append((html.relative_to(site), target))
    return broken


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, required=True)
    parser.add_argument("--base", default="/")
    args = parser.parse_args()

    site = args.site.resolve()
    if not site.is_dir():
        print(f"[broken-site] build directory does not exist: {site}")
        return 1
    broken = check_site(site, args.base)
    for source, target in broken:
        print(f"[broken-link] {source}: {target}")
    print(f"Site link validation: {len(broken)} broken link(s)")
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
