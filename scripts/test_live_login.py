
import urllib.request
import urllib.error
import json
import sys

def test_login(email, password, company_name, port=9000):
    url = f"http://localhost:{port}/api/{company_name}/auth/login/"
    print(f"Testing {url} with {email}...")
    
    data = json.dumps({'email': email, 'password': password}).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    
    try:
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                body = response.read().decode('utf-8')
                resp_json = json.loads(body)
                print(f"✓ Login Successful for {email}")
                # print(f"  Token: {resp_json.get('access_token')[:20]}...")
            else:
                print(f"✗ Status: {response.status}")
                
    except urllib.error.HTTPError as e:
        print(f"✗ HTTP Error {e.code}: {e.reason}")
        print(f"  Response: {e.read().decode('utf-8')}")
    except Exception as e:
        print(f"✗ Failed: {e}")

if __name__ == "__main__":
    # Test Agent
    test_login("agent@democorp.com", "password123", "demo")
    # Test Admin
    test_login("admin@democorp.com", "password123", "demo")
    # Test Head
    test_login("head@democorp.com", "password123", "demo")
