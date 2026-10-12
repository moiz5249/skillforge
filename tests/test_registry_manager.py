"""
test_registry_manager.py - Unit tests for skill package manager and registry.
"""

import tempfile
import unittest
from pathlib import Path

from skillforge.compiler.python_ast import PythonASTExtractor
from skillforge.compiler.generator import SkillPackageGenerator
from skillforge.manager.registry import SkillRegistryManager

class TestSkillRegistryManager(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.sample_path = Path(__file__).resolve().parent.parent / "examples" / "sample_library.py"

        # Generate a sample skill
        extractor = PythonASTExtractor(str(self.sample_path))
        meta = extractor.extract()
        meta.name = "audio-toolkit"

        generator = SkillPackageGenerator(Path(self.tmp_dir.name) / "compiled")
        self.compiled = generator.generate(meta)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_install_and_list_skills(self):
        target_dir = Path(self.tmp_dir.name) / "installed_skills"

        install_res = SkillRegistryManager.install_skill(self.compiled.output_dir, target_dir)
        self.assertTrue(install_res["success"])
        self.assertEqual(install_res["skill_name"], "audio-toolkit")
        self.assertTrue(install_res["compliant"])

        # List skills
        skills = SkillRegistryManager.list_skills(target_dir)
        self.assertEqual(len(skills), 1)
        self.assertEqual(skills[0]["name"], "audio-toolkit")
        self.assertTrue(skills[0]["compliant"])

    def test_export_archive(self):
        zip_path = Path(self.tmp_dir.name) / "audio-toolkit.zip"
        res_zip = SkillRegistryManager.export_archive(self.compiled.output_dir, zip_path)
        self.assertTrue(res_zip.is_file())
        self.assertGreater(res_zip.stat().st_size, 500)

if __name__ == "__main__":
    unittest.main()
