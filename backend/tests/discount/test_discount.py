from datetime import UTC, datetime, timedelta
from uuid import uuid4

import bcrypt
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from auth.models import User
from discount.models import CouponConfig, CouponTypeEnum, DiscountTypeEnum, PromoCode, UserCoupon
from discount.service import (
    apply_discount,
    calculate_discount,
    issue_new_user_coupon,
    revert_coupon,
    revoke_reward_coupons,
)

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
COUPONS_URL = "/api/v1/users/me/coupons"
VALIDATE_URL = "/api/v1/promo-codes/validate"
CONFIGS_URL = "/api/v1/admin/coupon-configs"
AUTO_CHECKOUT_URL = "/api/v1/admin/coupon-configs/auto-checkout"
PROMO_URL = "/api/v1/admin/promo-codes"
USER_COUPONS_URL = "/api/v1/admin/user-coupons"
ISSUE_URL = "/api/v1/admin/users/issue-coupons"

CUSTOMER = {"name": "折扣測試用戶", "email": "discount@example.com", "password": "testpass123"}
ADMIN_EMAIL = "discountadmin@test.com"
ADMIN_PASS = "adminpass123"


async def _make_customer(client, db, email=None, password=None):
    payload = {**CUSTOMER}
    if email:
        payload["email"] = email
    if password:
        payload["password"] = password
    await client.post(REGISTER_URL, json=payload)
    result = await db.execute(select(User).where(User.email == payload["email"]))
    user = result.scalar_one()
    user.is_email_verified = True
    await db.commit()
    return user


async def _make_admin(db):
    admin = User(
        name="DiscountAdmin",
        email=ADMIN_EMAIL,
        password_hash=bcrypt.hashpw(ADMIN_PASS.encode(), bcrypt.gensalt()).decode(),
        role="admin",
        is_active=True,
        is_email_verified=True,
    )
    db.add(admin)
    await db.commit()
    return admin


async def _login_customer(client, email=None, password=None):
    res = await client.post(LOGIN_URL, json={
        "email": email or CUSTOMER["email"],
        "password": password or CUSTOMER["password"],
    })
    if "access_token" in res.cookies:
        client.cookies.set("access_token", res.cookies["access_token"])
    return res


async def _login_admin(client):
    res = await client.post("/api/v1/admin/auth/login", json={
        "email": ADMIN_EMAIL, "password": ADMIN_PASS
    })
    if "access_token" in res.cookies:
        client.cookies.set("access_token", res.cookies["access_token"])
    return res


async def _make_new_user_config(db, discount_value=10.0, valid_days=30):
    config = CouponConfig(
        coupon_type=CouponTypeEnum.new_user,
        discount_type=DiscountTypeEnum.percentage,
        discount_value=discount_value,
        min_purchase=None,
        is_active=True,
        params={"valid_days": valid_days},
    )
    db.add(config)
    await db.commit()
    await db.refresh(config)
    return config


async def _make_manual_config(db, discount_value=100.0):
    config = CouponConfig(
        coupon_type=CouponTypeEnum.manual,
        discount_type=DiscountTypeEnum.fixed,
        discount_value=discount_value,
        min_purchase=None,
        is_active=True,
        params={},
    )
    db.add(config)
    await db.commit()
    await db.refresh(config)
    return config


async def _make_promo_code(db, code="TEST100", discount_value=100.0, max_total_uses=10,
                            max_per_user=1, min_purchase=None, is_active=True,
                            start_at=None, end_at=None):
    pc = PromoCode(
        code=code,
        discount_type=DiscountTypeEnum.fixed,
        discount_value=discount_value,
        min_purchase=min_purchase,
        max_total_uses=max_total_uses,
        max_per_user=max_per_user,
        is_active=is_active,
        start_at=start_at,
        end_at=end_at,
    )
    db.add(pc)
    await db.commit()
    await db.refresh(pc)
    return pc


