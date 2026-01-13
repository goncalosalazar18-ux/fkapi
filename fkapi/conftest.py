"""Pytest configuration for Django tests."""
import os
import django
from django.conf import settings
from django.test.utils import get_runner

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fkapi.test_settings')

# Setup Django
django.setup()
