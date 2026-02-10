import requests
import json
import os
import django
from django.conf import settings

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ticket_system_django.settings')
django.setup()

from django.contrib.auth import get_user_model
from tickets.models import Department

User = get_user_model()

def check_api_responses():
    print("--- Checking API Responses ---")
    
    # Simulate API calls by checking database counts and printing expected structure
    # Since we can't easily mock the full HTTP request stack here without running server, 
    # we will inspect the models directly to ensuring data exists, 
    # and then look at the view logic if needed.
    
    user_count = User.objects.count()
    dept_count = Department.objects.count()
    
    print(f"Users in DB: {user_count}")
    print(f"Departments in DB: {dept_count}")
    
    if dept_count > 0:
        print("Departments exist. API *should* return them.")
        for d in Department.objects.all()[:3]:
            print(f" - {d.name} (Active: {d.is_active})")
            
    if user_count > 0:
        print("Users exist. API *should* return them.")
        for u in User.objects.all()[:3]:
            print(f" - {u.email} (Role: {u.role})")

if __name__ == "__main__":
    check_api_responses()
