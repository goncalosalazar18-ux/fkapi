from django.core.management.base import BaseCommand

from core.models import Brand, Club, Competition, Kit


def fix_double_slash(url):
    if not url or "//" not in url:
        return url
    parts = url.split("://", 1)
    if len(parts) != 2:
        return url
    protocol, rest = parts
    while "//" in rest:
        rest = rest.replace("//", "/")
    return protocol + "://" + rest


def _process_field(model, field, dry_run, stdout):
    qs = model.objects.exclude(**{field: None}).exclude(**{f"{field}__exact": ""})
    to_update = []
    count = 0
    for obj in qs.iterator():
        val = getattr(obj, field)
        if not val or "//" not in val:
            continue
        new_val = fix_double_slash(val)
        if new_val == val:
            continue
        count += 1
        if dry_run:
            stdout.write(f"  {model.__name__} pk={obj.pk} {field}: ...{val[-60:]!r} -> ...{new_val[-60:]!r}")
        else:
            setattr(obj, field, new_val)
            to_update.append(obj)
    if to_update:
        model.objects.bulk_update(to_update, [field])
    return count


def _run_clean_models(dry_run, stdout):
    total = 0
    for model, fields in [
        (Brand, ["logo", "logo_dark"]),
        (Club, ["logo", "logo_dark"]),
        (Competition, ["logo", "logo_dark"]),
        (Kit, ["main_img_url", "fh_link"]),
    ]:
        for field in fields:
            total += _process_field(model, field, dry_run, stdout)
    return total


class Command(BaseCommand):
    help = "Fix URLs containing double slashes (e.g. ...com//static/...) in Brand, Club, Competition, Kit."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only print what would be updated, do not save.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN: no changes will be saved."))
        updated = _run_clean_models(dry_run, self.stdout)
        if dry_run:
            self.stdout.write(self.style.SUCCESS(f"Would update {updated} URL(s)."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Updated {updated} URL(s)."))
