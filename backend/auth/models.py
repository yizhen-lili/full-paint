import uuid
from enum import StrEnum

from sqlalchemy import TIMESTAMP, Boolean, Column, Date, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID

from core.database import Base


class GenderEnum(StrEnum):
    female = "female"
    male = "male"
    other = "other"


class RoleEnum(StrEnum):
    admin = "admin"
    customer = "customer"


class TokenTypeEnum(StrEnum):
    signup = "signup"
    email_change = "email_change"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    # Google-only 用戶沒有 password_hash（透過 google_signin 建立）；
    # email + password 用戶仍照舊（service 在 register 寫入）。
    # login service 用 password_hash IS NULL 守衛，避免 _verify_password 拿 None 炸。
    password_hash = Column(String, nullable=True)
    # Google ID token 的 "sub" claim — 唯一識別一個 Google 帳號（即使 Google 換 email 也不變）。
    # 部分 UNIQUE 索引（ux_users_google_sub WHERE google_sub IS NOT NULL）— 避免多個 NULL 衝突。
    google_sub = Column(String, nullable=True, unique=True)
    gender = Column(Enum(GenderEnum), nullable=True)
    birthday = Column(Date, nullable=True)
    role = Column(Enum(RoleEnum), nullable=False, default=RoleEnum.customer)
    is_active = Column(Boolean, nullable=False, default=True)
    is_email_verified = Column(Boolean, nullable=False, default=False)
    pending_email = Column(String, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class EmailVerificationToken(Base):
    __tablename__ = "email_verification_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    token = Column(String, nullable=False)
    token_type = Column(Enum(TokenTypeEnum), nullable=False)
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)
    used_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    token = Column(String, nullable=False)
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)
    used_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
