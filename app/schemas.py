# backend/app/schemas.py
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserOut(UserBase):
    id: int
    is_active: bool
    class Config:
        orm_mode = True

class TaskCreate(BaseModel):
    title: str
    assigned_to: Optional[str] = None
    due_date: Optional[datetime] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    assigned_to: Optional[str] = None
    due_date: Optional[datetime] = None
    completed: Optional[bool] = None

class TaskOut(TaskCreate):
    id: int
    completed: bool
    class Config:
        orm_mode = True

class MeetingCreate(BaseModel):
    title: Optional[str] = "Untitled meeting"
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

class MeetingOut(MeetingCreate):
    id: int
    transcript: Optional[str] = None
    summary: Optional[str] = None
    tasks: List[TaskOut] = []
    class Config:
        orm_mode = True
