import requests

# Test the clear-categories endpoint
url = 'http://localhost:8000/transactions/clear-categories'
session_id = 'test-session-id'

# Test 1: Query param
print("Test 1: Query param")
response = requests.post(url, params={'session_id': session_id}, json={})
print(f"Status: {response.status_code}")
print(f"Response: {response.text}")
print()

# Test 2: Body
print("Test 2: Body")
response = requests.post(url, json={'session_id': session_id})
print(f"Status: {response.status_code}")
print(f"Response: {response.text}")
print()

# Test 3: Both
print("Test 3: Both")
response = requests.post(url, params={'session_id': session_id}, json={'session_id': session_id})
print(f"Status: {response.status_code}")
print(f"Response: {response.text}")
