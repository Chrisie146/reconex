"""
Pydantic schemas for request/response validation
"""

from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


# ==================== Authentication Schemas ====================

class UserRegister(BaseModel):
    """Registration request schema"""
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    
    class Config:
        example = {
            "email": "accountant@example.com",
            "password": "SecurePassword123!",
            "full_name": "John Accountant"
        }


class UserLogin(BaseModel):
    """Login request schema"""
    email: EmailStr
    password: str
    
    class Config:
        example = {
            "email": "accountant@example.com",
            "password": "SecurePassword123!"
        }


class TokenResponse(BaseModel):
    """Token response schema"""
    access_token: str
    token_type: str = "bearer"
    user_id: int
    email: str
    full_name: Optional[str] = None


class UserResponse(BaseModel):
    """User response schema (for profile endpoints)"""
    id: int
    email: str
    full_name: Optional[str]
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class ChangePasswordRequest(BaseModel):
    """Change password request schema"""
    old_password: str
    new_password: str
    new_password_confirm: str


# ==================== Client Schemas ====================

class ClientCreate(BaseModel):
    """Create client request"""
    name: str


class ClientUpdate(BaseModel):
    """Update client request"""
    name: Optional[str] = None


class ClientResponse(BaseModel):
    """Client response schema"""
    id: int
    name: str
    user_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# ==================== Transaction Schemas ====================

class TransactionResponse(BaseModel):
    """Transaction response schema"""
    id: int
    client_id: Optional[int]
    session_id: str
    date: str
    description: str
    amount: float
    category: str
    
    class Config:
        from_attributes = True


# ==================== Session Schemas ====================

class SessionResponse(BaseModel):
    """Session response schema"""
    session_id: str
    locked: bool
    friendly_name: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True
