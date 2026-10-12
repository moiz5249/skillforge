"""
test_cli_parser.py - Unit tests for CLI tool help parser.
"""

import unittest
from skillforge.compiler.cli_parser import CLIToolExtractor

class TestCLIToolExtractor(unittest.TestCase):
    def test_parse_help_text(self):
        sample_help = """
Usage: data-sync [OPTIONS]

Synchronizes distributed datasets across cloud buckets.

Options:
  -b, --bucket BUCKET   Target cloud storage bucket name
  -f, --force           Force overwrite existing files
  --dry-run             Simulate transfer without writing
  --help                Show this message and exit.
"""
        extractor = CLIToolExtractor(sample_help, is_command=False)
        meta = extractor.extract()

        self.assertEqual(meta.name, "data-sync")
        self.assertEqual(len(meta.capabilities), 1)
        cap = meta.capabilities[0]
        self.assertEqual(cap.name, "run-data-sync")
        self.assertGreaterEqual(len(cap.parameters), 3)

        param_names = [p.name for p in cap.parameters]
        self.assertIn("bucket", param_names)
        self.assertIn("force", param_names)
        self.assertIn("dry_run", param_names)

if __name__ == "__main__":
    unittest.main()
