from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import BadRequestError, ConflictError, NotFoundError
from discount.models import (
    CouponConfig,
    CouponTypeEnum,
    DiscountTypeEnum,
    PromoCode,
    UserCoupon,
)


def _compute_discount_amount(discount_type: str, discount_value: Decimal, subtotal: float) -> float:
    if discount_type == DiscountTypeEnum.fixed:
        return min(float(discount_value), subtotal)
    return round(subtotal * float(discount_value) / 100, 2)



# ── 供其他模組呼叫的 service 函式 ───────────────────────────────────────────────

async def issue_new_user_coupon(db: AsyncSession, user_id: UUID) -> None:
    """E02: Email 驗證完成後自動發放 new_user 歡迎券。"""
    result = await db.execute(
        select(CouponConfig).where(
            CouponConfig.coupon_type == CouponTypeEnum.new_user,
            CouponConfig.is_active == True,  # noqa: E712
        )
    )
    config = result.scalar_one_or_none()
    if config is None:
        return

    valid_days = config.params.get("valid_days", 30)
    expires_at = datetime.now(UTC) + timedelta(days=valid_days)

    coupon = UserCoupon(
        user_id=user_id,
        coupon_config_id=config.id,
        discount_type=config.discount_type,
        discount_value=config.discount_value,
        min_purchase=config.min_purchase,
        expires_at=expires_at,
    )
    db.add(coupon)


async def issue_reward_coupon(
    db: AsyncSession, user_id: UUID, order_id: UUID, order_total: float
) -> None:
    """E40: 訂單完成時依優先序發放回饋券（returning_loyal > spend_reward）。"""
    # 直接查 orders 表（orders 模組建立後此處可改用 ORM）
    has_prior = await db.execute(
        text(
            "SELECT COUNT(*) FROM orders "
            "WHERE user_id = :uid AND status = 'completed' AND id != :oid"
        ),
        {"uid": str(user_id), "oid": str(order_id)},
    )
    has_prior_orders = (has_prior.scalar() or 0) > 0

    returning_result = await db.execute(
        select(CouponConfig).where(
            CouponConfig.coupon_type == CouponTypeEnum.returning_loyal,
            CouponConfig.is_active == True,  # noqa: E712
        )
    )
    returning_config = returning_result.scalar_one_or_none()

    spend_result = await db.execute(
        select(CouponConfig).where(
            CouponConfig.coupon_type == CouponTypeEnum.spend_reward,
            CouponConfig.is_active == True,  # noqa: E712
        )
    )
    spend_config = spend_result.scalar_one_or_none()

    chosen_config = None
    if (
        has_prior_orders
        and returning_config
        and order_total >= returning_config.params.get("trigger_threshold", 0)
    ):
        chosen_config = returning_config
    elif spend_config and order_total >= spend_config.params.get("trigger_threshold", 0):
        chosen_config = spend_config

    if chosen_config is None:
        return

    valid_days = chosen_config.params.get("valid_days", 30)
    expires_at = datetime.now(UTC) + timedelta(days=valid_days)

    coupon = UserCoupon(
        user_id=user_id,
        coupon_config_id=chosen_config.id,
        discount_type=chosen_config.discount_type,
        discount_value=chosen_config.discount_value,
        min_purchase=chosen_config.min_purchase,
        expires_at=expires_at,
        source_order_id=order_id,
    )
    db.add(coupon)


