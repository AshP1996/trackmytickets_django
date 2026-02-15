import requests
import time
import sys
import threading

BASE_URL = "http://localhost:8000"

def check_health():
    try:
        print(f"Checking {BASE_URL}/health/ ...")
        resp = requests.get(f"{BASE_URL}/health/")
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.json()}")
        if resp.status_code == 200:
            return True
        return False
    except Exception as e:
        print(f"Health check failed: {e}")
        return False

def load_test():
    print("\nStarting mini-load test (50 requests)...")
    success = 0
    errors = 0
    start_time = time.time()
    
    def make_request():
        nonlocal success, errors
        try:
            # Platform login page is public
            requests.get(f"{BASE_URL}/platform/login")
            success += 1
        except:
            errors += 1

    threads = []
    for _ in range(50):
        t = threading.Thread(target=make_request)
        threads.append(t)
        t.start()
        
    for t in threads:
        t.join()
        
    duration = time.time() - start_time
    print(f"Requests: 50, Success: {success}, Errors: {errors}")
    print(f"Total Time: {duration:.2f}s, RPS: {50/duration:.2f}")

if __name__ == "__main__":
    print("=== Performance Verification ===\n")
    if check_health():
        load_test()
    else:
        print("System is unhealthy. Aborting load test.")
        sys.exit(1)
