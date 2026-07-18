#!/usr/bin/env python3
"""Validate that CI and Pages workflows reuse the local release gate."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any

import yaml


@dataclass(frozen=True)
class Finding:
    code: str
    detail: str


def _load_workflow(path: Path) -> dict[str, Any]:
    content = yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    return content if isinstance(content, dict) else {}


def _job(workflow: dict[str, Any], name: str) -> dict[str, Any]:
    jobs = workflow.get("jobs", {})
    if not isinstance(jobs, dict):
        return {}
    job = jobs.get(name, {})
    return job if isinstance(job, dict) else {}


def _steps(job: dict[str, Any]) -> list[dict[str, Any]]:
    steps = job.get("steps", [])
    if not isinstance(steps, list):
        return []
    return [step for step in steps if isinstance(step, dict)]


def _is_unconditional(step: dict[str, Any]) -> bool:
    return "if" not in step and step.get("continue-on-error", "false") == "false"


def _is_make_check_gate(step: dict[str, Any]) -> bool:
    command = step.get("run")
    return (
        isinstance(command, str)
        and command.strip() == "make check"
        and _is_unconditional(step)
    )


def _workflow_gate_steps(
    workflow: dict[str, Any],
) -> list[tuple[str, int]]:
    gates: list[tuple[str, int]] = []
    jobs = workflow.get("jobs", {})
    if not isinstance(jobs, dict):
        return gates
    for job_name, job in jobs.items():
        if not isinstance(job, dict) or not _is_unconditional(job):
            continue
        gates.extend(
            (str(job_name), index)
            for index, step in enumerate(_steps(job))
            if _is_make_check_gate(step)
        )
    return gates


def _job_gate_indexes(job: dict[str, Any]) -> list[int]:
    if not _is_unconditional(job):
        return []
    return [
        index
        for index, step in enumerate(_steps(job))
        if _is_make_check_gate(step)
    ]


def _job_action_uses(job: dict[str, Any], prefix: str) -> list[str]:
    return [
        step["uses"]
        for step in _steps(job)
        if isinstance(step.get("uses"), str)
        and step["uses"].startswith(prefix)
    ]


def check_workflows(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    workflow_dir = root / ".github" / "workflows"
    quality_path = workflow_dir / "quality.yml"
    quality: dict[str, Any] = {}
    quality_gates: list[tuple[str, int]] = []
    if not quality_path.is_file():
        findings.append(Finding("quality-gate", "missing quality.yml"))
    else:
        quality = _load_workflow(quality_path)
        quality_gates = _workflow_gate_steps(quality)
        if len(quality_gates) != 1:
            findings.append(
                Finding(
                    "quality-gate",
                    "quality.yml must run exactly one unconditional `make check` gate",
                )
            )

    deploy_path = workflow_dir / "deploy.yml"
    deploy: dict[str, Any] = {}
    if not deploy_path.is_file():
        findings.append(Finding("deploy-gate", "missing deploy.yml"))
    else:
        deploy = _load_workflow(deploy_path)
        build = _job(deploy, "build")
        build_steps = _steps(build)
        uses = [step.get("uses", "") for step in build_steps]
        gate_indexes = _job_gate_indexes(build)
        if len(gate_indexes) != 1 or any(
            use.startswith("withastro/action@")
            for use in uses
            if isinstance(use, str)
        ):
            findings.append(
                Finding(
                    "deploy-gate",
                    "deploy.yml build must run exactly one unconditional `make check` gate without withastro/action",
                )
            )
        indexed_upload_steps = [
            (index, step)
            for index, step in enumerate(build_steps)
            if isinstance(step.get("uses"), str)
            and step["uses"].startswith("actions/upload-pages-artifact@")
        ]
        upload_steps = [step for _, step in indexed_upload_steps]
        upload_paths = [
            step.get("with", {}).get("path")
            for step in upload_steps
            if isinstance(step.get("with"), dict)
        ]
        if upload_paths != ["docs-site/dist"]:
            findings.append(
                Finding(
                    "deploy-artifact",
                    "deploy.yml must upload exactly `docs-site/dist`",
                )
            )
        if not (
            len(gate_indexes) == 1
            and len(indexed_upload_steps) == 1
            and indexed_upload_steps[0][0] == gate_indexes[0] + 1
            and _is_unconditional(indexed_upload_steps[0][1])
        ):
            findings.append(
                Finding(
                    "deploy-artifact-flow",
                    "the unconditional Pages artifact upload must immediately follow the validated gate",
                )
            )
        deploy_job = _job(deploy, "deploy")
        deploy_uses = [
            step.get("uses")
            for step in _steps(deploy_job)
            if isinstance(step.get("uses"), str)
            and step["uses"].startswith("actions/deploy-pages@")
        ]
        environment = deploy_job.get("environment", {})
        environment_name = (
            environment.get("name") if isinstance(environment, dict) else None
        )
        if (
            deploy_job.get("needs") != "build"
            or environment_name != "github-pages"
            or len(deploy_uses) != 1
        ):
            findings.append(
                Finding(
                    "deploy-wiring",
                    "deploy job must need build, use github-pages, and deploy once",
                )
            )
        configure_uses = [
            step.get("uses")
            for step in _steps(build)
            if isinstance(step.get("uses"), str)
            and step["uses"].startswith("actions/configure-pages@")
        ]
        if (
            configure_uses != ["actions/configure-pages@v6"]
            or [step.get("uses") for step in upload_steps]
            != ["actions/upload-pages-artifact@v5"]
            or deploy_uses != ["actions/deploy-pages@v5"]
        ):
            findings.append(
                Finding(
                    "pages-action-version",
                    "Pages actions must match the current calibrated major versions",
                )
            )
        triggers = deploy.get("on", {})
        permissions = deploy.get("permissions", {})
        concurrency = deploy.get("concurrency", {})
        expected_permissions = {
            "contents": "read",
            "pages": "write",
            "id-token": "write",
        }
        if (
            not isinstance(triggers, dict)
            or "workflow_dispatch" not in triggers
            or permissions != expected_permissions
            or not isinstance(concurrency, dict)
            or concurrency.get("group") != "pages"
            or concurrency.get("cancel-in-progress") != "false"
        ):
            findings.append(
                Finding(
                    "deploy-safety",
                    "deploy.yml must keep manual trigger, minimal permissions, and pages concurrency",
                )
            )
    if quality and deploy:
        quality_setup_uv_uses = (
            _job_action_uses(
                _job(quality, quality_gates[0][0]),
                "astral-sh/setup-uv@",
            )
            if len(quality_gates) == 1
            else []
        )
        deploy_setup_uv_uses = _job_action_uses(
            _job(deploy, "build"), "astral-sh/setup-uv@"
        )
        if quality_setup_uv_uses != ["astral-sh/setup-uv@v8.3.2"] or (
            deploy_setup_uv_uses != ["astral-sh/setup-uv@v8.3.2"]
        ):
            findings.append(
                Finding(
                    "setup-uv-version",
                    "Quality and Pages must use the current immutable setup-uv tag v8.3.2",
                )
            )
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()

    findings = check_workflows(args.root.resolve())
    for finding in findings:
        print(f"[workflow-contract:{finding.code}] {finding.detail}")
    print(f"Workflow contracts: {len(findings)} failure(s)")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
