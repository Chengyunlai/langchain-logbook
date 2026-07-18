"""Protect the package regions cited by the executable lessons."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

EXPECTED_REGIONS = {
    "mini_deerflow/models.py": ["tutorial:01-model-factory"],
    "mini_deerflow/streaming.py": ["tutorial:01-stream-normalizer"],
    "mini_deerflow/schemas.py": ["tutorial:02-domain-schemas"],
    "mini_deerflow/knowledge/indexer.py": ["tutorial:03-vector-index"],
    "mini_deerflow/knowledge/evaluation.py": ["tutorial:03-retrieval-eval"],
    "mini_deerflow/tools/__init__.py": ["tutorial:04-tool-registry"],
    "mini_deerflow/agents/lead_agent.py": ["tutorial:04-lead-agent-factory"],
    "mini_deerflow/context.py": ["tutorial:05-runtime-context"],
    "mini_deerflow/state.py": ["tutorial:05-thread-state"],
    "mini_deerflow/store.py": ["tutorial:05-store-policy"],
    "mini_deerflow/middleware/__init__.py": [
        "tutorial:06-lifecycle-trace-middleware",
        "tutorial:06-context-prompt-middleware",
        "tutorial:06-model-router-middleware",
        "tutorial:06-tool-error-middleware",
        "tutorial:06-tool-permission-middleware",
        "tutorial:06-governance-chain",
    ],
    "mini_deerflow/graph/react.py": ["tutorial:07-explicit-react-graph"],
    "mini_deerflow/graph/research.py": [
        "tutorial:08-deterministic-research-workflow"
    ],
    "mini_deerflow/graph/functional.py": ["tutorial:08-functional-research-flow"],
    "mini_deerflow/graph/migration.py": ["tutorial:09-state-migration"],
    "mini_deerflow/graph/approval.py": [
        "tutorial:10-dynamic-approval-workflow"
    ],
    "mini_deerflow/persistence.py": ["tutorial:10-idempotent-effect-ledger"],
    "mini_deerflow/subagents/patterns.py": ["tutorial:11-control-patterns"],
    "mini_deerflow/subagents/registry.py": ["tutorial:11-subagent-registry"],
    "mini_deerflow/subagents/executor.py": ["tutorial:11-subagent-executor"],
    "mini_deerflow/subagents/task_tool.py": ["tutorial:11-task-tool"],
    "mini_deerflow/subagents/builtins.py": ["tutorial:11-isolated-specialists"],
}


def test_tutorial_source_regions_are_unique_and_closed() -> None:
    for relative_path, markers in EXPECTED_REGIONS.items():
        source = (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
        for marker in markers:
            assert source.count(f"# region {marker}") == 1, (relative_path, marker)
            assert source.count(f"# endregion {marker}") == 1, (relative_path, marker)
