"""
test_skill_generator.py - Unit tests for full package generator.
"""

import tempfile
import unittest
from pathlib import Path

from skillforge.compiler.python_ast import PythonASTExtractor
from skillforge.compiler.generator import SkillPackageGenerator

class TestSkillPackageGenerator(unittest.TestCase):
    def setUp(self):
        self.sample_path = Path(__file__).resolve().parent.parent / "examples" / "sample_library.py"
        self.tmp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_full_package_compilation(self):
        extractor = PythonASTExtractor(str(self.sample_path))
        meta = extractor.extract()
        meta.name = "test-audio-toolkit"

        generator = SkillPackageGenerator(Path(self.tmp_dir.name))
        compiled = generator.generate(meta)

        self.assertEqual(compiled.name, "test-audio-toolkit")
        self.assertTrue(compiled.is_compliant)
        self.assertEqual(compiled.validation_report["score"], 100)

        # Check files on disk
        self.assertTrue((compiled.output_dir / "SKILL.md").is_file())
        self.assertTrue((compiled.output_dir / "scripts" / "normalize_audio_runner.py").is_file())
        self.assertTrue((compiled.output_dir / "examples" / "sample_usage.json").is_file())
        self.assertTrue((compiled.output_dir / "references" / "api_reference.md").is_file())

if __name__ == "__main__":
    unittest.main()
