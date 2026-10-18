from pathlib import Path
import json
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
        self.write("admin/_experience/example.md", "---\ntitle:\n  en: Example\n  pt: Exemplo\nsummary:\n  en: Work\n  pt: Trabalho\nhighlights:\n  - en: A result\n    pt: Um resultado\n---\nEnglish story.\n\n<!--pt-->\n\nHistória em português.\n")
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

    def test_collection_required_fields_and_long_form_cannot_be_omitted(self):
        valid = "---\ntitle:\n  en: Example\n  pt: Exemplo\nsummary:\n  en: Work\n  pt: Trabalho\nhighlights:\n  - en: A result\n    pt: Um resultado\n---\nEnglish story.\n\n<!--pt-->\n\nHistória em português.\n"
        invalid = (
            valid.replace("summary:\n  en: Work\n  pt: Trabalho\n", ""),
            valid.replace("highlights:\n  - en: A result\n    pt: Um resultado\n", ""),
            valid.replace("    pt: Um resultado\n", ""),
            valid.replace("<!--pt-->", ""),
            valid.replace("História em português.", ""),
            valid.replace("English story.", ""),
        )
        for text in invalid:
            with self.subTest(text=text):
                self.write("admin/_experience/example.md", text)
                self.assertTrue(check_source.scan(self.root))


class PortfolioContentTests(unittest.TestCase):
    root = Path(__file__).resolve().parents[1]

    def yaml(self, path, front_matter=False):
        self.assertTrue(path.is_file(), f"Missing content: {path.relative_to(self.root)}")
        text = path.read_text(encoding="utf-8")
        if front_matter:
            text = text.split("---", 2)[1]
        # Use the same YAML runtime as Jekyll without adding a Python dependency.
        result = subprocess.run(
            ["ruby", "-ryaml", "-rjson", "-e", "puts JSON.generate(YAML.safe_load(STDIN.read))"],
            input=text, capture_output=True, text=True, check=True,
        )
        return json.loads(result.stdout)

    def bilingual(self, value):
        self.assertIsInstance(value, dict)
        for language in ("en", "pt"):
            self.assertIsInstance(value.get(language), str)
            self.assertTrue(value[language].strip())

    def test_only_approved_public_contacts_and_identity(self):
        contacts = self.yaml(self.root / "admin/_data/contacts.yml")
        self.assertEqual({
            "email": "ricardojcviana@gmail.com",
            "linkedin": "https://www.linkedin.com/in/rviana01/",
            "github": "https://github.com/rViana1",
            "location": {"en": "Portugal", "pt": "Portugal"},
        }, contacts)
        profile = self.yaml(self.root / "admin/_data/profile.yml")
        self.assertEqual("Ricardo Viana", profile["name"])
        self.bilingual(profile["headline"])
        self.assertEqual("Junior Software Engineer", profile["headline"]["en"])
        self.assertFalse({"phone", "address", "birth_date", "date_of_birth"} & profile.keys())

    def test_navigation_has_eight_bilingual_destinations(self):
        nav = self.yaml(self.root / "admin/_data/nav.yml")
        self.assertEqual(
            ["/", "/experience/", "/projects/", "/education/", "/skills/", "/hobbies/", "/languages/", "/contacts/"],
            [item["url"] for item in nav],
        )
        for item in nav:
            self.bilingual(item["label"])
            self.assertTrue(item["show"])

    def test_required_collections_are_bilingual_and_have_no_empty_cards(self):
        expected = {
            "_experience": {"medana-ai", "screen-printing", "hockey-coach"},
            "_education": {"masters-informatics", "computer-engineering", "programming-technician", "python-iefp"},
            "_projects": {"codelp", "bionic-hand"},
            "_hobbies": {"roller-hockey"},
        }
        for collection, slugs in expected.items():
            directory = self.root / "admin" / collection
            self.assertEqual(slugs, {path.stem for path in directory.glob("*.md")})
            for path in directory.glob("*.md"):
                with self.subTest(item=path.stem):
                    metadata = self.yaml(path, front_matter=True)
                    for field in ("title", "summary", "subtitle"):
                        self.bilingual(metadata[field])
                    self.assertTrue(metadata["highlights"])
                    for highlight in metadata["highlights"]:
                        self.bilingual(highlight)
                    body = path.read_text(encoding="utf-8").split("---", 2)[2]
                    self.assertEqual(1, body.count("<!--pt-->"))
                    self.assertTrue(all(len(part.strip()) > 30 for part in body.split("<!--pt-->")))

    def test_exactly_three_launch_projects_reuse_medana_experience(self):
        projects = []
        for collection in ("_projects", "_experience"):
            for path in (self.root / "admin" / collection).glob("*.md"):
                metadata = self.yaml(path, front_matter=True)
                if collection == "_projects" or metadata.get("featured_project"):
                    projects.append((metadata["project_order"], path.stem))
        self.assertEqual([(1, "medana-ai"), (2, "codelp"), (3, "bionic-hand")], sorted(projects))
        self.assertEqual(1, len(list((self.root / "admin").rglob("medana-ai.md"))))
        codelp = self.yaml(self.root / "admin/_projects/codelp.md", front_matter=True)
        self.assertEqual("active", codelp["status"])
        self.assertEqual("https://github.com/rViana1/codelp", codelp["links"][0]["url"])

    def test_global_data_is_bilingual_and_skills_match_approved_evidence(self):
        for name in ("profile", "contacts", "nav", "skills", "languages", "tags", "ui"):
            path = self.root / f"admin/_data/{name}.yml"
            self.yaml(path)
            self.assertEqual([], check_source.bilingual_problems(path.read_text(encoding="utf-8")))
        skills = self.yaml(self.root / "admin/_data/skills.yml")
        self.assertEqual({
            "Java", "C#", "C", "JavaScript", "SQL", "Python", "Pandas", "regex", "OCR", "ETL",
            "CSV/JSON", "AWS Bedrock/LLM evaluation", "React", "React Native", "HTML", "CSS", "Git",
            "Linux", "MySQL", "MongoDB",
        }, {item["name"] for group in skills for item in group["items"]})
        for group in skills:
            self.bilingual(group["group"])
            self.bilingual(group["evidence"])
        languages = self.yaml(self.root / "admin/_data/languages.yml")
        self.assertEqual(["Portuguese", "English"], [item["name"]["en"] for item in languages])
        self.assertEqual("Native", languages[0]["level"]["en"])
        self.assertEqual("B2", languages[1]["cefr"])


if __name__ == "__main__":
    unittest.main()
