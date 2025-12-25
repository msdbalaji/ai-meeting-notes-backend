# backend/app/auth/google.py
from fastapi import APIRouter, Request, Depends
from starlette.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuth
from sqlalchemy.orm import Session
import os

from ..database import get_db
from .. import models
from .security import create_access_token

router = APIRouter()
oauth = OAuth()

oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

@router.get("/google/login")
async def google_login(request: Request):
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get("/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    token = await oauth.google.authorize_access_token(request)
    info = token["userinfo"]

    # 🔐 CREATE OR FETCH USER
    user = db.query(models.User).filter(
        models.User.email == info["email"]
    ).first()

    if not user:
        user = models.User(
            email=info["email"],
            name=info["name"],
            hashed_password="google-oauth",  # placeholder
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # ✅ JWT sub MUST BE USER.ID (NOT EMAIL)
    access_token = create_access_token({
        "sub": str(user.id),
        "name": user.name,
    })

    frontend_redirect = (
        f"http://localhost:3000/auth/google-success"
        f"?token={access_token}"
        f"&name={user.name}"
        f"&email={user.email}"
    )

    return RedirectResponse(frontend_redirect)
