"""
Management command to categorize and order existing Type_K entries.

This command analyzes all Type_K entries and assigns:
- category: match, prematch, preseason, training, travel, jacket
- category_order: 1-6 based on category
- is_goalkeeper: True if contains GK/Goalkeeper/Portero
- order_priority: Based on Home/Away/Third/Fourth/numbers
"""

import re
import sys

from django.core.management.base import BaseCommand

from core.models import Type_K

# Fix encoding for Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')


class Command(BaseCommand):
    help = 'Categorize and order all Type_K entries for proper search result sorting'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without saving',
        )

    def _normalize_name(self, name):
        """Normalize name for comparison."""
        return name.lower().strip()

    def _is_goalkeeper(self, name):
        """Check if type is goalkeeper related."""
        normalized = self._normalize_name(name)
        gk_keywords = ['gk', 'goalkeeper', 'portero', 'guardameta']
        return any(keyword in normalized for keyword in gk_keywords)

    def _extract_number(self, name):
        """Extract number from name (handles V2, V3, etc.)."""
        normalized = self._normalize_name(name)
        # Match numbers, including V2, V3, etc.
        number_match = re.search(r'v?(\d+)', normalized)
        if number_match:
            return int(number_match.group(1))
        return None

    def _get_order_priority(self, name, category):
        """Get order priority within category."""
        normalized = self._normalize_name(name)

        # Priority order for match/prematch/preseason/training/travel
        if category in ['match', 'prematch', 'preseason', 'training', 'travel']:
            # Home first
            if 'home' in normalized and 'away' not in normalized:
                return 1
            # Away second
            if 'away' in normalized:
                return 2
            # Third third
            if 'third' in normalized:
                return 3
            # Fourth fourth
            if 'fourth' in normalized:
                return 4
            # Then numbers (1, 2, 3, 4, etc.)
            number = self._extract_number(name)
            if number:
                return 10 + number
            # Everything else
            return 999

        # Priority order for jackets
        elif category == 'jacket':
            # Anthem first
            if 'anthem' in normalized:
                return 1
            # Rain second
            if 'rain' in normalized:
                number = self._extract_number(name)
                if number:
                    return 10 + number
                return 2
            # Jacket third
            if 'jacket' in normalized:
                number = self._extract_number(name)
                if number:
                    return 20 + number
                return 3
            # Windbreaker fourth
            if 'windbreaker' in normalized:
                return 4
            # Track fifth
            if 'track' in normalized:
                number = self._extract_number(name)
                if number:
                    return 30 + number
                return 5
            # Vest sixth
            if 'vest' in normalized:
                return 6
            # Everything else
            return 999

        return 999

    def _categorize(self, name):
        """Categorize type based on name."""
        normalized = self._normalize_name(name)

        # Check for jacket keywords as whole words (not substrings)
        # This avoids false positives like "Training" containing "rain"
        jacket_keywords = ['anthem', 'rain', 'jacket', 'windbreaker', 'track', 'vest']
        # Use word boundaries to match whole words only
        import re
        has_jacket_keyword = any(
            re.search(r'\b' + re.escape(keyword) + r'\b', normalized)
            for keyword in jacket_keywords
        )

        # Training (check if it's training but not a jacket type)
        # Training should be: Home, Away, Third, Fourth, and others with "training" but not jacket types
        if 'training' in normalized:
            # If it contains jacket keywords as whole words, it's a jacket, not training
            if has_jacket_keyword:
                return 'jacket', 6
            # Otherwise it's training
            return 'training', 4

        # Jackets (if not training)
        if has_jacket_keyword:
            return 'jacket', 6

        # Pre-match, bench, warm-up, staff
        prematch_keywords = ['pre-match', 'prematch', 'bench', 'warm-up', 'warmup', 'staff']
        if any(keyword in normalized for keyword in prematch_keywords):
            return 'prematch', 2

        # Pre-season, Temporary
        preseason_keywords = ['pre-season', 'preseason', 'temporary', 'temp']
        if any(keyword in normalized for keyword in preseason_keywords):
            return 'preseason', 3

        # Travel, Polo
        travel_keywords = ['travel', 'polo']
        if any(keyword in normalized for keyword in travel_keywords):
            return 'travel', 5

        # Default: Game kits
        return 'match', 1

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        # Check if migration has been applied
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='core_type_k' AND column_name='category'
            """)
            has_category = cursor.fetchone() is not None

        if not has_category:
            self.stdout.write(
                self.style.ERROR(
                    'Migration not applied. Please run: python manage.py migrate'
                )
            )
            return

        types = Type_K.objects.all()
        total = types.count()

        if total == 0:
            self.stdout.write(self.style.WARNING('No Type_K entries found.'))
            return

        self.stdout.write(f'Processing {total} Type_K entries...')

        updated = 0
        stats = {
            'match': 0,
            'prematch': 0,
            'preseason': 0,
            'training': 0,
            'travel': 0,
            'jacket': 0,
            'goalkeeper': 0,
        }

        for type_k in types:
            category, category_order = self._categorize(type_k.name)
            is_goalkeeper = self._is_goalkeeper(type_k.name)
            order_priority = self._get_order_priority(type_k.name, category)

            # Check if update is needed
            needs_update = (
                type_k.category != category or
                type_k.category_order != category_order or
                type_k.is_goalkeeper != is_goalkeeper or
                type_k.order_priority != order_priority
            )

            if needs_update:
                if dry_run:
                    self.stdout.write(
                        f'Would update: {type_k.name} -> '
                        f'category={category}, order={order_priority}, '
                        f'GK={is_goalkeeper}, cat_order={category_order}'
                    )
                else:
                    type_k.category = category
                    type_k.category_order = category_order
                    type_k.is_goalkeeper = is_goalkeeper
                    type_k.order_priority = order_priority
                    type_k.save()
                updated += 1

            stats[category] += 1
            if is_goalkeeper:
                stats['goalkeeper'] += 1

        if dry_run:
            self.stdout.write(self.style.WARNING(f'\nDRY RUN: Would update {updated} entries'))
        else:
            self.stdout.write(self.style.SUCCESS(f'\nSuccessfully updated {updated} entries'))

        self.stdout.write('\nStatistics:')
        self.stdout.write(f"  Match (Game kits): {stats['match']}")
        self.stdout.write(f"  Pre-match: {stats['prematch']}")
        self.stdout.write(f"  Pre-season: {stats['preseason']}")
        self.stdout.write(f"  Training: {stats['training']}")
        self.stdout.write(f"  Travel/Polo: {stats['travel']}")
        self.stdout.write(f"  Jackets: {stats['jacket']}")
        self.stdout.write(f"  Goalkeeper types: {stats['goalkeeper']}")
