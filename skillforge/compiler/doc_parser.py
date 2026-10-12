"""
doc_parser.py - Markdown documentation and API spec parser for SkillForge.
Extracts code snippets, usage guidelines, and references for skill progressive disclosure.
"""

import re
from pathlib import Path
from typing import Dict, Any, List


class DocumentationParser:
    """Extracts code blocks, API summaries, and usage notes from markdown files."""

    def __init__(self, doc_path: str):
        self.doc_path = Path(doc_path).resolve()
        if not self.doc_path.exists():
            raise FileNotFoundError(f"Documentation file not found: {self.doc_path}")
        self.content = self.doc_path.read_text(encoding="utf-8", errors="replace")

    def parse(self) -> Dict[str, Any]:
        """Extracts sections and executable snippets."""
        sections: Dict[str, str] = {}
        snippets: List[Dict[str, str]] = []

        # Extract code blocks
        code_pattern = re.compile(r"```([a-zA-Z0-9_\-]+)?\r?\n(.*?)```", re.DOTALL)
        for match in code_pattern.finditer(self.content):
            lang, code = match.groups()
            snippets.append({
                "language": lang or "text",
                "code": code.strip()
            })

        # Split headers (H1/H2)
        header_pattern = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)
        headers = list(header_pattern.finditer(self.content))
        for i, h in enumerate(headers):
            title = h.group(2).strip()
            start = h.end()
            end = headers[i + 1].start() if i + 1 < len(headers) else len(self.content)
            body = self.content[start:end].strip()
            sections[title] = body

        return {
            "file_name": self.doc_path.name,
            "total_snippets": len(snippets),
            "snippets": snippets,
            "sections": sections
        }
