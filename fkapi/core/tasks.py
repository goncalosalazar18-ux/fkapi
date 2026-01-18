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
    call_command('scrape_latest')


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
    """
    from core.scrapers import scrape_kit

    try:
        logger.info(f"Starting scrape_kit_task for kit: {slug} (ID: {kit_id})")
        result = scrape_kit(slug, kit_id=kit_id, use_proxy=use_proxy)
        if result:
            logger.info(f"Successfully scraped kit: {slug}")
        else:
            logger.warning(f"Failed to scrape kit: {slug}")
        return result
    except Exception as e:
        logger.error(f"Error in scrape_kit_task for slug {slug}: {str(e)}")
        raise

