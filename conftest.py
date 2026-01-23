"""
Pytest configuration for Django tests.
"""

import os
import sys
import unittest.mock

# Add project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "fkapi"))

# Configure Django to use test settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "test_settings")

# Mock celery before importing anything from fkapi
celery_mock = unittest.mock.MagicMock()
sys.modules["fkapi.celery"] = celery_mock
