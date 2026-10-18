from pathlib import Path
from html.parser import HTMLParser
import json
import re
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

    def test_translatable_fields_cannot_be_replaced_with_scalars(self):
        source_root = Path(__file__).resolve().parents[1]
        cases = (
            ("admin/_data/ui.yml", "cta_contact:\n  en: Get in touch\n  pt: Entrar em contacto", "cta_contact: Get in touch"),
            ("admin/_data/profile.yml", "headline:\n  en: Junior Software Engineer\n  pt: Engenheiro de Software Júnior", "headline: Junior Software Engineer"),
            ("admin/_data/profile.yml", "bio:\n  en: Computer Engineering graduate with a data engineering internship at Medana.ai. I build software projects and am continuing my studies with a master's in Informatics.\n  pt: Licenciado em Engenharia Informática, com um estágio em engenharia de dados na Medana.ai. Desenvolvo projetos de software e continuo a minha formação num mestrado em Informática.", "bio: Computer Engineering graduate"),
            ("admin/_data/profile.yml", "focus:\n  en: Software development and data engineering\n  pt: Desenvolvimento de software e engenharia de dados", "focus: Software development"),
            ("admin/_data/contacts.yml", "location:\n  en: Portugal\n  pt: Portugal", "location: Portugal"),
            ("admin/_data/nav.yml", "  label:\n    en: Home\n    pt: Início", "  label: Home"),
            ("admin/_data/skills.yml", "- group:\n    en: Data engineering\n    pt: Engenharia de dados", "- group: Data engineering"),
            ("admin/_data/skills.yml", "  evidence:\n    en: Applied during the Medana.ai internship.\n    pt: Aplicação durante o estágio na Medana.ai.", "  evidence: Applied during the internship"),
            ("admin/_data/languages.yml", "- name:\n    en: Portuguese\n    pt: Português", "- name: Portuguese"),
            ("admin/_data/languages.yml", "  level:\n    en: Native\n    pt: Nativo", "  level: Native"),
            ("admin/_data/languages.yml", "  note:\n    en: Mother tongue.\n    pt: Língua materna.", "  note: Mother tongue"),
            ("admin/_data/tags.yml", "internship:\n  en: Internship\n  pt: Estágio", "internship: Internship"),
            ("admin/_projects/codelp.md", "subtitle:\n  en: Repository understanding tool · In development\n  pt: Ferramenta de compreensão de repositórios · Em desenvolvimento", "subtitle: Repository understanding tool"),
            ("admin/_projects/codelp.md", "  - label:\n      en: Source code on GitHub\n      pt: Código-fonte no GitHub", "  - label: Source code on GitHub"),
        )
        for index, (relative, original, replacement) in enumerate(cases):
            with self.subTest(path=relative, replacement=replacement):
                source = (source_root / relative).read_text(encoding="utf-8")
                self.assertEqual(1, source.count(original))
                self.write(f"{index}/{relative}", source.replace(original, replacement))
                self.assertTrue(check_source.scan(self.root / str(index)))

    def test_nontranslatable_scalar_fields_remain_valid(self):
        source_root = Path(__file__).resolve().parents[1]
        for relative in ("admin/_data/profile.yml", "admin/_data/nav.yml", "admin/_data/skills.yml", "admin/_projects/codelp.md", "admin/_experience/medana-ai.md"):
            self.write(relative, (source_root / relative).read_text(encoding="utf-8"))
        self.assertEqual([], check_source.scan(self.root))


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
        self.bilingual(profile["bio"])
        self.bilingual(profile["focus"])
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
                    for link in metadata.get("links", []):
                        self.bilingual(link["label"])
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
        for name in ("ui", "tags"):
            for value in self.yaml(self.root / f"admin/_data/{name}.yml").values():
                self.bilingual(value)
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
        for item in languages:
            for field in ("name", "level", "note"):
                self.bilingual(item[field])
        self.assertEqual([], check_source.scan(self.root))


