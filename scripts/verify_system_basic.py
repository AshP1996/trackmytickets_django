import os
import sys
import requests
import json

BASE_URL = "http://localhost:8001"

def log(msg):
    print(f"[VERIFY] {msg}")

def verify():
    # 1. Check Health
    try:
        resp = requests.get(f"{BASE_URL}/health/")
        if resp.status_code != 200:
            log(f"Health check failed: {resp.status_code}")
            return
        log("Health check passed.")
    except Exception as e:
        log(f"Server not reachable: {e}")
        return

    # 2. Login (assuming we have a user or can create one)
    # Since we can't easily create a superuser via script without shell access,
    # we will try to login with a known default if it exists, or skip.
    # Actually, we can try to create a tenant via API if there is a public registration?
    # apps/accounts/views.py would tell us.
    
    # For now, let's just check if we can reach the API.
    resp = requests.get(f"{BASE_URL}/api/platform/organizations/")
    log(f"Platform Org List Status: {resp.status_code}")
    if resp.status_code == 200:
        log("Platform API accessible.")
    elif resp.status_code == 401:
        log("Platform API requires auth (Expected).")
    else:
        log(f"Unexpected status for Platform API: {resp.status_code}")

if __name__ == "__main__":
    verify()
