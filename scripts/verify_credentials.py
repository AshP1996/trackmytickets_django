
import requests
import json
import sys

BASE_URL = "http://localhost:8080"

RED = "\033[91m"
GREEN = "\033[92m"
RESET = "\033[0m"

def test_login(name, url, email, password):
    print(f"Testing {name} login ({email})...", end=" ")
    try:
        response = requests.post(url, json={
            "email": email,
            "password": password
        })
        
        if response.status_code == 200:
            print(f"{GREEN}SUCCESS{RESET}")
            return True, response.json()
        else:
            print(f"{RED}FAILED ({response.status_code}){RESET}")
            print(f"Response: {response.text}")
            return False, None
    except Exception as e:
        print(f"{RED}ERROR{RESET}: {e}")
        return False, None

def verify_credentials():
    results = {}
    
    # 1. Platform Admin
    success, data = test_login(
        "Platform Admin", 
        f"{BASE_URL}/api/platform/login", 
        "superadmin@platform.com", 
        "password123"
    )
    results["Platform Admin"] = success

    # 2. Org Admin
    success, data = test_login(
        "Org Admin", 
        f"{BASE_URL}/api/demo/auth/login/", 
        "admin@demo.com", 
        "password123"
    )
    results["Org Admin"] = success

    # 3. Org Agent
    success, data = test_login(
        "Org Agent", 
        f"{BASE_URL}/api/demo/auth/login/", 
        "agent@demo.com", 
        "password123"
    )
    results["Org Agent"] = success

    # 4. Org Customer
    success, data = test_login(
        "Org Customer", 
        f"{BASE_URL}/api/demo/auth/login/", 
        "customer@demo.com", 
        "password123"
    )
    results["Org Customer"] = success

    print("\nSummary:")
    all_passed = True
    for role, status in results.items():
        print(f"{role}: {'✅' if status else '❌'}")
        if not status:
            all_passed = False
            
    if all_passed:
        print(f"\n{GREEN}All credentials verified successfully!{RESET}")
        sys.exit(0)
    else:
        print(f"\n{RED}Some credentials failed verification.{RESET}")
        sys.exit(1)

if __name__ == "__main__":
    verify_credentials()
