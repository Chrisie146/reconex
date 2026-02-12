import urllib.request, urllib.error

url = 'http://localhost:8000/transactions/clear-categories?session_id=da31c9a9-7e3d-4daa-ae10-7d5a2a3d9f35'
req = urllib.request.Request(url, data=b'{}', method='POST')
try:
    resp = urllib.request.urlopen(req, timeout=10)
    body = resp.read().decode('utf-8')
    print('STATUS', resp.status)
    print(body)
except urllib.error.HTTPError as e:
    try:
        err = e.read().decode('utf-8')
    except Exception:
        err = str(e)
    print('HTTPError', e.code)
    print(err)
except Exception as e:
    print('ERROR', str(e))
