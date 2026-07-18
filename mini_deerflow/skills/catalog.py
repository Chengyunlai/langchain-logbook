"""Agent Skills 元数据发现与按需正文加载。"""

from __future__ import annotations

import json
from pathlib import Path
from collections.abc import Mapping

from langchain_core.tools import BaseTool
from langchain.tools import tool
from pydantic import BaseModel, ConfigDict, Field
import yaml


_MAX_SKILL_BYTES = 256_000


class SkillFormatError(ValueError):
    """SKILL.md frontmatter 或目录边界不满足最小契约。"""


class SkillMetadata(BaseModel):
    """始终可进入工具描述的轻量技能索引。"""

    model_config = ConfigDict(frozen=True)

    name: str = Field(pattern=r"^[a-z][a-z0-9_-]*$", max_length=80)
    description: str = Field(min_length=1, max_length=500)


class LoadedSkill(BaseModel):
    """模型显式调用 ``load_skill`` 后才返回的完整主说明。"""

    model_config = ConfigDict(frozen=True)

    name: str
    description: str
    instructions: str = Field(min_length=1, max_length=256_000)


class SkillLoadInput(BaseModel):
    name: str = Field(pattern=r"^[a-z][a-z0-9_-]*$", max_length=80)


def _parse_skill(content: str, *, source: Path) -> tuple[SkillMetadata, str]:
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        raise SkillFormatError(f"{source}: SKILL.md 必须以 YAML frontmatter 开始")
    try:
        closing = next(
            index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---"
        )
    except StopIteration as error:
        raise SkillFormatError(f"{source}: SKILL.md frontmatter 未闭合") from error

    try:
        raw_frontmatter = yaml.safe_load("\n".join(lines[1:closing]))
    except yaml.YAMLError as error:
        raise SkillFormatError(f"{source}: frontmatter 不是有效 YAML") from error
    if not isinstance(raw_frontmatter, Mapping):
        raise SkillFormatError(f"{source}: frontmatter 必须是 YAML object")
    values = {
        key: raw_frontmatter.get(key) for key in ("name", "description")
    }
    if not all(isinstance(values[key], str) for key in values):
        raise SkillFormatError(f"{source}: frontmatter 需要 name 和 description")
    metadata = SkillMetadata.model_validate(values)
    instructions = "\n".join(lines[closing + 1 :]).strip()
    if not instructions:
        raise SkillFormatError(f"{source}: 技能正文不能为空")
    return metadata, instructions


def _read_skill_file(path: Path) -> str:
    size = path.stat().st_size
    if size > _MAX_SKILL_BYTES:
        raise SkillFormatError(
            f"技能主文件超过 {_MAX_SKILL_BYTES} bytes: {path}"
        )
    return path.read_text(encoding="utf-8")


class SkillCatalog:
    """只缓存 metadata/path；正文每次 ``load`` 时从受控根目录读取。"""

    def __init__(
        self,
        root: Path,
        entries: dict[str, tuple[SkillMetadata, Path]],
    ) -> None:
        self.root = root
        self._entries = entries

    @classmethod
    def from_directory(cls, root: str | Path) -> SkillCatalog:
        resolved_root = Path(root).resolve()
        if not resolved_root.is_dir():
            raise FileNotFoundError(resolved_root)
        entries: dict[str, tuple[SkillMetadata, Path]] = {}
        for candidate in sorted(resolved_root.glob("*/SKILL.md")):
            if candidate.is_symlink():
                raise SkillFormatError(f"技能主文件不能是符号链接: {candidate}")
            resolved = candidate.resolve(strict=True)
            if not resolved.is_relative_to(resolved_root):
                raise SkillFormatError(f"技能文件越出 catalog root: {candidate}")
            content = _read_skill_file(resolved)
            metadata, _ = _parse_skill(content, source=resolved)
            if metadata.name in entries:
                raise SkillFormatError(f"技能 name 重复: {metadata.name}")
            entries[metadata.name] = (metadata, resolved)
        return cls(resolved_root, entries)

    def list_metadata(self) -> tuple[SkillMetadata, ...]:
        return tuple(self._entries[name][0] for name in sorted(self._entries))

    def render_index(self) -> str:
        return "\n".join(
            f"- {metadata.name}: {metadata.description}"
            for metadata in self.list_metadata()
        )

    def load(self, name: str) -> LoadedSkill:
        try:
            expected_metadata, path = self._entries[name]
        except KeyError as error:
            available = ", ".join(sorted(self._entries)) or "none"
            raise KeyError(f"未知 skill {name!r}; available: {available}") from error
        if path.is_symlink():
            raise SkillFormatError(f"技能主文件不能是符号链接: {path}")
        resolved = path.resolve(strict=True)
        if not resolved.is_relative_to(self.root):
            raise SkillFormatError(f"技能文件越出 catalog root: {path}")
        metadata, instructions = _parse_skill(
            _read_skill_file(resolved),
            source=resolved,
        )
        if metadata != expected_metadata:
            raise SkillFormatError(f"技能 metadata 在发现后发生变化: {name}")
        return LoadedSkill(
            name=metadata.name,
            description=metadata.description,
            instructions=instructions,
        )


def build_load_skill_tool(catalog: SkillCatalog) -> BaseTool:
    """把 metadata index 放入工具描述，正文只在工具调用时加载。"""

    index = catalog.render_index() or "- none"

    @tool(
        "load_skill",
        args_schema=SkillLoadInput,
        description=(
            "按名称加载一个 Agent Skill 的完整说明。先根据轻量索引选择，"
            f"不要猜测不存在的技能。\n可用技能：\n{index}"
        ),
    )
    def load_skill(name: str) -> str:
        return json.dumps(
            catalog.load(name).model_dump(mode="json"),
            ensure_ascii=False,
        )

    load_skill.metadata = {"source": "skill_catalog", "progressive_disclosure": True}
    return load_skill


__all__ = [
    "LoadedSkill",
    "SkillCatalog",
    "SkillFormatError",
    "SkillLoadInput",
    "SkillMetadata",
    "build_load_skill_tool",
]
