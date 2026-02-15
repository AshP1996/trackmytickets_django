import requests
import json
import random
import time

# Configuration
BASE_URL = "http://localhost:8000"
ORG = "acme"
ADMIN_EMAIL = "admin@acme.com"
PASSWORD = "password123"

def test_create_project_with_lead():
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})

    # 1. Login
    print(f"Logging in as {ADMIN_EMAIL}...")
    login_url = f"{BASE_URL}/api/{ORG}/auth/login/"
    resp = session.post(login_url, json={"email": ADMIN_EMAIL, "password": PASSWORD})
    
    if resp.status_code != 200:
        print(f"Login failed: {resp.status_code} - {resp.text}")
        return

    tokens = resp.json()
    access_token = tokens['access_token']
    user_id = tokens['user']['id']
    session.headers.update({"Authorization": f"Bearer {access_token}"})
    print(f"Login successful. User ID: {user_id}")

    # 2. Create Project
    suffix = int(time.time())
    project_payload = {
        "name": f"Lead Test Project {suffix}",
        "key": f"LU{suffix % 1000}", # Short key
        "description": "Testing lead user assignment",
        "lead_user": user_id, # Assign to self
        "start_date": "2026-03-01",
        "end_date": "2026-03-31"
    }
    
    print(f"Creating project with payload: {json.dumps(project_payload, indent=2)}")
    create_url = f"{BASE_URL}/api/{ORG}/projects/"
    resp = session.post(create_url, json=project_payload)
    
    if resp.status_code == 201:
        data = resp.json()
        print("Project created successfully.")
        print(json.dumps(data, indent=2))
        
        # Verify fields
        returned_lead = data.get('lead_user')
        returned_lead_name = data.get('lead_user_name')
        
        print(f"Returned lead_user: {returned_lead}")
        print(f"Returned lead_user_name: {returned_lead_name}")
        
        if returned_lead == user_id:
            print("SUCCESS: lead_user matches assigned ID.")
        else:
            print(f"FAILURE: lead_user mismatch. Expected {user_id}, got {returned_lead}")
            
        if returned_lead_name:
             print(f"SUCCESS: lead_user_name is present: {returned_lead_name}")
        else:
             print("FAILURE: lead_user_name is missing.")
             
    else:
        print(f"Failed to create project: {resp.status_code} - {resp.text}")

if __name__ == "__main__":
    test_create_project_with_lead()
