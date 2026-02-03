"""
URL configuration for fkapi project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from myapp.views import home
    2. Add a URL to urlpatterns:  path('', home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path
from django.views.generic import RedirectView

from core.views_docs import docs_index, docs_view

from .api import api

urlpatterns = [
    path("", RedirectView.as_view(url="/api/docs", permanent=False), name="home"),  # API root → docs
    path("admin/", admin.site.urls),
    path("api/", api.urls),
    path("docs/", docs_index, name="docs_index"),
    path("docs/<path:doc_path>/", docs_view, name="docs_view"),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
