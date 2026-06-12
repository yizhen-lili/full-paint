"""Integration tests for Module 09 — Orders."""

import bcrypt
import pytest
from sqlalchemy import select

from auth.models import User
from color.models import PhysicalColor, SystemSetting
from discount.models import CouponConfig, CouponTypeEnum, DiscountTypeEnum, UserCoupon
from notifications.models import AdminNotification
from orders.models import (
    Order,
    OrderItem,
    OrderStatusEnum,
    PaymentSubmission,
    ProductionProgress,
)
from palette.models import PaletteColorMapping
from product.models import Product, ProductVariant
from production.models import ProductionJob

# ── URLs ───────────────────────────────────────────────────────────────────────

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
CART_URL = "/api/v1/cart"
CART_ITEMS_URL = "/api/v1/cart/items"
ORDERS_URL = "/api/v1/orders"
ADMIN_ORDERS_URL = "/api/v1/admin/orders"

CUSTOMER = {"name": "訂單測試用戶", "email": "orders@example.com", "password": "testpass123"}
ADMIN_EMAIL = "ordersadmin@test.com"
ADMIN_PASS = "adminpass123"

# ── Helpers ────────────────────────────────────────────────────────────────────


async def _make_customer(client, db, email=None, name=None):
    payload = {**CUSTOMER}
    if email:
        payload["email"] = email
    if name:
        payload["name"] = name
    await client.post(REGISTER_URL, json=payload)
    result = await db.execute(select(User).where(User.email == payload["email"]))
    user = result.scalar_one()
    user.is_email_verified = True
    await db.commit()
    return user


async def _make_admin(db):
    admin = User(
        name="OrdersAdmin",
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
        "email": ADMIN_EMAIL, "password": ADMIN_PASS,
    })
    if "access_token" in res.cookies:
        client.cookies.set("access_token", res.cookies["access_token"])
    return res


async def _seed_system_settings(db):
    for key, value in [
        ("bank_account_number", "12345678901"),
        ("bank_name", "測試銀行"),
        ("bank_account_name", "測試戶名"),
        ("payment_absolute_deadline_hours", "48"),
        # ECpay 寄件人資訊（create_shipment 需要）
        ("ecpay_sender_name", "測試寄件"),
        ("ecpay_sender_phone", "0912345678"),
        ("ecpay_sender_zip_code", "100"),
        ("ecpay_sender_address", "台北市中正區"),
    ]:
        existing = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
        if existing.scalar_one_or_none() is None:
            db.add(SystemSetting(key=key, value=value))
    await db.commit()


async def _make_production_job(db):
    job = ProductionJob(
        detail="standard",
        difficulty="beginner",
        canvas_w_cm=20.0,
        canvas_h_cm=20.0,
    )
    db.add(job)
    await db.flush()
    return job


async def _make_product_and_variant(db, job_id, price=500.0, is_active=True):
    product = Product(
        title="測試畫布",
        description="Test",
        cover_image_url="http://example.com/img.jpg",
        status="on_sale",
    )
    db.add(product)
    await db.flush()

    variant = ProductVariant(
        product_id=product.id,
        production_job_id=job_id,
        price=price,
        price_formula_base=price,
        is_active=is_active,
    )
    db.add(variant)
    await db.flush()
    return product, variant


async def _add_to_cart(client, variant_id, quantity=1):
    return await client.post(CART_ITEMS_URL, json={
        "variant_id": str(variant_id),
        "quantity": quantity,
    })


async def _make_shipping_profile(client):
    res = await client.post("/api/v1/users/me/shipping-profiles", json={
        "shipping_type": "home",
        "recipient_name": "測試收件人",
        "phone": "0912345678",
        "city": "台北市",
        "district": "信義區",
        "address_detail": "忠孝東路一段1號",
    })
    return res.json()["id"]


async def _create_order(client, **extra):
    """Create order using a freshly created home shipping profile."""
    profile_id = await _make_shipping_profile(client)
    payload = {"shipping_profile_id": profile_id}
    payload.update(extra)
    return await client.post(ORDERS_URL, json=payload)


async def _lock_shipping(client, order_id):
    """admin 確認出貨資訊 → 鎖定。create_shipment 前必須先 lock 否則 400。

    backend 行為：admin 修改完出貨資訊（地址/超商門市）後 lock；lock 後不能再改。
    test helper：直接呼叫 lock（test 用 _create_order 已建好 shipping_snapshot 不需修改）
    """
    return await client.post(f"{ADMIN_ORDERS_URL}/{order_id}/lock-shipping")


# ── Cart Tests ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_empty_cart(client, db):
    await _make_customer(client, db)
    await _login_customer(client)
    res = await client.get(CART_URL)
    assert res.status_code == 200
    data = res.json()
    assert data["items"] == []
    assert data["subtotal"] == 0


@pytest.mark.asyncio
async def test_add_cart_item(client, db):
    await _make_customer(client, db)
    await _login_customer(client)
    job = await _make_production_job(db)
    _, variant = await _make_product_and_variant(db, job.id)
    await db.commit()

    res = await _add_to_cart(client, variant.id, quantity=2)
    assert res.status_code == 201
    assert res.json()["quantity"] == 2


@pytest.mark.asyncio
async def test_add_inactive_variant_rejected(client, db):
    await _make_customer(client, db)
    await _login_customer(client)
    job = await _make_production_job(db)
    _, variant = await _make_product_and_variant(db, job.id, is_active=False)
    await db.commit()

    res = await _add_to_cart(client, variant.id)
    assert res.status_code == 409


@pytest.mark.asyncio
async def test_add_same_variant_accumulates(client, db):
    await _make_customer(client, db)
    await _login_customer(client)
    job = await _make_production_job(db)
    _, variant = await _make_product_and_variant(db, job.id)
    await db.commit()

    await _add_to_cart(client, variant.id, quantity=1)
    await _add_to_cart(client, variant.id, quantity=2)

    res = await client.get(CART_URL)
    assert res.status_code == 200
    assert res.json()["items"][0]["quantity"] == 3


@pytest.mark.asyncio
async def test_update_cart_item_quantity(client, db):
    await _make_customer(client, db)
    await _login_customer(client)
    job = await _make_production_job(db)
    _, variant = await _make_product_and_variant(db, job.id)
    await db.commit()

    add_res = await _add_to_cart(client, variant.id, quantity=3)
    item_id = add_res.json()["id"]

    res = await client.patch(f"{CART_ITEMS_URL}/{item_id}", json={"quantity": 5})
    assert res.status_code == 200
    assert res.json()["quantity"] == 5


@pytest.mark.asyncio
async def test_update_cart_item_zero_deletes(client, db):
    await _make_customer(client, db)
    await _login_customer(client)
    job = await _make_production_job(db)
    _, variant = await _make_product_and_variant(db, job.id)
    await db.commit()

    add_res = await _add_to_cart(client, variant.id, quantity=1)
    item_id = add_res.json()["id"]

    res = await client.patch(f"{CART_ITEMS_URL}/{item_id}", json={"quantity": 0})
    assert res.status_code == 200
    assert res.json()["deleted"] is True

    cart_res = await client.get(CART_URL)
    assert cart_res.json()["items"] == []


@pytest.mark.asyncio
async def test_delete_cart_item(client, db):
    await _make_customer(client, db)
    await _login_customer(client)
    job = await _make_production_job(db)
    _, variant = await _make_product_and_variant(db, job.id)
    await db.commit()

    add_res = await _add_to_cart(client, variant.id, quantity=1)
    item_id = add_res.json()["id"]

    res = await client.delete(f"{CART_ITEMS_URL}/{item_id}")
    assert res.status_code == 204

    cart_res = await client.get(CART_URL)
    assert cart_res.json()["items"] == []


@pytest.mark.asyncio
async def test_delete_other_users_cart_item_returns_404(client, db):
    await _make_customer(client, db, email="user1orders@example.com", name="用戶一二三四")
    await _make_customer(client, db, email="user2orders@example.com", name="用戶五六七八")
    job = await _make_production_job(db)
    _, variant = await _make_product_and_variant(db, job.id)
    await db.commit()

    # user1 adds item
    await _login_customer(client, email="user1orders@example.com")
    add_res = await _add_to_cart(client, variant.id)
    item_id = add_res.json()["id"]

    # user2 tries to delete
    await _login_customer(client, email="user2orders@example.com")
    res = await client.delete(f"{CART_ITEMS_URL}/{item_id}")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_checkout_preview_with_discount_and_free_shipping(client, db):
    await _seed_system_settings(db)
    await _make_customer(client, db)
    await _login_customer(client)
    job = await _make_production_job(db)
    _, variant = await _make_product_and_variant(db, job.id, price=500.0)
    await db.commit()

    await _add_to_cart(client, variant.id, quantity=2)

    res = await client.post("/api/v1/cart/checkout-preview", json={"shipping_type": "home"})
    assert res.status_code == 200
    data = res.json()
    assert data["subtotal"] == 1000.0
    assert data["shipping_fee"] == 0.0  # >= 800 free shipping
    assert data["total"] == 1000.0


