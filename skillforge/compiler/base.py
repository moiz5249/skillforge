"""
base.py - Core data models and schemas for SkillForge compiler.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, List, Optional


@dataclass
class ParameterSpec:
    name: str
    type_name: str
    description: str
    required: bool = True
    default_value: Optional[str] = None


@dataclass
class CapabilitySpec:
    name: str
    description: str
    parameters: List[ParameterSpec] = field(default_factory=list)
    return_type: str = "Any"
    source_symbol: str = ""
    example_code: Optional[str] = None


@dataclass
class ExtractedToolMeta:
    name: str
    title: str
    description: str
    version: str = "1.0.0"
    license: str = "MIT"
    author: str = "SkillForge Compiler"
    source_type: str = "python_ast"  # "python_ast", "cli", "documentation"
    source_path: str = ""
    capabilities: List[CapabilitySpec] = field(default_factory=list)
    cli_flags: List[Dict[str, Any]] = field(default_factory=list)
    doc_sections: Dict[str, str] = field(default_factory=dict)


@dataclass
class CompiledSkill:
    name: str
    output_dir: Path
    skill_md_content: str
    scripts: Dict[str, str] = field(default_factory=dict)
    examples: Dict[str, str] = field(default_factory=dict)
    references: Dict[str, str] = field(default_factory=dict)
    is_compliant: bool = False
    validation_report: Dict[str, Any] = field(default_factory=dict)
