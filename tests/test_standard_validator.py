"""
test_standard_validator.py - Unit tests for Agent Skill Open Standard validator.
"""

import tempfile
import unittest
from pathlib import Path
from skillforge.compiler.validator import SkillStandardValidator

class TestSkillStandardValidator(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.skill_dir = Path(self.tmp_dir.name) / "my-test-skill"
        self.skill_dir.mkdir()

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_audit_missing_skill_md(self):
        validator = SkillStandardValidator(self.skill_dir)
        report = validator.audit()
        self.assertFalse(report["compliant"])
        self.assertLess(report["score"], 100)

    def test_audit_valid_skill(self):
        (self.skill_dir / "scripts").mkdir()
        (self.skill_dir / "scripts" / "run.py").write_text("#!/usr/bin/env python\nprint('ok')")
        (self.skill_dir / "references").mkdir()
        (self.skill_dir / "references" / "ref.md").write_text("# Reference Docs")

        skill_md = """---
name: my-test-skill
description: Autonomous interface for my test skill procedures. Use this skill when testing.
version: 1.0.0
license: MIT
inputs:
  param1:
    type: string
    description: Input parameter
outputs:
  result:
    type: string
    description: Output result
---

# My Test Skill

Refer to [run.py](./scripts/run.py) and [ref.md](./references/ref.md).
"""
        (self.skill_dir / "SKILL.md").write_text(skill_md, encoding="utf-8")

        validator = SkillStandardValidator(self.skill_dir)
        report = validator.audit()
        self.assertTrue(report["compliant"])
        self.assertEqual(report["score"], 100)

if __name__ == "__main__":
    unittest.main()