# ── Order Creation Tests ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_order_success(client, db):
    await _seed_system_settings(db)
    await _make_customer(client, db)
    await _login_customer(client)
    job = await _make_production_job(db)
    _, variant = await _make_product_and_variant(db, job.id, price=500.0)
    await db.commit()

    await _add_to_cart(client, variant.id, quantity=1)

    res = await _create_order(client)
    assert res.status_code == 201
    data = res.json()
    assert "order_id" in data
    assert "order_number" in data
    assert data["order_number"].startswith("PL-")
    assert data["total"] == 620.0  # 500 + 120 shipping


@pytest.mark.asyncio
async def test_create_order_free_shipping(client, db):
    await _seed_system_settings(db)
    await _make_customer(client, db)
    await _login_customer(client)
    job = await _make_production_job(db)
    _, variant = await _make_product_and_variant(db, job.id, price=900.0)
    await db.commit()

    await _add_to_cart(client, variant.id, quantity=1)

    res = await _create_order(client)
    assert res.status_code == 201
    assert res.json()["total"] == 900.0


@pytest.mark.asyncio
async def test_create_order_inactive_variant_rejected(client, db):
    await _seed_system_settings(db)
    await _make_customer(client, db)
    await _login_customer(client)
    job = await _make_production_job(db)
    _, variant = await _make_product_and_variant(db, job.id)
    await db.commit()

    # Add to cart while active
    await _add_to_cart(client, variant.id, quantity=1)

    # Deactivate variant
    variant.is_active = False
    await db.commit()

    res = await _create_order(client)
    assert res.status_code == 409


@pytest.mark.asyncio
async def test_create_order_with_user_coupon(client, db):
    await _seed_system_settings(db)
    user = await _make_customer(client, db)
    await _login_customer(client)
    job = await _make_production_job(db)
    _, variant = await _make_product_and_variant(db, job.id, price=500.0)

    coupon = UserCoupon(
        user_id=user.id,
        coupon_config_id=None,
        promo_code_id=None,
        discount_type=DiscountTypeEnum.fixed,
        discount_value=100,
        is_used=False,
    )
    # Need a config to satisfy CHECK constraint
    config = CouponConfig(
        coupon_type=CouponTypeEnum.manual,
        discount_type=DiscountTypeEnum.fixed,
        discount_value=100,
        is_active=True,
        params={},
    )
    db.add(config)
    await db.flush()
    coupon.coupon_config_id = config.id
    db.add(coupon)
    await db.commit()

    await _add_to_cart(client, variant.id, quantity=1)

    res = await _create_order(client, user_coupon_id=str(coupon.id))
    assert res.status_code == 201
    data = res.json()
    # 500 - 100 + 120 = 520
    assert data["total"] == 520.0


@pytest.mark.asyncio
async def test_create_order_with_preorder_split(client, db):
    """When stock covers only part of the quantity, fulfilled_qty + preorder_qty = total."""
    await _seed_system_settings(db)
    await _make_customer(client, db)
    await _login_customer(client)
    job = await _make_production_job(db)
    _, variant = await _make_product_and_variant(db, job.id, price=300.0)

    # Create a physical color with only 10ml stock
    color = PhysicalColor(
        code="TEST001", name="測試色", rgb=[100, 100, 100], stock_ml=10.0
    )
    db.add(color)
    await db.flush()

    # Map this color to the job with required_ml=5 (can fulfill max 2 units from 10ml)
    mapping = PaletteColorMapping(
        production_job_id=job.id,
        template_id=1,
        algorithm_rgb=[100, 100, 100],
        physical_color_id=color.id,
        required_ml=5.0,
    )
    db.add(mapping)
    await db.commit()

    # Add 3 units to cart (only 2 can be fulfilled)
    await _add_to_cart(client, variant.id, quantity=3)

    res = await _create_order(client)
    assert res.status_code == 201

    order_id = res.json()["order_id"]
    item_result = await db.execute(
        select(OrderItem).where(OrderItem.order_id == order_id)
    )
    item = item_result.scalar_one()
    assert item.fulfilled_qty == 2
    assert item.preorder_qty == 1
    assert item.fulfilled_qty + item.preorder_qty == item.quantity


