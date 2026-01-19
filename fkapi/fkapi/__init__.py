try:
    import os
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fkapi.settings')

    import django
    django.setup()

    from django.conf import settings
    if getattr(settings, 'ENABLE_CELERY', False):
        from .celery import app as celery_app
        __all__ = ('celery_app',)
    else:
        __all__ = ()
except Exception:
    __all__ = ()
