"""Agent Skills 的 metadata catalog 与按需加载工具。"""

from pathlib import Path

from mini_deerflow.skills.catalog import (
    LoadedSkill,
    SkillCatalog,
    SkillFormatError,
    SkillLoadInput,
    SkillMetadata,
    build_load_skill_tool,
)


def build_demo_skill_catalog() -> SkillCatalog:
    """加载随 package 分发的 research-report 教学 Skill。"""

    return SkillCatalog.from_directory(Path(__file__).parent / "examples")


__all__ = [
    "LoadedSkill",
    "SkillCatalog",
    "SkillFormatError",
    "SkillLoadInput",
    "SkillMetadata",
    "build_demo_skill_catalog",
    "build_load_skill_tool",
]
