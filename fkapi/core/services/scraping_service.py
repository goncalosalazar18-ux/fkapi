"""
Service for orchestrating scraping operations.
"""

import logging

from django.db import transaction

from core.models import Kit, Type_K
from core.parsers import KitPageData
from core.services.clubs_service import ClubsService
from core.services.kits_service import KitsService

logger = logging.getLogger(__name__)


class ScrapingService:
    """Service for orchestrating scraping operations."""

    @staticmethod
    def process_kit_data(
        data: KitPageData, slug: str, kit_id: str | None, use_proxy: bool = False, existing_kit_id: int | None = None
    ) -> Kit | None:
        """
        Process scraped kit data and create/update kit in database.

        Args:
            data: Parsed kit page data
            slug: Kit slug
            kit_id: Optional kit ID
            use_proxy: Whether to use proxy
            existing_kit_id: ID of existing kit to update (for re-scraping)

        Returns:
            Kit object if successful, None otherwise
        """
        try:
            # Get or create team (handles name and slug changes)
            logger.debug(f"Processing kit for team: {data.team_name} (slug: {data.team_slug})")
            team = ClubsService.handle_club_changes(data.team_slug, data.team_name, use_proxy)

            # Get or create brand
            from core.scrapers import _get_or_create_brand

            brand = _get_or_create_brand(data.brand_slug)
            if not brand:
                logger.error(f"Failed to get or create brand: {data.brand_slug}")
                return None

            # Get season
            logger.debug("Getting season information...")
            try:
                from core.scrapers import get_season

                season_text = data.season_text or slug
                season = get_season(season_text)
                logger.debug(f"Created/retrieved season: {season}")
            except Exception as e:
                logger.error(f"Error getting season: {str(e)}")
                return None

            # Get kit type and auto-categorize if newly created
            type_k, created = Type_K.objects.get_or_create(name=data.kit_type)
            if created:
                type_k.categorize()
                type_k.save()
                logger.debug(f"Created and categorized new kit type: {type_k.name} -> {type_k.category}")
            logger.debug(f"Kit type: {type_k}")

            # Create or update kit
            logger.debug("Creating/updating kit in database...")
            with transaction.atomic():
                kit_name = f"{data.team_name} {season} {type_k}"
                logger.debug(f"Kit name: {kit_name}")

                kit, created = KitsService.create_or_update_kit(
                    slug=slug,
                    kit_name=kit_name,
                    team=team,
                    season=season,
                    type_k=type_k,
                    brand=brand,
                    rating=data.rating,
                    main_img_url=data.main_img_url,
                    design=data.design,
                    kit_id=kit_id,
                    existing_kit_id=existing_kit_id,
                )

                # Process competitions
                logger.debug("Processing competitions...")
                KitsService.process_competitions(kit, data.competitions_html, slug)

                # Process colors if available
                if data.colors_str:
                    KitsService.process_colors(kit, data.colors_str)

                if not created:
                    logger.info(f"Updated existing kit: {kit}")
                else:
                    logger.info(f"Created new kit: {kit}")

                return kit

        except Exception as e:
            logger.error(f"Error processing kit data: {str(e)}", exc_info=True)
            return None
