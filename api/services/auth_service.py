from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
import jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from fastapi import HTTPException, status, Depends
import secrets

from api.models.users import User, AuthSession, TokenData
from api import config
from api.database import get_db

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, config.JWT_SECRET_KEY, algorithm=config.JWT_ALGORITHM)
    return encoded_jwt

def create_user(db: Session, username: str, email: Optional[str], password: str) -> User:
    hashed_password = get_password_hash(password)
    db_user = User(
        username=username,
        email=email,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user

def create_user_session(db: Session, user_id: UUID) -> AuthSession:
    # Delete any existing sessions for this user
    db.query(AuthSession).filter(AuthSession.user_id == user_id).delete()
    
    # Create new session
    expires_at = datetime.utcnow() + timedelta(days=7)
    session = AuthSession(
        user_id=user_id,
        token=create_access_token(
            {"sub": str(user_id)},
            expires_delta=timedelta(days=7)
        ),
        expires_at=expires_at
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session

async def get_current_user(token: str, db: Session) -> User:
    try:
        payload = jwt.decode(
            token,
            config.JWT_SECRET_KEY,
            algorithms=[config.JWT_ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )
        
        # Verify session exists and is not expired
        session = db.query(AuthSession).filter(
            AuthSession.user_id == user_id,
            AuthSession.token == token,
            AuthSession.expires_at > datetime.utcnow()
        ).first()
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired or invalid"
            )
        
        user = db.query(User).filter(User.id == user_id).first()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        return user
        
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )

async def get_current_user_or_default(token: str = None, db: Session = Depends(get_db)) -> User:
    """Get the current user from the token, or return the default user if authentication fails"""
    if not token:
        # Return default user
        default_user = db.query(User).filter(User.username == "default").first()
        if not default_user:
            default_user = create_default_user(db)
        return default_user
    
    try:
        return await get_current_user(token, db)
    except HTTPException:
        # Return default user on authentication failure
        default_user = db.query(User).filter(User.username == "default").first()
        if not default_user:
            default_user = create_default_user(db)
        return default_user

def create_default_user(db: Session) -> User:
    """Create the default user if it doesn't exist"""
    default_user = db.query(User).filter(User.username == "default").first()
    if default_user:
        return default_user
    
    return create_user(
        db=db,
        username="default",
        email="default@hubgpt.local",
        password=secrets.token_urlsafe(32)  # Generate a random password
    ) 