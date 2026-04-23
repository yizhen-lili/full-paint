from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from dependencies.auth import require_admin, require_auth
from discount import service
from discount.schemas.request import (
    CreateAutoCheckoutRequest,
    CreatePromoCodeRequest,
    IssueCouponsRequest,
    PatchCouponConfigRequest,
    UpdatePromoCodeRequest,
    ValidatePromoCodeRequest,
)
from discount.schemas.response import (
    AdminUserCouponListResponse,
    CouponConfigListResponse,
    CouponConfigResponse,
    CouponConfigUsageStatsResponse,
    IssueCouponsResponse,
    PromoCodeListResponse,
    PromoCodeResponse,
    UserCouponsListResponse,
    ValidatePromoCodeResponse,
)

router = APIRouter(tags=["Discount"])


# ── Customer ──────────────────────────────────────────────────────────────────

@router.get("/users/me/coupons", response_model=UserCouponsListResponse)
async def list_my_coupons(
    current_user=Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    return await service.list_user_coupons(db, current_user.id)


@router.post("/promo-codes/validate", response_model=ValidatePromoCodeResponse)
async def validate_promo_code(
    body: ValidatePromoCodeRequest,
    current_user=Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    return await service.validate_promo_code(db, current_user.id, body.code, body.subtotal)


# ── Admin: coupon-configs ─────────────────────────────────────────────────────

@router.get("/admin/coupon-configs", response_model=CouponConfigListResponse)
async def list_coupon_configs(
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    items = await service.list_coupon_configs(db)
    return {"items": items}


@router.get(
    "/admin/coupon-configs/{config_id}/usage-stats",
    response_model=CouponConfigUsageStatsResponse,
)
async def get_coupon_config_usage_stats(
    config_id: UUID,
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await service.get_coupon_config_usage_stats(db, config_id)


@router.patch("/admin/coupon-configs/{config_id}", response_model=CouponConfigResponse)
async def patch_coupon_config(
    config_id: UUID,
    body: PatchCouponConfigRequest,
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    data = body.model_dump(exclude_none=True)
    return await service.patch_coupon_config(db, config_id, data)


@router.post(
    "/admin/coupon-configs/auto-checkout",
    response_model=CouponConfigResponse,
    status_code=201,
)
async def create_auto_checkout(
    body: CreateAutoCheckoutRequest,
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    data = body.model_dump()
    return await service.create_auto_checkout(db, data)


@router.delete(
    "/admin/coupon-configs/{config_id}", response_model=None, status_code=204
)
async def delete_auto_checkout(
    config_id: UUID,
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    await service.delete_auto_checkout(db, config_id)


# ── Admin: promo-codes ────────────────────────────────────────────────────────

@router.get("/admin/promo-codes", response_model=PromoCodeListResponse)
async def list_promo_codes(
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    items = await service.list_promo_codes(db)
    return {"items": items}


@router.post("/admin/promo-codes", response_model=PromoCodeResponse, status_code=201)
async def create_promo_code(
    body: CreatePromoCodeRequest,
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await service.create_promo_code(db, body.model_dump())


@router.put("/admin/promo-codes/{promo_id}", response_model=PromoCodeResponse)
async def update_promo_code(
    promo_id: UUID,
    body: UpdatePromoCodeRequest,
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    return await service.update_promo_code(db, promo_id, data)


@router.delete("/admin/promo-codes/{promo_id}", response_model=None, status_code=204)
async def delete_promo_code(
    promo_id: UUID,
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    await service.delete_promo_code(db, promo_id)


# ── Admin: user-coupons ───────────────────────────────────────────────────────

@router.get("/admin/user-coupons", response_model=AdminUserCouponListResponse)
async def list_admin_user_coupons(
    user_id: UUID | None = Query(None),
    coupon_type: str | None = Query(None),
    is_used: bool | None = Query(None),
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    items = await service.list_admin_user_coupons(db, user_id, coupon_type, is_used)
    return {"items": items}


@router.post("/admin/users/issue-coupons", response_model=IssueCouponsResponse)
async def issue_coupons(
    body: IssueCouponsRequest,
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    issued = await service.issue_manual_coupons(db, body.user_ids, body.coupon_config_id)
    return {"issued": issued}
