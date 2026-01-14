from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self) -> None:
        """Initialize app when Django starts."""
        import os

        from core import cache_utils

        # Only setup cache invalidation if not in test mode
        if not os.environ.get('DJANGO_SETTINGS_MODULE', '').endswith('test_settings'):
            cache_utils.setup_cache_invalidation()