async def calculate_discount(
    db: AsyncSession,
    user_id: UUID,
    subtotal: float,
    user_coupon_id: UUID | None = None,
    promo_code: str | None = None,
) -> dict:
    """計算折扣（不實際扣減），供 checkout preview 使用。"""
    if promo_code:
        result = await db.execute(
            select(PromoCode).where(PromoCode.code == promo_code)
        )
        pc = result.scalar_one_or_none()
        if pc is None or not pc.is_active:
            raise BadRequestError("促銷碼無效")
        now = datetime.now(UTC)
        if pc.start_at and pc.start_at > now:
            raise BadRequestError("促銷碼尚未開始")
        if pc.end_at and pc.end_at < now:
            raise BadRequestError("促銷碼已過期")
        if pc.max_total_uses is not None and pc.total_used >= pc.max_total_uses:
            raise BadRequestError("促銷碼已達使用上限")
        per_user_count = await db.execute(
            select(func.count()).where(
                UserCoupon.user_id == user_id,
                UserCoupon.promo_code_id == pc.id,
            )
        )
        if (per_user_count.scalar() or 0) >= pc.max_per_user:
            raise BadRequestError("超過每人使用上限")
        if pc.min_purchase is not None and subtotal < float(pc.min_purchase):
            raise BadRequestError("未達最低消費門檻")
        amount = _compute_discount_amount(pc.discount_type, pc.discount_value, subtotal)
        return {
            "discount_amount": amount,
            "discount_source": "coupon",
            "user_coupon_id": None,
            "promo_code_id": pc.id,
            "auto_checkout_config_id": None,
        }

    if user_coupon_id:
        result = await db.execute(
            select(UserCoupon).where(
                UserCoupon.id == user_coupon_id,
                UserCoupon.user_id == user_id,
            )
        )
        uc = result.scalar_one_or_none()
        if uc is None:
            raise NotFoundError("折扣券不存在")
        if uc.is_used:
            raise BadRequestError("折扣券已使用")
        now = datetime.now(UTC)
        if uc.expires_at and uc.expires_at < now:
            raise BadRequestError("折扣券已過期")
        if uc.min_purchase is not None and subtotal < float(uc.min_purchase):
            raise BadRequestError("未達最低消費門檻")
        amount = _compute_discount_amount(uc.discount_type, uc.discount_value, subtotal)
        return {
            "discount_amount": amount,
            "discount_source": "coupon",
            "user_coupon_id": uc.id,
            "promo_code_id": None,
            "auto_checkout_config_id": None,
        }

    # auto_checkout
    now = datetime.now(UTC)
    result = await db.execute(
        select(CouponConfig).where(
            CouponConfig.coupon_type == CouponTypeEnum.auto_checkout,
            CouponConfig.is_active == True,  # noqa: E712
        )
    )
    auto_configs = result.scalars().all()

    best = None
    best_amount = 0.0
    for cfg in auto_configs:
        threshold = cfg.params.get("trigger_threshold", 0)
        if subtotal < threshold:
            continue
        start = cfg.params.get("start_at")
        end = cfg.params.get("end_at")
        if start and datetime.fromisoformat(start).replace(tzinfo=UTC) > now:
            continue
        if end and datetime.fromisoformat(end).replace(tzinfo=UTC) < now:
            continue
        amount = _compute_discount_amount(cfg.discount_type, cfg.discount_value, subtotal)
        if amount > best_amount:
            best_amount = amount
            best = cfg

    if best is None:
        return {
            "discount_amount": 0.0,
            "discount_source": None,
            "user_coupon_id": None,
            "promo_code_id": None,
            "auto_checkout_config_id": None,
        }

    return {
        "discount_amount": best_amount,
        "discount_source": "auto_checkout",
        "user_coupon_id": None,
        "promo_code_id": None,
        "auto_checkout_config_id": best.id,
    }


