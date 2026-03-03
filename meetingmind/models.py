"""
meetingmind/models.py — Pydantic request/response models
"""
from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List
from datetime import datetime

# ── Auth ──────────────────────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str
    team_code: Optional[str] = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

    @field_validator("role")
    @classmethod
    def role_valid(cls, v):
        if v not in ("manager", "member"):
            raise ValueError("Role must be manager or member")
        return v

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip()

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: str
    name: str
    user_id: int

class RefreshRequest(BaseModel):
    refresh_token: str

# ── User ──────────────────────────────────────────────────────────────────────
class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str
    team_id: Optional[int]
    team_name: Optional[str]

# ── Meetings ──────────────────────────────────────────────────────────────────
class ProcessNotesRequest(BaseModel):
    notes: str
    title: str

class ItemAssignRequest(BaseModel):
    item_id: int
    owner_id: Optional[int] = None
    owner_name: Optional[str] = None

class ItemResponse(BaseModel):
    id: int
    text: str
    priority: str
    owner_id: Optional[int]
    owner_name: Optional[str]
    status: str
    created_at: str

class MeetingResponse(BaseModel):
    id: int
    title: str
    created_at: str
    item_count: int
    high_count: int
    done_count: int

class UpdateStatusRequest(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def status_valid(cls, v):
        if v not in ("todo", "in-progress", "done"):
            raise ValueError("Invalid status")
        return v

# ── Team ──────────────────────────────────────────────────────────────────────
class TeamMemberResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str
    total_items: int
    open_items: int
    done_items: int
    completion_rate: int
    overloaded: bool
