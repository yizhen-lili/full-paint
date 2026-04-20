import uuid
from enum import StrEnum

from sqlalchemy import TIMESTAMP, Boolean, Column, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID

from core.database import Base


class ShippingTypeEnum(StrEnum):
    home = "home"
    seven_eleven = "seven_eleven"
    family_mart = "family_mart"


class ShippingProfile(Base):
    __tablename__ = "shipping_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    shipping_type = Column(Enum(ShippingTypeEnum), nullable=False)
    recipient_name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    email = Column(String, nullable=True)
    city = Column(String, nullable=True)
    district = Column(String, nullable=True)
    address_detail = Column(String, nullable=True)
    store_id = Column(String, nullable=True)
    store_name = Column(String, nullable=True)
    is_default = Column(Boolean, nullable=False, default=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
