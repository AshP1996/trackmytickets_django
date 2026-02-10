import requests
import json

BASE_URL = "http://localhost:9000/api/testverify"
AUTH_URL = f"{BASE_URL}/auth/login/"
TICKETS_URL = f"{BASE_URL}/tickets/"

def debug_tickets():
    # 1. Login
    print(f"Logging in to {AUTH_URL}...")
    try:
        resp = requests.post(AUTH_URL, json={'email': 'head@testverify.com', 'password': 'password'})
        print(f"Login Status: {resp.status_code}")
        if resp.status_code != 200:
            print("Login failed:", resp.text)
            return

        data = resp.json()
        token = data.get('access_token')
        if not token:
            print("No access token returned")
            return
        
        print("Login successful. Token obtained.")
        
        # 2. Get Tickets
        headers = {'Authorization': f'Bearer {token}'}
        print(f"Fetching tickets from {TICKETS_URL}...")
        resp = requests.get(TICKETS_URL, headers=headers)
        print(f"Tickets Status: {resp.status_code}")
        try:
            print("Response:", json.dumps(resp.json(), indent=2))
        except:
            print("Response text:", resp.text)

    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    debug_tickets()
