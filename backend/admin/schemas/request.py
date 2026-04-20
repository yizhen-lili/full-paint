import re
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, field_validator


def _validate_password(v: str) -> str:
    if len(v) < 10:
        raise ValueError("密碼至少需要 10 個字元")
    if not re.search(r"[A-Za-z]", v):
        raise ValueError("密碼需包含英文字母")
    if not re.search(r"\d", v):
        raise ValueError("密碼需包含數字")
    return v


class AdminUpdateUserRequest(BaseModel):
    name: str | None = None
    role: Literal["admin", "customer"] | None = None
    is_active: bool | None = None
    password: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if v is not None and len(v) < 4:
            raise ValueError("名稱至少需要 4 個字元")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if v is not None:
            return _validate_password(v)
        return v


class IssueCouponsRequest(BaseModel):
    user_ids: list[UUID]
    coupon_config_id: UUID
