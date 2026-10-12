"""
test_python_ast_extractor.py - Unit tests for AST extractor.
"""

import unittest
from pathlib import Path
from skillforge.compiler.python_ast import PythonASTExtractor

class TestPythonASTExtractor(unittest.TestCase):
    def setUp(self):
        self.sample_path = Path(__file__).resolve().parent.parent / "examples" / "sample_library.py"

    def test_extract_capabilities(self):
        extractor = PythonASTExtractor(str(self.sample_path))
        meta = extractor.extract()
        self.assertEqual(meta.name, "sample-library")
        self.assertGreaterEqual(len(meta.capabilities), 3)

        # Check normalize_audio function
        cap_names = [c.name for c in meta.capabilities]
        self.assertIn("normalize-audio", cap_names)
        self.assertIn("apply-bandpass-filter", cap_names)

        norm_cap = next(c for c in meta.capabilities if c.name == "normalize-audio")
        self.assertEqual(len(norm_cap.parameters), 3)
        self.assertEqual(norm_cap.parameters[0].name, "samples")
        self.assertTrue(norm_cap.parameters[0].required)
        self.assertFalse(norm_cap.parameters[1].required)

if __name__ == "__main__":
    unittest.main()
