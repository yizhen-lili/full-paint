from datetime import date

from pydantic import BaseModel


class LoginResponse(BaseModel):
    id: str
    name: str
    role: str


class MeResponse(BaseModel):
    id: str
    name: str
    email: str
    pending_email: str | None
    role: str
    gender: str | None
    birthday: date | None

    model_config = {"from_attributes": True}


class VerifyEmailResponse(BaseModel):
    token_type: str


class MessageResponse(BaseModel):
    message: str
