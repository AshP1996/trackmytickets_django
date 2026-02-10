
import os
import django
import sys
import json
import requests

# Setup Django environment
sys.path.append('/home/ashish/Documents/ticket_system_v1/ticket_system_django')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')
django.setup()

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from apps.accounts.models import Organization

User = get_user_model()

def test_notifications():
    # Get a demo user and organization
    try:
        org = Organization.objects.get(subdomain='demo')
        user = User.objects.get(email='admin@demo.com')
        print(f"Testing with User: {user.email}, Org: {org.subdomain}")
    except Exception as e:
        print(f"Error getting test data: {e}")
        return

    client = APIClient()
    client.force_authenticate(user=user)
    
    # 1. Test List Notifications
    url_list = f'/api/{org.subdomain}/notifications/'
    print(f"\n1. Testing GET {url_list}")
    response = client.get(url_list)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print("Success! Data sample:")
        data = response.json()
        # Handle pagination
        results = data.get('results', data) if isinstance(data, dict) else data
        print(json.dumps(results[:1] if results else [], indent=2))
        
        if results:
            notif_id = results[0]['id']
            
            # 2. Test Mark Read (Try 'mark_read' and 'read')
            # The view has @action(detail=True, methods=['post']) def mark_read(...)
            # Default URL should be {id}/mark_read/
            
            url_mark_read = f'/api/{org.subdomain}/notifications/{notif_id}/mark_read/'
            print(f"\n2. Testing POST {url_mark_read}")
            resp_mark = client.post(url_mark_read)
            print(f"Status: {resp_mark.status_code}")
            print(f"Response: {resp_mark.json() if resp_mark.content else ''}")

            # 3. Test Mark All Read
            # The view has @action(detail=False, methods=['post']) def mark_all_read(...)
            # Default URL should be notifications/mark_all_read/
            
            url_mark_all = f'/api/{org.subdomain}/notifications/mark_all_read/'
            print(f"\n3. Testing POST {url_mark_all}")
            resp_all = client.post(url_mark_all)
            print(f"Status: {resp_all.status_code}")
            print(f"Response: {resp_all.json() if resp_all.content else ''}")

    else:
        print(f"Failed to list notifications. Response: {response.content}")

if __name__ == '__main__':
    test_notifications()
