"""Check publishable text for inherited identity, private fields and EN/PT gaps."""

from pathlib import Path
import re
import sys


FORBIDDEN = (
    "Rodrigo Lopes", "rfa-lopes", "rfa.lopes", "rfa.lopess@gmail.com",
    "G-8CDPS3ZJPS", "994952", "Hockeyfy", "Corkified", "zaask.pt",
)
IGNORED = {
    ".git", ".superpowers", "__pycache__", ".pytest_cache", ".jekyll-cache",
    ".sass-cache", "tests", "tools", "vendor", "node_modules", ".bundle",
}
BINARY = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".woff", ".woff2", ".ttf", ".mp4", ".mp3", ".zip"}
PHONE = re.compile(r"(?<![\w#])\+?\(?\d(?:[ ()+.\-]*\d){8,14}(?!\w)")
PRIVATE_KEY = re.compile(
    r"(?im)(?:^|[,{])\s*(?:-\s*)?[\"']?(?:street[_ -]?address|address|morada|date[_ -]?of[_ -]?birth|birth[_ -]?date|dob|data[_ -]?(?:de[_ -]?)?nascimento)[\"']?\s*:"
)
MAPPING = re.compile(r"^( *)(?:- )?([\w-]+):\s*(.*?)\s*$")


def bilingual_problems(text: str, required_fields=()) -> list[str]:
    """Validate the project's indented YAML en/pt sibling mappings."""
    # shortcut: indented YAML mappings only; extend if the authoring format changes.
    groups = {}
    missing = set(required_fields)
    stack = [(-1, ())]
    lines = text.splitlines()
    for index, line in enumerate(lines):
        match = MAPPING.match(line)
        if not match:
            continue
        spaces, key, value = match.groups()
        indent = len(spaces)
        while stack[-1][0] >= indent:
            stack.pop()
        if line[indent:].startswith("- "):
            stack.append((indent, stack[-1][1] + (f"item@{index + 1}",)))
            indent += 2
        parent = stack[-1][1]
        if not parent:
            missing.discard(key)
        if key in {"en", "pt"}:
            value = value.split(" #", 1)[0].strip()
            if value in {"|", ">", "|-", ">-", "|+", ">+"}:
                value = ""
                for following in lines[index + 1:]:
                    if following.strip() and len(following) - len(following.lstrip()) <= indent:
                        break
                    if following.strip() and not following.lstrip().startswith("#"):
                        value = following.strip()
                        break
            groups.setdefault(parent, {})[key] = value not in {"", "''", '""', "null", "Null", "NULL", "~", "[]", "{}"} and not value.startswith("#")
        field = parent + (f"{key}@{index + 1}",)
        if key in required_fields:
            groups.setdefault(field, {})
        stack.append((indent, field))
    return ["missing bilingual field" for _ in missing] + ["incomplete en/pt mapping" for values in groups.values() if not all(values.get(language) for language in ("en", "pt"))]


def scan(root: Path) -> list[str]:
    root = Path(root)
    problems = []
    if not root.is_dir():
        return ["source directory does not exist"]
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(part in IGNORED or part.startswith("_site") for part in relative.parts):
            continue
        if path.is_symlink() or not path.is_file() or path.suffix.lower() in BINARY:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        except OSError:
            problems.append(f"{relative}: cannot read public source")
            continue
        if any(token.casefold() in text.casefold() for token in FORBIDDEN):
            problems.append(f"{relative}: forbidden inherited identity")
        if PHONE.search(text):
            problems.append(f"{relative}: phone-shaped public value")
        if PRIVATE_KEY.search(text):
            problems.append(f"{relative}: private address or birth-date field")
        if path.suffix.lower() in {".yml", ".yaml", ".md", ".markdown"}:
            body = ""
            if path.suffix.lower() in {".md", ".markdown"}:
                front_matter = re.match(r"\A---\s*\n(.*?)\n---(?:\s*\n|$)", text, re.DOTALL)
                body = text[front_matter.end():] if front_matter else text
                text = front_matter.group(1) if front_matter else ""
            collection = any(part in {"_experience", "_education", "_projects", "_hobbies"} for part in relative.parts)
            required = {"title", "summary"} if collection else ()
            problems.extend(f"{relative}: {problem}" for problem in bilingual_problems(text, required))
            if collection:
                if not re.search(r"(?m)^highlights:\s*\n +-(?: +en:| +pt:)", text):
                    problems.append(f"{relative}: missing bilingual highlights")
                if body.count("<!--pt-->") != 1 or not all(part.strip() for part in body.split("<!--pt-->")):
                    problems.append(f"{relative}: missing en/pt long-form content")
    return problems


if __name__ == "__main__":
    found = scan(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("."))
    for problem in found:
        print(problem)
    print(f"{len(found)} source safety problem(s)")
    raise SystemExit(bool(found))
