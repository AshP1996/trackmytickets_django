import requests
import json
import sys

BASE_URL = "http://localhost:8080/api"

def verify_acme():
    print("Verifying Acme Corp...")
    
    # 1. Login
    login_url = f"{BASE_URL}/acme/auth/login/"
    payload = {"email": "admin@acme.com", "password": "password123"}
    headers = {"Content-Type": "application/json"}
    
    response = requests.post(login_url, json=payload)
    if response.status_code != 200:
        print(f"Login failed: {response.status_code} {response.text}")
        sys.exit(1)
        
    data = response.json()
    token = data['access_token']
    print("Login successful.")
    
    auth_header = {"Authorization": f"Bearer {token}"}
    
    # 2. Check Initial Stats
    stats_url = f"{BASE_URL}/acme/tickets/stats/"
    response = requests.get(stats_url, headers=auth_header)
    if response.status_code != 200:
        print(f"Stats failed: {response.status_code} {response.text}")
        sys.exit(1)
        
    stats = response.json()
    print(f"Initial Stats: {stats}")
    if stats['total'] != 0:
        print("Warning: Expected 0 tickets.")
        
    # 3. Create Project
    project_url = f"{BASE_URL}/acme/projects/"
    # Generate random suffix
    import random
    suffix = random.randint(1000, 9999)
    project_payload = {
        "name": f"Acme Support {suffix}",
        "key": f"SUP{suffix}",
        "description": "Support Project",
        "start_date": "2026-01-01",
        "end_date": "2026-12-31"
    }
    
    response = requests.post(project_url, json=project_payload, headers=auth_header)
    if response.status_code != 201:
        print(f"Create Project failed: {response.status_code} {response.text}")
        sys.exit(1)
        
    project = response.json()
    project_id = project['id']
    print(f"Created Project: {project['name']} (ID: {project_id})")
    
    # 4. Create Ticket
    ticket_url = f"{BASE_URL}/acme/tickets/"
    ticket_payload = {
        "subject": "My First Issue",
        "description": "This is a test ticket.",
        "priority": "normal",
        "project": project_id
    }
    
    response = requests.post(ticket_url, json=ticket_payload, headers=auth_header)
    if response.status_code != 201:
        print(f"Create Ticket failed: {response.status_code} {response.text}")
        sys.exit(1)
        
    ticket = response.json()
    print(f"Created Ticket: {ticket['ticket_id']} - {ticket['subject']}")
    
    # 5. Check Stats Again
    response = requests.get(stats_url, headers=auth_header)
    stats = response.json()
    print(f"Updated Stats: {stats}")
    
    if stats['total'] == 1:
        print("SUCCESS: Stats verified!")
    else:
        print(f"FAILURE: Expected 1 ticket, got {stats['total']}")
        sys.exit(1)

if __name__ == '__main__':
    verify_acme()
