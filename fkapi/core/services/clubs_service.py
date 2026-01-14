"""
Service for club-related business logic.
"""

import logging

from django.db import transaction
from django.utils import timezone

from core.constants import TEAM_SLUG_CHANGES_LOG
from core.models import Club

logger = logging.getLogger(__name__)


class ClubsService:
    """Service for managing club-related business logic."""

    @staticmethod
    def handle_club_changes(team_slug: str, team_name: str, use_proxy: bool = False) -> Club:
        """
        Handle club changes (name or slug) and return the correct club object.

        This method handles cases where:
        - Club exists with same slug but different name (name update)
        - Club exists with same name but different slug (slug update)
        - Club doesn't exist (create new)

        Args:
            team_slug: The slug from the scraped data
            team_name: The name from the scraped data
            use_proxy: Whether to use proxy for scraping

        Returns:
            Club: The correct club object

        Raises:
            ValueError: If club scraping fails
        """
        # First, try to find by slug
        try:
            team = Club.objects.get(slug=team_slug)
            logger.debug(f"Found existing team by slug: {team}")

            # Update team name if different
            if team.name != team_name:
                logger.debug(f"Team name changed: {team.name} -> {team_name}")
                team.name = team_name
                team.save()

            return team

        except Club.DoesNotExist:
            logger.debug(f"Team {team_slug} not found by slug, checking by name...")

            # Try to find by name (case-insensitive)
            try:
                team = Club.objects.get(name__iexact=team_name)
                logger.debug(f"Found existing team by name: {team}")

                # The club exists but with a different slug - this means the club was renamed
                logger.debug(f"Club slug changed: {team.slug} -> {team_slug}")

                # Log the slug change
                with open(TEAM_SLUG_CHANGES_LOG, "a", encoding="utf-8") as log:
                    log.write(
                        f"{timezone.now()}: TEAM SLUG UPDATE - Name: {team_name} | Old Slug: {team.slug} | New Slug: {team_slug}\n"
                    )

                # Update the slug
                with transaction.atomic():
                    team.slug = team_slug
                    team.save()
                    logger.debug(f"Updated club slug: {team.slug}")

                return team

            except Club.DoesNotExist:
                logger.debug(f"Team {team_name} not found by name either, creating new team")

                # Create new team
                from core.scrapers import scrape_club_details

                team = scrape_club_details(team_slug, use_proxy)
                if not team:
                    logger.error(f"Failed to scrape team {team_slug}")
                    raise ValueError(f"Failed to scrape team {team_slug}") from None

                return team
