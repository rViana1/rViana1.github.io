"""Validate generated HTML, local references, accessibility and privacy."""

import argparse
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

if __package__:
    from .check_source import FORBIDDEN
else:
    from check_source import FORBIDDEN


def srcset_urls(value):
    """Read candidate URLs without splitting the commas inside data URLs."""
    while value:
        value = value.lstrip(" \t\n\r\f,")
        if not value:
            break
        parts = value.split(maxsplit=1)
        url = parts[0]
        value = parts[1] if len(parts) > 1 else ""
        yield url.rstrip(",")
        if not url.endswith(","):
            _, separator, value = value.partition(",")
            if not separator:
                break


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids = set()
        self.references = []
        self.problems = []
        self.headings = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id"):
            self.ids.add(attrs["id"])
        if tag == "a" and attrs.get("name"):
            self.ids.add(attrs["name"])
        if tag == "h1":
            self.headings += 1
        for key in ("href", "src", "poster"):
            if attrs.get(key):
                self.references.append(attrs[key])
        if attrs.get("srcset"):
            self.references.extend(srcset_urls(attrs["srcset"]))
        if tag == "img":
            if attrs.get("alt") is None:
                self.problems.append("image missing alt")
            for key in ("width", "height"):
                value = attrs.get(key) or ""
                if not value.isascii() or not value.isdecimal() or int(value) <= 0:
                    self.problems.append(f"image missing positive {key}")


def inspect_site(root: Path, baseurl: str = ""):
    root = Path(root).resolve()
    baseurl = "/" + baseurl.strip("/") if baseurl.strip("/") else ""
    problems = []
    pages = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".html", ".htm"}:
            continue
        relative = path.relative_to(root)
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            problems.append(f"{relative}: cannot read generated HTML")
            continue
        page = Page()
        page.feed(text)
        page.close()
        pages[path.resolve()] = page
        problems.extend(f"{relative}: {problem}" for problem in page.problems)
        if page.headings != 1:
            problems.append(f"{relative}: expected one h1, found {page.headings}")
        decoded = unescape(text).casefold()
        if any(token.casefold() in decoded for token in FORBIDDEN):
            problems.append(f"{relative}: forbidden inherited identity")
        if any(token in decoded for token in ("liquid error", "liquid exception", "liquid syntax error", "{{", "{%")):
            problems.append(f"{relative}: Liquid error or unrendered artifact")
    if not pages:
        problems.append("no generated HTML pages")
    for path, page in pages.items():
        relative = path.relative_to(root)
        for reference in page.references:
            try:
                url = urlsplit(reference)
            except ValueError:
                problems.append(f"{relative}: invalid reference URL")
                continue
            if url.scheme or url.netloc:
                continue
            target_path = unquote(url.path)
            if target_path.startswith("/"):
                if baseurl and (target_path == baseurl or target_path.startswith(baseurl + "/")):
                    target_path = target_path[len(baseurl):]
                target = root / target_path.lstrip("/")
            else:
                target = path.parent / target_path if target_path else path
            target = target.resolve()
            if not target.is_relative_to(root):
                problems.append(f"{relative}: internal target outside generated site")
                continue
            if target.is_dir():
                target = target / "index.html"
            if not target.is_file():
                problems.append(f"{relative}: missing internal target")
                continue
            if url.fragment and target.suffix.lower() in {".html", ".htm"}:
                target_page = pages.get(target)
                if target_page is None or unquote(url.fragment) not in target_page.ids:
                    problems.append(f"{relative}: broken internal fragment")
    return problems, pages


def check_site(root: Path, baseurl: str = "") -> list[str]:
    return inspect_site(root, baseurl)[0]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, nargs="?", default=Path("_site-test"))
    parser.add_argument("--baseurl", default="")
    args = parser.parse_args()
    problems, pages = inspect_site(args.root, args.baseurl)
    for problem in problems:
        print(problem)
    print(f"{len(pages)} HTML page(s), {sum(len(page.references) for page in pages.values())} reference(s)")
    print(f"{len(problems)} generated-site problem(s)")
    raise SystemExit(bool(problems))
