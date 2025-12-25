from fastapi.testclient import TestClient
from app.main import app

BASE = '/api'

def run_test():
    client = TestClient(app)

    print('Creating meeting...')
    r = client.post(BASE + '/meetings/', json={'title': 'InProc HTTP Smoke Meeting'})
    print('create', r.status_code, r.text)
    mid = r.json().get('id')

    text = 'This is inproc HTTP smoke. Action: Alice to prepare the slides by Friday.'
    r2 = client.post(BASE + '/transcribe/', params={'meeting_id': mid, 'text': text})
    print('transcribe', r2.status_code, r2.text)

    r3 = client.get(BASE + f'/meetings/{mid}')
    print('meeting', r3.status_code, r3.text)

    r4 = client.get(BASE + '/tasks/', params={'meeting_id': mid})
    print('tasks', r4.status_code, r4.text)

if __name__ == '__main__':
    run_test()
