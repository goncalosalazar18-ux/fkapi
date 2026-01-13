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
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from core.views import (
    assign_countries, 
    update_competition_country,
    propagate_countries,
    competition_clubs,
    review_country_assignments,
    get_club_competitions,
    suggest_competition_countries,
    clubs_without_country,
    random_kits_view,
    random_clubs_view,
    load_more_kits,
    load_more_clubs,
    merge_suggestions_view,
    top_clubs_by_country
)
from .api import api

urlpatterns = [
    path('', random_kits_view, name='home'),  # Redirect root to random kits
    path('admin/', admin.site.urls),
    path('api/', api.urls),
    path('assign-countries/', assign_countries, name='assign_countries'),
    path('update-competition-country/', update_competition_country, name='update_competition_country'),
    path('propagate-countries/', propagate_countries, name='propagate_countries'),
    path('competition-clubs/<int:competition_id>/', competition_clubs, name='competition_clubs'),
    path('review-country-assignments/', review_country_assignments, name='review_country_assignments'),
    path('get-club-competitions/', get_club_competitions, name='get_club_competitions'),
    path('suggest-competition-countries/', suggest_competition_countries, name='suggest_competition_countries'),
    path('clubs-without-country/', clubs_without_country, name='clubs_without_country'),
    path('random-kits/', random_kits_view, name='random_kits'),
    path('random-clubs/', random_clubs_view, name='random_clubs'),
    path('load-more-kits/', load_more_kits, name='load_more_kits'),
    path('load-more-clubs/', load_more_clubs, name='load_more_clubs'),
    path('merge-suggestions/', merge_suggestions_view, name='merge_suggestions'),
    path('top-clubs-by-country/', top_clubs_by_country, name='top_clubs_by_country'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
