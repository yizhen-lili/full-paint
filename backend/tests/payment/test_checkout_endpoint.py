"""Module 23 — checkout endpoint（導向付款頁 / 重新付款）整合測試。"""
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from auth.models import User
from orders.models import (
    Order,
    OrderItem,
    OrderStatusEnum,
    PaymentMethodEnum,
    PaymentTransaction,
)

pytestmark = pytest.mark.asyncio

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"

CUST = {"name": "結帳測試", "email": "checkout@example.com", "password": "testpass123"}


async def _make_customer_and_login(client, db):
    await client.post(REGISTER_URL, json=CUST)
    user = (await db.execute(select(User).where(User.email == CUST["email"]))).scalar_one()
    user.is_email_verified = True
    await db.commit()
    res = await client.post(LOGIN_URL, json={"email": CUST["email"], "password": CUST["password"]})
    if "access_token" in res.cookies:
        client.cookies.set("access_token", res.cookies["access_token"])
    return user


async def _make_order(db, user, *, status=OrderStatusEnum.pending_payment,
                      method=PaymentMethodEnum.ecpay, deadline_hours=24):
    order = Order(
        order_number=f"PL-CO-{uuid.uuid4().hex[:8]}",
        user_id=user.id,
        status=status,
        subtotal=1260,
        shipping_fee=0,
        total=1260,
        shipping_type="home",
        shipping_snapshot={"recipient_name": "x", "phone": "0912345678"},
        payment_method=method,
        payment_deadline=datetime.now(UTC) + timedelta(hours=deadline_hours),
    )
    db.add(order)
    await db.flush()
    db.add(OrderItem(
        order_id=order.id, product_variant_id=None,
        product_title_snapshot="油畫模板", variant_spec_snapshot={},
        unit_price=1260, quantity=1, fulfilled_qty=1, preorder_qty=0,
    ))
    await db.commit()
    return order


async def test_checkout_dry_run_creates_transaction(client, db):
    user = await _make_customer_and_login(client, db)
    order = await _make_order(db, user)

    res = await client.get(f"/api/v1/payment/ecpay/checkout/{order.id}")

    assert res.status_code == 200
    assert "data-dry-run='1'" in res.text  # conftest 設 dry_run
    # 建了一筆 transaction
    txns = (await db.execute(
        select(PaymentTransaction).where(PaymentTransaction.order_id == order.id)
    )).scalars().all()
    assert len(txns) == 1
    assert txns[0].merchant_trade_no in res.text


async def test_checkout_retry_creates_new_transaction(client, db):
    user = await _make_customer_and_login(client, db)
    order = await _make_order(db, user)

    await client.get(f"/api/v1/payment/ecpay/checkout/{order.id}")
    await client.get(f"/api/v1/payment/ecpay/checkout/{order.id}")

    txns = (await db.execute(
        select(PaymentTransaction).where(PaymentTransaction.order_id == order.id)
    )).scalars().all()
    assert len(txns) == 2  # 每次重試各一筆，單號不重用
    assert txns[0].merchant_trade_no != txns[1].merchant_trade_no


async def test_checkout_rejects_paid_order(client, db):
    user = await _make_customer_and_login(client, db)
    order = await _make_order(db, user, status=OrderStatusEnum.paid)

    res = await client.get(f"/api/v1/payment/ecpay/checkout/{order.id}")
    assert res.status_code == 409


async def test_checkout_rejects_bank_transfer_order(client, db):
    user = await _make_customer_and_login(client, db)
    order = await _make_order(db, user, method=PaymentMethodEnum.bank_transfer)

    res = await client.get(f"/api/v1/payment/ecpay/checkout/{order.id}")
    assert res.status_code == 409


async def test_checkout_rejects_expired_deadline(client, db):
    user = await _make_customer_and_login(client, db)
    order = await _make_order(db, user, deadline_hours=-1)  # 已過期

    res = await client.get(f"/api/v1/payment/ecpay/checkout/{order.id}")
    assert res.status_code == 409


async def test_checkout_other_users_order_404(client, db):
    await _make_customer_and_login(client, db)
    other = User(
        name="別人", email="other@example.com",
        password_hash="x", role="customer", is_active=True, is_email_verified=True,
    )
    db.add(other)
    await db.flush()
    order = await _make_order(db, other)

    res = await client.get(f"/api/v1/payment/ecpay/checkout/{order.id}")
    assert res.status_code == 404


async def test_checkout_requires_auth(client, db):
    user = await _make_customer_and_login(client, db)
    order = await _make_order(db, user)
    client.cookies.clear()

    res = await client.get(f"/api/v1/payment/ecpay/checkout/{order.id}")
    assert res.status_code in (401, 403)
