"""
python_ast.py - Static AST extractor for Python libraries and modules.
Inspects real Python code on disk and extracts typed capabilities and docstrings.
"""

import ast
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from .base import ExtractedToolMeta, CapabilitySpec, ParameterSpec


class PythonASTExtractor:
    """Extracts capabilities, parameter types, and docstrings from Python modules."""

    def __init__(self, file_path: str):
        self.file_path = Path(file_path).resolve()
        if not self.file_path.exists():
            raise FileNotFoundError(f"Python source not found: {self.file_path}")
        self.content = self.file_path.read_text(encoding="utf-8", errors="replace")
        self.lines = self.content.splitlines()

    def extract(self) -> ExtractedToolMeta:
        """Parses AST and builds capability metadata."""
        tree = ast.parse(self.content, filename=str(self.file_path))
        module_doc = ast.get_docstring(tree) or f"Capabilities for {self.file_path.stem}"

        raw_name = self.file_path.stem.lower().replace("_", "-")
        # Ensure kebab-case
        skill_name = re.sub(r"[^a-z0-9\-]", "", raw_name) or "python-tool"

        meta = ExtractedToolMeta(
            name=skill_name,
            title=self.file_path.stem.replace("_", " ").title(),
            description=module_doc.strip().split("\n")[0] if module_doc else f"Interface for {self.file_path.stem}",
            source_type="python_ast",
            source_path=str(self.file_path)
        )

        # 1. Top-level functions
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not node.name.startswith("_"):
                    cap = self._parse_function(node)
                    meta.capabilities.append(cap)
            elif isinstance(node, ast.ClassDef):
                if not node.name.startswith("_"):
                    class_caps = self._parse_class(node)
                    meta.capabilities.extend(class_caps)

        return meta

    def _parse_function(self, node: ast.FunctionDef, parent_class: Optional[str] = None) -> CapabilitySpec:
        doc = ast.get_docstring(node) or f"Executes {node.name}"
        params: List[ParameterSpec] = []

        # Parse arguments and defaults
        args = node.args.args
        defaults = node.args.defaults
        num_defaults = len(defaults)
        first_default_idx = len(args) - num_defaults

        for i, arg in enumerate(args):
            if arg.arg in ("self", "cls"):
                continue

            param_type = self._ast_to_type_str(arg.annotation) if arg.annotation else "str"
            has_default = i >= first_default_idx
            default_val = None
            if has_default:
                def_node = defaults[i - first_default_idx]
                default_val = self._ast_to_value_str(def_node)

            param_doc = self._extract_param_doc(doc, arg.arg) or f"Input parameter {arg.arg}"

            params.append(ParameterSpec(
                name=arg.arg,
                type_name=param_type,
                description=param_doc,
                required=not has_default,
                default_value=default_val
            ))

        return_type = self._ast_to_type_str(node.returns) if node.returns else "Any"
        symbol_name = f"{parent_class}.{node.name}" if parent_class else node.name

        return CapabilitySpec(
            name=node.name.replace("_", "-"),
            description=doc.strip().split("\n")[0],
            parameters=params,
            return_type=return_type,
            source_symbol=symbol_name,
            example_code=f"{symbol_name}({', '.join(p.name + '=...' for p in params[:2])})"
        )

    def _parse_class(self, node: ast.ClassDef) -> List[CapabilitySpec]:
        caps = []
        class_doc = ast.get_docstring(node) or node.name

        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not item.name.startswith("_") or item.name == "__init__":
                    cap = self._parse_function(item, parent_class=node.name)
                    if item.name == "__init__":
                        cap.name = f"create-{node.name.lower().replace('_', '-')}"
                        cap.description = f"Instantiates {node.name}. {class_doc.strip().splitlines()[0]}"
                    caps.append(cap)
        return caps

    @staticmethod
    def _ast_to_type_str(node: Optional[ast.AST]) -> str:
        if node is None:
            return "str"
        if isinstance(node, ast.Name):
            mapping = {"int": "integer", "float": "number", "str": "string", "bool": "boolean", "dict": "object", "list": "array"}
            return mapping.get(node.id, node.id)
        if isinstance(node, ast.Subscript):
            val = PythonASTExtractor._ast_to_type_str(node.value)
            return val
        if isinstance(node, ast.Constant):
            return str(type(node.value).__name__)
        return "string"

    @staticmethod
    def _ast_to_value_str(node: ast.AST) -> str:
        if isinstance(node, ast.Constant):
            return repr(node.value)
        if isinstance(node, ast.Name):
            return node.id
        return "..."

    @staticmethod
    def _extract_param_doc(docstring: str, param_name: str) -> Optional[str]:
        if not docstring:
            return None
        # Pattern: :param name: description or Args:\n  name: description
        pattern = re.compile(rf"(?::param\s+{param_name}:|\b{param_name}\s*:\s*)([^\n\r]+)")
        match = pattern.search(docstring)
        return match.group(1).strip() if match else None
