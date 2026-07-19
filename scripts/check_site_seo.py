#!/usr/bin/env python3
"""Validate SEO metadata and structured-data contracts in a built site."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from html.parser import HTMLParser
import json
from pathlib import Path
import sys
from typing import Any
from urllib.parse import urljoin, urlsplit
import xml.etree.ElementTree as ET


@dataclass(frozen=True)
class Finding:
    code: str
    source: Path
    detail: str


class SeoParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.has_html = False
        self.canonicals: list[str] = []
        self.meta: dict[str, list[str]] = {}
        self.structured_data: list[Any] = []
        self._json_ld_parts: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {name: value or "" for name, value in attrs}
        if tag == "html":
            self.has_html = True
        if tag == "link" and "canonical" in attributes.get("rel", "").split():
            self.canonicals.append(attributes.get("href", ""))
        if tag == "meta":
            key = attributes.get("name") or attributes.get("property")
            if key:
                self.meta.setdefault(key.lower(), []).append(
                    attributes.get("content", "")
                )
        if tag == "script" and attributes.get("type") == "application/ld+json":
            self._json_ld_parts = []

    def handle_data(self, data: str) -> None:
        if self._json_ld_parts is not None:
            self._json_ld_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag != "script" or self._json_ld_parts is None:
            return
        payload = "".join(self._json_ld_parts).strip()
        self._json_ld_parts = None
        if not payload:
            return
        try:
            self.structured_data.append(json.loads(payload))
        except json.JSONDecodeError:
            self.structured_data.append({"__invalid_json_ld__": payload})


def _parse_html(path: Path) -> SeoParser:
    parser = SeoParser()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser


def _expected_url(site_url: str, relative_path: Path) -> str:
    if relative_path == Path("index.html"):
        return site_url
    if relative_path.name == "index.html":
        return urljoin(site_url, relative_path.parent.as_posix().rstrip("/") + "/")
    return urljoin(site_url, relative_path.as_posix())


def _meta_value(parser: SeoParser, key: str) -> str | None:
    values = parser.meta.get(key.lower(), [])
    return values[0] if len(values) == 1 and values[0].strip() else None


def _structured_types(payload: Any) -> set[str]:
    types: set[str] = set()
    if isinstance(payload, dict):
        value = payload.get("@type")
        if isinstance(value, str):
            types.add(value)
        elif isinstance(value, list):
            types.update(item for item in value if isinstance(item, str))
        for nested in payload.values():
            types.update(_structured_types(nested))
    elif isinstance(payload, list):
        for nested in payload:
            types.update(_structured_types(nested))
    return types


def _has_search_action(payloads: list[Any]) -> bool:
    return any("SearchAction" in _structured_types(payload) for payload in payloads)


def _is_article(relative_path: Path) -> bool:
    parts = relative_path.parts
    return (
        len(parts) >= 3
        and parts[0] == "posts"
        and relative_path.name == "index.html"
    )


def check_seo(*, site: Path, site_url: str) -> list[Finding]:
    findings: list[Finding] = []
    normalized_site_url = site_url.rstrip("/") + "/"
    parsed_site_url = urlsplit(normalized_site_url)
    if not parsed_site_url.scheme or not parsed_site_url.netloc:
        return [Finding("site-url", Path("."), f"invalid site URL: {site_url!r}")]

    html_files = sorted(site.rglob("*.html"))
    if not html_files:
        return [Finding("build", Path("."), "no HTML files found")]

    noindex_paths = {Path("404.html"), Path("search/index.html")}
    indexable_urls: set[str] = set()
    noindex_urls: set[str] = set()
    required_meta = (
        "description",
        "og:title",
        "og:description",
        "og:url",
        "og:type",
        "og:image",
        "twitter:card",
        "twitter:title",
        "twitter:description",
        "twitter:image",
    )

    for html in html_files:
        relative = html.relative_to(site)
        parser = _parse_html(html)
        if not parser.has_html:
            continue
        robots = (_meta_value(parser, "robots") or "").lower()

        if relative in noindex_paths:
            if "noindex" not in robots or "follow" not in robots:
                findings.append(
                    Finding(
                        "robots",
                        relative,
                        "expected a single noindex, follow robots directive",
                    )
                )
            if relative == Path("404.html"):
                noindex_urls.add(_expected_url(normalized_site_url, relative))
                continue
        elif "noindex" in robots or "index" not in robots:
            findings.append(
                Finding(
                    "robots",
                    relative,
                    "indexable page must declare index, follow",
                )
            )

        expected_canonical = _expected_url(normalized_site_url, relative)
        if relative in noindex_paths:
            noindex_urls.add(expected_canonical)
        else:
            indexable_urls.add(expected_canonical)
        if parser.canonicals != [expected_canonical]:
            findings.append(
                Finding(
                    "canonical",
                    relative,
                    f"expected canonical {expected_canonical!r}, got {parser.canonicals!r}",
                )
            )

        for key in required_meta:
            if _meta_value(parser, key) is None:
                findings.append(
                    Finding("meta", relative, f"missing or duplicate {key!r} metadata")
                )

        expected_og_type = "article" if _is_article(relative) else "website"
        actual_og_type = _meta_value(parser, "og:type")
        if actual_og_type and actual_og_type != expected_og_type:
            findings.append(
                Finding(
                    "meta",
                    relative,
                    f"expected og:type={expected_og_type!r}, got {actual_og_type!r}",
                )
            )

        if _meta_value(parser, "og:url") not in {None, expected_canonical}:
            findings.append(
                Finding("meta", relative, "og:url must match the canonical URL")
            )

        serialized_data = json.dumps(parser.structured_data, ensure_ascii=False)
        structured_types = _structured_types(parser.structured_data)
        expected_structured_type = "BlogPosting" if _is_article(relative) else "WebPage"
        if (
            "WebSite" not in structured_types
            or expected_structured_type not in structured_types
            or "__invalid_json_ld__" in serialized_data
            or "undefined" in serialized_data
        ):
            findings.append(
                Finding(
                    "structured-data",
                    relative,
                    f"expected WebSite + {expected_structured_type} valid JSON-LD",
                )
            )
        if relative == Path("index.html") and not _has_search_action(
            parser.structured_data
        ):
            findings.append(
                Finding(
                    "structured-data",
                    relative,
                    "homepage WebSite data must expose a SearchAction",
                )
            )

    robots_path = site / "robots.txt"
    expected_sitemap = urljoin(normalized_site_url, "sitemap-index.xml")
    if not robots_path.is_file():
        findings.append(Finding("robots-sitemap", Path("robots.txt"), "missing"))
    else:
        robots_text = robots_path.read_text(encoding="utf-8")
        if f"Sitemap: {expected_sitemap}" not in robots_text:
            findings.append(
                Finding(
                    "robots-sitemap",
                    Path("robots.txt"),
                    f"expected Sitemap: {expected_sitemap}",
                )
            )

    sitemap_index = site / "sitemap-index.xml"
    sitemap_urls: set[str] = set()
    if not sitemap_index.is_file():
        findings.append(Finding("sitemap", Path("sitemap-index.xml"), "missing"))
    else:
        try:
            sitemap_root = ET.parse(sitemap_index).getroot()
            sitemap_locations = [
                (node.text or "").strip()
                for node in sitemap_root.findall(".//{*}loc")
                if (node.text or "").strip()
            ]
        except ET.ParseError as error:
            findings.append(
                Finding("sitemap", Path("sitemap-index.xml"), f"invalid XML: {error}")
            )
            sitemap_locations = []

        site_parts = urlsplit(normalized_site_url)
        site_base_path = site_parts.path.rstrip("/") + "/"
        for location in sitemap_locations:
            location_parts = urlsplit(location)
            if (
                (location_parts.scheme, location_parts.netloc)
                != (site_parts.scheme, site_parts.netloc)
                or not location_parts.path.startswith(site_base_path)
            ):
                findings.append(
                    Finding(
                        "sitemap",
                        Path("sitemap-index.xml"),
                        f"sitemap location is outside the site: {location}",
                    )
                )
                continue
            relative_sitemap = location_parts.path[len(site_base_path) :]
            sitemap_file = site / relative_sitemap
            if not sitemap_file.is_file():
                findings.append(
                    Finding("sitemap", Path(relative_sitemap), "referenced file is missing")
                )
                continue
            try:
                child_root = ET.parse(sitemap_file).getroot()
                sitemap_urls.update(
                    (node.text or "").strip()
                    for node in child_root.findall(".//{*}loc")
                    if (node.text or "").strip()
                )
            except ET.ParseError as error:
                findings.append(
                    Finding(
                        "sitemap",
                        Path(relative_sitemap),
                        f"invalid XML: {error}",
                    )
                )

    for url in sorted(noindex_urls & sitemap_urls):
        findings.append(
            Finding("sitemap", Path("sitemap-index.xml"), f"noindex URL listed: {url}")
        )
    for url in sorted(indexable_urls - sitemap_urls):
        findings.append(
            Finding("sitemap", Path("sitemap-index.xml"), f"indexable URL missing: {url}")
        )

    llms_path = site / "llms.txt"
    if not llms_path.is_file():
        findings.append(Finding("llms", Path("llms.txt"), "missing"))
    else:
        llms_text = llms_path.read_text(encoding="utf-8")
        required_llms_links = (normalized_site_url, expected_sitemap)
        for link in required_llms_links:
            if link not in llms_text:
                findings.append(
                    Finding("llms", Path("llms.txt"), f"missing discovery link: {link}")
                )

    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, required=True)
    parser.add_argument("--site-url", required=True)
    args = parser.parse_args()

    site = args.site.resolve()
    if not site.is_dir():
        print(f"[seo:build] build directory does not exist: {site}")
        return 1

    findings = check_seo(site=site, site_url=args.site_url)
    for finding in findings:
        print(f"[seo:{finding.code}] {finding.source}: {finding.detail}")
    print(f"SEO contracts: {len(findings)} failure(s)")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
