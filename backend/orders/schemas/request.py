from datetime import date, time
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, field_validator


class AddCartItemRequest(BaseModel):
    variant_id: UUID
    quantity: int = 1

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: int) -> int:
        if v < 1:
            raise ValueError("數量至少為 1")
        return v


class UpdateCartItemRequest(BaseModel):
    quantity: int

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: int) -> int:
        if v < 0:
            raise ValueError("數量不可為負數")
        return v


class CheckoutPreviewRequest(BaseModel):
    shipping_type: Literal["home", "seven_eleven", "family_mart"]
    user_coupon_id: UUID | None = None
    promo_code: str | None = None


class CreateOrderRequest(BaseModel):
    shipping_profile_id: UUID
    shipping_preference: Literal["together", "separate"] | None = None
    user_coupon_id: UUID | None = None
    promo_code: str | None = None
    customer_notes: str | None = None


class PaymentSubmissionRequest(BaseModel):
    transfer_amount: float
    transfer_date: date
    transfer_time: time
    account_last5: str
    notes: str | None = None

    @field_validator("account_last5")
    @classmethod
    def validate_account_last5(cls, v: str) -> str:
        if len(v) != 5 or not v.isdigit():
            raise ValueError("末五碼須為 5 位數字")
        return v


class AdminUpdateOrderStatusRequest(BaseModel):
    status: Literal[
        "paid", "processing", "shipped", "completed",
        "refund_processing", "cancelled"
    ]
    admin_notes: str | None = None


class FlagPaymentSubmissionRequest(BaseModel):
    is_flagged: Literal[True]
    admin_note: str | None = None


class CreateShipmentRequest(BaseModel):
    shipment_type: Literal["fulfilled", "preorder"]


class UpdateProductionProgressRequest(BaseModel):
    status: Literal["manufacturing", "packaging", "ready_to_ship"]
    notes: str | None = None


class RefundRequest(BaseModel):
    refund_amount: float
    returned_item_ids: list[UUID]
    cancel_reason: str | None = None

    @field_validator("refund_amount")
    @classmethod
    def validate_amount(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("退款金額須大於 0")
        return v


class CancelOrderRequest(BaseModel):
    cancel_reason: str | None = None


class AdminNotesRequest(BaseModel):
    admin_notes: str
