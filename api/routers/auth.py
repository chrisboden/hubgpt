from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Dict
import secrets

from api.database import get_db
from api.models.users import User, UserCreate, UserResponse, UserLogin, Token, AuthSession
from api.services.auth_service import (
    create_user,
    authenticate_user,
    create_user_session,
    get_current_user
)
from api import config

router = APIRouter(
    tags=["authentication"],
    redirect_slashes=False  # Prevent automatic slash redirection
)
security = HTTPBasic()

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    try:
        user = create_user(
            db,
            username=user_data.username,
            email=user_data.email,
            password=user_data.password
        )
        return user
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered"
        )

@router.post("/login", response_model=Token)
async def login(user_data: UserLogin, db: Session = Depends(get_db)):
    user = authenticate_user(db, user_data.username, user_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    session = create_user_session(db, user.id)
    return Token(access_token=session.token)

@router.post("/logout", response_model=Dict[str, str])
async def logout(request: Request, db: Session = Depends(get_db)):
    """Logout the current user by invalidating their session"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header"
        )
    
    token = auth_header.split(" ")[1]
    user = await get_current_user(token, db)
    
    # Delete all sessions for the user
    db.query(AuthSession).filter(AuthSession.user_id == user.id).delete()
    db.commit()
    return {"message": "Successfully logged out"}

@router.get("/verify", response_model=UserResponse)
async def verify(
    request: Request,
    credentials: HTTPBasicCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Verify the current user's credentials and return user info"""
    # First try JWT token
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        try:
            token = auth_header.split(" ")[1]
            return await get_current_user(token, db)
        except HTTPException:
            pass
    
    # Try basic auth
    is_username_correct = secrets.compare_digest(credentials.username, config.API_USERNAME)
    is_password_correct = secrets.compare_digest(credentials.password, config.API_PASSWORD)
    
    if not (is_username_correct and is_password_correct):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    # Get or create default user
    user = db.query(User).filter(User.username == credentials.username).first()
    if not user:
        user = create_user(
            db,
            username=credentials.username,
            email=config.DEFAULT_USER_EMAIL,
            password=config.API_PASSWORD
        )
    return user

@router.get("/users/me", response_model=UserResponse)
async def get_current_user_info(request: Request, db: Session = Depends(get_db)):
    """Get current user information"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header"
        )
    
    token = auth_header.split(" ")[1]
    user = await get_current_user(token, db)
    return user 