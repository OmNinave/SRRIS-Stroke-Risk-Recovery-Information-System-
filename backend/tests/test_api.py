import sys, requests
sys.path.insert(0, '.')

base = 'http://127.0.0.1:8080'
results = []

# 1. Health check
try:
    r = requests.get(base + '/', timeout=3)
    results.append('[PASS] GET / -> ' + str(r.status_code))
except Exception as e:
    results.append('[FAIL] Server not reachable: ' + str(e))
    for l in results: print(l)
    exit()

# 2. Login
r = requests.post(base + '/api/v1/auth/token', data={'username': 'dr_smith', 'password': 'admin123'}, timeout=5)
if r.status_code == 200:
    token = r.json()['access_token']
    results.append('[PASS] Login dr_smith/admin123 -> 200 OK')
else:
    results.append('[FAIL] Login -> ' + str(r.status_code) + ': ' + r.text)
    for l in results: print(l)
    exit()

headers = {'Authorization': 'Bearer ' + token}

# 3. /me
r = requests.get(base + '/api/v1/auth/me', headers=headers, timeout=5)
if r.status_code == 200:
    results.append('[PASS] /auth/me -> 200, user=' + r.json().get('username','?'))
else:
    results.append('[FAIL] /auth/me -> ' + str(r.status_code))

# 4. Patient list
r = requests.get(base + '/api/v1/patients/search?q=', headers=headers, timeout=5)
data = r.json() if r.status_code == 200 else []
results.append('[PASS] /patients/search -> ' + str(r.status_code) + ', ' + str(len(data)) + ' patients')

uid = data[0]['patient_uid'] if data else 'SR-XXXXXX'
results.append('  Using UID: ' + uid)

# 5. Get patient
r = requests.get(base + '/api/v1/patients/' + uid, headers=headers, timeout=5)
results.append('[PASS] GET /patients/' + uid + ' -> ' + str(r.status_code) if r.status_code == 200 else '[FAIL] GET /patients/' + uid + ' -> ' + str(r.status_code))

# 6. Summary - most critical
r = requests.get(base + '/api/v1/patients/' + uid + '/summary', headers=headers, timeout=15)
results.append('[PASS] /summary -> ' + str(r.status_code) + ' (' + str(len(r.text)) + ' bytes)' if r.status_code == 200 else '[FAIL] /summary -> ' + str(r.status_code) + ': ' + r.text[:100])

# 7. Timeline
r = requests.get(base + '/api/v1/patients/' + uid + '/timeline', headers=headers, timeout=10)
results.append('[PASS] /timeline -> ' + str(r.status_code) if r.status_code == 200 else '[FAIL] /timeline -> ' + str(r.status_code))

# 8. Documents
r = requests.get(base + '/api/v1/patients/' + uid + '/documents', headers=headers, timeout=5)
doc_count = len(r.json()) if r.status_code == 200 else 0
results.append('[PASS] /documents -> ' + str(r.status_code) + ', ' + str(doc_count) + ' docs' if r.status_code == 200 else '[FAIL] /documents -> ' + str(r.status_code))

# 9. Processing status (patients.py route)
r = requests.get(base + '/api/v1/patients/' + uid + '/processing-status', headers=headers, timeout=5)
results.append('[PASS] /processing-status -> ' + str(r.status_code) if r.status_code == 200 else '[FAIL] /processing-status -> ' + str(r.status_code))

# 10. Documents processing-status (documents.py route)
r = requests.get(base + '/api/v1/patients/' + uid + '/documents/processing-status', headers=headers, timeout=5)
results.append('[PASS] /docs/processing-status -> ' + str(r.status_code) if r.status_code == 200 else '[FAIL] /docs/processing-status -> ' + str(r.status_code))

# 11. Analytics
r = requests.get(base + '/api/v1/analytics/hospital-stats', headers=headers, timeout=5)
results.append('[PASS] /analytics/hospital-stats -> ' + str(r.status_code) if r.status_code == 200 else '[FAIL] /analytics -> ' + str(r.status_code) + ': ' + r.text[:80])

for l in results:
    print(l)
