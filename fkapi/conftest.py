"""Pytest configuration for Django tests."""

import os
import sys

# Set Django settings module before any Django imports
os.environ["DJANGO_SETTINGS_MODULE"] = "test_settings"

# Get the fkapi directory (where this conftest.py is located)
fkapi_dir = os.path.dirname(os.path.abspath(__file__))

# Only add fkapi directory to path - this allows both:
# - 'from core.xxx' imports (core/ is inside fkapi/)
# - 'from fkapi.xxx' imports (fkapi/ is inside fkapi/)
# Do NOT add project_root - it causes import conflicts.
if fkapi_dir not in sys.path:
    sys.path.insert(0, fkapi_dir)