async def apply_discount(
    db: AsyncSession,
    order_id: UUID,
    user_id: UUID,
    subtotal: float,
    user_coupon_id: UUID | None = None,
    promo_code: str | None = None,
) -> dict:
    """E44/E19: 下單時實際套用折扣（在同一 transaction 內執行）。"""
    calc = await calculate_discount(db, user_id, subtotal, user_coupon_id, promo_code)

    if calc["promo_code_id"]:
        # 原子遞增 total_used
        updated = await db.execute(
            update(PromoCode)
            .where(
                PromoCode.id == calc["promo_code_id"],
                (PromoCode.max_total_uses == None)  # noqa: E711
                | (PromoCode.total_used < PromoCode.max_total_uses),
            )
            .values(total_used=PromoCode.total_used + 1)
            .returning(PromoCode.id)
        )
        if updated.scalar_one_or_none() is None:
            raise BadRequestError("促銷碼已達使用上限")

        result = await db.execute(
            select(PromoCode).where(PromoCode.id == calc["promo_code_id"])
        )
        pc = result.scalar_one()
        uc = UserCoupon(
            user_id=user_id,
            promo_code_id=pc.id,
            discount_type=pc.discount_type,
            discount_value=pc.discount_value,
            min_purchase=pc.min_purchase,
            is_used=True,
            used_at=datetime.now(UTC),
            used_in_order_id=order_id,
        )
        db.add(uc)
        calc["user_coupon_id"] = None  # public_code 不記錄在 user_coupon_id

    elif calc["user_coupon_id"]:
        updated = await db.execute(
            update(UserCoupon)
            .where(
                UserCoupon.id == calc["user_coupon_id"],
                UserCoupon.is_used == False,  # noqa: E712
            )
            .values(is_used=True, used_at=datetime.now(UTC), used_in_order_id=order_id)
            .returning(UserCoupon.id)
        )
        if updated.scalar_one_or_none() is None:
            raise BadRequestError("折扣券已使用")

    return calc


async def revert_coupon(db: AsyncSession, order_id: UUID) -> None:
    """E23/E24/E25: 取消/逾期時回補折扣券。"""
    result = await db.execute(
        select(UserCoupon).where(UserCoupon.used_in_order_id == order_id)
    )
    coupons = result.scalars().all()

    for uc in coupons:
        if uc.promo_code_id:
            await db.execute(
                update(PromoCode)
                .where(PromoCode.id == uc.promo_code_id, PromoCode.total_used > 0)
                .values(total_used=PromoCode.total_used - 1)
            )
        uc.is_used = False
        uc.used_at = None
        uc.used_in_order_id = None


async def revoke_reward_coupons(
    db: AsyncSession,
    order_id: UUID,
    refund_amount: float | None = None,
    order_total: float | None = None,
) -> None:
    """E42: 退款時撤銷因此訂單觸發的回饋券（未使用者立即作廢）。"""
    result = await db.execute(
        select(UserCoupon).where(
            UserCoupon.source_order_id == order_id,
            UserCoupon.is_used == False,  # noqa: E712
        )
    )
    reward_coupons = result.scalars().all()

    if not reward_coupons:
        return

    is_full_refund = refund_amount is None or (
        order_total is not None and refund_amount >= order_total
    )

    for uc in reward_coupons:
        if is_full_refund:
            uc.expires_at = datetime.now(UTC)
            continue

        # 部分退款：依剩餘金額判斷
        remaining = (order_total or 0) - (refund_amount or 0)
        config_result = await db.execute(
            select(CouponConfig).where(CouponConfig.id == uc.coupon_config_id)
        )
        config = config_result.scalar_one_or_none()
        threshold = config.params.get("trigger_threshold", 0) if config else 0
        if remaining < threshold:
            uc.expires_at = datetime.now(UTC)


# ── Admin / Customer endpoint service 函式 ─────────────────────────────────────

async def list_user_coupons(db: AsyncSession, user_id: UUID) -> dict:
    result = await db.execute(
        select(UserCoupon, CouponConfig.coupon_type.label("ct"))
        .outerjoin(CouponConfig, UserCoupon.coupon_config_id == CouponConfig.id)
        .where(UserCoupon.user_id == user_id)
    )
    rows = result.all()

    now = datetime.now(UTC)
    available, used, expired = [], [], []

    for uc, coupon_type in rows:
        item = {
            "id": uc.id,
            "coupon_type": coupon_type,
            "discount_type": uc.discount_type,
            "discount_value": float(uc.discount_value),
            "min_purchase": float(uc.min_purchase) if uc.min_purchase else None,
            "expires_at": uc.expires_at,
        }
        if uc.is_used:
            used.append(item)
        elif uc.expires_at and uc.expires_at < now:
            expired.append(item)
        else:
            available.append(item)

    return {"available": available, "used": used, "expired": expired}


