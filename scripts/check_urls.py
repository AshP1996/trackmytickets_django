
import os
import sys
import django
from django.urls import resolve, reverse

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

def check_url_resolution():
    print("Checking URL resolution...")
    path = '/api/demo/admin/dashboard/'
    try:
        match = resolve(path)
        print(f"✓ Resolved '{path}' to: {match.view_name}")
        if match.view_name == 'admin_dashboard':
             print("  Matches expected view name 'admin_dashboard'")
        else:
             print(f"  Warning: Expected 'admin_dashboard', got '{match.view_name}'")
    except Exception as e:
        print(f"✗ Failed to resolve '{path}': {e}")
        
if __name__ == '__main__':
    check_url_resolution()
