"""
registry.py - Agent Skill package manager and registry.
Handles discovery, installation, listing, and packaging across agent workspaces.
"""

import shutil
import zipfile
from pathlib import Path
from typing import Dict, Any, List, Optional
from ..compiler.validator import SkillStandardValidator


class SkillRegistryManager:
    """Manages installation, discovery, and packaging of agent skills."""

    @staticmethod
    def install_skill(source_dir: Path, target_dir: Path) -> Dict[str, Any]:
        """Installs a skill directory into the target agent workspace."""
        source_dir = Path(source_dir).resolve()
        target_dir = Path(target_dir).resolve()

        if not source_dir.is_dir() or not (source_dir / "SKILL.md").exists():
            return {
                "success": False,
                "error": f"Invalid skill directory: {source_dir} (missing SKILL.md)"
            }

        skill_name = source_dir.name
        dest = target_dir / skill_name
        dest.parent.mkdir(parents=True, exist_ok=True)

        if dest.exists():
            shutil.rmtree(dest)

        shutil.copytree(source_dir, dest)

        # Run validation on installed copy
        validator = SkillStandardValidator(dest)
        report = validator.audit()

        return {
            "success": True,
            "skill_name": skill_name,
            "installed_path": str(dest),
            "compliant": report["compliant"],
            "score": report["score"]
        }

    @staticmethod
    def list_skills(search_dir: Path) -> List[Dict[str, Any]]:
        """Discovers all skills within search_dir and audits their specs."""
        search_dir = Path(search_dir).resolve()
        skills = []
        if not search_dir.exists():
            return skills

        # Look for subdirectories containing SKILL.md
        for child in search_dir.iterdir():
            if child.is_dir() and (child / "SKILL.md").is_file():
                validator = SkillStandardValidator(child)
                report = validator.audit()
                skill_md_content = (child / "SKILL.md").read_text(encoding="utf-8", errors="replace")
                fm, _ = validator._parse_frontmatter(skill_md_content)

                skills.append({
                    "name": child.name,
                    "path": str(child),
                    "version": fm.get("version", "unknown") if fm else "unknown",
                    "description": fm.get("description", "") if fm else "",
                    "compliant": report["compliant"],
                    "score": report["score"]
                })
        return skills

    @staticmethod
    def export_archive(skill_dir: Path, output_zip: Path) -> Path:
        """Packages a skill folder into a standard zip distribution."""
        skill_dir = Path(skill_dir).resolve()
        output_zip = Path(output_zip).resolve()

        with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            for file_path in skill_dir.rglob("*"):
                if not any(x in file_path.parts for x in ["__pycache__", ".git"]):
                    arcname = file_path.relative_to(skill_dir)
                    zf.write(file_path, arcname)
        return output_zip

    @staticmethod
    def remove_skill(skill_name: str, target_dir: Path) -> bool:
        """Removes an installed skill from the agent workspace."""
        target = Path(target_dir).resolve() / skill_name
        if target.exists() and target.is_dir():
            shutil.rmtree(target)
            return True
        return False
