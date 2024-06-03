from celery import shared_task
from django.core.management import call_command


@shared_task
def scrape_daily():
    """Scrape latest updated kits once a day using django command called scrape_latest"""
    call_command('scrape_latest')

