#!/usr/bin/env python3
"""Fetch the small, pinned DeerFlow source slice used by the reading guide."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
from typing import Callable
from urllib.parse import quote
from urllib.request import Request, urlopen


DEERFLOW_COMMIT = "4af617835805dd7cd78162ebed02fd6b782ea8bf"
GITHUB_REPOSITORY = "bytedance/deer-flow"
SNAPSHOT_PATHS = (
    "backend/langgraph.json",
    "backend/packages/harness/deerflow/agents/lead_agent/agent.py",
    "backend/packages/harness/deerflow/agents/thread_state.py",
    "backend/packages/harness/deerflow/agents/middlewares/__init__.py",
    "backend/packages/harness/deerflow/tools/builtins/task_tool.py",
    "backend/packages/harness/deerflow/subagents/executor.py",
    "backend/app/gateway/app.py",
    "backend/app/gateway/routers/thread_runs.py",
    "backend/app/gateway/routers/runs.py",
    "backend/packages/harness/deerflow/runtime/runs/manager.py",
    "backend/packages/harness/deerflow/runtime/runs/worker.py",
    "backend/packages/harness/deerflow/runtime/journal.py",
    "backend/packages/harness/deerflow/runtime/stream_bridge/base.py",
)
MANIFEST_NAME = ".deerflow-snapshot.json"
FetchJson = Callable[[str, str], dict[str, object]]


def _git_blob_sha(content: bytes) -> str:
    header = f"blob {len(content)}\0".encode()
    return hashlib.sha1(header + content).hexdigest()


def fetch_github_json(path: str, commit: str) -> dict[str, object]:
    """Read one file through GitHub's Contents API at an exact commit."""

    encoded_path = quote(path, safe="/")
    url = (
        f"https://api.github.com/repos/{GITHUB_REPOSITORY}/contents/"
        f"{encoded_path}?ref={commit}"
    )
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "langchain-logbook-course",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    with urlopen(Request(url, headers=headers), timeout=30) as response:
        return json.load(response)


def _decode_file(payload: dict[str, object], expected_path: str) -> tuple[bytes, str]:
    if payload.get("type") != "file" or payload.get("path") != expected_path:
        raise ValueError(f"GitHub API 没有返回预期文件: {expected_path}")
    if payload.get("encoding") != "base64":
        raise ValueError(f"GitHub API 返回了未知编码: {expected_path}")
    encoded = payload.get("content")
    blob_sha = payload.get("sha")
    if not isinstance(encoded, str) or not isinstance(blob_sha, str):
        raise ValueError(f"GitHub API 缺少文件内容或 blob sha: {expected_path}")
    content = base64.b64decode(encoded)
    if _git_blob_sha(content) != blob_sha:
        raise ValueError(f"下载内容与 GitHub blob hash 不一致: {expected_path}")
    return content, blob_sha


def fetch_snapshot(
    output: Path,
    *,
    commit: str = DEERFLOW_COMMIT,
    fetch_json: FetchJson = fetch_github_json,
) -> Path:
    """Download only the files needed by the four evidence trails."""

    if commit != DEERFLOW_COMMIT:
        raise ValueError(f"课程只接受固定提交 {DEERFLOW_COMMIT}")
    output.mkdir(parents=True, exist_ok=True)
    files: dict[str, dict[str, object]] = {}
    for path in SNAPSHOT_PATHS:
        relative = Path(path)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"非法快照路径: {path}")
        content, blob_sha = _decode_file(fetch_json(path, commit), path)
        destination = output / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        files[path] = {"blob_sha": blob_sha, "bytes": len(content)}
        print(f"fetched {path}")

    (output / "DEERFLOW_COMMIT").write_text(f"{commit}\n", encoding="utf-8")
    manifest = {
        "repository": GITHUB_REPOSITORY,
        "commit": commit,
        "files": files,
    }
    (output / MANIFEST_NAME).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    verify_snapshot(output)
    return output


def verify_snapshot(output: Path) -> None:
    """Reject a missing, mixed-version, or locally modified reading snapshot."""

    manifest_path = output / MANIFEST_NAME
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("repository") != GITHUB_REPOSITORY:
        raise ValueError("快照 repository 与课程不一致")
    if manifest.get("commit") != DEERFLOW_COMMIT:
        raise ValueError("快照 commit 与课程不一致")
    files = manifest.get("files")
    if not isinstance(files, dict) or set(files) != set(SNAPSHOT_PATHS):
        raise ValueError("快照文件集合与课程不一致")
    for path in SNAPSHOT_PATHS:
        metadata = files[path]
        if not isinstance(metadata, dict):
            raise ValueError(f"快照 manifest 条目无效: {path}")
        content = (output / path).read_bytes()
        if _git_blob_sha(content) != metadata.get("blob_sha"):
            raise ValueError(f"快照文件 blob hash 校验失败: {path}")
    commit_file = (output / "DEERFLOW_COMMIT").read_text(encoding="utf-8").strip()
    if commit_file != DEERFLOW_COMMIT:
        raise ValueError("DEERFLOW_COMMIT 文件与课程不一致")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("/tmp/deerflow-course-snapshot"),
        help="快照目录（默认：/tmp/deerflow-course-snapshot）",
    )
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    if args.verify_only:
        verify_snapshot(args.output)
        print(f"verified {DEERFLOW_COMMIT} in {args.output}")
    else:
        fetch_snapshot(args.output)
        print(f"ready {DEERFLOW_COMMIT} in {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
