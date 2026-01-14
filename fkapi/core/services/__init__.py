"""
Service layer for business logic.

This module provides services that encapsulate business logic,
separating it from views and scrapers for better testability and maintainability.
"""

from .clubs_service import ClubsService
from .kits_service import KitsService
from .scraping_service import ScrapingService

__all__ = ["ClubsService", "KitsService", "ScrapingService"]
