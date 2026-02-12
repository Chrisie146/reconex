"""
Authentication utilities for JWT-based authentication
Handles password hashing, token generation, and user verification
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Bearer token scheme
security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password for storage"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token
    
    Args:
        data: Dictionary containing user data (typically {"sub": user_id})
        expires_delta: Optional custom expiration time
    
    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decode and verify a JWT token
    
    Args:
        token: JWT token string
    
    Returns:
        Decoded token payload if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> int:
    """
    Dependency to extract and verify current user from JWT token
    
    This should be used in all protected endpoints:
    @app.get("/protected")
    def protected_route(current_user_id: int = Depends(get_current_user_id)):
        # current_user_id is now guaranteed to be authenticated
    
    Raises:
        AuthenticationError: If token is invalid or user not found
    
    Returns:
        User ID of authenticated user
    """
    from exceptions import AuthenticationError
    
    try:
        token = credentials.credentials
        payload = decode_access_token(token)
        
        if payload is None:
            raise AuthenticationError("Could not validate credentials")
        
        user_id: str = payload.get("sub")
        if user_id is None:
            raise AuthenticationError("Could not validate credentials")
        
        # Convert to integer (our User model uses integer IDs)
        return int(user_id)
        
    except (JWTError, ValueError, AttributeError):
        raise AuthenticationError("Could not validate credentials")


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(lambda: None)
):
    """
    Dependency to get full User object from JWT token
    
    Note: db is injected by FastAPI when used as a dependency
    
    Returns:
        User model instance
    """
    from models import User, get_db  # Import here to avoid circular imports
    from exceptions import AuthenticationError
    
    # Get database session
    if db is None:
        # This shouldn't happen in normal FastAPI usage, but handle it gracefully
        db_gen = get_db()
        db = next(db_gen)
    
    try:
        token = credentials.credentials
        payload = decode_access_token(token)
        
        if payload is None:
            raise AuthenticationError("Could not validate credentials")
        
        user_id: str = payload.get("sub")
        if user_id is None:
            raise AuthenticationError("Could not validate credentials")
        
        # Get user from database
        user = db.query(User).filter(User.id == int(user_id)).first()
        if user is None:
            raise AuthenticationError("User not found")
        
        return user
        
    except AuthenticationError:
        raise
    except (JWTError, ValueError, AttributeError):
        raise AuthenticationError("Could not validate credentials")
