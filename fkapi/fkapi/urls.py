"""
URL configuration for fkapi project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path
from django.views.generic import RedirectView

from core.views import (
    assign_countries,
    clubs_without_country,
    competition_clubs,
    get_club_competitions,
    load_more_clubs,
    load_more_kits,
    propagate_countries,
    random_clubs_view,
    random_kits_view,
    review_country_assignments,
    suggest_competition_countries,
    top_clubs_by_country,
    update_competition_country,
)
from core.views_docs import docs_index, docs_view

from .api import api

urlpatterns = [
    # Redirect API root to interactive API docs
    path("", RedirectView.as_view(url="/api/docs", permanent=False), name="home"),
    path("admin/", admin.site.urls),
    path("api/", api.urls),
    path("docs/", docs_index, name="docs_index"),
    path("docs/<path:doc_path>/", docs_view, name="docs_view"),
    path("assign-countries/", assign_countries, name="assign_countries"),
    path("update-competition-country/", update_competition_country, name="update_competition_country"),
    path("propagate-countries/", propagate_countries, name="propagate_countries"),
    path("competition-clubs/<int:competition_id>/", competition_clubs, name="competition_clubs"),
    path("review-country-assignments/", review_country_assignments, name="review_country_assignments"),
    path("get-club-competitions/", get_club_competitions, name="get_club_competitions"),
    path("suggest-competition-countries/", suggest_competition_countries, name="suggest_competition_countries"),
    path("clubs-without-country/", clubs_without_country, name="clubs_without_country"),
    path("random-kits/", random_kits_view, name="random_kits"),
    path("random-clubs/", random_clubs_view, name="random_clubs"),
    path("load-more-kits/", load_more_kits, name="load_more_kits"),
    path("load-more-clubs/", load_more_clubs, name="load_more_clubs"),
    path("top-clubs-by-country/", top_clubs_by_country, name="top_clubs_by_country"),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
