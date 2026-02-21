import requests
import json

# Try to get sessions
try:
    resp = requests.get('http://localhost:8000/sessions')
    if resp.status_code == 200:
        sessions = resp.json().get('sessions', [])
        if sessions:
            print('Available sessions:')
            for s in sessions[:5]:  # Show first 5
                print(f'  {s.get("session_id")}: {s.get("friendly_name", "Unnamed")}')

            # Use the first session to check categories
            session_id = sessions[0]['session_id']
            print(f'\nUsing session: {session_id}')

            # Get transactions for this session
            resp = requests.get(f'http://localhost:8000/transactions?session_id={session_id}')
            if resp.status_code == 200:
                data = resp.json()
                txns = data.get('transactions', [])

                # Count categories
                categories = {}
                empty_count = 0
                other_count = 0

                for t in txns:
                    cat = t.get('category', '')
                    if not cat or cat == '':
                        empty_count += 1
                    elif cat == 'Other':
                        other_count += 1
                    else:
                        categories[cat] = categories.get(cat, 0) + 1

                print(f'Total transactions: {len(txns)}')
                print(f'Empty/null categories: {empty_count}')
                print(f'"Other" categories: {other_count}')
                print(f'Other categories: {dict(list(categories.items())[:10])}')  # Show first 10
        else:
            print('No sessions found')
    else:
        print(f'Failed to get sessions: {resp.status_code}')
except Exception as e:
    print(f'Error: {e}')