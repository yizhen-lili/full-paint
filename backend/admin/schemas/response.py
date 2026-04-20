from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AdminUserResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    name: str
    email: str
    role: str
    is_active: bool
    is_email_verified: bool
    created_at: datetime


class AdminUserListResponse(BaseModel):
    items: list[AdminUserResponse]
    total: int
    page: int
    page_size: int


class IssueCouponsResponse(BaseModel):
    issued_count: int
