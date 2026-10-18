from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tools.check_site import check_site


class GeneratedSiteTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def write(self, name, text=""):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def page(self, body="", name="index.html"):
        self.write(name, f"<!doctype html><html><body><h1>Portfolio</h1>{body}</body></html>")

    def test_rejects_missing_directory_and_zero_html_output(self):
        self.assertTrue(check_site(self.root / "absent"))
        self.write("assets/main.css", "body {}")
        self.assertTrue(check_site(self.root))

    def test_accepts_real_internal_pages_assets_and_fragments(self):
        self.page('<a href="/projects/?lang=pt#work">Work</a><a href="#top">Top</a><p id="top"></p><script src="/assets/main.js"></script><link href="/assets/main.css" rel="stylesheet"><img src="/photo.webp" alt="" width="600" height="800">')
        self.page('<section id="work"></section><a href="../index.html#top">Home</a>', "projects/index.html")
        for name in ("assets/main.js", "assets/main.css", "photo.webp"):
            self.write(name)
        self.assertEqual([], check_site(self.root))

    def test_rejects_missing_internal_paths_in_both_quote_styles(self):
        for quote in ('"', "'"):
            for tag, attribute in (("a", "href"), ("script", "src"), ("link", "href")):
                with self.subTest(quote=quote, tag=tag):
                    self.page(f"<{tag} {attribute}={quote}/missing{quote}></{tag}>")
                    self.assertTrue(check_site(self.root))

    def test_rejects_broken_local_and_cross_page_fragments(self):
        self.page("", "projects/index.html")
        for target in ("#missing", "/projects/#missing"):
            with self.subTest(target=target):
                self.page(f"<a href='{target}'>Missing</a>")
                self.assertTrue(check_site(self.root))

    def test_accepts_named_anchors_and_percent_encoded_paths_and_fragments(self):
        self.page('<a href="/project%20one/#sec%C3%A7%C3%A3o">Project</a>')
        self.page('<a name="secção"></a>', "project one/index.html")
        self.assertEqual([], check_site(self.root))

    def test_ignores_external_nonfile_urls_and_empty_fragments(self):
        self.page('<a href="https://example.com/missing#missing">External</a><a href="//example.com/missing">External</a><a href="mailto:hello@example.com">Email</a><a href="tel:123">Call</a><a href="#">Top</a><img src="data:image/png;base64,AAAA" alt="" width="1" height="1">')
        self.assertEqual([], check_site(self.root))

    def test_rejects_srcset_targets_on_images_and_picture_sources(self):
        self.write("small.webp")
        for quote in ('"', "'"):
            for tag in ("img", "source"):
                with self.subTest(quote=quote, tag=tag):
                    self.page(f"<{tag} srcset={quote}/small.webp 1x, /missing.webp 2x{quote} alt='' width='1' height='1'>")
                    self.assertTrue(check_site(self.root))

    def test_accepts_srcset_width_density_and_data_url_candidates(self):
        for name in ("small.webp", "large.webp"):
            self.write(name)
        self.page('<picture><source srcset="/small.webp 400w, /large.webp 800w"><img src="/small.webp" srcset="data:image/png;base64,AAAA 1x, /large.webp 2x" alt="Photo" width="800" height="600"></picture>')
        self.assertEqual([], check_site(self.root))

    def test_rejects_missing_image_alt_but_accepts_decorative_alt(self):
        self.write("photo.webp")
        self.page('<img src="/photo.webp" width="600" height="800">')
        self.assertTrue(check_site(self.root))
        self.page('<img src="/photo.webp" alt="" width="600" height="800">')
        self.assertEqual([], check_site(self.root))

    def test_rejects_missing_empty_or_nonpositive_image_dimensions(self):
        self.write("photo.webp")
        for dimensions in ('width="600"', 'height="800"', 'width="" height="800"', 'width="0" height="800"', 'width="600" height="-1"', 'width="100%" height="800"'):
            with self.subTest(dimensions=dimensions):
                self.page(f'<img src="/photo.webp" alt="Photo" {dimensions}>')
                self.assertTrue(check_site(self.root))

    def test_rejects_missing_or_duplicate_h1_per_page(self):
        for heading in ("", "<h1>First</h1><h1>Second</h1>"):
            with self.subTest(heading=heading):
                self.write("index.html", f"<html><body>{heading}</body></html>")
                self.assertTrue(check_site(self.root))

    def test_rejects_liquid_errors_and_unrendered_artifacts(self):
        for artifact in ("Liquid error: missing include", "Liquid Exception: invalid value", "Liquid syntax error", "{{ site.title }}", "{% include missing.html %}"):
            with self.subTest(artifact=artifact):
                self.page(artifact)
                self.assertTrue(check_site(self.root))

    def test_rejects_forbidden_privacy_tokens_in_text_attributes_and_comments(self):
        for body in ("Rodrigo Lopes", '<a href="https://rfa-lopes.example">Link</a>', '<!-- G-8CDPS3ZJPS -->', "Hockeyfy", "Corkified", "zaask.pt", "994952", "rfa.lopess@gmail.com", "RFA.LOPES", "Rodrigo&#32;Lopes"):
            with self.subTest(body=body):
                self.page(body)
                self.assertTrue(check_site(self.root))

    def test_rejects_links_outside_output_and_directories_without_index(self):
        (self.root / "empty").mkdir()
        for target in ("/empty/", "../../outside.html"):
            with self.subTest(target=target):
                self.page(f'<a href="{target}">Link</a>')
                self.assertTrue(check_site(self.root))

    def test_baseurl_is_stripped_only_at_path_boundary(self):
        self.write("photo.webp")
        self.page('<a href="/portfolio/projects/#work">Project</a><img src="/portfolio/photo.webp" alt="Photo" width="1" height="1">')
        self.page('<section id="work"></section><a href="../">Home</a>', "projects/index.html")
        self.assertEqual([], check_site(self.root, baseurl="/portfolio/"))
        self.page('<a href="/portfolio-other/projects/">Missing</a>')
        self.assertTrue(check_site(self.root, baseurl="/portfolio"))

    def test_cli_reports_counts_and_fails_without_echoing_private_values(self):
        self.page('<a href="#main">Main</a><main id="main"></main>')
        script = Path(__file__).resolve().parents[1] / "tools/check_site.py"
        result = subprocess.run([sys.executable, str(script), str(self.root)], capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("1 HTML page(s), 1 reference(s)", result.stdout)
        self.assertIn("0 generated-site problem(s)", result.stdout)
        self.page("Rodrigo Lopes")
        result = subprocess.run([sys.executable, str(script), str(self.root)], capture_output=True, text=True)
        self.assertNotEqual(0, result.returncode)
        self.assertNotIn("Rodrigo Lopes", result.stdout)


if __name__ == "__main__":
    unittest.main()
