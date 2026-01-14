from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self) -> None:
        """Initialize app when Django starts."""
        from core import cache_utils
        cache_utils.setup_cache_invalidation()
