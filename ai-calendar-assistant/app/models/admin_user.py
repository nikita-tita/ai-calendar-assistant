"""Admin user models for authentication and authorization."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class AdminUser(BaseModel):
    """Admin user model."""
    
    id: Optional[int] = None
    username: str = Field(..., min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    password_hash: str  # bcrypt hash
    totp_secret: Optional[str] = None  # Base32 encoded secret for Google Authenticator
    totp_enabled: bool = False
    panic_password_hash: Optional[str] = None  # For fake mode (optional)
    role: str = "admin"  # admin, viewer, moderator, super_admin
    created_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    last_login_ip: Optional[str] = None
    is_active: bool = True
    
    class Config:
        from_attributes = True


class AdminUserCreate(BaseModel):
    """Model for creating a new admin user."""
    
    username: str = Field(..., min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    password: str = Field(..., min_length=8)
    panic_password: Optional[str] = None  # Optional panic password for fake mode
    role: str = "admin"


class AdminUserUpdate(BaseModel):
    """Model for updating admin user."""
    
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8)
    panic_password: Optional[str] = None
    totp_enabled: Optional[bool] = None
    is_active: Optional[bool] = None
    role: Optional[str] = None


class AdminLoginRequest(BaseModel):
    """Login request model."""
    
    username: str
    password: str
    totp_code: Optional[str] = Field(None, min_length=6, max_length=6)


class AdminLoginResponse(BaseModel):
    """Login response model."""
    
    success: bool
    mode: str  # "real", "fake", "invalid"
    message: Optional[str] = None
    totp_required: bool = False
    totp_qr_code: Optional[str] = None  # Base64 encoded QR code for first-time setup


class AdminTokenPayload(BaseModel):
    """JWT token payload."""
    
    user_id: int
    username: str
    role: str
    mode: str  # "real" or "fake"
    ip: str
    ua_hash: str
    exp: datetime
    iat: datetime


class AdminSessionInfo(BaseModel):
    """Session information."""
    
    user_id: int
    username: str
    email: Optional[str]
    role: str
    last_login_at: Optional[datetime]
    last_login_ip: Optional[str]
    totp_enabled: bool


class AdminAuditLogEntry(BaseModel):
    """Audit log entry."""
    
    id: Optional[int] = None
    admin_user_id: int
    username: str
    action_type: str  # login, logout, broadcast, hide_user, export, etc.
    timestamp: datetime
    details: Optional[str] = None  # JSON string with action details
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    success: bool = True
    
    class Config:
        from_attributes = True


class TOTPSetupResponse(BaseModel):
    """TOTP setup response with QR code."""
    
    secret: str  # Base32 encoded secret (to be stored)
    qr_code: str  # Base64 encoded QR code image
    manual_entry_key: str  # For manual entry in authenticator apps
    issuer: str = "AI Calendar Admin"

