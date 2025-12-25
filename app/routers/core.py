from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from fastapi.responses import FileResponse
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
import tempfile

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT

from ..database import get_db
from .. import crud, schemas, models
from ..auth.dependencies import (
    get_current_user_optional,
)

router = APIRouter()

# =========================
# HEALTH
# =========================
@router.get("/", tags=["health"])
def health():
    return {"status": "ok", "service": "AI Meeting Notes backend"}


# =========================
# MEETINGS
# =========================
@router.post("/meetings/", response_model=schemas.MeetingOut, tags=["meetings"])
def create_meeting_endpoint(
    meeting: schemas.MeetingCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user_optional),
):
    if not user:
        anon_count = (
            db.query(models.Meeting)
            .filter(models.Meeting.owner_id == None)
            .count()
        )
        if anon_count >= 1:
            raise HTTPException(
                status_code=401,
                detail="Please login or signup to create more meetings",
            )
        return crud.create_meeting(db, meeting)

    return crud.create_meeting(db, meeting, owner_id=user.id)


@router.get("/meetings/{meeting_id}", response_model=schemas.MeetingOut, tags=["meetings"])
def get_meeting_endpoint(
    meeting_id: int,
    db: Session = Depends(get_db),
):
    meeting = crud.get_meeting(db, meeting_id)
    if not meeting:
        raise HTTPException(404, "Meeting not found")
    return meeting


@router.get("/meetings/", response_model=List[schemas.MeetingOut], tags=["meetings"])
def list_meetings_endpoint(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    user=Depends(get_current_user_optional),
):
    if user:
        return (
            db.query(models.Meeting)
            .filter(models.Meeting.owner_id == user.id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    return (
        db.query(models.Meeting)
        .filter(models.Meeting.owner_id == None)
        .offset(skip)
        .limit(limit)
        .all()
    )


# =========================
# TASKS
# =========================
@router.post("/meetings/{meeting_id}/tasks/", response_model=schemas.TaskOut, tags=["tasks"])
def create_task_endpoint(
    meeting_id: int,
    task: schemas.TaskCreate,
    db: Session = Depends(get_db),
):
    meeting = crud.get_meeting(db, meeting_id)
    if not meeting:
        raise HTTPException(404, "Meeting not found")
    return crud.create_task(db, meeting_id, task)


@router.get("/tasks/", response_model=List[schemas.TaskOut], tags=["tasks"])
def list_tasks_endpoint(
    meeting_id: Optional[int] = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user_optional),
):
    if user:
        return crud.list_tasks(db, meeting_id, user_id=user.id)

    meetings_count = db.query(models.Meeting).count()
    if meetings_count > 1:
        raise HTTPException(
            status_code=401,
            detail="Login required to view tasks",
        )

    return crud.list_tasks(db, meeting_id)


@router.put("/tasks/{task_id}", response_model=schemas.TaskOut, tags=["tasks"])
def update_task_endpoint(
    task_id: int,
    payload: schemas.TaskUpdate,
    db: Session = Depends(get_db),
):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(404, "Task not found")

    for field, value in payload.dict(exclude_unset=True).items():
        setattr(task, field, value)

    db.commit()
    db.refresh(task)
    return task


# =========================
# TRANSCRIPTION — TEXT
# =========================
@router.post("/transcribe/text", tags=["transcription"])
async def transcribe_text(
    meeting_id: int,
    text: str,
    db: Session = Depends(get_db),
):
    transcript = text

    summary = None
    try:
        from ..summarizer import summarize_meeting
        summary = summarize_meeting(transcript)
    except Exception:
        pass

    crud.add_transcript_and_summary(
        db,
        meeting_id,
        transcript=transcript,
        summary=summary,
    )

    return {
        "meeting_id": meeting_id,
        "transcript": transcript,
        "summary": summary,
    }


# =========================
# TRANSCRIPTION — AUDIO
# =========================
@router.post("/transcribe/audio", tags=["transcription"])
async def transcribe_audio_file(
    meeting_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    contents = await file.read()

    try:
        from ..asr import transcribe_bytes
        result = await transcribe_bytes(contents, filename=file.filename)
        transcript = result.get("text", "")
    except Exception:
        transcript = (
            f"[Audio uploaded: {file.filename} | {len(contents)} bytes]\n\n"
            "⚠️ Automatic transcription is currently unavailable."
        )

    summary = None
    try:
        from ..summarizer import summarize_meeting
        summary = summarize_meeting(transcript)
    except Exception:
        pass

    crud.add_transcript_and_summary(
        db,
        meeting_id,
        transcript=transcript,
        summary=summary,
    )

    return {
        "meeting_id": meeting_id,
        "transcript": transcript,
        "summary": summary,
    }


# =========================
# PDF EXPORT
# =========================
@router.get("/meetings/{meeting_id}/export/pdf", tags=["export"])
def export_meeting_pdf(
    meeting_id: int,
    db: Session = Depends(get_db),
):
    meeting = db.query(models.Meeting).filter(models.Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(404, "Meeting not found")

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")

    doc = SimpleDocTemplate(
        tmp.name,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="TitleStyle",
            fontSize=18,
            leading=22,
            spaceAfter=16,
            alignment=TA_LEFT,
        )
    )

    elements = []
    elements.append(Paragraph(meeting.title, styles["TitleStyle"]))
    elements.append(Paragraph("Summary", styles["Heading2"]))
    elements.append(
        Paragraph((meeting.summary or "—").replace("\n", "<br/>"), styles["BodyText"])
    )

    doc.build(elements)

    return FileResponse(
        tmp.name,
        filename=f"meeting-{meeting_id}.pdf",
        media_type="application/pdf",
    )
