from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tools import check_source


class SourceSafetyTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def test_forbidden_owner_tokens_in_public_sources(self):
        for token in (
            "Rodrigo Lopes", "rfa-lopes", "rfa.lopes", "rfa.lopess@gmail.com",
            "G-8CDPS3ZJPS", "994952", "Hockeyfy", "Corkified", "zaask.pt",
        ):
            with self.subTest(token=token):
                self.write("index.html", token)
                self.assertTrue(check_source.scan(self.root))

    def test_phone_shaped_public_values(self):
        for value in ("+351 912 345 678", "912345678", "(212) 555-0123", "212.555.0123"):
            with self.subTest(value=value):
                self.write("index.html", f"<p>{value}</p>")
                self.assertTrue(check_source.scan(self.root))

    def test_adjacent_phone_numbers_are_detected_individually(self):
        for value in ("912345678 923456789", "Call 912345678 (+351 923 456 789)"):
            with self.subTest(value=value):
                self.write("index.html", f"<p>{value}</p>")
                self.assertIn("index.html: phone-shaped public value", check_source.scan(self.root))

    def test_long_unbroken_identifier_is_not_a_phone_candidate(self):
        self.write("index.html", "<p>1234567890123456</p>")
        self.assertEqual([], check_source.scan(self.root))

    def test_private_field_names(self):
        for key in ("street_address", "street-address", "address", "morada", "date_of_birth", "birth_date", "dob", "data_nascimento"):
            with self.subTest(key=key):
                self.write("admin/_data/profile.yml", f"{key}: example\n")
                self.assertTrue(check_source.scan(self.root))

    def test_private_keys_inside_lists_and_json(self):
        for text in ("- street_address: example\n", '{"address": "example"}'):
            with self.subTest(text=text):
                self.write("admin/_data/profile.yml", text)
                self.assertTrue(check_source.scan(self.root))

    def test_missing_or_empty_bilingual_mapping(self):
        for value in ("  en: Hello\n", "  pt: Olá\n", "  en: Hello\n  pt: ''\n", "  en: null\n  pt: Olá\n"):
            with self.subTest(value=value):
                self.write("admin/_data/profile.yml", "headline:\n" + value)
                self.assertTrue(check_source.scan(self.root))

    def test_markdown_front_matter_requires_both_languages(self):
        self.write("admin/_experience/example.md", "---\ntitle:\n  en: Example\n---\nBody\n")
        self.assertTrue(check_source.scan(self.root))

    def test_collection_titles_cannot_skip_bilingual_structure(self):
        self.write("admin/_experience/example.md", "---\ntitle: Example\n---\nBody\n")
        self.assertTrue(check_source.scan(self.root))

    def test_clean_bilingual_sources(self):
        self.write("admin/_data/profile.yml", "name: Ricardo Viana\nheadline:\n  en: Engineer\n  pt: Engenheiro\n")
        self.write("admin/_experience/example.md", "---\ntitle:\n  en: Example\n  pt: Exemplo\n---\nBody\n")
        self.write("assets/style.css", "body { color: #123456; }\n")
        self.assertEqual([], check_source.scan(self.root))

    def test_bilingual_block_values_cannot_be_empty(self):
        self.write("admin/_data/profile.yml", "bio:\n  en: |\n    Hello\n  pt: |\n")
        self.assertTrue(check_source.scan(self.root))

    def test_clean_bilingual_blocks_and_multiple_records(self):
        self.write("admin/_data/profile.yml", "bio:\n  en: |\n    Hello\n  pt: |\n    Olá\n")
        self.write("admin/_data/skills.yml", "- title:\n    en: First\n    pt: Primeiro\n- title:\n    en: Second\n    pt: Segundo\n")
        self.assertEqual([], check_source.scan(self.root))

    def test_nonpublic_and_generated_files_are_ignored(self):
        for directory in (".git", ".superpowers", "_site", "_site-test", "__pycache__", "tests", "tools", "vendor", "node_modules"):
            self.write(f"{directory}/example.md", "Rodrigo Lopes")
        (self.root / "photo.png").write_bytes(b"\x89PNG\x00Rodrigo Lopes")
        self.assertEqual([], check_source.scan(self.root))

    def test_cli_failure_does_not_echo_private_values(self):
        self.write("index.html", "+351 912 345 678")
        result = subprocess.run([sys.executable, str(Path(check_source.__file__)), str(self.root)], capture_output=True, text=True)
        self.assertNotEqual(0, result.returncode)
        self.assertNotIn("912 345 678", result.stdout)


if __name__ == "__main__":
    unittest.main()