# ── GET /users/me/coupons ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_coupons_empty(client: AsyncClient, db):
    await _make_customer(client, db)
    await _login_customer(client)
    res = await client.get(COUPONS_URL)
    assert res.status_code == 200
    data = res.json()
    assert data["available"] == []
    assert data["used"] == []
    assert data["expired"] == []


@pytest.mark.asyncio
async def test_list_coupons_categorized(client: AsyncClient, db):
    user = await _make_customer(client, db)
    config = await _make_new_user_config(db)

    now = datetime.now(UTC)
    available_coupon = UserCoupon(
        user_id=user.id, coupon_config_id=config.id,
        discount_type=DiscountTypeEnum.percentage, discount_value=10,
        expires_at=now + timedelta(days=30),
    )
    used_coupon = UserCoupon(
        user_id=user.id, coupon_config_id=config.id,
        discount_type=DiscountTypeEnum.percentage, discount_value=10,
        is_used=True, used_at=now,
    )
    expired_coupon = UserCoupon(
        user_id=user.id, coupon_config_id=config.id,
        discount_type=DiscountTypeEnum.percentage, discount_value=10,
        expires_at=now - timedelta(days=1),
    )
    db.add_all([available_coupon, used_coupon, expired_coupon])
    await db.commit()

    await _login_customer(client)
    res = await client.get(COUPONS_URL)
    assert res.status_code == 200
    data = res.json()
    assert len(data["available"]) == 1
    assert len(data["used"]) == 1
    assert len(data["expired"]) == 1


@pytest.mark.asyncio
async def test_list_coupons_unauthenticated(client: AsyncClient, db):
    res = await client.get(COUPONS_URL)
    assert res.status_code == 401


# ── POST /promo-codes/validate ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_validate_promo_code_success(client: AsyncClient, db):
    await _make_customer(client, db)
    await _make_promo_code(db, min_purchase=500)
    await _login_customer(client)
    res = await client.post(VALIDATE_URL, json={"code": "TEST100", "subtotal": 800})
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is True
    assert data["discount_value"] == 100.0


@pytest.mark.asyncio
async def test_validate_promo_code_not_found(client: AsyncClient, db):
    await _make_customer(client, db)
    await _login_customer(client)
    res = await client.post(VALIDATE_URL, json={"code": "NOTEXIST", "subtotal": 800})
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_validate_promo_code_inactive(client: AsyncClient, db):
    await _make_customer(client, db)
    await _make_promo_code(db, is_active=False)
    await _login_customer(client)
    res = await client.post(VALIDATE_URL, json={"code": "TEST100", "subtotal": 800})
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_validate_promo_code_usage_limit(client: AsyncClient, db):
    await _make_customer(client, db)
    pc = await _make_promo_code(db, max_total_uses=5)
    pc.total_used = 5
    await db.commit()
    await _login_customer(client)
    res = await client.post(VALIDATE_URL, json={"code": "TEST100", "subtotal": 800})
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_validate_promo_code_per_user_limit(client: AsyncClient, db):
    user = await _make_customer(client, db)
    pc = await _make_promo_code(db, max_per_user=1)
    existing = UserCoupon(
        user_id=user.id, promo_code_id=pc.id,
        discount_type=DiscountTypeEnum.fixed, discount_value=100,
        is_used=True,
    )
    db.add(existing)
    await db.commit()
    await _login_customer(client)
    res = await client.post(VALIDATE_URL, json={"code": "TEST100", "subtotal": 800})
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_validate_promo_code_below_min_purchase(client: AsyncClient, db):
    await _make_customer(client, db)
    await _make_promo_code(db, min_purchase=500)
    await _login_customer(client)
    res = await client.post(VALIDATE_URL, json={"code": "TEST100", "subtotal": 300})
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_validate_promo_code_expired(client: AsyncClient, db):
    await _make_customer(client, db)
    end = datetime.now(UTC) - timedelta(days=1)
    await _make_promo_code(db, end_at=end)
    await _login_customer(client)
    res = await client.post(VALIDATE_URL, json={"code": "TEST100", "subtotal": 800})
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_validate_promo_code_unauthenticated(client: AsyncClient, db):
    res = await client.post(VALIDATE_URL, json={"code": "TEST100", "subtotal": 800})
    assert res.status_code == 401


