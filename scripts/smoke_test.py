import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from fastapi.testclient import TestClient
from app.main import app

def run():
    client = TestClient(app)

    print('Creating meeting...')
    r = client.post('/api/meetings/', json={'title': 'Smoke Test Meeting'})
    print('create status', r.status_code)
    print(r.json())
    mid = r.json().get('id')

    print('Posting transcript text...')
    text = 'This is a test transcript. Action: Alice to prepare the slides by Friday.'
    r2 = client.post(f"/api/transcribe/?meeting_id={mid}&text={text}")
    print('transcribe status', r2.status_code)
    print(r2.json())

    print('Fetching meeting...')
    r3 = client.get(f'/api/meetings/{mid}')
    print('meeting status', r3.status_code)
    print(r3.json())

    print('Listing tasks...')
    r4 = client.get(f'/api/tasks/?meeting_id={mid}')
    print('tasks status', r4.status_code)
    print(r4.json())

if __name__ == '__main__':
    run()
