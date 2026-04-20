import re
from datetime import date
from typing import Literal

from pydantic import BaseModel, EmailStr, field_validator, model_validator


def _validate_password(v: str) -> str:
    if len(v) < 10:
        raise ValueError("密碼至少需要 10 個字元")
    if not re.search(r"[A-Za-z]", v):
        raise ValueError("密碼需包含英文字母")
    if not re.search(r"\d", v):
        raise ValueError("密碼需包含數字")
    return v


class UpdateProfileRequest(BaseModel):
    name: str | None = None
    gender: Literal["female", "male", "other"] | None = None
    birthday: date | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if v is not None and len(v) < 4:
            raise ValueError("名稱至少需要 4 個字元")
        return v


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        return _validate_password(v)


class RequestEmailChangeRequest(BaseModel):
    new_email: EmailStr


class ShippingProfileRequest(BaseModel):
    shipping_type: Literal["home", "seven_eleven", "family_mart"]
    recipient_name: str
    phone: str
    email: EmailStr | None = None
    city: str | None = None
    district: str | None = None
    address_detail: str | None = None
    store_id: str | None = None
    store_name: str | None = None
    is_default: bool = False

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        if not re.fullmatch(r"09\d{8}", v):
            raise ValueError("電話格式錯誤，需為台灣手機號碼（09xxxxxxxx）")
        return v

    @model_validator(mode="after")
    def validate_fields_by_type(self) -> "ShippingProfileRequest":
        if self.shipping_type == "home":
            missing = [f for f in ("city", "district", "address_detail") if not getattr(self, f)]
            if missing:
                raise ValueError(f"宅配到府必填：{', '.join(missing)}")
        else:
            missing = [f for f in ("store_id", "store_name") if not getattr(self, f)]
            if missing:
                raise ValueError(f"超商取件必填：{', '.join(missing)}")
        return self