# ── GET /admin/coupon-configs ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_coupon_configs(client: AsyncClient, db):
    await _make_admin(db)
    await _login_admin(client)
    await _make_new_user_config(db)
    res = await client.get(CONFIGS_URL)
    assert res.status_code == 200
    assert len(res.json()["items"]) >= 1


# ── GET /admin/coupon-configs/{id}/usage-stats ────────────────────────────────

@pytest.mark.asyncio
async def test_coupon_config_usage_stats_empty(client: AsyncClient, db):
    await _make_admin(db)
    await _login_admin(client)
    config = await _make_new_user_config(db)
    res = await client.get(f"{CONFIGS_URL}/{config.id}/usage-stats")
    assert res.status_code == 200
    data = res.json()
    assert data["total_issued"] == 0
    assert data["total_used"] == 0


@pytest.mark.asyncio
async def test_coupon_config_usage_stats(client: AsyncClient, db):
    user = await _make_customer(client, db)
    await _make_admin(db)
    config = await _make_new_user_config(db)
    uc = UserCoupon(
        user_id=user.id, coupon_config_id=config.id,
        discount_type=DiscountTypeEnum.percentage, discount_value=10,
        is_used=True,
    )
    db.add(uc)
    await db.commit()
    await _login_admin(client)
    res = await client.get(f"{CONFIGS_URL}/{config.id}/usage-stats")
    assert res.status_code == 200
    assert res.json()["total_issued"] == 1
    assert res.json()["total_used"] == 1


# ── PATCH /admin/coupon-configs/{id} ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_patch_coupon_config_success(client: AsyncClient, db):
    await _make_admin(db)
    await _login_admin(client)
    config = await _make_new_user_config(db, discount_value=10.0)
    res = await client.patch(
        f"{CONFIGS_URL}/{config.id}",
        json={"discount_value": 15.0, "params": {"valid_days": 60}},
    )
    assert res.status_code == 200
    assert res.json()["discount_value"] == 15.0


@pytest.mark.asyncio
async def test_patch_auto_checkout_blocked(client: AsyncClient, db):
    await _make_admin(db)
    await _login_admin(client)
    res = await client.post(
        AUTO_CHECKOUT_URL,
        json={
            "discount_type": "fixed", "discount_value": 50,
            "params": {"trigger_threshold": 500},
        },
    )
    config_id = res.json()["id"]
    res2 = await client.patch(f"{CONFIGS_URL}/{config_id}", json={"discount_value": 80.0})
    assert res2.status_code == 400


# ── POST /admin/coupon-configs/auto-checkout ──────────────────────────────────

@pytest.mark.asyncio
async def test_create_auto_checkout(client: AsyncClient, db):
    await _make_admin(db)
    await _login_admin(client)
    res = await client.post(
        AUTO_CHECKOUT_URL,
        json={
            "discount_type": "fixed",
            "discount_value": 50,
            "params": {"trigger_threshold": 500},
        },
    )
    assert res.status_code == 201
    assert res.json()["coupon_type"] == "auto_checkout"


@pytest.mark.asyncio
async def test_create_auto_checkout_missing_threshold(client: AsyncClient, db):
    await _make_admin(db)
    await _login_admin(client)
    res = await client.post(
        AUTO_CHECKOUT_URL,
        json={"discount_type": "fixed", "discount_value": 50, "params": {}},
    )
    assert res.status_code == 422


