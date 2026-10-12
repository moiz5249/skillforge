"""
validator.py - Agent Skill Open Standard (ASOS) Auditor & Linter.
Validates skill directory structure, frontmatter schemas, link resolution, and quality.
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple


class SkillStandardValidator:
    """Verifies compliance against the Agent Skill Open Standard (ASOS)."""

    REQUIRED_FIELDS = ["name", "description", "version", "license", "inputs", "outputs"]

    def __init__(self, skill_dir: Path):
        self.skill_dir = Path(skill_dir).resolve()

    def audit(self) -> Dict[str, Any]:
        """Runs compliance checks and returns audit score and details."""
        report = {
            "compliant": True,
            "skill_path": str(self.skill_dir),
            "score": 100,
            "checks": [],
            "errors": [],
            "warnings": []
        }

        def record(name: str, passed: bool, message: str, weight: int = 10):
            report["checks"].append({
                "name": name,
                "passed": passed,
                "message": message
            })
            if not passed:
                report["compliant"] = False
                report["score"] = max(0, report["score"] - weight)
                report["errors"].append(f"[{name}] {message}")

        # Check 1: Directory exists
        if not self.skill_dir.is_dir():
            record("Skill Directory Exists", False, f"Directory not found: {self.skill_dir}", 100)
            return report
        record("Skill Directory Exists", True, "Directory exists on filesystem.")

        # Check 2: SKILL.md exists
        skill_md = self.skill_dir / "SKILL.md"
        record("SKILL.md Exists", skill_md.is_file(), "Specification file SKILL.md must be at the root.", 25)
        if not skill_md.is_file():
            return report

        content = skill_md.read_text(encoding="utf-8", errors="replace")
        frontmatter, body = self._parse_frontmatter(content)

        # Check 3: Frontmatter syntax
        record("YAML Frontmatter Enclosure", frontmatter is not None, "Frontmatter must be enclosed in '---' markers.", 20)
        if not frontmatter:
            return report

        # Check 4: Required fields
        for field in self.REQUIRED_FIELDS:
            has_field = field in frontmatter and bool(frontmatter[field])
            record(f"Required Field: {field}", has_field, f"Field '{field}' is required by the standard.", 10)

        # Check 5: Kebab-case naming
        name = str(frontmatter.get("name", ""))
        valid_name = bool(re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", name))
        record("Kebab-case Name Format", valid_name, f"Skill name '{name}' must be lowercase hyphenated.", 10)

        # Check 6: Description depth
        desc = str(frontmatter.get("description", ""))
        record("Description Quality", len(desc) >= 20, "Description must be at least 20 characters explaining when to invoke.", 10)

        # Check 7: Input / Output schema structure
        inputs = frontmatter.get("inputs")
        valid_inputs = isinstance(inputs, dict)
        record("Inputs Schema Dict", valid_inputs, "Inputs must be declared as a typed key-value dictionary.", 10)

        outputs = frontmatter.get("outputs")
        valid_outputs = isinstance(outputs, dict)
        record("Outputs Schema Dict", valid_outputs, "Outputs must be declared as a typed key-value dictionary.", 10)

        # Check 8: Scripts directory and helper files
        scripts_dir = self.skill_dir / "scripts"
        has_scripts = scripts_dir.is_dir() and len(list(scripts_dir.glob("*.py"))) > 0
        record("Executable Scripts Present", has_scripts, "scripts/ directory contains executable helper tools.", 10)

        # Check 9: References directory (Progressive Disclosure)
        ref_dir = self.skill_dir / "references"
        record("References Directory Present", ref_dir.is_dir(), "references/ directory isolates heavy schemas or docs.", 5)

        # Check 10: Link integrity
        broken_links = self._check_internal_links(body)
        record("Internal Link Integrity", len(broken_links) == 0,
               f"Broken relative links found: {broken_links}" if broken_links else "All linked scripts and references resolve on disk.", 10)

        return report

    def _parse_frontmatter(self, content: str) -> Tuple[Optional[Dict[str, Any]], str]:
        pattern = re.compile(r"^---\r?\n(.*?)\r?\n---\r?\n(.*)$", re.DOTALL)
        match = pattern.match(content)
        if not match:
            return None, content

        yaml_block, body = match.groups()
        data = {}
        current_key = None

        lines = yaml_block.splitlines()
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            top_match = re.match(r"^([a-zA-Z0-9_-]+):\s*(.*)$", line)
            if top_match and not line.startswith(" ") and not line.startswith("\t"):
                key, val = top_match.groups()
                key = key.strip()
                val = val.strip()
                if val.startswith(">") or val.startswith("|"):
                    data[key] = ""
                    current_key = key
                elif val.startswith("[") and val.endswith("]"):
                    data[key] = [x.strip().strip("'\"") for x in val[1:-1].split(",") if x.strip()]
                    current_key = None
                elif val:
                    data[key] = val.strip("'\"")
                    current_key = None
                else:
                    data[key] = {}
                    current_key = key
            elif current_key and line.startswith("  "):
                sub_match = re.match(r"^\s+([a-zA-Z0-9_-]+):\s*(.*)$", line)
                list_match = re.match(r"^\s*-\s+(.*)$", line)
                if isinstance(data.get(current_key), list) or list_match:
                    if not isinstance(data.get(current_key), list):
                        data[current_key] = []
                    if list_match:
                        data[current_key].append(list_match.group(1).strip().strip("'\""))
                elif sub_match:
                    s_key, s_val = sub_match.groups()
                    if isinstance(data[current_key], dict):
                        data[current_key][s_key.strip()] = s_val.strip("'\"") if s_val else {}
                elif isinstance(data.get(current_key), str):
                    data[current_key] = (data[current_key] + " " + stripped).strip()

        return data, body

    def _check_internal_links(self, markdown_body: str) -> List[str]:
        links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', markdown_body)
        broken = []
        for text, link in links:
            if not link.startswith("http") and not link.startswith("#") and not link.startswith("mailto:"):
                # Clean query strings / anchors
                clean_link = link.split("#")[0].split("?")[0]
                if clean_link:
                    target = (self.skill_dir / clean_link).resolve()
                    if not target.exists():
                        broken.append(link)
        return broken
