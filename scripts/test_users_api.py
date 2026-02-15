import requests
import json
import os

# Configuration
BASE_URL = "http://localhost:8000"
ORG = "acme"
ADMIN_EMAIL = "admin@acme.com"
PASSWORD = "password123"

def test_users_api():
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
    session.headers.update({"Authorization": f"Bearer {access_token}"})
    print("Login successful.")

    # 2. Get Users
    print(f"Fetching users from /api/{ORG}/auth/users/...")
    users_url = f"{BASE_URL}/api/{ORG}/auth/users/"
    resp = session.get(users_url)
    
    if resp.status_code == 200:
        data = resp.json()
        print(f"Status: {resp.status_code}")
        print("Response keys:", data.keys() if isinstance(data, dict) else "List")
        
        results = data.get('results', data) if isinstance(data, dict) else data
        print(f"Found {len(results)} users.")
        if len(results) > 0:
            print("First user sample:", json.dumps(results[0], indent=2))
            
        # Check compatibility with frontend expectation
        # Frontend expects: usersData.results || usersData.users || usersData
        # And user.id, user.full_name, user.is_active
        if isinstance(data, dict) and 'results' in data:
            print("Structure matches 'results' key.")
        elif isinstance(data, list):
            print("Structure matches raw list.")
    else:
        print(f"Failed to get users: {resp.status_code} - {resp.text}")

if __name__ == "__main__":
    test_users_api()
