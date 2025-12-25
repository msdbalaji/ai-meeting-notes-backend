import subprocess
import time
import requests
import os
import sys

BASE = 'http://127.0.0.1:8001/api'

def is_up():
    try:
        r = requests.get(BASE + '/')
        return r.status_code == 200
    except Exception:
        return False

def start_server():
    # Start uvicorn in a background process
    print('Starting uvicorn...')
    p = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8001'], cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), '..')),
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return p

def wait_up(timeout=20):
    start = time.time()
    while time.time() - start < timeout:
        if is_up():
            return True
        time.sleep(1)
    return False

def run_test():
    if not is_up():
        proc = start_server()
        ok = wait_up(30)
        if not ok:
            print('Server did not start in time')
            # print stderr
            try:
                out, err = proc.communicate(timeout=1)
                print('uvicorn stderr:', err.decode(errors='ignore'))
            except Exception:
                pass
            return
    else:
        proc = None

    # Create meeting
    print('Creating meeting...')
    r = requests.post(BASE + '/meetings/', json={'title': 'HTTP Smoke Meeting'})
    print('create', r.status_code, r.text)
    mid = r.json().get('id')

    # Post transcript via query params (text is parsed as query when File is present)
    text = 'This is HTTP smoke. Action: Alice to prepare the slides by Friday.'
    r2 = requests.post(f"{BASE}/transcribe/", params={'meeting_id': mid, 'text': text})
    print('transcribe', r2.status_code, r2.text)

    # Get meeting
    r3 = requests.get(f"{BASE}/meetings/{mid}")
    print('meeting', r3.status_code, r3.text)

    # Get tasks
    r4 = requests.get(BASE + '/tasks/', params={'meeting_id': mid})
    print('tasks', r4.status_code, r4.text)

if __name__ == '__main__':
    run_test()