class PublicPageTests(unittest.TestCase):
    root = PortfolioContentTests.root
    yaml = PortfolioContentTests.yaml
    bilingual = PortfolioContentTests.bilingual

    def test_navigation_pages_and_404_have_metadata_and_one_heading(self):
        for route in ('/', '/experience/', '/education/', '/projects/', '/skills/', '/hobbies/', '/languages/', '/contacts/', '/404.html'):
            name = 'index.html' if route == '/' else route.strip('/').removesuffix('.html') + '.html'
            with self.subTest(route=route):
                path = self.root / name
                metadata = self.yaml(path, front_matter=True)
                self.assertEqual(route, metadata['permalink'])
                self.assertEqual('default', metadata['layout'])
                self.bilingual(metadata['title'])
                self.bilingual(metadata['summary'])
                self.assertEqual(1, len(re.findall(r'<h1\b', path.read_text())))

    def test_home_has_three_approved_metrics_and_shared_content(self):
        path = self.root / 'index.html'
        self.assertTrue(path.is_file(), 'Missing Home page')
        source = path.read_text()
        self.assertEqual(3, source.count('class="metric"'))
        for text in ('18/20', '55,000', '55 000', 'More than 10', 'Mais de 10'):
            self.assertIn(text, source)
        for text in ('site.data.profile', 'site.data.nav', 'project-card.html', 'contact-links.html', '/images/profile/ricardo-viana.webp'):
            self.assertIn(text, source)

    def test_project_pages_reuse_featured_experience_urls(self):
        for name in ('index.html', 'projects.html'):
            path = self.root / name
            self.assertTrue(path.is_file(), f'Missing {name}')
            source = path.read_text()
            self.assertIn("site.experience | where: 'featured_project', true", source)
            self.assertIn("site.projects | concat: featured_experience | sort: 'project_order'", source)
            self.assertIn('include project-card.html item=item', source)
        card = self.root / '_includes/project-card.html'
        self.assertTrue(card.is_file(), 'Missing project card')
        source = card.read_text()
        self.assertIn('include.item.url | relative_url', source)
        self.assertIn('include.item.summary.en', source)
        self.assertNotIn('/projects/medana', source)

    def test_collection_lists_reuse_timeline_and_detail_navigation(self):
        for collection in ('experience', 'education', 'hobbies'):
            path = self.root / f'{collection}.html'
            self.assertTrue(path.is_file(), f'Missing {collection} list')
            self.assertIn(f'include timeline.html collection="{collection}"', path.read_text())
        timeline = self.root / '_includes/timeline.html'
        self.assertTrue(timeline.is_file(), 'Missing timeline')
        self.assertIn('item.url | relative_url', timeline.read_text())
        detail = (self.root / '_layouts/detail.html').read_text()
        self.assertIn('site[page.collection]', detail)
        self.assertIn('rel="prev"', detail)
        self.assertIn('rel="next"', detail)
        self.assertIn('page.cover', detail)

    def test_end_only_period_has_a_rendering_branch_and_callers_allow_it(self):
        period = (self.root / '_includes/period.html').read_text()
        self.assertRegex(period, r"elsif include.end and include.end != ''[^%]*%}\s*{% include date_label.html d=include.end %}")
        for name, item in (('_layouts/detail.html', 'page'), ('_includes/timeline.html', 'item')):
            path = self.root / name
            self.assertTrue(path.is_file(), f'Missing {name}')
            self.assertIn(f'if {item}.start or {item}.end', path.read_text())


class RenderedPublicPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        available = subprocess.run(['ruby', '-e', "require 'jekyll'; require 'kramdown-parser-gfm'; require 'jekyll-sitemap'"], capture_output=True, text=True)
        if available.returncode:
            raise unittest.SkipTest('Jekyll runtime unavailable; run with the installed project gems')
        harness = r'''
require 'jekyll'
require 'json'
require 'tmpdir'
Dir.mktmpdir do |destination|
  site = Jekyll::Site.new(Jekyll.configuration('source' => Dir.pwd, 'destination' => destination, 'quiet' => true))
  site.reset
  site.read
  site.generate
  site.render
  pages = (site.pages + site.collections.values.flat_map(&:docs)).to_h { |page| [page.url, page.output] }
  periods = [
    '{% include period.html %}',
    '{% include period.html end="2026-07" %}',
    '{% include period.html start="2025-09" %}',
    '{% include period.html start="2025-09" end="2026-05" %}',
    '{% include period.html start="2026-07" end="2026-07" %}'
  ].map { |source| Liquid::Template.parse(source).render!(site.site_payload, registers: { site: site }) }
  puts JSON.generate('pages' => pages, 'periods' => periods)
end
'''
        result = subprocess.run(['ruby', '-e', harness], cwd=PortfolioContentTests.root, capture_output=True, text=True)
        if result.returncode:
            raise AssertionError(result.stderr)
        cls.rendered = json.loads(result.stdout)

    def test_all_sections_render_one_heading_bilingual_metadata_and_content(self):
        for route in ('/', '/experience/', '/education/', '/projects/', '/skills/', '/hobbies/', '/languages/', '/contacts/', '/404.html'):
            with self.subTest(route=route):
                html = self.rendered['pages'][route]
                self.assertEqual(1, len(re.findall(r'<h1\b', html)))
                self.assertNotIn('Liquid error', html)
                self.assertRegex(html, r'<title[^>]*data-pt="[^"]+"')
                self.assertIn('data-l="pt"', html)

    def test_projects_have_three_cards_with_correct_detail_destinations(self):
        for route in ('/', '/projects/'):
            html = self.rendered['pages'][route]
            self.assertEqual(3, html.count('class="project-card"'))
            cards = re.findall(r'<article class="project-card">(.*?)</article>', html, re.S)
            for card, destination in zip(cards, ('/experience/medana-ai/', '/projects/codelp/', '/projects/bionic-hand/')):
                self.assertIn(f'href="{destination}"', card)
            self.assertNotIn('/projects/medana-ai/', html)

    def test_timelines_and_detail_navigation_cover_all_collections(self):
        for collection, slugs in {
            'experience': ['medana-ai', 'screen-printing', 'hockey-coach'],
            'education': ['masters-informatics', 'computer-engineering', 'programming-technician', 'python-iefp'],
            'projects': ['codelp', 'bionic-hand'],
            'hobbies': ['roller-hockey'],
        }.items():
            listing = self.rendered['pages'][f'/{collection}/']
            for i, slug in enumerate(slugs):
                with self.subTest(collection=collection, slug=slug):
                    self.assertIn(f'href="/{collection}/{slug}/"', listing)
                    detail = self.rendered['pages'][f'/{collection}/{slug}/']
                    self.assertIn(f'href="/{collection}/"', detail)
                    self.assertEqual(len(slugs) > 1, 'aria-label="More in this section / Mais nesta secção"' in detail)
                    self.assertEqual(i > 0, 'rel="prev"' in detail)
                    self.assertEqual(i < len(slugs) - 1, 'rel="next"' in detail)
                    if i:
                        self.assertIn(f'rel="prev" href="/{collection}/{slugs[i-1]}/"', detail)
                    if i < len(slugs) - 1:
                        self.assertIn(f'rel="next" href="/{collection}/{slugs[i+1]}/"', detail)

    def test_period_handles_missing_single_and_equal_endpoints(self):
        empty, end_only, start_only, both, equal = self.rendered['periods']
        self.assertEqual('', empty.strip())
        self.assertIn('Jul 2026', end_only)
        self.assertIn('jul 2026', end_only)
        self.assertNotIn('Present', end_only)
        self.assertIn('Present', start_only)
        self.assertIn('Atualidade', start_only)
        self.assertIn('Sep 2025', both)
        self.assertIn('May 2026', both)
        self.assertEqual(1, equal.count('<time'))
        for route in ('/education/', '/education/computer-engineering/'):
            self.assertIn('Jul 2026', self.rendered['pages'][route])


