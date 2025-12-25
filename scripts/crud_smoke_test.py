import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import database, crud, models
from types import SimpleNamespace

def run():
    # ensure tables
    database.Base.metadata.create_all(bind=database.engine)
    db = next(database.get_db())

    # create meeting
    m = SimpleNamespace(title='CRUD Smoke Meeting')
    meeting = crud.create_meeting(db, m)
    print('Created meeting id', meeting.id)

    # add transcript and summary
    transcript = 'This is a test. Action: Bob to send the proposal by next Monday.'
    from app import actions
    items = actions.extract_action_items(transcript)
    crud.add_transcript_and_summary(db, meeting.id, transcript=transcript, summary='Short summary')
    print('Extracted items:', items)

    for it in items:
        crud.create_task(db, meeting.id, {
            'title': it.get('task') or it.get('context'),
            'assigned_to': it.get('assignee'),
            'due_date': it.get('deadline')
        })

    print('Meeting row:', crud.get_meeting(db, meeting.id).transcript[:80])
    print('Tasks:', crud.list_tasks(db, meeting.id))

if __name__ == '__main__':
    run()