# ── DELETE /admin/coupon-configs/{id} ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_auto_checkout(client: AsyncClient, db):
    await _make_admin(db)
    await _login_admin(client)
    res = await client.post(
        AUTO_CHECKOUT_URL,
        json={
            "discount_type": "fixed", "discount_value": 50,
            "params": {"trigger_threshold": 500},
        },
    )
    config_id = res.json()["id"]
    del_res = await client.delete(f"{CONFIGS_URL}/{config_id}")
    assert del_res.status_code == 204


@pytest.mark.asyncio
async def test_delete_non_auto_checkout_blocked(client: AsyncClient, db):
    await _make_admin(db)
    await _login_admin(client)
    config = await _make_new_user_config(db)
    res = await client.delete(f"{CONFIGS_URL}/{config.id}")
    assert res.status_code == 400


# ── POST /admin/promo-codes ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_promo_code(client: AsyncClient, db):
    await _make_admin(db)
    await _login_admin(client)
    res = await client.post(
        PROMO_URL,
        json={
            "code": "NEWCODE",
            "discount_type": "fixed",
            "discount_value": 100,
            "max_per_user": 1,
        },
    )
    assert res.status_code == 201
    assert res.json()["code"] == "NEWCODE"


@pytest.mark.asyncio
async def test_create_promo_code_duplicate(client: AsyncClient, db):
    await _make_admin(db)
    await _login_admin(client)
    await client.post(
        PROMO_URL,
        json={"code": "DUP", "discount_type": "fixed", "discount_value": 50, "max_per_user": 1},
    )
    res = await client.post(
        PROMO_URL,
        json={"code": "DUP", "discount_type": "fixed", "discount_value": 50, "max_per_user": 1},
    )
    assert res.status_code == 409


# ── PUT /admin/promo-codes/{id} ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_promo_code(client: AsyncClient, db):
    await _make_admin(db)
    await _login_admin(client)
    pc = await _make_promo_code(db, code="UPDME")
    res = await client.put(
        f"{PROMO_URL}/{pc.id}",
        json={"code": "UPDME", "discount_type": "fixed", "discount_value": 200, "max_per_user": 1},
    )
    assert res.status_code == 200
    assert res.json()["discount_value"] == 200.0


# ── DELETE /admin/promo-codes/{id} ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_promo_code(client: AsyncClient, db):
    await _make_admin(db)
    await _login_admin(client)
    pc = await _make_promo_code(db, code="DELME")
    res = await client.delete(f"{PROMO_URL}/{pc.id}")
    assert res.status_code == 204


@pytest.mark.asyncio
async def test_delete_promo_code_has_usage(client: AsyncClient, db):
    await _make_admin(db)
    await _login_admin(client)
    pc = await _make_promo_code(db, code="USEDCODE")
    pc.total_used = 1
    await db.commit()
    res = await client.delete(f"{PROMO_URL}/{pc.id}")
    assert res.status_code == 400


# ── GET /admin/user-coupons ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_user_coupons_by_user(client: AsyncClient, db):
    user = await _make_customer(client, db)
    await _make_admin(db)
    config = await _make_new_user_config(db)
    uc = UserCoupon(
        user_id=user.id, coupon_config_id=config.id,
        discount_type=DiscountTypeEnum.percentage, discount_value=10,
    )
    db.add(uc)
    await db.commit()
    await _login_admin(client)
    res = await client.get(f"{USER_COUPONS_URL}?user_id={user.id}")
    assert res.status_code == 200
    assert len(res.json()["items"]) == 1


@pytest.mark.asyncio
async def test_list_user_coupons_by_used(client: AsyncClient, db):
    user = await _make_customer(client, db)
    await _make_admin(db)
    config = await _make_new_user_config(db)
    uc1 = UserCoupon(
        user_id=user.id, coupon_config_id=config.id,
        discount_type=DiscountTypeEnum.percentage, discount_value=10, is_used=False,
    )
    uc2 = UserCoupon(
        user_id=user.id, coupon_config_id=config.id,
        discount_type=DiscountTypeEnum.percentage, discount_value=10, is_used=True,
    )
    db.add_all([uc1, uc2])
    await db.commit()
    await _login_admin(client)
    res = await client.get(f"{USER_COUPONS_URL}?is_used=true")
    assert res.status_code == 200
    assert all(item["is_used"] for item in res.json()["items"])


