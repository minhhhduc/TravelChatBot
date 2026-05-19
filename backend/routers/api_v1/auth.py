"""API v1 authentication endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.auth_utils import create_access_token, get_current_user
from backend.database import get_db
from backend.models import User
from .schemas import ApiUser, LoginRequest, LoginResponse

router = APIRouter(prefix="/auth", tags=["API v1 - Auth"])


@router.post("/login", response_model=LoginResponse)
def api_login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not user.check_password(payload.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password.")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user profile.")
    return {
        "access_token": create_access_token(data={"sub": user.username}),
        "token_type": "bearer",
        "user": user,
    }


@router.get("/me", response_model=ApiUser)
def api_me(current_user: User = Depends(get_current_user)):
    return current_user
