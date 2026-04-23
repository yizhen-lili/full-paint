import uuid
from enum import StrEnum

from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    CheckConstraint,
    Column,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from core.database import Base


class CouponTypeEnum(StrEnum):
    new_user = "new_user"
    spend_reward = "spend_reward"
    returning_loyal = "returning_loyal"
    manual = "manual"
    auto_checkout = "auto_checkout"


class DiscountTypeEnum(StrEnum):
    percentage = "percentage"
    fixed = "fixed"


class CouponConfig(Base):
    __tablename__ = "coupon_configs"
    __table_args__ = (
        Index(
            "ix_coupon_configs_coupon_type_unique",
            "coupon_type",
            unique=True,
            postgresql_where=text("coupon_type != 'auto_checkout'"),
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    coupon_type = Column(Enum(CouponTypeEnum), nullable=False)
    discount_type = Column(Enum(DiscountTypeEnum), nullable=False)
    discount_value = Column(Numeric(10, 2), nullable=False)
    min_purchase = Column(Numeric(10, 2), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    params = Column(JSONB, nullable=False, default=dict)
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class PromoCode(Base):
    __tablename__ = "promo_codes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String, nullable=False, unique=True)
    discount_type = Column(Enum(DiscountTypeEnum), nullable=False)
    discount_value = Column(Numeric(10, 2), nullable=False)
    min_purchase = Column(Numeric(10, 2), nullable=True)
    start_at = Column(TIMESTAMP(timezone=True), nullable=True)
    end_at = Column(TIMESTAMP(timezone=True), nullable=True)
    max_total_uses = Column(Integer, nullable=True)
    max_per_user = Column(Integer, nullable=False, default=1)
    total_used = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class UserCoupon(Base):
    __tablename__ = "user_coupons"
    __table_args__ = (
        CheckConstraint(
            "coupon_config_id IS NOT NULL OR promo_code_id IS NOT NULL",
            name="ck_user_coupons_config_or_promo",
        ),
        Index("ix_user_coupons_user_id_is_used", "user_id", "is_used"),
        Index("ix_user_coupons_source_order_id", "source_order_id"),
        Index("ix_user_coupons_used_in_order_id", "used_in_order_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    coupon_config_id = Column(
        UUID(as_uuid=True), ForeignKey("coupon_configs.id"), nullable=True
    )
    promo_code_id = Column(
        UUID(as_uuid=True), ForeignKey("promo_codes.id"), nullable=True
    )
    discount_type = Column(Enum(DiscountTypeEnum), nullable=False)
    discount_value = Column(Numeric(10, 2), nullable=False)
    min_purchase = Column(Numeric(10, 2), nullable=True)
    expires_at = Column(TIMESTAMP(timezone=True), nullable=True)
    is_used = Column(Boolean, nullable=False, default=False)
    used_at = Column(TIMESTAMP(timezone=True), nullable=True)
    # FK to orders.id added in orders module migration (orders table not yet created)
    used_in_order_id = Column(UUID(as_uuid=True), nullable=True)
    source_order_id = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