# ── POST /admin/users/issue-coupons ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_issue_manual_coupons(client: AsyncClient, db):
    user = await _make_customer(client, db)
    await _make_admin(db)
    config = await _make_manual_config(db)
    await _login_admin(client)
    res = await client.post(
        ISSUE_URL,
        json={"user_ids": [str(user.id)], "coupon_config_id": str(config.id)},
    )
    assert res.status_code == 200
    assert res.json()["issued"] == 1

    result = await db.execute(
        select(UserCoupon).where(UserCoupon.user_id == user.id)
    )
    assert result.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_issue_non_manual_coupon_blocked(client: AsyncClient, db):
    user = await _make_customer(client, db)
    await _make_admin(db)
    config = await _make_new_user_config(db)
    await _login_admin(client)
    res = await client.post(
        ISSUE_URL,
        json={"user_ids": [str(user.id)], "coupon_config_id": str(config.id)},
    )
    assert res.status_code == 400


# ── Service 函式：issue_new_user_coupon ───────────────────────────────────────

@pytest.mark.asyncio
async def test_issue_new_user_coupon(client: AsyncClient, db):
    user = await _make_customer(client, db)
    config = await _make_new_user_config(db, discount_value=10.0, valid_days=30)

    await issue_new_user_coupon(db, user.id)
    await db.commit()

    result = await db.execute(
        select(UserCoupon).where(UserCoupon.user_id == user.id)
    )
    uc = result.scalar_one_or_none()
    assert uc is not None
    assert uc.coupon_config_id == config.id
    assert float(uc.discount_value) == 10.0
    assert uc.expires_at is not None


@pytest.mark.asyncio
async def test_issue_new_user_coupon_inactive(client: AsyncClient, db):
    user = await _make_customer(client, db)
    config = CouponConfig(
        coupon_type=CouponTypeEnum.new_user,
        discount_type=DiscountTypeEnum.percentage,
        discount_value=10,
        is_active=False,
        params={"valid_days": 30},
    )
    db.add(config)
    await db.commit()

    await issue_new_user_coupon(db, user.id)
    await db.commit()

    result = await db.execute(
        select(UserCoupon).where(UserCoupon.user_id == user.id)
    )
    assert result.scalar_one_or_none() is None


# ── Service 函式：calculate_discount ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_calculate_discount_promo_priority(client: AsyncClient, db):
    user = await _make_customer(client, db)
    await _make_promo_code(db, code="PRIORITY", discount_value=100)

    # 同時有 user_coupon 也有 promo_code，promo_code 優先
    config = await _make_new_user_config(db, discount_value=5)
    from datetime import UTC, datetime, timedelta
    uc = UserCoupon(
        user_id=user.id, coupon_config_id=config.id,
        discount_type=DiscountTypeEnum.percentage, discount_value=5,
        expires_at=datetime.now(UTC) + timedelta(days=30),
    )
    db.add(uc)
    await db.commit()
    await db.refresh(uc)

    result = await calculate_discount(
        db, user.id, 800.0, user_coupon_id=uc.id, promo_code="PRIORITY"
    )
    assert result["promo_code_id"] is not None
    assert result["user_coupon_id"] is None
    assert result["discount_amount"] == 100.0