async def validate_promo_code(db: AsyncSession, user_id: UUID, code: str, subtotal: float) -> dict:
    result = await db.execute(select(PromoCode).where(PromoCode.code == code))
    pc = result.scalar_one_or_none()
    if pc is None or not pc.is_active:
        raise BadRequestError("促銷碼無效")
    now = datetime.now(UTC)
    if pc.start_at and pc.start_at > now:
        raise BadRequestError("促銷碼尚未開始")
    if pc.end_at and pc.end_at < now:
        raise BadRequestError("促銷碼已過期")
    if pc.max_total_uses is not None and pc.total_used >= pc.max_total_uses:
        raise BadRequestError("促銷碼已達使用上限")
    per_user = await db.execute(
        select(func.count()).where(
            UserCoupon.user_id == user_id,
            UserCoupon.promo_code_id == pc.id,
        )
    )
    if (per_user.scalar() or 0) >= pc.max_per_user:
        raise BadRequestError("超過每人使用上限")
    if pc.min_purchase is not None and subtotal < float(pc.min_purchase):
        raise BadRequestError("未達最低消費門檻")
    return {
        "valid": True,
        "discount_type": pc.discount_type,
        "discount_value": float(pc.discount_value),
    }


async def list_coupon_configs(db: AsyncSession) -> list:
    result = await db.execute(select(CouponConfig).order_by(CouponConfig.coupon_type))
    return result.scalars().all()


async def get_coupon_config_usage_stats(db: AsyncSession, config_id: UUID) -> dict:
    result = await db.execute(select(CouponConfig).where(CouponConfig.id == config_id))
    if result.scalar_one_or_none() is None:
        raise NotFoundError("coupon config 不存在")

    total_issued = await db.execute(
        select(func.count()).where(UserCoupon.coupon_config_id == config_id)
    )
    total_used = await db.execute(
        select(func.count()).where(
            UserCoupon.coupon_config_id == config_id,
            UserCoupon.is_used == True,  # noqa: E712
        )
    )
    total_discount = await db.execute(
        select(func.coalesce(func.sum(UserCoupon.discount_value), 0)).where(
            UserCoupon.coupon_config_id == config_id,
            UserCoupon.is_used == True,  # noqa: E712
        )
    )

    month_result = await db.execute(
        text(
            """
            SELECT TO_CHAR(created_at, 'YYYY-MM') AS month,
                   COUNT(*) AS issued,
                   SUM(CASE WHEN is_used THEN 1 ELSE 0 END) AS used,
                   SUM(CASE WHEN is_used THEN discount_value ELSE 0 END) AS discount_amount
            FROM user_coupons
            WHERE coupon_config_id = :config_id
            GROUP BY month
            ORDER BY month
            """
        ),
        {"config_id": str(config_id)},
    )

    return {
        "total_issued": total_issued.scalar() or 0,
        "total_used": total_used.scalar() or 0,
        "total_discount_amount": float(total_discount.scalar() or 0),
        "usage_by_month": [
            {
                "month": row.month,
                "issued": row.issued,
                "used": row.used,
                "discount_amount": float(row.discount_amount or 0),
            }
            for row in month_result
        ],
    }


async def patch_coupon_config(db: AsyncSession, config_id: UUID, data: dict) -> CouponConfig:
    result = await db.execute(select(CouponConfig).where(CouponConfig.id == config_id))
    config = result.scalar_one_or_none()
    if config is None:
        raise NotFoundError("coupon config 不存在")
    if config.coupon_type == CouponTypeEnum.auto_checkout:
        raise BadRequestError("auto_checkout 類型請刪除後重建")
    for key, value in data.items():
        if value is not None:
            setattr(config, key, value)
    config.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(config)
    return config


async def create_auto_checkout(db: AsyncSession, data: dict) -> CouponConfig:
    config = CouponConfig(
        coupon_type=CouponTypeEnum.auto_checkout,
        **data,
    )
    db.add(config)
    await db.commit()
    await db.refresh(config)
    return config


async def delete_auto_checkout(db: AsyncSession, config_id: UUID) -> None:
    result = await db.execute(select(CouponConfig).where(CouponConfig.id == config_id))
    config = result.scalar_one_or_none()
    if config is None:
        raise NotFoundError("coupon config 不存在")
    if config.coupon_type != CouponTypeEnum.auto_checkout:
        raise BadRequestError("僅允許刪除 auto_checkout 類型")
    await db.delete(config)
    await db.commit()


