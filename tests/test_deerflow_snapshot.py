from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts.fetch_deerflow_snapshot import (
    DEERFLOW_COMMIT,
    SNAPSHOT_PATHS,
    fetch_snapshot,
    verify_snapshot,
)


def _git_blob_sha(content: bytes) -> str:
    header = f"blob {len(content)}\0".encode()
    return hashlib.sha1(header + content).hexdigest()


class DeerFlowSnapshotTests(unittest.TestCase):
    def test_fetches_pinned_files_and_verifies_blob_hashes(self) -> None:
        def fake_fetch(path: str, commit: str) -> dict[str, object]:
            self.assertEqual(commit, DEERFLOW_COMMIT)
            content = f"fixed:{path}\n".encode()
            return {
                "type": "file",
                "path": path,
                "sha": _git_blob_sha(content),
                "content": base64.b64encode(content).decode(),
                "encoding": "base64",
            }

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            fetch_snapshot(root, fetch_json=fake_fetch)

            self.assertEqual(
                (root / "DEERFLOW_COMMIT").read_text(encoding="utf-8").strip(),
                DEERFLOW_COMMIT,
            )
            manifest = json.loads(
                (root / ".deerflow-snapshot.json").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["commit"], DEERFLOW_COMMIT)
            self.assertEqual(set(manifest["files"]), set(SNAPSHOT_PATHS))
            verify_snapshot(root)

            changed = root / SNAPSHOT_PATHS[0]
            changed.write_text("mutated", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "blob hash"):
                verify_snapshot(root)


if __name__ == "__main__":
    unittest.main()
