from django.conf import settings

if getattr(settings, 'ENABLE_CELERY', False):
    try:
        from .celery import app as celery_app
        __all__ = ('celery_app',)
    except ImportError:
        __all__ = ()
else:
    __all__ = ()
