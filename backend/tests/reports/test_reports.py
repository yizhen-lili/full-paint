"""Module 14 — Reports tests (sales report)."""

import bcrypt
import pytest

from auth.models import User
from orders.models import Order, OrderStatusEnum

ADMIN_EMAIL = "report_admin@test.com"
ADMIN_PASS = "adminpass123"
URL = "/api/v1/admin/reports/sales"


async def _make_admin(db):
    admin = User(
        name="ReportAdmin",
        email=ADMIN_EMAIL,
        password_hash=bcrypt.hashpw(ADMIN_PASS.encode(), bcrypt.gensalt()).decode(),
        role="admin",
        is_active=True,
        is_email_verified=True,
    )
    db.add(admin)
    await db.commit()
    return admin


async def _login_admin(client):
    res = await client.post("/api/v1/admin/auth/login", json={
        "email": ADMIN_EMAIL, "password": ADMIN_PASS,
    })
    if "access_token" in res.cookies:
        client.cookies.set("access_token", res.cookies["access_token"])


async def _make_user(db, email="ord@test.com", name="OrdUser"):
    user = User(
        name=name,
        email=email,
        password_hash=bcrypt.hashpw(b"x", bcrypt.gensalt()).decode(),
        role="customer",
        is_active=True,
        is_email_verified=True,
    )
    db.add(user)
    await db.commit()
    return user


async def _make_order(db, user_id, *, status=OrderStatusEnum.completed, total=1000, refund=None):
    import uuid
    o = Order(
        order_number=f"PL-{uuid.uuid4().hex[:8]}",
        user_id=user_id,
        status=status,
        subtotal=total,
        discount_amount=0,
        shipping_fee=0,
        total=total,
        shipping_type="home",
        shipping_snapshot={},
        refund_amount=refund,
    )
    db.add(o)
    await db.commit()
    return o


@pytest.mark.asyncio
async def test_sales_empty(client, db):
    await _make_admin(db)
    await _login_admin(client)
    res = await client.get(URL)
    assert res.status_code == 200
    body = res.json()
    assert body["total_orders"] == 0
    assert body["total_revenue"] == 0.0


@pytest.mark.asyncio
async def test_sales_completed_only(client, db):
    await _make_admin(db)
    user = await _make_user(db)
    await _make_order(db, user.id, total=1000)  # completed
    await _make_order(db, user.id, total=500, status=OrderStatusEnum.pending_payment)
    await _login_admin(client)
    res = await client.get(URL)
    body = res.json()
    assert body["total_orders"] == 1
    assert body["total_revenue"] == 1000.0


@pytest.mark.asyncio
async def test_sales_partial_refund_deducted(client, db):
    """Partial refund: status=partially_refunded, revenue = total - refund_amount."""
    await _make_admin(db)
    user = await _make_user(db)
    await _make_order(
        db, user.id, total=1000, refund=300,
        status=OrderStatusEnum.partially_refunded,
    )
    await _login_admin(client)
    res = await client.get(URL)
    body = res.json()
    assert body["total_orders"] == 1
    assert body["total_revenue"] == 700.0


@pytest.mark.asyncio
async def test_sales_full_refund_excluded(client, db):
    """Full refund: status=refunded, must be excluded from sales report."""
    await _make_admin(db)
    user = await _make_user(db)
    await _make_order(
        db, user.id, total=1000, refund=1000, status=OrderStatusEnum.refunded,
    )
    await _make_order(db, user.id, total=500)
    await _login_admin(client)
    res = await client.get(URL)
    body = res.json()
    assert body["total_orders"] == 1
    assert body["total_revenue"] == 500.0


@pytest.mark.asyncio
async def test_sales_date_filter(client, db):
    """date_from / date_to filters scope query to created_at range."""
    from datetime import UTC, datetime
    await _make_admin(db)
    user = await _make_user(db)
    o_old = await _make_order(db, user.id, total=300)
    o_new = await _make_order(db, user.id, total=700)
    o_old.created_at = datetime(2026, 4, 20, 10, 0, tzinfo=UTC)
    o_new.created_at = datetime(2026, 4, 25, 10, 0, tzinfo=UTC)
    await db.commit()

    await _login_admin(client)
    res = await client.get(f"{URL}?date_from=2026-04-22")
    body = res.json()
    assert body["total_orders"] == 1
    assert body["total_revenue"] == 700.0

    res = await client.get(f"{URL}?date_to=2026-04-22")
    body = res.json()
    assert body["total_orders"] == 1
    assert body["total_revenue"] == 300.0


@pytest.mark.asyncio
async def test_sales_non_admin_blocked(client, db):
    res = await client.get(URL)
    assert res.status_code == 401