@pytest.mark.asyncio
async def test_calculate_discount_user_coupon_priority(client: AsyncClient, db):
    user = await _make_customer(client, db)

    # auto_checkout 存在
    auto = CouponConfig(
        coupon_type=CouponTypeEnum.auto_checkout,
        discount_type=DiscountTypeEnum.fixed, discount_value=50,
        is_active=True, params={"trigger_threshold": 500},
    )
    db.add(auto)

    # user_coupon 存在
    config = await _make_new_user_config(db, discount_value=80)
    from datetime import UTC, datetime, timedelta
    uc = UserCoupon(
        user_id=user.id, coupon_config_id=config.id,
        discount_type=DiscountTypeEnum.fixed, discount_value=80,
        expires_at=datetime.now(UTC) + timedelta(days=30),
    )
    db.add(uc)
    await db.commit()
    await db.refresh(uc)

    result = await calculate_discount(db, user.id, 800.0, user_coupon_id=uc.id)
    assert result["user_coupon_id"] == uc.id
    assert result["auto_checkout_config_id"] is None


@pytest.mark.asyncio
async def test_calculate_discount_best_auto_checkout(client: AsyncClient, db):
    user = await _make_customer(client, db)

    low = CouponConfig(
        coupon_type=CouponTypeEnum.auto_checkout,
        discount_type=DiscountTypeEnum.fixed, discount_value=30,
        is_active=True, params={"trigger_threshold": 300},
    )
    high = CouponConfig(
        coupon_type=CouponTypeEnum.auto_checkout,
        discount_type=DiscountTypeEnum.fixed, discount_value=80,
        is_active=True, params={"trigger_threshold": 500},
    )
    db.add_all([low, high])
    await db.commit()
    await db.refresh(high)

    result = await calculate_discount(db, user.id, 800.0)
    assert result["discount_amount"] == 80.0
    assert result["auto_checkout_config_id"] == high.id


# ── Service 函式：apply_discount ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_apply_discount_promo_code_increments(client: AsyncClient, db):
    user = await _make_customer(client, db)
    pc = await _make_promo_code(db, code="APPLY100")
    order_id = uuid4()

    await apply_discount(db, order_id, user.id, 800.0, promo_code="APPLY100")
    await db.commit()

    await db.refresh(pc)
    assert pc.total_used == 1

    result = await db.execute(
        select(UserCoupon).where(UserCoupon.promo_code_id == pc.id)
    )
    uc = result.scalar_one_or_none()
    assert uc is not None
    assert uc.is_used is True
    assert uc.used_in_order_id == order_id


# ── Service 函式：revert_coupon ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_revert_coupon_user_coupon(client: AsyncClient, db):
    user = await _make_customer(client, db)
    config = await _make_new_user_config(db)
    order_id = uuid4()
    uc = UserCoupon(
        user_id=user.id, coupon_config_id=config.id,
        discount_type=DiscountTypeEnum.percentage, discount_value=10,
        is_used=True, used_in_order_id=order_id,
    )
    db.add(uc)
    await db.commit()
    await db.refresh(uc)

    await revert_coupon(db, order_id)
    await db.commit()

    await db.refresh(uc)
    assert uc.is_used is False
    assert uc.used_in_order_id is None


@pytest.mark.asyncio
async def test_revert_coupon_promo_code_decrements(client: AsyncClient, db):
    user = await _make_customer(client, db)
    pc = await _make_promo_code(db, code="REVERT")
    pc.total_used = 3
    order_id = uuid4()
    uc = UserCoupon(
        user_id=user.id, promo_code_id=pc.id,
        discount_type=DiscountTypeEnum.fixed, discount_value=100,
        is_used=True, used_in_order_id=order_id,
    )
    db.add(uc)
    await db.commit()

    await revert_coupon(db, order_id)
    await db.commit()

    await db.refresh(pc)
    assert pc.total_used == 2


# ── Service 函式：revoke_reward_coupons ───────────────────────────────────────

