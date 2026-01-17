"""
Contract: library/cookbook/__init__.py
Purpose: Module index for available skills in the cookbook
Layer: Library
"""

from pathlib import Path


COOKBOOK_DIR = Path(__file__).parent


def list_skills() -> list[str]:
    """List all available skill files in the cookbook."""
    skills = []
    for path in COOKBOOK_DIR.glob("*.py"):
        if path.name != "__init__.py":
            skills.append(path.stem)
    return sorted(skills)


def get_skill_path(skill_name: str) -> Path | None:
    """Get the path to a skill file if it exists."""
    skill_path = COOKBOOK_DIR / f"{skill_name}.py"
    return skill_path if skill_path.exists() else None


def load_skill(skill_name: str) -> str | None:
    """Load and return the content of a skill file."""
    skill_path = get_skill_path(skill_name)
    if skill_path:
        with open(skill_path, "r", encoding="utf-8") as f:
            return f.read()
    return None


def skill_exists(skill_name: str) -> bool:
    """Check if a skill exists in the cookbook."""
    return get_skill_path(skill_name) is not None


# Module-level access
__all__ = ["list_skills", "get_skill_path", "load_skill", "skill_exists", "COOKBOOK_DIR"]
