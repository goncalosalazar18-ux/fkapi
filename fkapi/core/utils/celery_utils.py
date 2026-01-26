"""
Utility functions for Celery detection and fallback handling.
"""

import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

_CELERY_AVAILABLE = None
_CELERY_ACTIVE = None


def is_celery_available() -> bool:
    """
    Check if Celery is installed and can be imported.
    """
    global _CELERY_AVAILABLE
    if _CELERY_AVAILABLE is not None:
        return _CELERY_AVAILABLE

    try:
        import celery  # noqa: F401

        _CELERY_AVAILABLE = True
        return True
    except ImportError:
        _CELERY_AVAILABLE = False
        return False


def is_celery_active() -> bool:
    """
    Check if Celery is not only available but also properly configured and active.
    This checks if:
    1. Celery is installed
    2. Celery app can be loaded
    3. Settings indicate Celery is enabled
    """
    global _CELERY_ACTIVE
    if _CELERY_ACTIVE is not None:
        return _CELERY_ACTIVE

    if not is_celery_available():
        _CELERY_ACTIVE = False
        return False

    try:
        from django.conf import settings

        enable_celery = getattr(settings, "ENABLE_CELERY", False)
        if not enable_celery:
            _CELERY_ACTIVE = False
            return False

        from fkapi.celery import app

        _ = app.main
        _CELERY_ACTIVE = True
        return True
    except Exception as e:
        logger.debug(f"Celery not active: {e}")
        _CELERY_ACTIVE = False
        return False


def execute_task_async(task_func: Callable, *args, **kwargs) -> Any:
    """
    Execute a task asynchronously using Celery if available, otherwise use threading.

    Args:
        task_func: The function to execute
        *args: Positional arguments for the task
        **kwargs: Keyword arguments for the task

    Returns:
        If Celery is available: Celery AsyncResult
        If threading fallback: Thread object (can be used to check status)
    """
    if is_celery_active():
        try:
            return task_func.delay(*args, **kwargs)
        except Exception as e:
            logger.warning(f"Celery task failed, falling back to threading: {e}")

    import threading
    import traceback

    def task_wrapper():
        """Wrapper to catch and log errors in thread execution."""
        try:
            from django.db import connections

            task_name = getattr(task_func, "__name__", str(task_func))
            logger.info(f"Executing task {task_name} in thread")
            result = task_func(*args, **kwargs)
            logger.info(f"Task {task_name} completed successfully")

            connections.close_all()
            return result
        except Exception as e:
            task_name = getattr(task_func, "__name__", str(task_func))
            logger.error(
                f"Error executing task {task_name} in thread: {str(e)}\n"
                f"Traceback: {traceback.format_exc()}"
            )
            from django.db import connections
            connections.close_all()
            raise

    thread = threading.Thread(target=task_wrapper, daemon=True)
    thread.start()
    task_name = getattr(task_func, "__name__", str(task_func))
    logger.info(f"Task {task_name} executed in thread (Celery not available)")
    return thread
