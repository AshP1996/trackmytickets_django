
import requests
import sys

BASE_URL = "http://localhost:8001"
EMAIL = "agent@acme.com"
PASSWORD = "password123"

def log(msg):
    print(f"[PAGINATION] {msg}")

def test_pagination():
    # 1. Login
    log("Logging in...")
    resp = requests.post(f"{BASE_URL}/api/acme/auth/login/", json={"email": EMAIL, "password": PASSWORD})
    if resp.status_code != 200:
        log(f"Login failed: {resp.status_code}")
        return
    token = resp.json()['access_token']
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Test Default (20) - Should get 20? No if we have 30 tickets.
    log("Testing default pagination (page 1)...")
    resp = requests.get(f"{BASE_URL}/api/acme/tickets/", headers=headers)
    data = resp.json()
    count = data['count']
    results = data['results']
    log(f"Total count: {count}")
    log(f"Returned results: {len(results)}")
    
    if count < 30:
        log("Warning: Less than 30 tickets. Run seed_data.py first.")
    
    # 3. Test Page Size = 10
    log("Testing page_size=10...")
    resp = requests.get(f"{BASE_URL}/api/acme/tickets/?page_size=10", headers=headers)
    results = resp.json()['results']
    if len(results) == 10:
        log("Success: Got 10 tickets.")
    else:
        log(f"Failure: Expected 10, got {len(results)}")

    # 4. Test Page Size = 25
    log("Testing page_size=25...")
    resp = requests.get(f"{BASE_URL}/api/acme/tickets/?page_size=25", headers=headers)
    results = resp.json()['results']
    if len(results) == 25:
        log("Success: Got 25 tickets.")
    else:
        log(f"Failure: Expected 25, got {len(results)}")

    # 5. Test Page 2 with page_size=10
    log("Testing page 2 (size 10)...")
    resp = requests.get(f"{BASE_URL}/api/acme/tickets/?page_size=10&page=2", headers=headers)
    results = resp.json()['results']
    # Check if results are different from page 1?
    # Simple check: we got results.
    if len(results) > 0:
        log("Success: Got tickets on page 2.")
    else:
        log("Failure: No tickets on page 2.")

if __name__ == "__main__":
    test_pagination()
