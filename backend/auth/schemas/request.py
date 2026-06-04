import re

from pydantic import BaseModel, EmailStr, field_validator


def _validate_password(v: str) -> str:
    if len(v) < 10:
        raise ValueError("密碼至少需要 10 個字元")
    if not re.search(r"[A-Za-z]", v):
        raise ValueError("密碼需包含英文字母")
    if not re.search(r"\d", v):
        raise ValueError("密碼需包含數字")
    return v


class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if len(v) < 4:
            raise ValueError("名稱至少需要 4 個字元")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return _validate_password(v)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class VerifyEmailRequest(BaseModel):
    token: str


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        return _validate_password(v)


class GoogleSigninRequest(BaseModel):
    """Google Sign-in：前端 GIS popup 拿到的 ID token（JWT 字串，由 Google 簽）。"""
    id_token: str
