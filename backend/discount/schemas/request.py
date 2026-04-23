from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, field_validator

from discount.models import DiscountTypeEnum


class ValidatePromoCodeRequest(BaseModel):
    code: str
    subtotal: float


class PatchCouponConfigRequest(BaseModel):
    is_active: bool | None = None
    discount_type: DiscountTypeEnum | None = None
    discount_value: float | None = None
    min_purchase: float | None = None
    params: dict | None = None


class CreateAutoCheckoutRequest(BaseModel):
    discount_type: DiscountTypeEnum
    discount_value: float
    min_purchase: float | None = None
    params: dict

    @field_validator("params")
    @classmethod
    def validate_params(cls, v: dict) -> dict:
        if "trigger_threshold" not in v:
            raise ValueError("auto_checkout params 必須包含 trigger_threshold")
        return v


class CreatePromoCodeRequest(BaseModel):
    code: str
    discount_type: DiscountTypeEnum
    discount_value: float
    min_purchase: float | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    max_total_uses: int | None = None
    max_per_user: int = 1


class UpdatePromoCodeRequest(BaseModel):
    code: str | None = None
    discount_type: DiscountTypeEnum | None = None
    discount_value: float | None = None
    min_purchase: float | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    max_total_uses: int | None = None
    max_per_user: int | None = None
    is_active: bool | None = None


class IssueCouponsRequest(BaseModel):
    user_ids: list[UUID]
    coupon_config_id: UUID

    @field_validator("user_ids")
    @classmethod
    def validate_user_ids(cls, v: list[UUID]) -> list[UUID]:
        if len(v) == 0:
            raise ValueError("user_ids 不可為空")
        if len(v) > 100:
            raise ValueError("一次最多發放 100 個用戶")
        return v
