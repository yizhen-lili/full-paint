"""Module 23 階段2 — ECpay PaymentInfoURL（ATM/超商取號）webhook 測試。"""
import uuid
from datetime import UTC, datetime, timedelta

import bcrypt
import pytest
from sqlalchemy import func, select

from auth.models import User
from orders.models import (
    Order,
    OrderItem,
    OrderStatusEnum,
    PaymentMethodEnum,
    PaymentTransaction,
    PaymentTransactionStatusEnum,
    ProductionProgress,
)
from payment import service

pytestmark = pytest.mark.asyncio


async def _make_order_with_txn(db, *, total=1260, deadline_hours=24):
    user = User(
        name="取號測試",
        email=f"atm_{uuid.uuid4().hex[:8]}@test.com",
        password_hash=bcrypt.hashpw(b"x", bcrypt.gensalt()).decode(),
        role="customer", is_active=True, is_email_verified=True,
    )
    db.add(user)
    await db.flush()
    order = Order(
        order_number=f"PL-ATM-{uuid.uuid4().hex[:8]}",
        user_id=user.id,
        status=OrderStatusEnum.pending_payment,
        subtotal=total, shipping_fee=0, total=total,
        shipping_type="home",
        shipping_snapshot={"recipient_name": "x", "phone": "0912345678"},
        payment_method=PaymentMethodEnum.ecpay,
        payment_deadline=datetime.now(UTC) + timedelta(hours=deadline_hours),
    )
    db.add(order)
    await db.flush()
    db.add(OrderItem(
        order_id=order.id, product_variant_id=None,
        product_title_snapshot="油畫模板", variant_spec_snapshot={},
        unit_price=total, quantity=1, fulfilled_qty=0, preorder_qty=1,
    ))
    txn = PaymentTransaction(
        order_id=order.id,
        merchant_trade_no=f"PAY{uuid.uuid4().hex[:12].upper()}",
        amount=service.charge_amount(order),
        status=PaymentTransactionStatusEnum.created,
    )
    db.add(txn)
    await db.commit()
    return user, order, txn


def _sign(params):
    params = {k: v for k, v in params.items() if k != "CheckMacValue"}
    params["CheckMacValue"] = service.calculate_check_mac_value(params)
    return params


async def _count_progress(db, order_id):
    return (await db.execute(
        select(func.count()).select_from(ProductionProgress)
        .join(OrderItem, ProductionProgress.order_item_id == OrderItem.id)
        .where(OrderItem.order_id == order_id)
    )).scalar()


async def test_atm_code_issued_stores_account(db):
    _, order, txn = await _make_order_with_txn(db)
    params = _sign({
        "MerchantID": "3002607",
        "MerchantTradeNo": txn.merchant_trade_no,
        "RtnCode": "2",  # ATM 取號成功
        "RtnMsg": "Get VirtualAccount Succeeded",
        "TradeNo": "EC" + uuid.uuid4().hex[:8].upper(),
        "PaymentType": "ATM_TAISHIN",
        "BankCode": "812",
        "vAccount": "9103522012345678",
        "ExpireDate": "2026/06/12",
    })

    result = await service.process_payment_info_webhook(db, params)

    assert result == "1|OK"
    txn_r = (await db.execute(
        select(PaymentTransaction).where(PaymentTransaction.id == txn.id)
    )).scalar_one()
    assert txn_r.status == PaymentTransactionStatusEnum.awaiting_atm
    assert txn_r.bank_code == "812"
    assert txn_r.vaccount == "9103522012345678"
    assert txn_r.expire_date is not None
    # 取號 ≠ 付款：訂單仍 pending_payment、不建 production_progress
    order_r = (await db.execute(select(Order).where(Order.id == order.id))).scalar_one()
    assert order_r.status == OrderStatusEnum.pending_payment
    assert await _count_progress(db, order.id) == 0


async def test_cvs_code_issued_stores_payment_no(db):
    _, order, txn = await _make_order_with_txn(db)
    params = _sign({
        "MerchantID": "3002607",
        "MerchantTradeNo": txn.merchant_trade_no,
        "RtnCode": "10100073",  # 超商代碼取號成功
        "RtnMsg": "Get CVS Code Succeeded",
        "PaymentType": "CVS_CVS",
        "PaymentNo": "LLL123456789",
        "ExpireDate": "2026/06/12 23:59:59",
    })

    result = await service.process_payment_info_webhook(db, params)

    assert result == "1|OK"
    txn_r = (await db.execute(
        select(PaymentTransaction).where(PaymentTransaction.id == txn.id)
    )).scalar_one()
    assert txn_r.status == PaymentTransactionStatusEnum.awaiting_atm
    assert txn_r.payment_no == "LLL123456789"