class ShellTests(unittest.TestCase):
    root = Path(__file__).resolve().parents[1]

    def source(self, name):
        path = self.root / name
        self.assertTrue(path.is_file(), f"Missing shell component: {name}")
        return path.read_text(encoding="utf-8")

    def test_shell_has_one_main_skip_link_and_language_agnostic_content(self):
        layout = self.source("_layouts/default.html")
        self.assertEqual(1, len(re.findall(r"<main\b", layout)))
        self.assertIn('id="main-content"', layout)
        self.assertIn('href="#main-content"', layout)
        self.assertIn('{{ content }}', layout)
        self.assertNotIn('page.collection', layout)
        self.assertIn('lang="en"', layout)
        translation = self.source("_includes/i18n.html")
        for language in ("en", "pt"):
            self.assertIn(f'data-l="{language}"', translation)
            self.assertIn(f'lang="{language}"', translation)

    def test_controls_have_labels_and_navigation_has_full_name(self):
        header = self.source("_includes/header.html")
        self.assertIn('Ricardo Viana', header)
        class Controls(HTMLParser):
            def __init__(self):
                super().__init__()
                self.buttons = []
            def handle_starttag(self, tag, attrs):
                if tag == "button":
                    self.buttons.append(dict(attrs))
        parser = Controls()
        parser.feed(header)
        self.assertGreaterEqual(len(parser.buttons), 3)
        for button in parser.buttons:
            self.assertEqual("button", button.get("type"))
            self.assertTrue(button.get("aria-label"))
        self.assertIn('aria-controls="site-nav"', header)
        self.assertIn('aria-expanded="false"', header)

    def test_focus_targets_reduced_motion_and_no_js_content(self):
        css = self.source("assets/css/main.css")
        self.assertIn(':focus-visible', css)
        self.assertRegex(css, r'min-height:\s*44px')
        self.assertRegex(css, r'min-width:\s*44px')
        self.assertIn('prefers-reduced-motion: reduce', css)
        self.assertIn('html[data-lang="en"] [data-l="pt"]', css)
        self.assertIn('html[data-lang="pt"] [data-l="en"]', css)
        self.assertNotRegex(css, r'(?m)^\[data-l[^\n]*display:\s*none')

    def test_both_palettes_meet_text_contrast(self):
        css = self.source("assets/css/main.css")
        palettes = re.findall(r'(?:\:root|\[data-theme="light"\])\s*\{([^}]+)', css)
        self.assertEqual(2, len(palettes))
        def luminance(hex_value):
            values = [int(hex_value[i:i+2], 16) / 255 for i in (1, 3, 5)]
            linear = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in values]
            return sum(v * weight for v, weight in zip(linear, (.2126, .7152, .0722)))
        for palette in palettes:
            tokens = dict(re.findall(r'--([\w-]+):\s*(#[\da-fA-F]{6})', palette))
            for foreground in ('text', 'muted', 'primary'):
                for background in ('bg', 'surface'):
                    a, b = sorted((luminance(tokens[foreground]), luminance(tokens[background])))
                    self.assertGreaterEqual((b + .05) / (a + .05), 4.5, (foreground, background))

    def test_shell_has_no_remote_assets_or_inherited_tracking(self):
        for name in ('_includes/head.html', '_includes/header.html', '_includes/footer.html', '_includes/skill.html', 'assets/js/main.js', 'assets/css/main.css'):
            text = self.source(name)
            self.assertNotRegex(text, r'(?:src=|@import|url\()[\s\"\']*https?://')
            self.assertNotRegex(text.lower(), r'gtag|analytics|devicon|zaask')
        self.assertEqual([], check_source.scan(self.root))

    def test_media_derivatives_have_no_identifying_metadata(self):
        for name, dimensions in (("images/profile/ricardo-viana.webp", (600, 800)), ("images/projects/codelp/workspace.webp", (1440, 810))):
            path = self.root / name
            self.assertTrue(path.is_file(), f"Missing derivative: {name}")
            raw = path.read_bytes()
            self.assertEqual(b'RIFF', raw[:4])
            self.assertEqual(b'WEBP', raw[8:12])
            offset = 12
            chunks = []
            actual_dimensions = None
            while offset < len(raw):
                kind = raw[offset:offset+4]
                size = int.from_bytes(raw[offset+4:offset+8], 'little')
                chunks.append(kind)
                if kind == b'VP8 ':
                    payload = raw[offset+8:offset+8+size]
                    self.assertEqual(b'\x9d\x01\x2a', payload[3:6])
                    actual_dimensions = tuple(int.from_bytes(payload[i:i+2], 'little') & 0x3fff for i in (6, 8))
                offset += 8 + size + size % 2
            self.assertFalse({b'EXIF', b'XMP ', b'IPTC', b'ICCP'} & set(chunks))
            self.assertEqual(len(raw), offset)
            self.assertEqual(dimensions, actual_dimensions)

    def test_head_emits_bilingual_metadata_with_english_defaults(self):
        head = self.source("_includes/head.html")
        self.assertIn('page.title.pt', head)
        self.assertIn('page.summary.pt', head)
        self.assertIn('site.data.profile.bio.pt', head)
        self.assertRegex(head, r'<title[^>]*data-en="{{ title_en \| escape }}"[^>]*data-pt="{{ title_pt \| escape }}"[^>]*>{{ title_en \| escape }}</title>')
        self.assertRegex(head, r'<meta name="description" content="{{ description_en \| escape }}"[^>]*data-en="{{ description_en \| escape }}"[^>]*data-pt="{{ description_pt \| escape }}"')
        self.assertEqual(1, head.count('<title'))
        self.assertEqual(1, head.count('name="description"'))

    def test_language_metadata_theme_and_menu_behaviour(self):
        script = self.source("assets/js/main.js")
        harness = r'''
const vm = require('node:vm');
const assert = require('node:assert/strict');
const source = SOURCE;
function run(language, saved = {}, blocked = false) {
  const listeners = {};
  const node = () => ({ dataset: {}, attrs: {}, hidden: true, focused: false,
    setAttribute(k,v) { this.attrs[k] = String(v); },
    addEventListener(k,fn) { this[k] = fn; }, focus() { this.focused = true; } });
  const root = node(), en = node(), pt = node(), theme = node(), menu = node(), nav = node();
  const title = node(), description = node();
  title.dataset = {en: "Master's in Informatics · Ricardo Viana", pt: 'Mestrado em Informática · Ricardo Viana'};
  description.dataset = {en: 'Continuing my studies in Informatics.', pt: 'Continuação dos estudos em Informática.'};
  description.content = description.dataset.en;
  en.dataset.setLang = 'en'; pt.dataset.setLang = 'pt';
  nav.contains = () => true;
  const document = { documentElement: root, title: title.dataset.en,
    querySelectorAll: () => [en, pt],
    querySelector: s => ({'#theme-toggle': theme, '#menu-toggle': menu, '#site-nav': nav, 'title': title, 'meta[name="description"]': description})[s],
    addEventListener: (k,fn) => listeners[k] = fn };
  vm.runInNewContext(source, {document, navigator: {language},
    localStorage: {getItem(k) { if(blocked) throw Error(); return saved[k]; }, setItem(k,v) { if(blocked) throw Error(); saved[k] = v; }},
    matchMedia: () => ({matches: false})});
  return {root, en, pt, theme, menu, nav, saved, listeners, document, description};
}
let page = run('pt-PT');
assert.equal(page.root.dataset.lang, 'pt');
assert.equal(page.root.lang, 'pt');
assert.equal(page.document.title, 'Mestrado em Informática · Ricardo Viana');
assert.equal(page.description.content, 'Continuação dos estudos em Informática.');
page.en.click();
assert.equal(page.root.dataset.lang, 'en');
assert.equal(page.saved['rv-language'], 'en');
assert.equal(page.en.attrs['aria-pressed'], 'true');
assert.equal(page.document.title, "Master's in Informatics · Ricardo Viana");
assert.equal(page.description.content, 'Continuing my studies in Informatics.');
page.pt.click();
assert.equal(page.document.title, 'Mestrado em Informática · Ricardo Viana');
assert.equal(page.description.content, 'Continuação dos estudos em Informática.');
page.theme.click();
assert.equal(page.saved['rv-theme'], 'light');
page.menu.click();
assert.equal(page.menu.attrs['aria-expanded'], 'true');
assert.equal(page.nav.hidden, false);
page.listeners.keydown({key: 'Escape'});
assert.equal(page.menu.attrs['aria-expanded'], 'false');
assert.equal(page.menu.focused, true);
page.menu.focused = false;
page.menu.click(); page.menu.click();
assert.equal(page.menu.focused, true);
page = run('pt-BR', {'rv-language': 'en', 'rv-theme': 'light'});
assert.equal(page.root.dataset.lang, 'en');
assert.equal(page.root.dataset.theme, 'light');
assert.equal(page.document.title, "Master's in Informatics · Ricardo Viana");
assert.equal(page.description.content, 'Continuing my studies in Informatics.');
page = run('en-US', {'rv-language': 'pt'});
assert.equal(page.document.title, 'Mestrado em Informática · Ricardo Viana');
assert.equal(page.description.content, 'Continuação dos estudos em Informática.');
page = run('fr', {'rv-language': 'invalid', 'rv-theme': 'invalid'});
assert.equal(page.root.dataset.lang, 'en');
assert.equal(page.root.dataset.theme, 'dark');
page = run('pt-PT', {}, true);
assert.equal(page.root.dataset.lang, 'pt');
page.en.click(); page.theme.click();
assert.equal(page.root.dataset.lang, 'en');
console.log('language/theme/menu checks passed');
'''.replace('SOURCE', json.dumps(script))
        result = subprocess.run(['node', '-e', harness], capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stderr)


if __name__ == "__main__":
    unittest.main()
