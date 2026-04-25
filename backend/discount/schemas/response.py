from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from discount.models import CouponTypeEnum, DiscountTypeEnum


class UserCouponResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    coupon_type: CouponTypeEnum | None = None
    discount_type: DiscountTypeEnum
    discount_value: float
    min_purchase: float | None
    expires_at: datetime | None


class UserCouponsListResponse(BaseModel):
    available: list[UserCouponResponse]
    used: list[UserCouponResponse]
    expired: list[UserCouponResponse]


class ValidatePromoCodeResponse(BaseModel):
    valid: bool
    discount_type: DiscountTypeEnum
    discount_value: float


class CouponConfigResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    coupon_type: CouponTypeEnum
    discount_type: DiscountTypeEnum
    discount_value: float
    min_purchase: float | None
    is_active: bool
    params: dict
    updated_at: datetime


class CouponConfigListResponse(BaseModel):
    items: list[CouponConfigResponse]


class UsageByMonth(BaseModel):
    month: str
    issued: int
    used: int
    discount_amount: float


class CouponConfigUsageStatsResponse(BaseModel):
    total_issued: int
    total_used: int
    total_discount_amount: float
    usage_by_month: list[UsageByMonth]


class PromoCodeResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    code: str
    discount_type: DiscountTypeEnum
    discount_value: float
    min_purchase: float | None
    start_at: datetime | None
    end_at: datetime | None
    max_total_uses: int | None
    max_per_user: int
    total_used: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PromoCodeListResponse(BaseModel):
    items: list[PromoCodeResponse]


class AdminUserCouponResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    user_id: UUID
    coupon_type: CouponTypeEnum | None = None
    discount_type: DiscountTypeEnum
    discount_value: float
    min_purchase: float | None
    expires_at: datetime | None
    is_used: bool
    used_at: datetime | None
    created_at: datetime


class AdminUserCouponListResponse(BaseModel):
    items: list[AdminUserCouponResponse]


class IssueCouponsResponse(BaseModel):
    issued_count: int
    coupon_config_id: UUID
    coupon_type: str
    discount_type: str
    discount_value: float
    expires_at: datetime | None
    user_ids: list[UUID]


class DiscountCalculation(BaseModel):
    discount_amount: float
    discount_source: str | None
    user_coupon_id: UUID | None
    promo_code_id: UUID | None
    auto_checkout_config_id: UUID | None