async def list_promo_codes(db: AsyncSession) -> list:
    result = await db.execute(
        select(PromoCode).order_by(PromoCode.created_at.desc())
    )
    return result.scalars().all()


async def create_promo_code(db: AsyncSession, data: dict) -> PromoCode:
    existing = await db.execute(select(PromoCode).where(PromoCode.code == data["code"]))
    if existing.scalar_one_or_none():
        raise ConflictError("促銷碼已存在")
    pc = PromoCode(**data)
    db.add(pc)
    await db.commit()
    await db.refresh(pc)
    return pc


async def update_promo_code(db: AsyncSession, promo_id: UUID, data: dict) -> PromoCode:
    result = await db.execute(select(PromoCode).where(PromoCode.id == promo_id))
    pc = result.scalar_one_or_none()
    if pc is None:
        raise NotFoundError("促銷碼不存在")
    if "code" in data and data["code"] != pc.code:
        existing = await db.execute(
            select(PromoCode).where(PromoCode.code == data["code"])
        )
        if existing.scalar_one_or_none():
            raise ConflictError("促銷碼已存在")
    for key, value in data.items():
        if value is not None:
            setattr(pc, key, value)
    await db.commit()
    await db.refresh(pc)
    return pc


async def delete_promo_code(db: AsyncSession, promo_id: UUID) -> None:
    result = await db.execute(select(PromoCode).where(PromoCode.id == promo_id))
    pc = result.scalar_one_or_none()
    if pc is None:
        raise NotFoundError("促銷碼不存在")
    if pc.total_used > 0:
        raise BadRequestError("促銷碼已有使用記錄，無法刪除")
    await db.delete(pc)
    await db.commit()


async def list_admin_user_coupons(
    db: AsyncSession,
    user_id: UUID | None = None,
    coupon_type: str | None = None,
    is_used: bool | None = None,
) -> list:
    query = (
        select(UserCoupon, CouponConfig.coupon_type.label("ct"))
        .outerjoin(CouponConfig, UserCoupon.coupon_config_id == CouponConfig.id)
    )
    if user_id:
        query = query.where(UserCoupon.user_id == user_id)
    if is_used is not None:
        query = query.where(UserCoupon.is_used == is_used)
    if coupon_type:
        query = query.where(CouponConfig.coupon_type == coupon_type)

    result = await db.execute(query.order_by(UserCoupon.created_at.desc()))
    rows = result.all()

    return [
        {
            "id": uc.id,
            "user_id": uc.user_id,
            "coupon_type": ct,
            "discount_type": uc.discount_type,
            "discount_value": float(uc.discount_value),
            "min_purchase": float(uc.min_purchase) if uc.min_purchase else None,
            "expires_at": uc.expires_at,
            "is_used": uc.is_used,
            "used_at": uc.used_at,
            "created_at": uc.created_at,
        }
        for uc, ct in rows
    ]


async def issue_manual_coupons(
    db: AsyncSession, user_ids: list[UUID], config_id: UUID
) -> int:
    result = await db.execute(select(CouponConfig).where(CouponConfig.id == config_id))
    config = result.scalar_one_or_none()
    if config is None:
        raise NotFoundError("coupon config 不存在")
    if config.coupon_type != CouponTypeEnum.manual:
        raise BadRequestError("僅允許發放 manual 類型券")

    expires_at_raw = config.params.get("expires_at")
    if expires_at_raw:
        dt = datetime.fromisoformat(expires_at_raw)
        expires_at = dt if dt.tzinfo else dt.replace(tzinfo=UTC)
    else:
        expires_at = None

    for uid in user_ids:
        coupon = UserCoupon(
            user_id=uid,
            coupon_config_id=config.id,
            discount_type=config.discount_type,
            discount_value=config.discount_value,
            min_purchase=config.min_purchase,
            expires_at=expires_at,
        )
        db.add(coupon)

    await db.commit()
    return len(user_ids)
