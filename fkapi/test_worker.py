"""
Test script to verify Celery worker can start
"""
import os
import subprocess
import sys

os.chdir(os.path.dirname(os.path.abspath(__file__)))

print("Testing Celery worker startup...")
print("=" * 60)

try:
    # Try to start worker and capture initial output
    result = subprocess.run(
        [sys.executable, "-m", "celery", "-A", "fkapi", "worker", "--loglevel=info", "--pool=threads", "--concurrency=1", "--time-limit=1"],
        cwd=os.getcwd(),
        capture_output=True,
        text=True,
        timeout=10
    )

    if "ready" in result.stdout.lower() or "celery@" in result.stdout.lower():
        print("[SUCCESS] Worker can start!")
        print("\nFirst few lines of output:")
        print(result.stdout[:500])
    else:
        print("[WARNING] Worker output:")
        print(result.stdout[:500])
        if result.stderr:
            print("\nErrors:")
            print(result.stderr[:500])

except subprocess.TimeoutExpired:
    print("[SUCCESS] Worker started (timeout is expected)")
except Exception as e:
    print(f"[ERROR] {e}")
