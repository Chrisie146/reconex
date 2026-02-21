import requests
import json

# Test login
login_data = {'email': 'dev@example.com', 'password': 'dev123456'}
try:
    response = requests.post('http://localhost:8000/auth/login', json=login_data)
    print('Login status:', response.status_code)
    if response.status_code == 200:
        token = response.json()['access_token']
        print('Got token')

        # Test sessions endpoint
        headers = {'Authorization': f'Bearer {token}'}
        sessions_resp = requests.get('http://localhost:8000/sessions', headers=headers)
        print('Sessions status:', sessions_resp.status_code)
        if sessions_resp.status_code == 200:
            sessions_data = sessions_resp.json()
            print('Sessions:', len(sessions_data.get('sessions', [])))
            for s in sessions_data.get('sessions', []):
                print(f'  {s.get("session_id")}: {s.get("transaction_count")} txns')

        # Test transactions for the session
        if sessions_data.get('sessions'):
            session_id = sessions_data['sessions'][0]['session_id']
            tx_resp = requests.get(f'http://localhost:8000/transactions?session_id={session_id}', headers=headers)
            print(f'Transactions for {session_id}:', tx_resp.status_code)
            if tx_resp.status_code == 200:
                tx_data = tx_resp.json()
                print(f'Found {len(tx_data.get("transactions", []))} transactions')
    else:
        print('Login failed:', response.text)
except Exception as e:
    print('Error:', e)