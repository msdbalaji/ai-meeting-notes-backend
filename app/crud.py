from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional, Dict, Any
import json

from . import models, schemas


def add_transcript_and_summary(
    db: Session,
    meeting_id: int,
    transcript: str = None,
    summary: str = None,
):
    meeting = db.query(models.Meeting).filter(models.Meeting.id == meeting_id).first()
    if meeting is None:
        meeting = models.Meeting(id=meeting_id, title=f"Meeting {meeting_id}")
        db.add(meeting)
        db.commit()
        db.refresh(meeting)

    if transcript is not None:
        meeting.transcript = transcript
    if summary is not None:
        meeting.summary = summary

    db.commit()
    db.refresh(meeting)
    return meeting


def create_task(
    db: Session,
    meeting_id: int,
    task_obj,
):
    title_val = ""
    assigned = None
    due_dt = None
    metadata_content = None

    if hasattr(task_obj, "dict"):
        tdict = task_obj.dict()
    elif isinstance(task_obj, dict):
        tdict = task_obj
    else:
        tdict = {"title": str(task_obj)}

    title_val = (tdict.get("title") or "")[:512]
    assigned = tdict.get("assigned_to") or tdict.get("assignee")

    due_date_raw = tdict.get("due_date")
    if due_date_raw:
        try:
            from dateutil import parser as date_parser
            due_dt = date_parser.parse(due_date_raw)
        except Exception:
            pass

    meta = {k: v for k, v in tdict.items() if k not in ("title", "assigned_to", "assignee", "due_date")}
    if meta:
        metadata_content = json.dumps(meta)

    task = models.Task(
        meeting_id=meeting_id,
        title=title_val,
        assigned_to=assigned,
        due_date=due_dt,
        completed=False,
        metadata_json=metadata_content,
    )

    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def list_tasks(
    db: Session,
    meeting_id: Optional[int] = None,
    user_id: Optional[int] = None,
):
    q = db.query(models.Task).join(models.Meeting)

    if user_id:
        q = q.filter(models.Meeting.owner_id == user_id)
    if meeting_id:
        q = q.filter(models.Task.meeting_id == meeting_id)

    return q.all()


def get_meeting(db: Session, meeting_id: int):
    return db.query(models.Meeting).filter(models.Meeting.id == meeting_id).first()


def create_meeting(
    db: Session,
    meeting: schemas.MeetingCreate,
    owner_id: Optional[int] = None,
):
    m = models.Meeting(
        title=meeting.title,
        owner_id=owner_id,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


def list_meetings(db: Session, skip: int = 0, limit: int = 50):
    return db.query(models.Meeting).offset(skip).limit(limit).all()
