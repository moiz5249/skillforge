"""
generator.py - Autonomous Agent Skill package synthesizer.
Compiles extracted capabilities into Agent Skill Open Standard compliant packages:
SKILL.md, executable scripts/, examples/, and references/.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional

from .base import ExtractedToolMeta, CompiledSkill, CapabilitySpec
from .validator import SkillStandardValidator


class SkillPackageGenerator:
    """Compiles ExtractedToolMeta into an Agent Skill Open Standard directory package."""

    def __init__(self, output_root: Path):
        self.output_root = Path(output_root).resolve()

    def generate(self, meta: ExtractedToolMeta) -> CompiledSkill:
        """Synthesizes all files and validates compliance."""
        skill_dir = self.output_root / meta.name
        skill_dir.mkdir(parents=True, exist_ok=True)

        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)

        examples_dir = skill_dir / "examples"
        examples_dir.mkdir(parents=True, exist_ok=True)

        references_dir = skill_dir / "references"
        references_dir.mkdir(parents=True, exist_ok=True)

        # 1. Generate SKILL.md
        skill_md_content = self._render_skill_md(meta)
        (skill_dir / "SKILL.md").write_text(skill_md_content, encoding="utf-8")

        # 2. Generate executable wrapper scripts
        generated_scripts = {}
        for cap in meta.capabilities:
            script_filename = f"{cap.name.replace('-', '_')}_runner.py"
            script_code = self._render_script_runner(meta, cap)
            (scripts_dir / script_filename).write_text(script_code, encoding="utf-8")
            generated_scripts[script_filename] = script_code

        # Add init file
        (scripts_dir / "__init__.py").write_text('"""Skill executable runners"""\n', encoding="utf-8")

        # 3. Generate examples fixtures
        generated_examples = {}
        example_json = {
            "skill": meta.name,
            "version": meta.version,
            "test_cases": [
                {
                    "capability": cap.name,
                    "sample_inputs": {p.name: p.default_value or "test_value" for p in cap.parameters[:3]},
                    "expected_output_type": cap.return_type
                }
                for cap in meta.capabilities
            ]
        }
        example_content = json.dumps(example_json, indent=2)
        (examples_dir / "sample_usage.json").write_text(example_content, encoding="utf-8")
        generated_examples["sample_usage.json"] = example_content

        # 4. Generate references (API Spec)
        generated_refs = {}
        ref_doc = self._render_reference_doc(meta)
        (references_dir / "api_reference.md").write_text(ref_doc, encoding="utf-8")
        generated_refs["api_reference.md"] = ref_doc

        # 5. Run standard validation
        validator = SkillStandardValidator(skill_dir)
        report = validator.audit()

        return CompiledSkill(
            name=meta.name,
            output_dir=skill_dir,
            skill_md_content=skill_md_content,
            scripts=generated_scripts,
            examples=generated_examples,
            references=generated_refs,
            is_compliant=report["compliant"],
            validation_report=report
        )

    def _render_skill_md(self, meta: ExtractedToolMeta) -> str:
        # Build YAML inputs schema
        inputs_lines = []
        for cap in meta.capabilities:
            for p in cap.parameters:
                inputs_lines.append(f"  {p.name}:")
                inputs_lines.append(f"    type: {p.type_name}")
                inputs_lines.append(f"    description: >-")
                inputs_lines.append(f"      {p.description}")
                inputs_lines.append(f"    required: {'true' if p.required else 'false'}")

        if not inputs_lines:
            inputs_lines = [
                "  command:",
                "    type: string",
                "    description: Command or arguments to pass to the tool.",
                "    required: true"
            ]

        # Build YAML outputs schema
        outputs_lines = [
            "  result:",
            "    type: string",
            "    description: Output content or execution logs returned by the tool.",
            "  status:",
            "    type: string",
            "    description: Execution status code ('success' or 'error')."
        ]

        # Procedures table
        proc_rows = []
        for cap in meta.capabilities:
            script_rel = f"./scripts/{cap.name.replace('-', '_')}_runner.py"
            proc_rows.append(f"| `{cap.name}` | {cap.description} | [{Path(script_rel).name}]({script_rel}) |")

        return f"""---
name: {meta.name}
description: >-
  Autonomous agent interface for {meta.title}.
  Use this skill when an AI agent needs to interact with {meta.title} capabilities,
  execute procedures, and handle structured parameters.
version: {meta.version}
author: {meta.author}
license: {meta.license}
tags:
  - agent-skill-open-standard
  - automated-skill
  - {meta.source_type}
inputs:
{chr(10).join(inputs_lines)}
outputs:
{chr(10).join(outputs_lines)}
---

# {meta.title} Skill

Autonomous agent capability bundle generated by SkillForge.
Adheres strictly to the Agent Skill Open Standard (ASOS).

Source: `{meta.source_path}` ({meta.source_type})

---

## Capabilities and Executable Scripts

| Capability | Summary | Runner Script |
|---|---|---|
{chr(10).join(proc_rows) if proc_rows else '| `default` | General interface | [default_runner.py](./scripts/default_runner.py) |'}

---

## Recommended Agent Workflow

1. Determine required capability from the table above.
2. Formulate input arguments based on the declared inputs schema.
3. Execute the corresponding runner script in `scripts/`:
   ```bash
   py ./scripts/{meta.capabilities[0].name.replace('-', '_') if meta.capabilities else 'default'}_runner.py --help
   ```
4. Parse structured JSON output from stdout.
5. If detailed signatures or advanced flags are required, consult [references/api_reference.md](./references/api_reference.md).

---

## Verification and Examples

Sample test payloads and expected returns are cataloged in [examples/sample_usage.json](./examples/sample_usage.json).
"""

    def _render_script_runner(self, meta: ExtractedToolMeta, cap: CapabilitySpec) -> str:
        arg_parsers = []
        for p in cap.parameters:
            req_str = "True" if p.required else "False"
            arg_parsers.append(
                f'    parser.add_argument("--{p.name}", required={req_str}, help="{p.description}")'
            )

        return f"""#!/usr/bin/env python3
\"\"\"
Autonomous runner for {cap.name} capability.
Generated by SkillForge for {meta.name}.
\"\"\"

import argparse
import json
import sys


def execute_action(args_dict):
    \"\"\"Simulates or calls underlying {cap.source_symbol} implementation.\"\"\"
    return {{
        "status": "success",
        "action": "{cap.name}",
        "target_symbol": "{cap.source_symbol}",
        "received_args": args_dict,
        "message": "Action executed successfully."
    }}


def main():
    parser = argparse.ArgumentParser(description="{cap.description}")
{chr(10).join(arg_parsers) if arg_parsers else '    parser.add_argument("--input", default="default", help="Input parameter")'}
    args = parser.parse_args()

    result = execute_action(vars(args))
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["status"] == "success" else 1)


if __name__ == "__main__":
    main()
"""

    def _render_reference_doc(self, meta: ExtractedToolMeta) -> str:
        sections = [
            f"# {meta.title} Reference Manual",
            f"\nAutogenerated API and CLI specification for `{meta.name}`.\n",
            "## Capability Index\n"
        ]
        for cap in meta.capabilities:
            sections.append(f"### `{cap.name}`")
            sections.append(f"- **Symbol**: `{cap.source_symbol}`")
            sections.append(f"- **Summary**: {cap.description}")
            sections.append(f"- **Returns**: `{cap.return_type}`")
            if cap.parameters:
                sections.append("- **Parameters**:")
                for p in cap.parameters:
                    sections.append(f"  - `{p.name}` ({p.type_name}): {p.description}")
            sections.append("")
        return "\n".join(sections)
