"""
Pydantic schemas for request/response validation
"""

from pydantic import BaseModel, EmailStr, Field
from typing import List, Literal, Optional
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
        orm_mode = True
        from_attributes = True


class ChangePasswordRequest(BaseModel):
    """Change password request schema"""
    old_password: str
    new_password: str
    new_password_confirm: str


class ForgotPasswordRequest(BaseModel):
    """Forgot password request schema"""
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Reset password request schema"""
    token: str
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
        orm_mode = True
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
    account_id: Optional[int]
    category: str

    class Config:
        orm_mode = True
        from_attributes = True


# ==================== Account / Chart-of-Accounts Schemas ====================


AccountType = Literal["asset", "liability", "equity", "revenue", "expense"]
NormalBalance = Literal["DR", "CR"]
CashFlowSection = Literal["operating", "investing", "financing", "none"]
VATTreatment = Literal["standard_15", "zero_rated", "exempt", "out_of_scope"]


class AccountCreate(BaseModel):
    """Create a new (user-defined) account."""
    client_id: int
    code: str
    name: str
    parent_id: Optional[int] = None
    account_type: AccountType
    account_subtype: Optional[str] = None
    normal_balance: NormalBalance
    cash_flow_section: CashFlowSection = "none"
    is_vat_control: bool = False
    vat_treatment: Optional[VATTreatment] = None
    vat_rate: Optional[float] = None
    is_postable: bool = True
    description: Optional[str] = None


class AccountUpdate(BaseModel):
    """Patch an account.

    For system (template-seeded) accounts the API only honours
    name / description / cash_flow_section / vat_rate / vat_treatment.
    """
    name: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[int] = None
    account_subtype: Optional[str] = None
    cash_flow_section: Optional[CashFlowSection] = None
    vat_treatment: Optional[VATTreatment] = None
    vat_rate: Optional[float] = None
    is_postable: Optional[bool] = None
    is_active: Optional[bool] = None


class AccountResponse(BaseModel):
    """Account row returned by the API."""
    id: int
    client_id: int
    code: str
    name: str
    parent_id: Optional[int]
    path: str
    level: int
    account_type: AccountType
    account_subtype: Optional[str]
    normal_balance: NormalBalance
    cash_flow_section: CashFlowSection
    is_vat_control: bool
    vat_treatment: Optional[VATTreatment]
    vat_rate: Optional[float]
    is_postable: bool
    is_active: bool
    is_system: bool
    description: Optional[str]

    class Config:
        orm_mode = True
        from_attributes = True


class AccountNode(AccountResponse):
    """Tree variant — same payload plus a `children` list of the same shape."""
    children: List["AccountNode"] = Field(default_factory=list)


if hasattr(AccountNode, "model_rebuild"):
    AccountNode.model_rebuild()
else:
    AccountNode.update_forward_refs()


class SeedTemplateRequest(BaseModel):
    """Body for POST /accounts/seed-template — idempotent re-seed."""
    client_id: int
    template_name: str = "sa_sme_v1"


# ==================== Session Schemas ====================

class SessionResponse(BaseModel):
    """Session response schema"""
    session_id: str
    locked: bool
    friendly_name: Optional[str]
    created_at: datetime
    
    class Config:
        orm_mode = True
        from_attributes = True
