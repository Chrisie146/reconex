import requests, sys
url = 'http://localhost:8000/upload_pdf?preview=true'
files = {'file': open('Standard bank.pdf','rb')}
try:
    r = requests.post(url, files=files, timeout=30)
    print('Status:', r.status_code)
    try:
        data = r.json()
        print('Response:', data)
        if data.get('transactions'):
            print('Transaction count:', len(data['transactions']))
    except Exception as ex:
        print('Parse error:', ex)
        print('Text:', r.text[:1000])
except Exception as e:
    print('Request error:', repr(e))
