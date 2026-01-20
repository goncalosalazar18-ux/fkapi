"""
Script para probar que Celery está configurado correctamente.
Ejecutar: python test_celery.py
"""

import os

import django
import redis

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fkapi.settings')
django.setup()

print("=" * 60)
print("Testing Celery Configuration")
print("=" * 60)

# Test Redis connection
print("\n1. Testing Redis connection...")
try:
    r = redis.Redis(host='localhost', port=6379)
    r.ping()
    print("   [OK] Redis is running!")
except Exception as e:
    print(f"   [ERROR] Redis connection failed: {e}")
    print("   Please install and start Redis first.")
    print("   See INSTALL_REDIS_WINDOWS.md for instructions")
    exit(1)

# Test Celery app
print("\n2. Testing Celery app...")
try:
    from fkapi.celery import app
    print(f"   [OK] Celery app loaded: {app.main}")
    print(f"   [OK] Broker URL: {app.conf.broker_url}")
    print(f"   [OK] Result Backend: {app.conf.result_backend}")
except Exception as e:
    print(f"   [ERROR] Celery app failed: {e}")
    exit(1)

# Test task registration
print("\n3. Testing task registration...")
try:
    registered_tasks = [name for name in app.tasks.keys() if not name.startswith('celery.')]
    print(f"   [OK] Found {len(registered_tasks)} registered tasks:")
    for task in registered_tasks[:5]:  # Show first 5
        print(f"     - {task}")
    if len(registered_tasks) > 5:
        print(f"     ... and {len(registered_tasks) - 5} more")
except Exception as e:
    print(f"   [ERROR] Task registration failed: {e}")
    exit(1)

print("\n" + "=" * 60)
print("[SUCCESS] All tests passed! Celery is configured correctly.")
print("=" * 60)
print("\nNext steps:")
print("1. Start Celery worker: start_celery_worker.bat")
print("2. (Optional) Start Celery beat: start_celery_beat.bat")
print("3. Test a task from Django shell or the web interface")
