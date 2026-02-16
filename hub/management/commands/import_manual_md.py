import re
from pathlib import Path

from django.core.management.base import BaseCommand
from django.utils.text import slugify

from hub.models import ManualPage


class Command(BaseCommand):
    help = "Import markdown files into ManualPage."

    def add_arguments(self, parser):
        parser.add_argument(
            "path",
            nargs="?",
            default="docs/manual",
            help="Path containing markdown files",
        )
        parser.add_argument(
            "--skip-existing",
            action="store_true",
            help="Skip pages that already exist",
        )

    def handle(self, *args, **options):
        base_path = Path(options["path"]).expanduser().resolve()
        if not base_path.exists():
            self.stderr.write(self.style.ERROR(f"Path not found: {base_path}"))
            return

        md_files = sorted(base_path.rglob("*.md"))
        if not md_files:
            self.stdout.write("No markdown files found.")
            return

        created = 0
        updated = 0
        skipped = 0

        for path in md_files:
            relative = path.relative_to(base_path)
            section_parts = list(relative.parts[:-1])
            section = "/".join(section_parts)
            slug_source = "/".join(relative.with_suffix("").parts)
            slug = slugify(slug_source) or slug_source.lower().replace(" ", "-")
            content = path.read_text(encoding="utf-8")
            title, cleaned = self._extract_title_and_content(content)
            title = title or self._fallback_title(path.stem)
            content = cleaned

            existing = ManualPage.objects.filter(slug=slug).first()
            if existing:
                if options["skip_existing"]:
                    skipped += 1
                    continue
                existing.title = title
                existing.section = section
                existing.content = content
                existing.save(update_fields=["title", "section", "content", "updated_at"])
                updated += 1
                continue

            ManualPage.objects.create(slug=slug, title=title, section=section, content=content)
            created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Import complete: {created} created, {updated} updated, {skipped} skipped."
            )
        )

    def _extract_title_and_content(self, content):
        lines = content.splitlines()
        for index, line in enumerate(lines):
            stripped = line.lstrip()
            if stripped.startswith("# "):
                raw_title = stripped[2:].strip()
                title = self._strip_order_prefix(raw_title)
                remaining = lines[:index] + lines[index + 1 :]
                if remaining and remaining[0].strip() == "":
                    remaining = remaining[1:]
                return title, "\n".join(remaining)
        return None, content

    def _fallback_title(self, stem):
        cleaned = self._strip_order_prefix(stem)
        return cleaned.replace("-", " ").replace("_", " ").title()

    def _strip_order_prefix(self, value):
        return re.sub(r"^\\s*\\d+\\s*[-._]\\s*", "", value or "").strip()