@pytest.mark.asyncio
async def test_revoke_reward_full_refund(client: AsyncClient, db):
    user = await _make_customer(client, db)
    config = CouponConfig(
        coupon_type=CouponTypeEnum.spend_reward,
        discount_type=DiscountTypeEnum.fixed, discount_value=50,
        is_active=True, params={"trigger_threshold": 1000, "valid_days": 30},
    )
    db.add(config)
    await db.commit()
    await db.refresh(config)

    order_id = uuid4()
    uc = UserCoupon(
        user_id=user.id, coupon_config_id=config.id,
        discount_type=DiscountTypeEnum.fixed, discount_value=50,
        is_used=False, source_order_id=order_id,
    )
    db.add(uc)
    await db.commit()
    await db.refresh(uc)

    await revoke_reward_coupons(db, order_id)
    await db.commit()

    await db.refresh(uc)
    from datetime import UTC, datetime
    assert uc.expires_at is not None
    assert uc.expires_at <= datetime.now(UTC)


@pytest.mark.asyncio
async def test_revoke_reward_partial_above_threshold(client: AsyncClient, db):
    user = await _make_customer(client, db)
    config = CouponConfig(
        coupon_type=CouponTypeEnum.spend_reward,
        discount_type=DiscountTypeEnum.fixed, discount_value=50,
        is_active=True, params={"trigger_threshold": 1000, "valid_days": 30},
    )
    db.add(config)
    await db.commit()
    await db.refresh(config)

    order_id = uuid4()
    uc = UserCoupon(
        user_id=user.id, coupon_config_id=config.id,
        discount_type=DiscountTypeEnum.fixed, discount_value=50,
        is_used=False, source_order_id=order_id,
    )
    db.add(uc)
    await db.commit()
    await db.refresh(uc)
    old_expires = uc.expires_at

    # 部分退款，但剩餘 1200 >= threshold 1000，不撤銷
    await revoke_reward_coupons(db, order_id, refund_amount=300, order_total=1500)
    await db.commit()

    await db.refresh(uc)
    assert uc.expires_at == old_expires


@pytest.mark.asyncio
async def test_revoke_reward_partial_below_threshold(client: AsyncClient, db):
    user = await _make_customer(client, db)
    config = CouponConfig(
        coupon_type=CouponTypeEnum.spend_reward,
        discount_type=DiscountTypeEnum.fixed, discount_value=50,
        is_active=True, params={"trigger_threshold": 1000, "valid_days": 30},
    )
    db.add(config)
    await db.commit()
    await db.refresh(config)

    order_id = uuid4()
    uc = UserCoupon(
        user_id=user.id, coupon_config_id=config.id,
        discount_type=DiscountTypeEnum.fixed, discount_value=50,
        is_used=False, source_order_id=order_id,
    )
    db.add(uc)
    await db.commit()
    await db.refresh(uc)

    # 部分退款，剩餘 800 < threshold 1000，撤銷
    await revoke_reward_coupons(db, order_id, refund_amount=500, order_total=1300)
    await db.commit()

    await db.refresh(uc)
    from datetime import UTC, datetime
    assert uc.expires_at is not None
    assert uc.expires_at <= datetime.now(UTC)


@pytest.mark.asyncio
async def test_revoke_reward_already_used_not_revoked(client: AsyncClient, db):
    user = await _make_customer(client, db)
    config = CouponConfig(
        coupon_type=CouponTypeEnum.spend_reward,
        discount_type=DiscountTypeEnum.fixed, discount_value=50,
        is_active=True, params={"trigger_threshold": 1000, "valid_days": 30},
    )
    db.add(config)
    await db.commit()
    await db.refresh(config)

    order_id = uuid4()
    uc = UserCoupon(
        user_id=user.id, coupon_config_id=config.id,
        discount_type=DiscountTypeEnum.fixed, discount_value=50,
        is_used=True, source_order_id=order_id,  # 已使用，不應被撤銷
    )
    db.add(uc)
    await db.commit()

    # is_used=True 的券不在撤銷範圍（service 只查 is_used=False）
    await revoke_reward_coupons(db, order_id)
    await db.commit()

    result = await db.execute(select(UserCoupon).where(UserCoupon.source_order_id == order_id))
    uc = result.scalar_one()
    assert uc.is_used is True  # 未被撤銷
