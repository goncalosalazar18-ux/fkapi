import logging

from django.core.management import call_command

from core.utils.celery_utils import is_celery_active

logger = logging.getLogger(__name__)

if is_celery_active():
    from celery import shared_task

    task_decorator = shared_task
else:

    def task_decorator(func):
        return func


@task_decorator
def scrape_daily():
    """Scrape latest updated kits once a day using django command called scrape_latest"""
    call_command("scrape_latest")


@task_decorator
def scrape_whole_club_task(club_id: int, use_proxy: bool = False):
    """
    Celery task to scrape all kits for a club.

    Args:
        club_id: ID of the club to scrape
        use_proxy: Whether to use proxy for requests
    """
    from core.models import Club
    from core.scrapers import scrape_whole_club

    try:
        club = Club.objects.get(id=club_id)
        logger.info(f"Starting scrape_whole_club_task for club: {club.name} (ID: {club_id})")
        result = scrape_whole_club(club)
        if result:
            logger.info(f"Successfully scraped club: {club.name}")
        else:
            logger.warning(f"Failed to scrape club: {club.name}")
        return result
    except Club.DoesNotExist:
        logger.error(f"Club with ID {club_id} does not exist")
        raise
    except Exception as e:
        logger.error(f"Error in scrape_whole_club_task for club_id {club_id}: {str(e)}")
        raise


@task_decorator
def scrape_kit_task(slug: str, kit_id: str | None = None, use_proxy: bool = False):
    """
    Celery task to scrape a single kit.

    Args:
        slug: Kit slug
        kit_id: Optional kit ID
        use_proxy: Whether to use proxy for requests

    Returns:
        dict with 'success' and 'kit_id' keys, or None if failed
    """
    from core.scrapers import scrape_kit

    try:
        logger.info(f"Starting scrape_kit_task for kit: {slug} (ID: {kit_id})")
        result = scrape_kit(slug, kit_id=kit_id, use_proxy=use_proxy)
        if result:
            logger.info(f"Successfully scraped kit: {slug}")
            return {"success": True, "kit_id": result.id, "slug": slug}
        else:
            logger.warning(f"Failed to scrape kit: {slug}")
            return {"success": False, "slug": slug}
    except Exception as e:
        logger.error(f"Error in scrape_kit_task for slug {slug}: {str(e)}")
        return {"success": False, "slug": slug, "error": str(e)}


@task_decorator
def scrape_user_collection_task(userid: int) -> dict:
    """
    Celery task to scrape user collection from FootballKitArchive API.

    Args:
        userid: User ID from FootballKitArchive

    Returns:
        dict: Task result with success status and metadata

    Raises:
        Exception: If scraping fails
    """
    from django.core.cache import cache

    from core.cache_utils import generate_cache_key
    from core.scrapers import scrape_user_collection_api

    try:
        logger.info(f"Starting scrape_user_collection_task for userid: {userid}")

        # Scrape collection data
        logger.info(f"Calling scrape_user_collection_api for userid: {userid}")
        data = scrape_user_collection_api(userid)
        logger.info(f"Scraping completed for userid: {userid}, got {len(data.get('entries', []))} entries")

        # Cache for 1 week (604800 seconds)
        cache_key = generate_cache_key("user_collection", userid)
        cache.set(cache_key, data, timeout=604800)

        entries_count = len(data.get("entries", []))
        logger.info(f"Successfully scraped and cached collection for userid: {userid} ({entries_count} entries)")

        entries_count = len(data.get("entries", []))
        logger.info(f"Successfully scraped and cached collection for userid: {userid} ({entries_count} entries)")

        return {
            "success": True,
            "userid": userid,
            "entries_count": entries_count,
            "pages_scraped": data.get("pages_scraped", 0),
        }
    except Exception as e:
        logger.error(f"Error scraping user collection for userid {userid}: {str(e)}", exc_info=True)
        raise
