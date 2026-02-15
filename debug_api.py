import json
import requests

with open('token.json', 'r') as f:
    data = json.load(f)
    token = data['access_token']

headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
}

base_url = 'http://localhost:8080/api/demo'

print(f"Testing Users API: {base_url}/auth/users/")
try:
    response = requests.get(f'{base_url}/auth/users/', headers=headers)
    print(f"Users Status: {response.status_code}")
    print(f"Users Response: {response.text[:200]}...")
    with open('users.json', 'w') as f:
        f.write(response.text)
except Exception as e:
    print(f"Users API Error: {e}")

print(f"Testing Projects API: {base_url}/projects/")
try:
    response = requests.get(f'{base_url}/projects/', headers=headers)
    print(f"Projects Status: {response.status_code}")
    print(f"Projects Response: {response.text[:200]}...")
    with open('projects.json', 'w') as f:
        f.write(response.text)
except Exception as e:
    print(f"Projects API Error: {e}")
