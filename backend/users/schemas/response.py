from datetime import date
from uuid import UUID

from pydantic import BaseModel


class UserProfileResponse(BaseModel):
    id: UUID
    name: str
    email: str
    pending_email: str | None
    role: str
    gender: str | None
    birthday: date | None

    model_config = {"from_attributes": True}


class ShippingProfileResponse(BaseModel):
    id: UUID
    shipping_type: str
    recipient_name: str
    phone: str
    email: str | None
    city: str | None
    district: str | None
    address_detail: str | None
    store_id: str | None
    store_name: str | None
    is_default: bool

    model_config = {"from_attributes": True}
