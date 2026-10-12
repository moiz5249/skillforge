"""
server.py - Utilitarian developer server for SkillForge web studio.
Provides REST endpoints for compilation, validation, and package management.
"""

import http.server
import json
import os
import sys
import tempfile
import urllib.parse
from pathlib import Path
from typing import Dict, Any

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from skillforge.compiler.python_ast import PythonASTExtractor
from skillforge.compiler.cli_parser import CLIToolExtractor
from skillforge.compiler.generator import SkillPackageGenerator
from skillforge.compiler.validator import SkillStandardValidator
from skillforge.manager.registry import SkillRegistryManager

STATIC_DIR = Path(__file__).resolve().parent / "static"
OUTPUT_DIR = BASE_DIR / "output_skills"


class SkillForgeRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Handles REST API and static asset serving."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        path = url.path

        if path == "/api/skills":
            skills = SkillRegistryManager.list_skills(OUTPUT_DIR)
            self._send_json({"skills": skills})
        elif path == "/api/sample-inputs":
            sample_lib = (BASE_DIR / "examples" / "sample_library.py").read_text(encoding="utf-8", errors="replace")
            self._send_json({
                "sample_code": sample_lib,
                "sample_name": "audio-dsp-toolkit"
            })
        else:
            super().do_GET()

    def do_POST(self):
        url = urllib.parse.urlparse(self.path)
        path = url.path

        if path == "/api/compile":
            content_len = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_len).decode("utf-8")
            try:
                payload = json.loads(body)
            except Exception:
                self._send_json({"error": "Invalid JSON"}, status=400)
                return

            source_code = payload.get("source_code", "")
            source_type = payload.get("source_type", "python")
            skill_name = payload.get("skill_name", "custom-skill").strip()

            if not source_code.strip():
                self._send_json({"error": "Source code or input text cannot be empty."}, status=400)
                return

            with tempfile.NamedTemporaryFile("w", suffix=".py" if source_type == "python" else ".txt", delete=False, encoding="utf-8") as tmp:
                tmp.write(source_code)
                tmp_path = tmp.name

            try:
                if source_type == "python":
                    extractor = PythonASTExtractor(tmp_path)
                    meta = extractor.extract()
                else:
                    extractor = CLIToolExtractor(tmp_path, is_command=False)
                    meta = extractor.extract()

                if skill_name:
                    meta.name = skill_name

                generator = SkillPackageGenerator(OUTPUT_DIR)
                compiled = generator.generate(meta)

                # Return compiled files and report
                self._send_json({
                    "status": "success",
                    "skill_name": compiled.name,
                    "output_dir": str(compiled.output_dir),
                    "is_compliant": compiled.is_compliant,
                    "validation_report": compiled.validation_report,
                    "skill_md": compiled.skill_md_content,
                    "scripts": compiled.scripts,
                    "examples": compiled.examples,
                    "references": compiled.references
                })
            except Exception as e:
                self._send_json({"error": str(e)}, status=500)
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

        elif path == "/api/install":
            content_len = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_len).decode("utf-8")
            payload = json.loads(body)
            skill_name = payload.get("skill_name")
            target_type = payload.get("target_type", "workspace")

            source_path = OUTPUT_DIR / skill_name
            if target_type == "global":
                target_dir = Path.home() / ".gemini" / "config" / "skills"
            else:
                target_dir = BASE_DIR / ".agents" / "skills"

            res = SkillRegistryManager.install_skill(source_path, target_dir)
            self._send_json(res)
        else:
            self._send_json({"error": "Not Found"}, status=404)

    def _send_json(self, data: Dict[str, Any], status: int = 200):
        raw = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(raw)


def run_server(port: int = 8899):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    addr = ("127.0.0.1", port)
    httpd = http.server.HTTPServer(addr, SkillForgeRequestHandler)
    print("\n=======================================================")
    print(f"SkillForge Developer Studio running at http://127.0.0.1:{port}")
    print("Agent Skill Open Standard Compiler & Manager")
    print("=======================================================\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
        httpd.server_close()


if __name__ == "__main__":
    run_server()
