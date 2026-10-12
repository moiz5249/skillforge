"""
cli_parser.py - CLI tool and help text extractor for SkillForge.
Parses CLI help manuals, argument flags, and subcommands into agent capabilities.
"""

import re
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
from .base import ExtractedToolMeta, CapabilitySpec, ParameterSpec


class CLIToolExtractor:
    """Extracts capabilities and parameters from CLI tools and help manuals."""

    def __init__(self, executable_or_help: str, is_command: bool = False):
        self.raw_input = executable_or_help
        self.is_command = is_command

    def extract(self) -> ExtractedToolMeta:
        """Parses CLI help text or executes --help on the tool."""
        help_text = self._get_help_text()
        tool_name = self._infer_tool_name(help_text)

        meta = ExtractedToolMeta(
            name=tool_name,
            title=tool_name.replace("-", " ").title(),
            description=self._infer_description(help_text),
            source_type="cli",
            source_path=self.raw_input if self.is_command else "custom-help-text"
        )

        # Parse options and flags
        flags = self._parse_flags(help_text)
        params = []
        for flag in flags:
            p_name = flag["long"].lstrip("-").replace("-", "_") if flag["long"] else flag["short"].lstrip("-")
            params.append(ParameterSpec(
                name=p_name,
                type_name="boolean" if flag["is_flag"] else "string",
                description=flag["description"],
                required=False,
                default_value=flag.get("default")
            ))

        # Main CLI capability
        cap = CapabilitySpec(
            name=f"run-{tool_name}",
            description=f"Executes {tool_name} CLI with configured parameters and flags.",
            parameters=params,
            return_type="string",
            source_symbol=tool_name,
            example_code=f"{tool_name} {flags[0]['long'] if flags else '--help'}"
        )
        meta.capabilities.append(cap)
        meta.cli_flags = flags
        return meta

    def _get_help_text(self) -> str:
        if not self.is_command:
            p = Path(self.raw_input)
            if p.is_file():
                return p.read_text(encoding="utf-8", errors="replace")
            return self.raw_input

        # Execute command with --help
        try:
            res = subprocess.run([self.raw_input, "--help"], capture_output=True, text=True, timeout=5)
            output = res.stdout or res.stderr
            if output:
                return output
        except Exception:
            pass
        return f"Usage: {self.raw_input} [OPTIONS] COMMAND [ARGS]..."

    def _infer_tool_name(self, help_text: str) -> str:
        match = re.search(r"Usage:\s*([a-zA-Z0-9_\-]+)", help_text, re.IGNORECASE)
        if match:
            return match.group(1).lower()
        if self.is_command:
            return Path(self.raw_input).stem.lower().replace("_", "-")
        return "cli-tool"

    @staticmethod
    def _infer_description(help_text: str) -> str:
        lines = [line.strip() for line in help_text.splitlines() if line.strip()]
        for line in lines[1:5]:
            if not line.startswith("Usage:") and not line.startswith("Options:") and not line.startswith("-"):
                return line
        return "Autonomous command line tool interface."

    @staticmethod
    def _parse_flags(help_text: str) -> List[Dict[str, Any]]:
        flags = []
        # Matches patterns like: -f, --file FILE   Description of file
        # or --verbose   Enable debug output
        pattern = re.compile(r"^\s*(?:(-[a-zA-Z]),?\s+)?(--[a-zA-Z0-9_\-]+)(?:\s+([A-Z_]+))?\s{2,}(.*)$", re.MULTILINE)
        for match in pattern.finditer(help_text):
            short, long_name, arg_val, desc = match.groups()
            flags.append({
                "short": short,
                "long": long_name,
                "has_value": bool(arg_val),
                "is_flag": not bool(arg_val),
                "arg_name": arg_val,
                "description": desc.strip()
            })
        return flags
