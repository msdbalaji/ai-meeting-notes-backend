# backend/app/auth/dependencies.py

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from .security import SECRET_KEY, ALGORITHM
from ..database import get_db
from .. import models

oauth2_scheme_optional = OAuth2PasswordBearer(
    tokenUrl="/api/auth/login",
    auto_error=False,
)

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/login"
)

def get_current_user_optional(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme_optional),
):
    if not token:
        return None

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        if not sub:
            return None

        # ✅ BACKWARD-COMPAT FIX
        if str(sub).isdigit():
            return db.query(models.User).filter(
                models.User.id == int(sub)
            ).first()
        else:
            return db.query(models.User).filter(
                models.User.email == sub
            ).first()

    except JWTError:
        return None

def get_current_user_required(
    user=Depends(get_current_user_optional),
):
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return user