async def test_deadline_aligned_to_earlier_expire(db):
    # 訂單付款期限 5 天後；ExpireDate 設明天 → payment_deadline 應縮到 ExpireDate
    _, order, txn = await _make_order_with_txn(db, deadline_hours=120)
    tomorrow = (datetime.now(UTC) + timedelta(days=1)).strftime("%Y/%m/%d")
    params = _sign({
        "MerchantID": "3002607",
        "MerchantTradeNo": txn.merchant_trade_no,
        "RtnCode": "2",
        "BankCode": "812",
        "vAccount": "9103522099999999",
        "ExpireDate": tomorrow,
    })

    await service.process_payment_info_webhook(db, params)

    order_r = (await db.execute(select(Order).where(Order.id == order.id))).scalar_one()
    # deadline 已被縮短到 ExpireDate（< 原本 5 天）
    assert order_r.payment_deadline < datetime.now(UTC) + timedelta(days=5)


async def test_bad_mac_no_change(db):
    _, order, txn = await _make_order_with_txn(db)
    params = {
        "MerchantID": "3002607",
        "MerchantTradeNo": txn.merchant_trade_no,
        "RtnCode": "2",
        "vAccount": "9103522012345678",
        "CheckMacValue": "BADMAC",
    }

    result = await service.process_payment_info_webhook(db, params)

    assert result == "0|CheckMacValueError"
    txn_r = (await db.execute(
        select(PaymentTransaction).where(PaymentTransaction.id == txn.id)
    )).scalar_one()
    assert txn_r.status == PaymentTransactionStatusEnum.created
    assert txn_r.vaccount is None


async def test_unknown_trade_no(db):
    _, _, txn = await _make_order_with_txn(db)
    params = _sign({
        "MerchantID": "3002607",
        "MerchantTradeNo": "PAYNOTEXIST",
        "RtnCode": "2",
        "vAccount": "9103522012345678",
    })

    result = await service.process_payment_info_webhook(db, params)
    assert result == "0|OrderNotFound"


async def test_code_issued_resend_idempotent(db):
    """同一取號通知重送 → 狀態維持 awaiting_atm、帳號不被破壞、不報錯。"""
    _, order, txn = await _make_order_with_txn(db)
    params = _sign({
        "MerchantID": "3002607",
        "MerchantTradeNo": txn.merchant_trade_no,
        "RtnCode": "2",
        "BankCode": "812",
        "vAccount": "9103522012345678",
        "ExpireDate": "2026/06/12",
    })

    r1 = await service.process_payment_info_webhook(db, params)
    r2 = await service.process_payment_info_webhook(db, params)

    assert r1 == "1|OK" and r2 == "1|OK"
    txn_r = (await db.execute(
        select(PaymentTransaction).where(PaymentTransaction.id == txn.id)
    )).scalar_one()
    assert txn_r.status == PaymentTransactionStatusEnum.awaiting_atm
    assert txn_r.vaccount == "9103522012345678"


async def test_code_issued_does_not_downgrade_paid(db):
    """已 paid 的交易收到遲到的取號通知 → 不回退成 awaiting_atm。"""
    _, order, txn = await _make_order_with_txn(db)
    txn.status = PaymentTransactionStatusEnum.paid
    await db.commit()
    params = _sign({
        "MerchantID": "3002607",
        "MerchantTradeNo": txn.merchant_trade_no,
        "RtnCode": "2",
        "BankCode": "812",
        "vAccount": "9103522012345678",
        "ExpireDate": "2026/06/12",
    })

    await service.process_payment_info_webhook(db, params)

    txn_r = (await db.execute(
        select(PaymentTransaction).where(PaymentTransaction.id == txn.id)
    )).scalar_one()
    assert txn_r.status == PaymentTransactionStatusEnum.paid


async def test_mark_awaiting_transactions_expired(db):
    """逾期掃描：awaiting_atm 交易標 expired，created/paid 不動。"""
    _, order, txn = await _make_order_with_txn(db)
    txn.status = PaymentTransactionStatusEnum.awaiting_atm
    await db.commit()

    await service.mark_awaiting_transactions_expired(db, order.id)
    await db.commit()

    txn_r = (await db.execute(
        select(PaymentTransaction).where(PaymentTransaction.id == txn.id)
    )).scalar_one()
    assert txn_r.status == PaymentTransactionStatusEnum.expired