# ── Customer Order Query Tests ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_orders(client, db):
    await _seed_system_settings(db)
    await _make_customer(client, db)
    await _login_customer(client)
    job = await _make_production_job(db)
    _, variant = await _make_product_and_variant(db, job.id, price=300.0)
    await db.commit()

    await _add_to_cart(client, variant.id)
    await _create_order(client)

    res = await client.get(ORDERS_URL)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_get_order_detail(client, db):
    await _seed_system_settings(db)
    await _make_customer(client, db)
    await _login_customer(client)
    job = await _make_production_job(db)
    _, variant = await _make_product_and_variant(db, job.id, price=300.0)
    await db.commit()

    await _add_to_cart(client, variant.id)
    create_res = await _create_order(client)
    order_id = create_res.json()["order_id"]

    res = await client.get(f"{ORDERS_URL}/{order_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == order_id
    assert data["can_cancel"] is True
    assert data["can_confirm_received"] is False


@pytest.mark.asyncio
async def test_get_other_users_order_returns_404(client, db):
    await _seed_system_settings(db)
    await _make_customer(client, db, email="u1orders@example.com", name="用戶一二三四")
    await _make_customer(client, db, email="u2orders@example.com", name="用戶五六七八")

    job = await _make_production_job(db)
    _, variant = await _make_product_and_variant(db, job.id, price=300.0)
    await db.commit()

    await _login_customer(client, email="u1orders@example.com")
    await _add_to_cart(client, variant.id)
    create_res = await _create_order(client)
    order_id = create_res.json()["order_id"]

    await _login_customer(client, email="u2orders@example.com")
    res = await client.get(f"{ORDERS_URL}/{order_id}")
    assert res.status_code == 404


# ── Payment Submission Tests ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_submit_payment(client, db):
    await _seed_system_settings(db)
    await _make_customer(client, db)
    await _login_customer(client)
    job = await _make_production_job(db)
    _, variant = await _make_product_and_variant(db, job.id, price=300.0)
    await db.commit()

    await _add_to_cart(client, variant.id)
    create_res = await _create_order(client)
    order_id = create_res.json()["order_id"]

    res = await client.post(f"{ORDERS_URL}/{order_id}/payment-submission", json={
        "transfer_amount": 420.0,
        "transfer_date": "2026-04-23",
        "transfer_time": "14:30:00",
        "account_last5": "12345",
    })
    assert res.status_code == 201
    body = res.json()
    assert body["transfer_amount"] == 420.0
    assert body["account_last5"] == "12345"
    assert body["is_flagged"] is False
    assert "id" in body and "created_at" in body

    notif_result = await db.execute(
        select(AdminNotification).where(AdminNotification.type == "payment_submitted")
    )
    assert notif_result.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_submit_payment_non_pending_rejected(client, db):
    await _seed_system_settings(db)
    await _make_customer(client, db)
    await _login_customer(client)
    job = await _make_production_job(db)
    _, variant = await _make_product_and_variant(db, job.id, price=300.0)
    await db.commit()

    await _add_to_cart(client, variant.id)
    create_res = await _create_order(client)
    order_id = create_res.json()["order_id"]

    # Cancel first
    await client.post(f"{ORDERS_URL}/{order_id}/cancel", json={})

    res = await client.post(f"{ORDERS_URL}/{order_id}/payment-submission", json={
        "transfer_amount": 420.0,
        "transfer_date": "2026-04-23",
        "transfer_time": "14:30:00",
        "account_last5": "12345",
    })
    assert res.status_code == 400


# ── Cancel Order Tests ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cancel_pending_order(client, db):
    await _seed_system_settings(db)
    await _make_customer(client, db)
    await _login_customer(client)
    job = await _make_production_job(db)
    _, variant = await _make_product_and_variant(db, job.id, price=300.0)
    await db.commit()

    await _add_to_cart(client, variant.id)
    create_res = await _create_order(client)
    order_id = create_res.json()["order_id"]

    res = await client.post(f"{ORDERS_URL}/{order_id}/cancel", json={})
    assert res.status_code == 200

    order_res = await db.execute(select(Order).where(Order.id == order_id))
    order = order_res.scalar_one()
    assert order.status == OrderStatusEnum.cancelled


@pytest.mark.asyncio
async def test_cancel_paid_order_rejected(client, db):
    await _seed_system_settings(db)
    await _make_customer(client, db)
    await _make_admin(db)
    job = await _make_production_job(db)
    _, variant = await _make_product_and_variant(db, job.id, price=300.0)
    await db.commit()

    await _login_customer(client)
    await _add_to_cart(client, variant.id)
    create_res = await _create_order(client)
    order_id = create_res.json()["order_id"]

    # Mark as paid via admin
    await _login_admin(client)
    await client.patch(f"{ADMIN_ORDERS_URL}/{order_id}/status", json={"status": "paid"})

    await _login_customer(client)
    res = await client.post(f"{ORDERS_URL}/{order_id}/cancel", json={})
    assert res.status_code == 400


# ── Confirm Received Tests ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_confirm_received_success(client, db):
    await _seed_system_settings(db)
    await _make_customer(client, db)
    await _make_admin(db)
    job = await _make_production_job(db)
    _, variant = await _make_product_and_variant(db, job.id, price=300.0)
    await db.commit()

    await _login_customer(client)
    await _add_to_cart(client, variant.id)
    create_res = await _create_order(client)
    order_id = create_res.json()["order_id"]

    # Admin: paid → lock-shipping → create shipment (marks as shipped)
    await _login_admin(client)
    await client.patch(f"{ADMIN_ORDERS_URL}/{order_id}/status", json={"status": "paid"})
    await _lock_shipping(client, order_id)
    await client.post(
        f"{ADMIN_ORDERS_URL}/{order_id}/shipments", json={"shipment_type": "fulfilled"}
    )

    await _login_customer(client)
    res = await client.post(f"{ORDERS_URL}/{order_id}/confirm-received")
    assert res.status_code == 200, f"got {res.status_code}: {res.text}"

    order_res = await db.execute(select(Order).where(Order.id == order_id))
    order = order_res.scalar_one()
    assert order.status == OrderStatusEnum.completed


@pytest.mark.asyncio
async def test_confirm_received_non_shipped_rejected(client, db):
    await _seed_system_settings(db)
    await _make_customer(client, db)
    await _login_customer(client)
    job = await _make_production_job(db)
    _, variant = await _make_product_and_variant(db, job.id, price=300.0)
    await db.commit()

    await _add_to_cart(client, variant.id)
    create_res = await _create_order(client)
    order_id = create_res.json()["order_id"]

    res = await client.post(f"{ORDERS_URL}/{order_id}/confirm-received")
    assert res.status_code == 400


# ── Confirm Refund Tests ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_confirm_refund_success(client, db):
    await _seed_system_settings(db)
    await _make_customer(client, db)
    await _make_admin(db)
    job = await _make_production_job(db)
    _, variant = await _make_product_and_variant(db, job.id, price=300.0)
    await db.commit()

    await _login_customer(client)
    await _add_to_cart(client, variant.id)
    create_res = await _create_order(client)
    order_id = create_res.json()["order_id"]

    await _login_admin(client)
    await client.patch(f"{ADMIN_ORDERS_URL}/{order_id}/status", json={"status": "paid"})
    await client.patch(
        f"{ADMIN_ORDERS_URL}/{order_id}/status", json={"status": "refund_processing"}
    )

    # Get order items for refund
    order_res = await db.execute(select(OrderItem).where(OrderItem.order_id == order_id))
    items = order_res.scalars().all()
    item_ids = [str(i.id) for i in items]

    await client.post(f"{ADMIN_ORDERS_URL}/{order_id}/refund", json={
        "refund_amount": 420.0,
        "returned_item_ids": item_ids,
    })

    await _login_customer(client)
    res = await client.post(f"{ORDERS_URL}/{order_id}/confirm-refund")
    assert res.status_code == 204


@pytest.mark.asyncio
async def test_confirm_refund_already_confirmed_rejected(client, db):
    await _seed_system_settings(db)
    await _make_customer(client, db)
    await _make_admin(db)
    job = await _make_production_job(db)
    _, variant = await _make_product_and_variant(db, job.id, price=300.0)
    await db.commit()

    await _login_customer(client)
    await _add_to_cart(client, variant.id)
    create_res = await _create_order(client)
    order_id = create_res.json()["order_id"]

    await _login_admin(client)
    await client.patch(f"{ADMIN_ORDERS_URL}/{order_id}/status", json={"status": "paid"})
    await client.patch(
        f"{ADMIN_ORDERS_URL}/{order_id}/status", json={"status": "refund_processing"}
    )

    order_res = await db.execute(select(OrderItem).where(OrderItem.order_id == order_id))
    items = order_res.scalars().all()
    item_ids = [str(i.id) for i in items]
    await client.post(f"{ADMIN_ORDERS_URL}/{order_id}/refund", json={
        "refund_amount": 420.0,
        "returned_item_ids": item_ids,
    })

    await _login_customer(client)
    await client.post(f"{ORDERS_URL}/{order_id}/confirm-refund")
    # Second confirm
    res = await client.post(f"{ORDERS_URL}/{order_id}/confirm-refund")
    assert res.status_code == 400


# ── Admin Order Tests ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_list_orders_with_search(client, db):
    await _seed_system_settings(db)
    await _make_customer(client, db)
    await _make_admin(db)
    job = await _make_production_job(db)
    _, variant = await _make_product_and_variant(db, job.id, price=300.0)
    await db.commit()

    await _login_customer(client)
    await _add_to_cart(client, variant.id)
    create_res = await _create_order(client)
    order_number = create_res.json()["order_number"]

    await _login_admin(client)
    res = await client.get(f"{ADMIN_ORDERS_URL}?search={order_number}")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    assert any(o["order_number"] == order_number for o in data["items"])


@pytest.mark.asyncio
async def test_admin_get_order_detail(client, db):
    await _seed_system_settings(db)
    await _make_customer(client, db)
    await _make_admin(db)
    job = await _make_production_job(db)
    _, variant = await _make_product_and_variant(db, job.id, price=300.0)
    await db.commit()

    await _login_customer(client)
    await _add_to_cart(client, variant.id)
    create_res = await _create_order(client)
    order_id = create_res.json()["order_id"]

    await _login_admin(client)
    res = await client.get(f"{ADMIN_ORDERS_URL}/{order_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == order_id
    assert "user_name" in data
    assert "admin_notes" in data


@pytest.mark.asyncio
async def test_admin_status_to_paid_creates_production_progress(client, db):
    await _seed_system_settings(db)
    await _make_customer(client, db)
    await _make_admin(db)
    job = await _make_production_job(db)
    _, variant = await _make_product_and_variant(db, job.id, price=300.0)
    await db.commit()

    await _login_customer(client)
    await _add_to_cart(client, variant.id)
    create_res = await _create_order(client)
    order_id = create_res.json()["order_id"]

    await _login_admin(client)
    res = await client.patch(f"{ADMIN_ORDERS_URL}/{order_id}/status", json={"status": "paid"})
    assert res.status_code == 200
    assert res.json()["status"] == "paid"

    prog_result = await db.execute(
        select(ProductionProgress)
        .join(OrderItem, ProductionProgress.order_item_id == OrderItem.id)
        .where(OrderItem.order_id == order_id)
    )
    assert prog_result.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_admin_cancel_pending_order(client, db):
    await _seed_system_settings(db)
    await _make_customer(client, db)
    await _make_admin(db)
    job = await _make_production_job(db)
    _, variant = await _make_product_and_variant(db, job.id, price=300.0)
    await db.commit()

    await _login_customer(client)
    await _add_to_cart(client, variant.id)
    create_res = await _create_order(client)
    order_id = create_res.json()["order_id"]

    await _login_admin(client)
    res = await client.patch(f"{ADMIN_ORDERS_URL}/{order_id}/status", json={
        "status": "cancelled",
        "admin_notes": "Admin cancel test",
    })
    assert res.status_code == 200
    assert res.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_admin_cancel_paid_order_rejected(client, db):
    await _seed_system_settings(db)
    await _make_customer(client, db)
    await _make_admin(db)
    job = await _make_production_job(db)
    _, variant = await _make_product_and_variant(db, job.id, price=300.0)
    await db.commit()

    await _login_customer(client)
    await _add_to_cart(client, variant.id)
    create_res = await _create_order(client)
    order_id = create_res.json()["order_id"]

    await _login_admin(client)
    await client.patch(f"{ADMIN_ORDERS_URL}/{order_id}/status", json={"status": "paid"})

    res = await client.patch(f"{ADMIN_ORDERS_URL}/{order_id}/status", json={"status": "cancelled"})
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_admin_status_to_refund_processing(client, db):
    await _seed_system_settings(db)
    await _make_customer(client, db)
    await _make_admin(db)
    job = await _make_production_job(db)
    _, variant = await _make_product_and_variant(db, job.id, price=300.0)
    await db.commit()

    await _login_customer(client)
    await _add_to_cart(client, variant.id)
    create_res = await _create_order(client)
    order_id = create_res.json()["order_id"]

    await _login_admin(client)
    await client.patch(f"{ADMIN_ORDERS_URL}/{order_id}/status", json={"status": "paid"})
    res = await client.patch(
        f"{ADMIN_ORDERS_URL}/{order_id}/status", json={"status": "refund_processing"}
    )
    assert res.status_code == 200
    assert res.json()["status"] == "refund_processing"


@pytest.mark.asyncio
async def test_create_shipment_ecpay_mock(client, db):
    await _seed_system_settings(db)
    await _make_customer(client, db)
    await _make_admin(db)
    job = await _make_production_job(db)
    _, variant = await _make_product_and_variant(db, job.id, price=300.0)
    await db.commit()

    await _login_customer(client)
    await _add_to_cart(client, variant.id)
    create_res = await _create_order(client)
    order_id = create_res.json()["order_id"]

    await _login_admin(client)
    paid_res = await client.patch(f"{ADMIN_ORDERS_URL}/{order_id}/status", json={"status": "paid"})
    assert paid_res.status_code == 200, f"paid: {paid_res.status_code} {paid_res.text}"
    lock_res = await _lock_shipping(client, order_id)
    assert lock_res.status_code == 200, f"lock: {lock_res.status_code} {lock_res.text}"

    res = await client.post(
        f"{ADMIN_ORDERS_URL}/{order_id}/shipments", json={"shipment_type": "fulfilled"}
    )
    assert res.status_code == 201, f"shipment: {res.status_code} {res.text}"
    data = res.json()
    # dry-run mode: tracking 以 DRY 開頭（13 字 CVSPaymentNo 格式），ecpay_logistics_id 以 MOCK 開頭
    assert data["tracking_number"].startswith("DRY"), f"got tracking: {data['tracking_number']}"
    assert data["ecpay_logistics_id"].startswith("MOCK"), (
        f"got logistics_id: {data['ecpay_logistics_id']}"
    )

    order_res = await db.execute(select(Order).where(Order.id == order_id))
    order = order_res.scalar_one()
    assert order.status == OrderStatusEnum.shipped


@pytest.mark.asyncio
async def test_update_production_progress_manufacturing(client, db):
    await _seed_system_settings(db)
    await _make_customer(client, db)
    await _make_admin(db)
    job = await _make_production_job(db)
    _, variant = await _make_product_and_variant(db, job.id, price=300.0)
    await db.commit()

    await _login_customer(client)
    await _add_to_cart(client, variant.id)
    create_res = await _create_order(client)
    order_id = create_res.json()["order_id"]

    await _login_admin(client)
    await client.patch(f"{ADMIN_ORDERS_URL}/{order_id}/status", json={"status": "paid"})

    prog_result = await db.execute(
        select(ProductionProgress)
        .join(OrderItem, ProductionProgress.order_item_id == OrderItem.id)
        .where(OrderItem.order_id == order_id)
    )
    progress = prog_result.scalar_one()

    res = await client.patch(
        f"{ADMIN_ORDERS_URL}/{order_id}/production-progress/{progress.id}",
        json={"status": "manufacturing"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "manufacturing"
    assert body["order_item_id"] == str(progress.order_item_id)
    assert "updated_at" in body


@pytest.mark.asyncio
async def test_update_production_progress_shipped_rejected(client, db):
    await _seed_system_settings(db)
    await _make_customer(client, db)
    await _make_admin(db)
    job = await _make_production_job(db)
    _, variant = await _make_product_and_variant(db, job.id, price=300.0)
    await db.commit()

    await _login_customer(client)
    await _add_to_cart(client, variant.id)
    create_res = await _create_order(client)
    order_id = create_res.json()["order_id"]

    await _login_admin(client)
    await client.patch(f"{ADMIN_ORDERS_URL}/{order_id}/status", json={"status": "paid"})

    prog_result = await db.execute(
        select(ProductionProgress)
        .join(OrderItem, ProductionProgress.order_item_id == OrderItem.id)
        .where(OrderItem.order_id == order_id)
    )
    progress = prog_result.scalar_one()

    res = await client.patch(
        f"{ADMIN_ORDERS_URL}/{order_id}/production-progress/{progress.id}",
        json={"status": "shipped"},
    )
    # "shipped" rejected at schema level — not in Literal
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_full_refund(client, db):
    await _seed_system_settings(db)
    await _make_customer(client, db)
    await _make_admin(db)
    job = await _make_production_job(db)
    _, variant = await _make_product_and_variant(db, job.id, price=300.0)
    await db.commit()

    await _login_customer(client)
    await _add_to_cart(client, variant.id)
    create_res = await _create_order(client)
    order_id = create_res.json()["order_id"]
    total = create_res.json()["total"]

    await _login_admin(client)
    await client.patch(f"{ADMIN_ORDERS_URL}/{order_id}/status", json={"status": "paid"})
    await client.patch(
        f"{ADMIN_ORDERS_URL}/{order_id}/status", json={"status": "refund_processing"}
    )

    item_result = await db.execute(select(OrderItem).where(OrderItem.order_id == order_id))
    items = item_result.scalars().all()
    item_ids = [str(i.id) for i in items]

    res = await client.post(f"{ADMIN_ORDERS_URL}/{order_id}/refund", json={
        "refund_amount": total,
        "returned_item_ids": item_ids,
    })
    assert res.status_code == 200
    assert res.json()["status"] == "refunded"


@pytest.mark.asyncio
async def test_partial_refund(client, db):
    await _seed_system_settings(db)
    await _make_customer(client, db)
    await _make_admin(db)
    job = await _make_production_job(db)
    _, v1 = await _make_product_and_variant(db, job.id, price=300.0)
    _, v2 = await _make_product_and_variant(db, job.id, price=200.0)
    await db.commit()

    await _login_customer(client)
    await _add_to_cart(client, v1.id)
    await _add_to_cart(client, v2.id)
    create_res = await _create_order(client)
    order_id = create_res.json()["order_id"]

    await _login_admin(client)
    await client.patch(f"{ADMIN_ORDERS_URL}/{order_id}/status", json={"status": "paid"})
    await client.patch(
        f"{ADMIN_ORDERS_URL}/{order_id}/status", json={"status": "refund_processing"}
    )

    item_result = await db.execute(select(OrderItem).where(OrderItem.order_id == order_id))
    items = item_result.scalars().all()
    # Return only first item
    one_item_id = [str(items[0].id)]

    res = await client.post(f"{ADMIN_ORDERS_URL}/{order_id}/refund", json={
        "refund_amount": 300.0,
        "returned_item_ids": one_item_id,
    })
    assert res.status_code == 200
    assert res.json()["status"] == "partially_refunded"


@pytest.mark.asyncio
async def test_refund_exceeds_total_rejected(client, db):
    """Admin cannot refund more than the order total."""
    await _seed_system_settings(db)
    await _make_customer(client, db)
    await _make_admin(db)
    job = await _make_production_job(db)
    _, variant = await _make_product_and_variant(db, job.id, price=300.0)
    await db.commit()

    await _login_customer(client)
    await _add_to_cart(client, variant.id)
    create_res = await _create_order(client)
    order_id = create_res.json()["order_id"]
    order_total = create_res.json()["total"]

    await _login_admin(client)
    await client.patch(f"{ADMIN_ORDERS_URL}/{order_id}/status", json={"status": "paid"})
    await client.patch(
        f"{ADMIN_ORDERS_URL}/{order_id}/status", json={"status": "refund_processing"}
    )

    item_result = await db.execute(select(OrderItem).where(OrderItem.order_id == order_id))
    items = item_result.scalars().all()
    item_ids = [str(i.id) for i in items]

    res = await client.post(f"{ADMIN_ORDERS_URL}/{order_id}/refund", json={
        "refund_amount": order_total + 1000.0,
        "returned_item_ids": item_ids,
    })
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_flag_payment_submission(client, db):
    await _seed_system_settings(db)
    await _make_customer(client, db)
    await _make_admin(db)
    job = await _make_production_job(db)
    _, variant = await _make_product_and_variant(db, job.id, price=300.0)
    await db.commit()

    await _login_customer(client)
    await _add_to_cart(client, variant.id)
    create_res = await _create_order(client)
    order_id = create_res.json()["order_id"]

    await client.post(f"{ORDERS_URL}/{order_id}/payment-submission", json={
        "transfer_amount": 420.0,
        "transfer_date": "2026-04-23",
        "transfer_time": "14:30:00",
        "account_last5": "12345",
    })

    sub_result = await db.execute(
        select(PaymentSubmission).where(PaymentSubmission.order_id == order_id)
    )
    sub = sub_result.scalar_one()

    await _login_admin(client)
    res = await client.patch(
        f"{ADMIN_ORDERS_URL}/{order_id}/payment-submissions/{sub.id}/flag",
        json={"is_flagged": True, "admin_note": "金額有誤"},
    )
    assert res.status_code == 200
    assert "payment_deadline" in res.json()


@pytest.mark.asyncio
async def test_update_admin_notes(client, db):
    await _seed_system_settings(db)
    await _make_customer(client, db)
    await _make_admin(db)
    job = await _make_production_job(db)
    _, variant = await _make_product_and_variant(db, job.id, price=300.0)
    await db.commit()

    await _login_customer(client)
    await _add_to_cart(client, variant.id)
    create_res = await _create_order(client)
    order_id = create_res.json()["order_id"]

    await _login_admin(client)
    res = await client.patch(f"{ADMIN_ORDERS_URL}/{order_id}/admin-notes", json={
        "admin_notes": "需確認收款",
    })
    assert res.status_code == 200
    assert res.json()["admin_notes"] == "需確認收款"


# ── Webhook Tests ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ecpay_webhook_delivered_completes_order(client, db):
    await _seed_system_settings(db)
    await _make_customer(client, db)
    await _make_admin(db)
    job = await _make_production_job(db)
    _, variant = await _make_product_and_variant(db, job.id, price=300.0)
    await db.commit()

    await _login_customer(client)
    await _add_to_cart(client, variant.id)
    create_res = await _create_order(client)
    order_id = create_res.json()["order_id"]

    await _login_admin(client)
    await client.patch(f"{ADMIN_ORDERS_URL}/{order_id}/status", json={"status": "paid"})
    await _lock_shipping(client, order_id)
    ship_res = await client.post(
        f"{ADMIN_ORDERS_URL}/{order_id}/shipments", json={"shipment_type": "fulfilled"}
    )
    ecpay_logistics_id = ship_res.json()["ecpay_logistics_id"]

    res = await client.post("/api/v1/webhooks/ecpay", data={
        "AllPayLogisticsID": ecpay_logistics_id,
        "RtnCode": "3",
        "RtnMsg": "已投遞",
    })
    assert res.status_code == 200
    assert res.text == "1|OK"

    order_res = await db.execute(select(Order).where(Order.id == order_id))
    order = order_res.scalar_one()
    assert order.status == OrderStatusEnum.completed


@pytest.mark.asyncio
async def test_ecpay_webhook_other_status_creates_notification(client, db):
    await _seed_system_settings(db)
    await _make_customer(client, db)
    await _make_admin(db)
    job = await _make_production_job(db)
    _, variant = await _make_product_and_variant(db, job.id, price=300.0)
    await db.commit()

    await _login_customer(client)
    await _add_to_cart(client, variant.id)
    create_res = await _create_order(client)
    order_id = create_res.json()["order_id"]

    await _login_admin(client)
    await client.patch(f"{ADMIN_ORDERS_URL}/{order_id}/status", json={"status": "paid"})
    await _lock_shipping(client, order_id)
    ship_res = await client.post(
        f"{ADMIN_ORDERS_URL}/{order_id}/shipments", json={"shipment_type": "fulfilled"}
    )
    ecpay_logistics_id = ship_res.json()["ecpay_logistics_id"]

    res = await client.post("/api/v1/webhooks/ecpay", data={
        "AllPayLogisticsID": ecpay_logistics_id,
        "RtnCode": "99",
        "RtnMsg": "派送中",
    })
    assert res.status_code == 200

    notif_result = await db.execute(
        select(AdminNotification).where(AdminNotification.type == "ecpay_status")
    )
    assert notif_result.scalar_one_or_none() is not None


# ── Reorder (過期訂單重新下單) ──────────────────────────────────────────────────


async def _make_expired_order(
    db, user, *, variant=None, custom_request=None, title="測試畫布", qty=1,
):
    """直接建一筆 payment_expired 訂單 + 一個 order_item（變體或客製）。"""
    import uuid as _uuid
    from datetime import UTC, datetime

    order = Order(
        order_number=f"PL-{_uuid.uuid4().hex[:8]}",
        user_id=user.id,
        status=OrderStatusEnum.payment_expired,
        subtotal=500, discount_amount=0, shipping_fee=0, total=500,
        shipping_type="home", shipping_snapshot={},
        created_at=datetime.now(UTC),
    )
    db.add(order)
    await db.flush()
    db.add(OrderItem(
        order_id=order.id,
        product_variant_id=variant.id if variant else None,
        custom_request_id=custom_request.id if custom_request else None,
        product_title_snapshot=title,
        variant_spec_snapshot={},
        unit_price=500, quantity=qty, fulfilled_qty=0, preorder_qty=0,
        is_returned=False,
    ))
    await db.commit()
    return order


@pytest.mark.asyncio
async def test_reorder_expired_order_ok(client, db):
    """過期訂單 + 在架變體 → 200，品項加回購物車。"""
    user = await _make_customer(client, db)
    await _login_customer(client)
    job = await _make_production_job(db)
    _, variant = await _make_product_and_variant(db, job.id, is_active=True)
    order = await _make_expired_order(db, user, variant=variant, qty=2)

    res = await client.post(f"{ORDERS_URL}/{order.id}/reorder")
    assert res.status_code == 200
    body = res.json()
    assert body["added_count"] == 1
    assert body["unavailable_count"] == 0
    assert body["added"][0]["quantity"] == 2

    cart = (await client.get(CART_URL)).json()
    assert any(
        item["variant_id"] == str(variant.id) for item in cart["items"]
    )


@pytest.mark.asyncio
async def test_reorder_inactive_variant_unavailable(client, db):
    """過期訂單 + 已停用變體 → 列入 unavailable，不加入購物車。"""
    user = await _make_customer(client, db)
    await _login_customer(client)
    job = await _make_production_job(db)
    _, variant = await _make_product_and_variant(db, job.id, is_active=False)
    order = await _make_expired_order(db, user, variant=variant, title="已下架畫布")

    res = await client.post(f"{ORDERS_URL}/{order.id}/reorder")
    assert res.status_code == 200
    body = res.json()
    assert body["added_count"] == 0
    assert body["unavailable_count"] == 1
    u = body["unavailable"][0]
    assert u["title"] == "已下架畫布"
    # 一般商品下架：非客製，code 與 custom_request_id 應為 null
    assert u["code"] is None
    assert u["custom_request_id"] is None

    cart = (await client.get(CART_URL)).json()
    assert cart["items"] == []


@pytest.mark.asyncio
async def test_reorder_partial_some_unavailable(client, db):
    """過期訂單含一在架 + 一停用變體 → 一加入、一無法購買。"""
    user = await _make_customer(client, db)
    await _login_customer(client)
    job = await _make_production_job(db)
    _, active_v = await _make_product_and_variant(db, job.id, is_active=True)
    job2 = await _make_production_job(db)
    _, dead_v = await _make_product_and_variant(db, job2.id, is_active=False)

    import uuid as _uuid
    from datetime import UTC, datetime

    order = Order(
        order_number=f"PL-{_uuid.uuid4().hex[:8]}",
        user_id=user.id, status=OrderStatusEnum.payment_expired,
        subtotal=1000, discount_amount=0, shipping_fee=0, total=1000,
        shipping_type="home", shipping_snapshot={}, created_at=datetime.now(UTC),
    )
    db.add(order)
    await db.flush()
    for v, title in [(active_v, "在架"), (dead_v, "停用")]:
        db.add(OrderItem(
            order_id=order.id, product_variant_id=v.id,
            product_title_snapshot=title, variant_spec_snapshot={},
            unit_price=500, quantity=1, fulfilled_qty=0, preorder_qty=0,
            is_returned=False,
        ))
    await db.commit()

    res = await client.post(f"{ORDERS_URL}/{order.id}/reorder")
    assert res.status_code == 200
    body = res.json()
    assert body["added_count"] == 1
    assert body["unavailable_count"] == 1


@pytest.mark.asyncio
async def test_reorder_non_expired_order_409(client, db):
    """非逾期訂單（paid）→ 409。"""
    user = await _make_customer(client, db)
    await _login_customer(client)
    job = await _make_production_job(db)
    _, variant = await _make_product_and_variant(db, job.id, is_active=True)

    import uuid as _uuid
    from datetime import UTC, datetime

    order = Order(
        order_number=f"PL-{_uuid.uuid4().hex[:8]}",
        user_id=user.id, status=OrderStatusEnum.paid,
        subtotal=500, discount_amount=0, shipping_fee=0, total=500,
        shipping_type="home", shipping_snapshot={}, created_at=datetime.now(UTC),
    )
    db.add(order)
    await db.flush()
    db.add(OrderItem(
        order_id=order.id, product_variant_id=variant.id,
        product_title_snapshot="x", variant_spec_snapshot={},
        unit_price=500, quantity=1, fulfilled_qty=0, preorder_qty=0,
        is_returned=False,
    ))
    await db.commit()

    res = await client.post(f"{ORDERS_URL}/{order.id}/reorder")
    assert res.status_code == 409


@pytest.mark.asyncio
async def test_reorder_other_users_order_404(client, db):
    """他人訂單 → 404（不可洩漏存在）。"""
    owner = await _make_customer(client, db, email="reorder_owner@example.com")
    job = await _make_production_job(db)
    _, variant = await _make_product_and_variant(db, job.id, is_active=True)
    order = await _make_expired_order(db, owner, variant=variant)

    # 換另一個登入的使用者
    await _make_customer(client, db, email="reorder_other@example.com")
    await _login_customer(client, email="reorder_other@example.com")

    res = await client.post(f"{ORDERS_URL}/{order.id}/reorder")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_reorder_custom_item_quote_valid_and_expired(client, db):
    """客製品項：報價未過期 → 加入；報價已過期 → unavailable。"""
    import uuid as _uuid
    from datetime import UTC, datetime, timedelta

    from custom.models import (
        CustomRequest,
        CustomRequestStatusEnum,
        CustomRequestTypeEnum,
    )

    user = await _make_customer(client, db)
    await _login_customer(client)
    job = await _make_production_job(db)

    valid_cr = CustomRequest(
        user_id=user.id,
        request_type=CustomRequestTypeEnum.custom_photo,
        status=CustomRequestStatusEnum.quote_sent,
        quoted_price=800,
        quote_expires_at=datetime.now(UTC) + timedelta(days=3),
        quoted_production_job_id=job.id,
    )
    db.add(valid_cr)
    await db.flush()
    order = await _make_expired_order(
        db, user, custom_request=valid_cr, title="客製油畫"
    )

    res = await client.post(f"{ORDERS_URL}/{order.id}/reorder")
    assert res.status_code == 200
    assert res.json()["added_count"] == 1

    # 過期報價 → unavailable
    job2 = await _make_production_job(db)
    expired_cr = CustomRequest(
        user_id=user.id,
        request_type=CustomRequestTypeEnum.custom_photo,
        status=CustomRequestStatusEnum.quote_sent,
        quoted_price=800,
        quote_expires_at=datetime.now(UTC) - timedelta(days=1),
        quoted_production_job_id=job2.id,
    )
    db.add(expired_cr)
    await db.flush()
    order2 = Order(
        order_number=f"PL-{_uuid.uuid4().hex[:8]}",
        user_id=user.id, status=OrderStatusEnum.payment_expired,
        subtotal=800, discount_amount=0, shipping_fee=0, total=800,
        shipping_type="home", shipping_snapshot={}, created_at=datetime.now(UTC),
    )
    db.add(order2)
    await db.flush()
    db.add(OrderItem(
        order_id=order2.id, custom_request_id=expired_cr.id,
        product_title_snapshot="客製油畫(過期報價)", variant_spec_snapshot={},
        unit_price=800, quantity=1, fulfilled_qty=0, preorder_qty=0,
        is_returned=False,
    ))
    await db.commit()

    res2 = await client.post(f"{ORDERS_URL}/{order2.id}/reorder")
    assert res2.status_code == 200
    body2 = res2.json()
    assert body2["unavailable_count"] == 1
    # 客製報價過期應帶 code 與 custom_request_id，供前端引導重新申請
    u = body2["unavailable"][0]
    assert u["code"] == "QUOTE_EXPIRED"
    assert u["custom_request_id"] == str(expired_cr.id)


@pytest.mark.asyncio
async def test_reorder_unauthenticated_401(client, db):
    """未登入呼叫 reorder → 401。"""
    owner = await _make_customer(client, db, email="reorder_anon@example.com")
    job = await _make_production_job(db)
    _, variant = await _make_product_and_variant(db, job.id, is_active=True)
    order = await _make_expired_order(db, owner, variant=variant)

    client.cookies.clear()
    res = await client.post(f"{ORDERS_URL}/{order.id}/reorder")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_reorder_pending_past_deadline_expires_and_readds(client, db):
    """pending_payment 但付款期限已過（Celery 尚未翻狀態）→ 主動過期 + 加回購物車。"""
    import uuid as _uuid
    from datetime import UTC, datetime, timedelta

    user = await _make_customer(client, db)
    await _login_customer(client)
    job = await _make_production_job(db)
    _, variant = await _make_product_and_variant(db, job.id, is_active=True)

    order = Order(
        order_number=f"PL-{_uuid.uuid4().hex[:8]}",
        user_id=user.id, status=OrderStatusEnum.pending_payment,
        subtotal=500, discount_amount=0, shipping_fee=0, total=500,
        shipping_type="home", shipping_snapshot={},
        payment_deadline=datetime.now(UTC) - timedelta(hours=1),
        created_at=datetime.now(UTC) - timedelta(hours=49),
    )
    db.add(order)
    await db.flush()
    db.add(OrderItem(
        order_id=order.id, product_variant_id=variant.id,
        product_title_snapshot="過期前訂單", variant_spec_snapshot={},
        unit_price=500, quantity=1, fulfilled_qty=0, preorder_qty=0,
        is_returned=False,
    ))
    await db.commit()

    res = await client.post(f"{ORDERS_URL}/{order.id}/reorder")
    assert res.status_code == 200
    assert res.json()["added_count"] == 1

    # 原訂單應已被就地標記為 payment_expired
    await db.refresh(order)
    assert order.status == OrderStatusEnum.payment_expired

    cart = (await client.get(CART_URL)).json()
    assert any(item["variant_id"] == str(variant.id) for item in cart["items"])


@pytest.mark.asyncio
async def test_reorder_pending_within_deadline_409(client, db):
    """pending_payment 且付款期限未過 → 不可重新下單，回 409。"""
    import uuid as _uuid
    from datetime import UTC, datetime, timedelta

    user = await _make_customer(client, db)
    await _login_customer(client)
    job = await _make_production_job(db)
    _, variant = await _make_product_and_variant(db, job.id, is_active=True)

    order = Order(
        order_number=f"PL-{_uuid.uuid4().hex[:8]}",
        user_id=user.id, status=OrderStatusEnum.pending_payment,
        subtotal=500, discount_amount=0, shipping_fee=0, total=500,
        shipping_type="home", shipping_snapshot={},
        payment_deadline=datetime.now(UTC) + timedelta(hours=10),
        created_at=datetime.now(UTC),
    )
    db.add(order)
    await db.flush()
    db.add(OrderItem(
        order_id=order.id, product_variant_id=variant.id,
        product_title_snapshot="未過期", variant_spec_snapshot={},
        unit_price=500, quantity=1, fulfilled_qty=0, preorder_qty=0,
        is_returned=False,
    ))
    await db.commit()

    res = await client.post(f"{ORDERS_URL}/{order.id}/reorder")
    assert res.status_code == 409


@pytest.mark.asyncio
async def test_reorder_incomplete_item_unavailable(client, db):
    """order_item 既無變體也無客製 → 列為「品項資料不完整」unavailable。"""
    user = await _make_customer(client, db)
    await _login_customer(client)
    order = await _make_expired_order(db, user, title="不完整品項")

    res = await client.post(f"{ORDERS_URL}/{order.id}/reorder")
    assert res.status_code == 200
    body = res.json()
    assert body["added_count"] == 0
    assert body["unavailable_count"] == 1
    assert body["unavailable"][0]["reason"] == "品項資料不完整"


# ── Revive (逾期訂單重新申請付款) ─────────────────────────────────────────────


async def _make_custom_request(db, user, *, status, job_id=None, expires_in_h=48,
                               order_id=None):
    from datetime import UTC, datetime, timedelta

    from custom.models import CustomRequest, CustomRequestTypeEnum

    cr = CustomRequest(
        user_id=user.id,
        request_type=CustomRequestTypeEnum.custom_photo,
        status=status,
        quoted_price=800,
        quote_expires_at=datetime.now(UTC) + timedelta(hours=expires_in_h),
        quoted_production_job_id=job_id,
        order_id=order_id,
    )
    db.add(cr)
    await db.flush()
    return cr


@pytest.mark.asyncio
async def test_revive_payment_expired_custom_rebinds_and_repayable(client, db):
    """逾期客製訂單重新申請付款：復活成 pending_payment、客製重新綁定 quote_confirmed。"""
    from custom.models import CustomRequest, CustomRequestStatusEnum

    user = await _make_customer(client, db)
    await _login_customer(client)
    job = await _make_production_job(db)
    # 模擬舊邏輯把客製退回 quote_sent + 解綁的壞掉狀態
    cr = await _make_custom_request(
        db, user, status=CustomRequestStatusEnum.quote_sent,
        job_id=job.id, expires_in_h=-1, order_id=None,
    )
    order = await _make_expired_order(db, user, custom_request=cr, title="客製作品")

    res = await client.post(f"{ORDERS_URL}/{order.id}/revive")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "pending_payment"
    assert body["discount_dropped"] is False

    await db.refresh(order)
    assert order.status == OrderStatusEnum.pending_payment
    assert order.payment_deadline is not None

    refreshed_cr = (await db.execute(
        select(CustomRequest).where(CustomRequest.id == cr.id)
    )).scalar_one()
    assert refreshed_cr.status == CustomRequestStatusEnum.quote_confirmed
    assert refreshed_cr.order_id == order.id


@pytest.mark.asyncio
async def test_revive_pending_past_deadline(client, db):
    """pending_payment 但付款期限已過（Celery 沒翻）→ 可直接復活。"""
    import uuid as _uuid
    from datetime import UTC, datetime, timedelta

    user = await _make_customer(client, db)
    await _login_customer(client)
    job = await _make_production_job(db)
    _, variant = await _make_product_and_variant(db, job.id, is_active=True)

    order = Order(
        order_number=f"PL-{_uuid.uuid4().hex[:8]}",
        user_id=user.id, status=OrderStatusEnum.pending_payment,
        subtotal=500, discount_amount=0, shipping_fee=70, total=570,
        shipping_type="home", shipping_snapshot={},
        payment_deadline=datetime.now(UTC) - timedelta(hours=1),
        created_at=datetime.now(UTC) - timedelta(hours=49),
    )
    db.add(order)
    await db.flush()
    db.add(OrderItem(
        order_id=order.id, product_variant_id=variant.id,
        product_title_snapshot="x", variant_spec_snapshot={},
        unit_price=500, quantity=1, fulfilled_qty=0, preorder_qty=0,
        is_returned=False,
    ))
    await db.commit()

    res = await client.post(f"{ORDERS_URL}/{order.id}/revive")
    assert res.status_code == 200
    await db.refresh(order)
    assert order.status == OrderStatusEnum.pending_payment
    assert order.payment_deadline > datetime.now(UTC)


@pytest.mark.asyncio
async def test_revive_non_expired_and_cancelled_409(client, db):
    """paid 或 cancelled 訂單不可復活 → 409。"""
    import uuid as _uuid
    from datetime import UTC, datetime

    user = await _make_customer(client, db)
    await _login_customer(client)

    for status in (OrderStatusEnum.paid, OrderStatusEnum.cancelled):
        order = Order(
            order_number=f"PL-{_uuid.uuid4().hex[:8]}",
            user_id=user.id, status=status,
            subtotal=500, discount_amount=0, shipping_fee=0, total=500,
            shipping_type="home", shipping_snapshot={},
            created_at=datetime.now(UTC),
        )
        db.add(order)
        await db.commit()
        res = await client.post(f"{ORDERS_URL}/{order.id}/revive")
        assert res.status_code == 409


@pytest.mark.asyncio
async def test_revive_other_users_order_404(client, db):
    owner = await _make_customer(client, db, email="revive_owner@example.com")
    job = await _make_production_job(db)
    _, variant = await _make_product_and_variant(db, job.id, is_active=True)
    order = await _make_expired_order(db, owner, variant=variant)

    await _make_customer(client, db, email="revive_other@example.com")
    await _login_customer(client, email="revive_other@example.com")
    res = await client.post(f"{ORDERS_URL}/{order.id}/revive")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_revive_expired_coupon_dropped(client, db):
    """原折扣券已過期 → discount_dropped、total 重算為 subtotal+shipping。"""
    import uuid as _uuid
    from datetime import UTC, datetime, timedelta

    from discount.models import (
        CouponConfig,
        CouponTypeEnum,
        DiscountTypeEnum,
        UserCoupon,
    )

    user = await _make_customer(client, db)
    await _login_customer(client)
    job = await _make_production_job(db)
    _, variant = await _make_product_and_variant(db, job.id, is_active=True)

    config = CouponConfig(
        coupon_type=CouponTypeEnum.manual,
        discount_type=DiscountTypeEnum.fixed,
        discount_value=100,
        min_purchase=0,
    )
    db.add(config)
    await db.flush()

    # 已過期的 user coupon（逾期時被 revert 設回 is_used=False）
    coupon = UserCoupon(
        user_id=user.id,
        coupon_config_id=config.id,
        discount_type=DiscountTypeEnum.fixed,
        discount_value=100,
        min_purchase=0,
        is_used=False,
        expires_at=datetime.now(UTC) - timedelta(days=1),
    )
    db.add(coupon)
    await db.flush()

    order = Order(
        order_number=f"PL-{_uuid.uuid4().hex[:8]}",
        user_id=user.id, status=OrderStatusEnum.payment_expired,
        subtotal=500, discount_amount=100, shipping_fee=70, total=470,
        shipping_type="home", shipping_snapshot={},
        user_coupon_id=coupon.id,
        created_at=datetime.now(UTC),
    )
    db.add(order)
    await db.flush()
    db.add(OrderItem(
        order_id=order.id, product_variant_id=variant.id,
        product_title_snapshot="x", variant_spec_snapshot={},
        unit_price=500, quantity=1, fulfilled_qty=0, preorder_qty=0,
        is_returned=False,
    ))
    await db.commit()

    res = await client.post(f"{ORDERS_URL}/{order.id}/revive")
    assert res.status_code == 200
    body = res.json()
    assert body["discount_dropped"] is True
    assert body["total"] == 570.0  # 500 + 70，折扣去除

    await db.refresh(order)
    assert order.user_coupon_id is None
    assert float(order.discount_amount) == 0


@pytest.mark.asyncio
async def test_update_payment_method_switch(client, db):
    """待付款訂單可切換付款方式 ecpay ↔ bank_transfer；非待付款 → 400。"""
    import uuid as _uuid
    from datetime import UTC, datetime, timedelta

    user = await _make_customer(client, db)
    await _login_customer(client)
    job = await _make_production_job(db)
    _, variant = await _make_product_and_variant(db, job.id, is_active=True)

    def _new_order(status, method):
        return Order(
            order_number=f"PL-{_uuid.uuid4().hex[:8]}",
            user_id=user.id, status=status,
            subtotal=500, discount_amount=0, shipping_fee=70, total=570,
            shipping_type="home", shipping_snapshot={},
            payment_method=method,
            payment_deadline=datetime.now(UTC) + timedelta(hours=10),
            created_at=datetime.now(UTC),
        )

    order = _new_order(OrderStatusEnum.pending_payment, "ecpay")
    db.add(order)
    await db.flush()
    db.add(OrderItem(
        order_id=order.id, product_variant_id=variant.id,
        product_title_snapshot="x", variant_spec_snapshot={},
        unit_price=500, quantity=1, fulfilled_qty=0, preorder_qty=0,
        is_returned=False,
    ))
    await db.commit()

    res = await client.patch(
        f"{ORDERS_URL}/{order.id}/payment-method",
        json={"payment_method": "bank_transfer"},
    )
    assert res.status_code == 200
    assert res.json()["payment_method"] == "bank_transfer"

    # 切回 ecpay
    res2 = await client.patch(
        f"{ORDERS_URL}/{order.id}/payment-method",
        json={"payment_method": "ecpay"},
    )
    assert res2.status_code == 200
    assert res2.json()["payment_method"] == "ecpay"

    # 已付款訂單不可切換 → 400
    paid = _new_order(OrderStatusEnum.paid, "ecpay")
    db.add(paid)
    await db.commit()
    res3 = await client.patch(
        f"{ORDERS_URL}/{paid.id}/payment-method",
        json={"payment_method": "bank_transfer"},
    )
    assert res3.status_code == 400

    # payment_expired 不可切換 → 400（需先 revive）
    exp = _new_order(OrderStatusEnum.payment_expired, "ecpay")
    db.add(exp)
    await db.commit()
    res4 = await client.patch(
        f"{ORDERS_URL}/{exp.id}/payment-method",
        json={"payment_method": "bank_transfer"},
    )
    assert res4.status_code == 400


@pytest.mark.asyncio
async def test_update_payment_method_expires_txn_and_guards(client, db):
    """切離 ecpay 時作廢未繳費取號交易；他人訂單 404；相同方式 no-op。"""
    from orders.models import PaymentTransaction, PaymentTransactionStatusEnum

    owner = await _make_customer(client, db, email="switch_owner@example.com")
    await _login_customer(client, email="switch_owner@example.com")
    import uuid as _uuid
    from datetime import UTC, datetime, timedelta

    order = Order(
        order_number=f"PL-{_uuid.uuid4().hex[:8]}",
        user_id=owner.id, status=OrderStatusEnum.pending_payment,
        subtotal=500, discount_amount=0, shipping_fee=70, total=570,
        shipping_type="home", shipping_snapshot={}, payment_method="ecpay",
        payment_deadline=datetime.now(UTC) + timedelta(hours=10),
        created_at=datetime.now(UTC),
    )
    db.add(order)
    await db.flush()
    txn = PaymentTransaction(
        order_id=order.id, merchant_trade_no=f"PAY{_uuid.uuid4().hex[:12].upper()}",
        amount=570, status=PaymentTransactionStatusEnum.awaiting_atm,
    )
    db.add(txn)
    await db.commit()

    # 切到銀行轉帳 → 取號交易應被標 expired
    res = await client.patch(
        f"{ORDERS_URL}/{order.id}/payment-method",
        json={"payment_method": "bank_transfer"},
    )
    assert res.status_code == 200
    await db.refresh(txn)
    assert txn.status == PaymentTransactionStatusEnum.expired

    # 相同方式 no-op（再切 bank_transfer）→ 200
    res_noop = await client.patch(
        f"{ORDERS_URL}/{order.id}/payment-method",
        json={"payment_method": "bank_transfer"},
    )
    assert res_noop.status_code == 200

    # 他人訂單 → 404
    await _make_customer(client, db, email="switch_other@example.com")
    await _login_customer(client, email="switch_other@example.com")
    res404 = await client.patch(
        f"{ORDERS_URL}/{order.id}/payment-method",
        json={"payment_method": "ecpay"},
    )
    assert res404.status_code == 404


@pytest.mark.asyncio
async def test_revive_promo_discount_dropped(client, db):
    """促銷碼折扣（user_coupon_id 為 None）→ revive 一律去除折扣、重算 total，
    不沿用折扣（避免名額回收漏洞 + 客戶白享折扣）。"""
    import uuid as _uuid
    from datetime import UTC, datetime

    user = await _make_customer(client, db)
    await _login_customer(client)
    job = await _make_production_job(db)
    _, variant = await _make_product_and_variant(db, job.id, is_active=True)

    # 模擬促銷碼訂單：有折扣金額但 user_coupon_id 為 None（promo 走 public_code 不記在此欄）
    order = Order(
        order_number=f"PL-{_uuid.uuid4().hex[:8]}",
        user_id=user.id, status=OrderStatusEnum.payment_expired,
        subtotal=500, discount_amount=80, shipping_fee=70, total=490,
        discount_source="coupon", user_coupon_id=None,
        shipping_type="home", shipping_snapshot={},
        created_at=datetime.now(UTC),
    )
    db.add(order)
    await db.flush()
    db.add(OrderItem(
        order_id=order.id, product_variant_id=variant.id,
        product_title_snapshot="x", variant_spec_snapshot={},
        unit_price=500, quantity=1, fulfilled_qty=0, preorder_qty=0,
        is_returned=False,
    ))
    await db.commit()

    res = await client.post(f"{ORDERS_URL}/{order.id}/revive")
    assert res.status_code == 200
    body = res.json()
    assert body["discount_dropped"] is True
    assert body["total"] == 570.0

    await db.refresh(order)
    assert float(order.discount_amount) == 0
    assert order.discount_source is None


@pytest.mark.asyncio
async def test_revive_valid_coupon_reclaimed(client, db):
    """會員券仍有效 → revive 重新搶回（is_used=True 綁回訂單）、沿用原折扣、total 不變。"""
    import uuid as _uuid
    from datetime import UTC, datetime, timedelta

    from discount.models import (
        CouponConfig,
        CouponTypeEnum,
        DiscountTypeEnum,
        UserCoupon,
    )

    user = await _make_customer(client, db)
    await _login_customer(client)
    job = await _make_production_job(db)
    _, variant = await _make_product_and_variant(db, job.id, is_active=True)

    config = CouponConfig(
        coupon_type=CouponTypeEnum.manual,
        discount_type=DiscountTypeEnum.fixed,
        discount_value=100, min_purchase=0,
    )
    db.add(config)
    await db.flush()
    # 逾期時 revert_coupon 把券設回 is_used=False；仍未過期
    coupon = UserCoupon(
        user_id=user.id, coupon_config_id=config.id,
        discount_type=DiscountTypeEnum.fixed, discount_value=100, min_purchase=0,
        is_used=False, expires_at=datetime.now(UTC) + timedelta(days=5),
    )
    db.add(coupon)
    await db.flush()

    order = Order(
        order_number=f"PL-{_uuid.uuid4().hex[:8]}",
        user_id=user.id, status=OrderStatusEnum.payment_expired,
        subtotal=500, discount_amount=100, shipping_fee=70, total=470,
        discount_source="coupon", user_coupon_id=coupon.id,
        shipping_type="home", shipping_snapshot={},
        created_at=datetime.now(UTC),
    )
    db.add(order)
    await db.flush()
    db.add(OrderItem(
        order_id=order.id, product_variant_id=variant.id,
        product_title_snapshot="x", variant_spec_snapshot={},
        unit_price=500, quantity=1, fulfilled_qty=0, preorder_qty=0,
        is_returned=False,
    ))
    await db.commit()

    res = await client.post(f"{ORDERS_URL}/{order.id}/revive")
    assert res.status_code == 200
    body = res.json()
    assert body["discount_dropped"] is False
    assert body["total"] == 470.0  # 沿用原折扣

    refreshed_coupon = (await db.execute(
        select(UserCoupon).where(UserCoupon.id == coupon.id)
    )).scalar_one()
    assert refreshed_coupon.is_used is True
    assert refreshed_coupon.used_in_order_id == order.id


@pytest.mark.asyncio
async def test_expire_keeps_custom_bound_but_cancel_reverts(client, db):
    """expire_pending_order 保留客製 quote_confirmed；cancel_order 則退回 quote_sent。"""
    import uuid as _uuid
    from datetime import UTC, datetime, timedelta

    from custom.models import CustomRequest, CustomRequestStatusEnum
    from orders.service import cancel_order, expire_pending_order

    user = await _make_customer(client, db)
    await _seed_system_settings(db)
    job = await _make_production_job(db)

    async def _build_order():
        order = Order(
            order_number=f"PL-{_uuid.uuid4().hex[:8]}",
            user_id=user.id, status=OrderStatusEnum.pending_payment,
            subtotal=800, discount_amount=0, shipping_fee=0, total=800,
            shipping_type="home", shipping_snapshot={},
            payment_deadline=datetime.now(UTC) - timedelta(hours=1),
            created_at=datetime.now(UTC) - timedelta(hours=49),
        )
        db.add(order)
        await db.flush()
        cr = await _make_custom_request(
            db, user, status=CustomRequestStatusEnum.quote_confirmed,
            job_id=job.id, order_id=order.id,
        )
        db.add(OrderItem(
            order_id=order.id, custom_request_id=cr.id,
            product_title_snapshot="客製", variant_spec_snapshot={},
            unit_price=800, quantity=1, fulfilled_qty=0, preorder_qty=0,
            is_returned=False,
        ))
        await db.commit()
        return order, cr

    # expire → 保留 quote_confirmed
    order1, cr1 = await _build_order()
    await expire_pending_order(db, order1)
    await db.commit()
    cr1_db = (await db.execute(
        select(CustomRequest).where(CustomRequest.id == cr1.id)
    )).scalar_one()
    assert cr1_db.status == CustomRequestStatusEnum.quote_confirmed
    assert cr1_db.order_id == order1.id

    # cancel → 退回 quote_sent + 解綁
    order2, cr2 = await _build_order()
    await cancel_order(db, user.id, order2.id, "test")
    cr2_db = (await db.execute(
        select(CustomRequest).where(CustomRequest.id == cr2.id)
    )).scalar_one()
    assert cr2_db.status == CustomRequestStatusEnum.quote_sent
    assert cr2_db.order_id is None
