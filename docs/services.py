import re
from pathlib import Path

from django.conf import settings
from django.http import Http404
from django.utils.html import strip_tags
from django.utils.text import slugify
from markdown import markdown


MARKDOWN_EXTENSIONS = [
    "fenced_code",
    "codehilite",
    "tables",
    "admonition",
]


def docs_root():
    return Path(getattr(settings, "MANUAL_DOCS_ROOT", settings.BASE_DIR / "docs" / "manual"))


def _strip_order_prefix(value):
    return re.sub(r"^\s*\d+\s*[-._]\s*", "", value or "").strip()


def _fallback_title(path):
    cleaned = _strip_order_prefix(path.stem)
    return cleaned.replace("-", " ").replace("_", " ").title()


def _extract_title_and_body(content, path):
    lines = content.splitlines()
    for index, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith("# "):
            title = _strip_order_prefix(stripped[2:].strip()) or _fallback_title(path)
            remaining = lines[:index] + lines[index + 1 :]
            if remaining and not remaining[0].strip():
                remaining = remaining[1:]
            return title, "\n".join(remaining)
    return _fallback_title(path), content


def _section_label(section_key):
    label_source = section_key.split("/")[-1] if section_key else ""
    return _strip_order_prefix(label_source).replace("-", " ").replace("_", " ").title() or "General"


def load_docs():
    root = docs_root()
    if not root.exists():
        return []

    pages = []
    for path in sorted(root.rglob("*.md")):
        relative = path.relative_to(root)
        raw_content = path.read_text(encoding="utf-8")
        title, markdown_body = _extract_title_and_body(raw_content, path)
        slug_source = "/".join(relative.with_suffix("").parts)
        slug = slugify(slug_source) or slug_source.lower().replace(" ", "-")
        section = "/".join(relative.parts[:-1])
        content_html = markdown(markdown_body, extensions=MARKDOWN_EXTENSIONS)
        plain_text = strip_tags(content_html)
        pages.append(
            {
                "slug": slug,
                "title": title,
                "section": section,
                "section_label": _section_label(section),
                "content": markdown_body,
                "content_html": content_html,
                "plain_text": plain_text,
                "path": path,
            }
        )
    return pages


def group_docs(pages, active_slug="", query=""):
    sections = []
    lowered_query = query.strip().lower()

    for page in pages:
        if not sections or sections[-1]["key"] != page["section"]:
            sections.append(
                {
                    "key": page["section"],
                    "label": page["section_label"],
                    "pages": [],
                    "is_active": False,
                }
            )
        match = not lowered_query or lowered_query in page["title"].lower() or lowered_query in page["plain_text"].lower()
        sections[-1]["pages"].append({**page, "matches_query": match})
        if page["slug"] == active_slug:
            sections[-1]["is_active"] = True

    return sections


def search_docs(query):
    pages = load_docs()
    lowered = (query or "").strip().lower()
    if not lowered:
        return pages

    results = []
    for page in pages:
        haystack = f"{page['title']} {page['plain_text']}".lower()
        if lowered not in haystack:
            continue
        excerpt_source = page["plain_text"]
        position = excerpt_source.lower().find(lowered)
        if position == -1:
            excerpt = excerpt_source[:180]
        else:
            start = max(0, position - 70)
            end = min(len(excerpt_source), position + len(lowered) + 90)
            excerpt = excerpt_source[start:end].strip()
        results.append({**page, "excerpt": excerpt})
    return results


def get_doc_or_404(slug):
    for page in load_docs():
        if page["slug"] == slug:
            return page
    raise Http404("Document not found")

